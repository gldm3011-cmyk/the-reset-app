"""Inscripciones a rutas y programas de acompañamiento: calendario, avance, observaciones, registros y pausas."""
from __future__ import annotations

import json
from datetime import date, timedelta

from . import db
from .programas import PROGRAMAS, SEMANAS, programa

DIAS_SEMANA = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
MOMENTOS = ["Mañana", "Tarde", "Noche"]
MODALIDAD_PREF = ["Virtual", "Presencial", "Indiferente"]
TIPOS_REGISTRO = {"comida": "Comida", "habito": "Hábito", "actividad": "Actividad"}


def _hoy() -> date:
    return date.today()


# ------------------------------------------------------------------ inscripción
def inscribir(con, usuario_id: int, programa_id: str, fecha_inicio=None, objetivos=None, preferencias=None) -> int:
    if programa_id not in PROGRAMAS:
        raise db.ValidationError("Programa no válido.")
    u = db.obtener_usuario(con, usuario_id)
    if not u:
        raise db.ValidationError("Usuario no encontrado.")
    f = date.fromisoformat(db._fecha(fecha_inicio or _hoy(), "Fecha de inicio"))
    if f < _hoy() - timedelta(days=28) or f > _hoy() + timedelta(days=30):
        raise db.ValidationError("La fecha de inicio debe estar entre las últimas 4 semanas y los próximos 30 días.")
    objetivos = [o for o in (objetivos or []) if o]
    if not objetivos:
        raise db.ValidationError("Elija al menos un objetivo para el programa.")
    pref = preferencias or {}
    if any(d not in DIAS_SEMANA for d in pref.get("dias", [])):
        raise db.ValidationError("Días preferidos no válidos.")
    if pref.get("momento") and pref["momento"] not in MOMENTOS:
        raise db.ValidationError("Momento del día no válido.")
    if vigente(con, usuario_id, programa_id):
        raise db.ValidationError("Ya tiene este programa activo o en pausa. Reanúdelo en lugar de inscribirse de nuevo.")
    try:
        with db.tx(con):
            cur = con.execute("""INSERT INTO inscripciones (usuario_id, programa_id, estado, fecha_inicio, objetivos, preferencias, medicamento_declarado, creado, actualizado)
                                 VALUES (?,?,?,?,?,?,?,?,?)""",
                              (usuario_id, programa_id, "activo", f.isoformat(), json.dumps(objetivos, ensure_ascii=False),
                               json.dumps(pref, ensure_ascii=False), u["medicamento_declarado"], db.now(), db.now()))
            iid = cur.lastrowid
            con.executemany("""INSERT INTO plan_actividades (inscripcion_id, orden, semana, dia, fecha, categoria, titulo, descripcion, accion)
                               VALUES (?,?,?,?,?,?,?,?,?)""",
                            [(iid, i, s, d, (f + timedelta(days=(s - 1) * 7 + d - 1)).isoformat(), cat, t, desc, acc)
                             for i, (s, d, cat, t, desc, acc) in enumerate(programa(programa_id)["actividades"])])
    except db.IntegrityError:
        raise db.ValidationError("Ya tiene este programa activo o en pausa.")
    return iid


def vigente(con, usuario_id, programa_id):
    r = con.execute("SELECT * FROM inscripciones WHERE usuario_id=? AND programa_id=? AND estado IN ('activo','pausado')", (usuario_id, programa_id)).fetchone()
    return _insc(dict(r)) if r else None


def _insc(r: dict) -> dict:
    r["objetivos"] = json.loads(r["objetivos"] or "[]")
    r["preferencias"] = json.loads(r["preferencias"] or "{}")
    r["programa"] = programa(r["programa_id"])
    return r


def obtener(con, iid):
    r = con.execute("SELECT * FROM inscripciones WHERE id=?", (iid,)).fetchone()
    return _insc(dict(r)) if r else None


