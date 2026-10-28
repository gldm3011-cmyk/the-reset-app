"""Pruebas de la capa de datos: registro, citas, plan, seguimiento, eventos adversos e indicadores."""
from datetime import date, timedelta
import pytest
from core import db, seed


@pytest.fixture
def con():
    c = db.connect(":memory:")
    seed.poblar(c)
    return c


def dia_valido(con, pid, salto=0):
    return seed.proximo_dia(db.obtener_profesional(con, pid), date.today(), salto)


# ---- registro
def test_registro_y_recuperacion(con):
    uid = db.crear_usuario(con, "Prueba Uno", 30, "Femenino", peso_kg=70)
    u = db.obtener_usuario(con, uid)
    assert u["nombre"] == "Prueba Uno" and u["peso_kg"] == 70 and u["medicamento_declarado"] is None
    assert len(db.listar_plan(con, uid)) == len(db.PLAN_BASE)        # el plan de ejemplo se crea al registrar


@pytest.mark.parametrize("kw,msg", [({"nombre": "", "edad": 30, "sexo": "Femenino"}, "obligatorio"),
                                    ({"nombre": "Ana", "edad": 15, "sexo": "Femenino"}, "18 y 100"),
                                    ({"nombre": "Ana", "edad": 30, "sexo": "X"}, "sexo"),
                                    ({"nombre": "Ana", "edad": 30, "sexo": "Femenino", "peso_kg": 500}, "30 y 300"),
                                    ({"nombre": "Ana", "edad": 30, "sexo": "Femenino", "correo_demo": "malo"}, "correo")])
def test_registro_validaciones(con, kw, msg):
    with pytest.raises(db.ValidationError, match=msg):
        db.crear_usuario(con, **kw)


def test_actualizar_perfil(con):
    db.actualizar_usuario(con, 1, peso_kg=80.5, ciudad="Cali")
    u = db.obtener_usuario(con, 1)
    assert u["peso_kg"] == 80.5 and u["ciudad"] == "Cali"


# ---- citas
def test_cita_crear_reprogramar_cancelar(con):
    uid = db.crear_usuario(con, "Citas Test", 40, "Masculino")
    f = dia_valido(con, 3, 1)
    cid = db.crear_cita(con, uid, 3, f, "08:00", "Virtual", "prueba")
    assert db.obtener_cita(con, cid)["estado"] == "programada"
    assert "08:00" not in db.horarios_disponibles(con, 3, f)                 # el horario queda ocupado
    f2 = dia_valido(con, 3, 2)
    db.reprogramar_cita(con, cid, f2, "14:00")
    c = db.obtener_cita(con, cid)
    assert (c["fecha"], c["hora"], c["veces_reprogramada"]) == (f2.isoformat(), "14:00", 1)
    assert "08:00" in db.horarios_disponibles(con, 3, f)                     # el horario anterior se libera
    db.cancelar_cita(con, cid)
    assert db.obtener_cita(con, cid)["estado"] == "cancelada"
    assert "14:00" in db.horarios_disponibles(con, 3, f2)                    # cancelar libera el horario
    with pytest.raises(db.ValidationError):
        db.cancelar_cita(con, cid)                                           # no se cancela dos veces


def test_cita_sin_duplicados(con):
    u1 = db.crear_usuario(con, "Uno", 40, "Masculino"); u2 = db.crear_usuario(con, "Dos", 41, "Femenino")
    f = dia_valido(con, 7, 1)
    db.crear_cita(con, u1, 7, f, "09:00", "Virtual")
    with pytest.raises(db.ValidationError):
        db.crear_cita(con, u2, 7, f, "09:00", "Virtual")                    # mismo profesional y horario
    otro = next(p for p in db.listar_profesionales(con) if p["id"] != 7 and db.atiende_ese_dia(p, f) and "Virtual" in p["modalidades"])
    assert "09:00" not in db.horarios_disponibles(con, otro["id"], f, usuario_id=u1)
    with pytest.raises(db.ValidationError, match="choca"):
        db.crear_cita(con, u1, otro["id"], f, "09:00", "Virtual")        # el mismo usuario no puede tener dos citas a la misma hora


def test_cita_validaciones(con):
    uid = db.crear_usuario(con, "Val", 40, "Masculino")
    with pytest.raises(db.ValidationError, match="pasadas"):
        db.crear_cita(con, uid, 1, date.today() - timedelta(days=1), "09:00", "Virtual")
    p = db.obtener_profesional(con, 2)                                       # solo virtual, Mar y Jue
    d = date.today() + timedelta(days=1)
    while db.atiende_ese_dia(p, d):
        d += timedelta(days=1)
    with pytest.raises(db.ValidationError, match="no atiende"):
        db.crear_cita(con, uid, 2, d, "09:00", "Virtual")
    with pytest.raises(db.ValidationError, match="Modalidad"):
        db.crear_cita(con, uid, 2, dia_valido(con, 2), "09:00", "Presencial")