def listar(con, usuario_id, estados=("activo", "pausado")):
    q = f"SELECT * FROM inscripciones WHERE usuario_id=? AND estado IN ({','.join('?' * len(estados))}) ORDER BY estado, id"
    return [_insc(dict(r)) for r in con.execute(q, (usuario_id, *estados))]


def actualizar_objetivos(con, iid, objetivos, preferencias):
    if not objetivos:
        raise db.ValidationError("Elija al menos un objetivo.")
    with db.tx(con):
        con.execute("UPDATE inscripciones SET objetivos=?, preferencias=?, actualizado=? WHERE id=?",
                    (json.dumps(objetivos, ensure_ascii=False), json.dumps(preferencias or {}, ensure_ascii=False), db.now(), iid))


# ------------------------------------------------------------------ estados
def pausar(con, iid):
    i = obtener(con, iid)
    if not i or i["estado"] != "activo":
        raise db.ValidationError("Solo se puede pausar un programa activo.")
    with db.tx(con):
        con.execute("UPDATE inscripciones SET estado='pausado', fecha_pausa=?, actualizado=? WHERE id=?", (_hoy().isoformat(), db.now(), iid))


def reanudar(con, iid):
    """Reanuda y corre hacia adelante las actividades pendientes tantos días como duró la pausa."""
    i = obtener(con, iid)
    if not i or i["estado"] != "pausado":
        raise db.ValidationError("Solo se puede reanudar un programa en pausa.")
    dias = max(0, (_hoy() - date.fromisoformat(i["fecha_pausa"])).days)
    with db.tx(con):
        if dias:
            pend = con.execute("SELECT id, fecha FROM plan_actividades WHERE inscripcion_id=? AND completada=0", (iid,)).fetchall()
            con.executemany("UPDATE plan_actividades SET fecha=? WHERE id=?",
                            [((date.fromisoformat(r["fecha"]) + timedelta(days=dias)).isoformat(), r["id"]) for r in pend])
        con.execute("UPDATE inscripciones SET estado='activo', fecha_pausa=NULL, dias_pausa=dias_pausa+?, actualizado=? WHERE id=?", (dias, db.now(), iid))
    return dias


def finalizar(con, iid):
    i = obtener(con, iid)
    if not i or i["estado"] == "finalizado":
        raise db.ValidationError("El programa ya está finalizado.")
    with db.tx(con):
        con.execute("UPDATE inscripciones SET estado='finalizado', actualizado=? WHERE id=?", (db.now(), iid))


# ------------------------------------------------------------------ actividades
def actividades(con, iid, semana=None):
    q, args = "SELECT * FROM plan_actividades WHERE inscripcion_id=?", [iid]
    if semana:
        q += " AND semana=?"; args.append(semana)
    return db.rows(con.execute(q + " ORDER BY fecha, orden", args))


def _actividad(con, aid):
    r = con.execute("SELECT a.*, i.estado FROM plan_actividades a JOIN inscripciones i ON i.id=a.inscripcion_id WHERE a.id=?", (aid,)).fetchone()
    if not r:
        raise db.ValidationError("Actividad no encontrada.")
    return dict(r)


def marcar(con, aid, hecha: bool):
    a = _actividad(con, aid)
    if a["estado"] != "activo":
        raise db.ValidationError("Reanude el programa para registrar avances.")
    with db.tx(con):
        con.execute("UPDATE plan_actividades SET completada=?, fecha_completada=? WHERE id=?",
                    (int(hecha), _hoy().isoformat() if hecha else None, aid))


def observar(con, aid, texto):
    _actividad(con, aid)
    texto = db._txt(texto, "Observación", obligatorio=False, maxlen=500)
    with db.tx(con):
        con.execute("UPDATE plan_actividades SET observacion=? WHERE id=?", (texto, aid))