# ---- plan
def test_plan_progreso(con):
    uid = db.crear_usuario(con, "Plan", 33, "Otro")
    items = db.listar_plan(con, uid)
    for it in items[:3]:
        db.marcar_item(con, it["id"], True)
    p = db.progreso_plan(con, uid)
    assert p["completados"] == 3 and p["pct"] == round(100 * 3 / len(items), 1)
    db.marcar_item(con, items[0]["id"], False)
    assert db.progreso_plan(con, uid)["completados"] == 2


# ---- seguimiento
def test_seguimiento_crud(con):
    uid = db.crear_usuario(con, "Seg", 50, "Femenino")
    sid = db.crear_seguimiento(con, uid, date.today(), 90, ["Náuseas"], 3, "obs")
    db.actualizar_seguimiento(con, sid, date.today(), 89.5, ["Náuseas", "Fatiga"], 4, "editado")
    s = db.listar_seguimientos(con, uid)[0]
    assert s["peso_kg"] == 89.5 and s["sintomas"] == "Náuseas,Fatiga" and s["observaciones"] == "editado"
    with pytest.raises(db.ValidationError):
        db.crear_seguimiento(con, uid, date.today() + timedelta(days=2), 90)       # fecha futura
    with pytest.raises(db.ValidationError):
        db.crear_seguimiento(con, uid, date.today())                               # registro vacío
    db.eliminar_seguimiento(con, sid)
    assert db.listar_seguimientos(con, uid) == []


# ---- eventos adversos
def test_reporte_borrador_y_completar(con):
    uid = db.crear_usuario(con, "Ev", 45, "Femenino")
    rid = db.guardar_reporte(con, uid, {"medicamento": "Tirzepatida", "descripcion": "Náuseas", "edad": 45, "sexo": "Femenino", "desenlace": "Desconocido"}, como_borrador=True)
    r = db.obtener_reporte(con, rid)
    c = db.completitud(r)
    assert r["estado"] == "borrador" and not c["minimos_ok"] and set(c["faltantes"]) == {"Peso", "Desenlace conocido", "Fecha del evento"}
    with pytest.raises(db.ValidationError, match="faltan"):
        db.guardar_reporte(con, uid, {"medicamento": "X", "descripcion": "Y"}, como_borrador=False)   # incompleto no puede ser 'completo'
    assert db.actualizar_reporte(con, rid, {"desenlace": "En recuperación", "peso_kg": 82}) == "borrador"   # aún falta la fecha
    assert db.actualizar_reporte(con, rid, {"fecha_evento": date.today() - timedelta(days=2)}) == "completo"
    assert db.completitud(db.obtener_reporte(con, rid))["minimos_ok"]
    hist = db.historial_reporte(con, rid)
    assert len(hist) == 3 and "Desenlace conocido: Desconocido → En recuperación" in hist[1]["cambio"]
    with pytest.raises(db.ValidationError, match="borradores"):
        db.eliminar_reporte(con, rid)                                                # los completos se conservan


def test_reporte_validaciones(con):
    with pytest.raises(db.ValidationError):
        db.guardar_reporte(con, 1, {}, como_borrador=True)                              # vacío
    with pytest.raises(db.ValidationError):
        db.guardar_reporte(con, 1, {"descripcion": "x", "peso_kg": 10}, como_borrador=True)
    with pytest.raises(db.ValidationError):
        db.guardar_reporte(con, 1, {"descripcion": "x", "fecha_evento": date.today() + timedelta(days=3)}, como_borrador=True)


# ---- indicadores
def test_indicadores(con):
    ind = db.indicadores(con)
    reps = db.listar_reportes(con)
    assert ind["reportes"] == len(reps) == 3
    assert ind["reportes_completos"] == 1 and ind["borradores"] == 2
    assert ind["pct_4_minimos"] == round(100 / 3, 1)
    assert ind["pct_con_peso"] == round(100 / 3, 1) and ind["pct_con_edad"] == round(200 / 3, 1)
    assert ind["citas_programadas"] == 4 and ind["citas_canceladas"] == 1
    assert ind["seguimientos"] == 7 and ind["seguimientos_con_peso"] == 6


def test_persistencia_en_archivo(tmp_path):
    p = tmp_path / "x.db"
    c = db.connect(p); seed.poblar(c)
    uid = db.crear_usuario(c, "Persistente", 30, "Femenino"); c.close()
    c2 = db.connect(p)
    assert db.obtener_usuario(c2, uid)["nombre"] == "Persistente"
    assert seed.poblar(c2) is False                                                    # no duplica los datos demo