# ------------------------------------------------------------------ notas y registros
def agregar_nota(con, iid, semana, texto):
    if not obtener(con, iid):
        raise db.ValidationError("Programa no encontrado.")
    if not 1 <= int(semana) <= SEMANAS:
        raise db.ValidationError("Semana no válida.")
    texto = db._txt(texto, "Observación", maxlen=800)
    with db.tx(con):
        cur = con.execute("INSERT INTO plan_notas (inscripcion_id, semana, fecha, texto) VALUES (?,?,?,?)", (iid, int(semana), db.now(), texto))
    return cur.lastrowid


def notas(con, iid):
    return db.rows(con.execute("SELECT * FROM plan_notas WHERE inscripcion_id=? ORDER BY id DESC", (iid,)))


def registrar(con, iid, tipo, fecha, detalle, minutos=None, nota=None):
    i = obtener(con, iid)
    if not i:
        raise db.ValidationError("Programa no encontrado.")
    if i["estado"] != "activo":
        raise db.ValidationError("Reanude el programa para agregar registros.")
    if tipo not in TIPOS_REGISTRO:
        raise db.ValidationError("Tipo de registro no válido.")
    f = db._fecha(fecha, "Fecha", permitir_futuro=False)
    if not f:
        raise db.ValidationError("La fecha es obligatoria.")
    detalle = db._txt(detalle, "Detalle", maxlen=300)
    if minutos not in (None, ""):
        minutos = int(minutos)
        if not 1 <= minutos <= 600:
            raise db.ValidationError("Los minutos deben estar entre 1 y 600.")
    else:
        minutos = None
    with db.tx(con):
        cur = con.execute("INSERT INTO plan_registros (inscripcion_id, tipo, fecha, detalle, minutos, nota, creado) VALUES (?,?,?,?,?,?,?)",
                          (iid, tipo, f, detalle, minutos, db._txt(nota, "Nota", False, 300), db.now()))
    return cur.lastrowid


def registros(con, iid, tipo=None):
    q, a = "SELECT * FROM plan_registros WHERE inscripcion_id=?", [iid]
    if tipo:
        q += " AND tipo=?"; a.append(tipo)
    return db.rows(con.execute(q + " ORDER BY fecha DESC, id DESC", a))


def eliminar_registro(con, rid):
    with db.tx(con):
        con.execute("DELETE FROM plan_registros WHERE id=?", (rid,))


# ------------------------------------------------------------------ progreso
def semana_actual(insc: dict, hoy: date | None = None) -> int:
    hoy = hoy or _hoy()
    ref = date.fromisoformat(insc["fecha_pausa"]) if insc["estado"] == "pausado" and insc.get("fecha_pausa") else hoy
    dias = (ref - date.fromisoformat(insc["fecha_inicio"])).days - int(insc.get("dias_pausa") or 0)
    return max(1, min(SEMANAS, dias // 7 + 1))


def progreso(con, iid):
    acts = actividades(con, iid)
    total, hechas = len(acts), sum(a["completada"] for a in acts)
    por_semana = []
    for s in range(1, SEMANAS + 1):
        a_s = [a for a in acts if a["semana"] == s]
        h = sum(a["completada"] for a in a_s)
        por_semana.append({"semana": s, "total": len(a_s), "hechas": h, "pct": round(100 * h / len(a_s), 1) if a_s else 0.0})
    i = obtener(con, iid)
    sa = semana_actual(i)
    pend = [a for a in acts if a["semana"] == sa and not a["completada"]]
    return {"total": total, "hechas": hechas, "pct": round(100 * hechas / total, 1) if total else 0.0, "por_semana": por_semana,
            "semana_actual": sa, "pendientes_semana": pend}


def pendientes_usuario(con, usuario_id, limite=5):
    out = []
    for i in listar(con, usuario_id, ("activo",)):
        sa = semana_actual(i)
        for a in actividades(con, i["id"], sa):
            if not a["completada"]:
                out.append({**a, "programa": i["programa"]["corto"], "inscripcion_id": i["id"]})
    return sorted(out, key=lambda a: a["fecha"])[:limite]
