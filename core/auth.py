"""Cuentas, inicio de sesión y auditoría.

- Contraseñas guardadas con PBKDF2-SHA256 (310.000 iteraciones, sal aleatoria). Nunca se guardan en texto plano.
- Bloqueo temporal tras 5 intentos fallidos.
- Roles: paciente, profesional (requiere aprobación del administrador) y admin.
- El administrador inicial se crea con ADMIN_EMAIL y ADMIN_PASSWORD (secretos o variables de entorno).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta

from . import db
from .conexion import config

ITERACIONES = 310_000
MAX_INTENTOS = 5
MINUTOS_BLOQUEO = 15
POLITICA_VERSION = "1.0"
ROLES = ("paciente", "profesional", "admin")
CORREO_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ------------------------------------------------------------------ contraseñas
def hash_clave(clave: str) -> str:
    sal = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", clave.encode(), sal, ITERACIONES)
    return f"pbkdf2_sha256${ITERACIONES}${base64.b64encode(sal).decode()}${base64.b64encode(dk).decode()}"


def verificar_clave(clave: str, guardado: str) -> bool:
    try:
        algo, it, sal, dk = guardado.split("$")
        calc = hashlib.pbkdf2_hmac("sha256", clave.encode(), base64.b64decode(sal), int(it))
        return algo == "pbkdf2_sha256" and hmac.compare_digest(calc, base64.b64decode(dk))
    except Exception:
        return False


def validar_clave(clave: str):
    if not clave or len(clave) < 8:
        raise db.ValidationError("La contraseña debe tener al menos 8 caracteres.")
    if len(clave) > 128:
        raise db.ValidationError("La contraseña es demasiado larga.")
    if not re.search(r"[A-Za-z]", clave) or not re.search(r"\d", clave):
        raise db.ValidationError("La contraseña debe combinar letras y números.")


def _correo(correo: str) -> str:
    c = (correo or "").strip().lower()
    if not CORREO_RE.match(c) or len(c) > 120:
        raise db.ValidationError("Escriba un correo electrónico válido.")
    return c


def clave_temporal() -> str:
    """Contraseña temporal legible (letras y números) para restablecimientos hechos por el administrador."""
    alf = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    while True:
        c = "".join(secrets.choice(alf) for _ in range(10))
        if re.search(r"\d", c) and re.search(r"[A-Za-z]", c):
            return c


# ------------------------------------------------------------------ auditoría
def auditar(con, cuenta_id, accion, detalle=None):
    try:
        con.execute("INSERT INTO auditoria (cuenta_id, accion, detalle, fecha) VALUES (?,?,?,?)", (cuenta_id, accion, (detalle or "")[:400], db.now()))
        con.commit()
    except Exception:
        pass   # la auditoría nunca debe impedir el uso de la app


def listar_auditoria(con, limite=200):
    return db.rows(con.execute(
        "SELECT a.*, c.correo FROM auditoria a LEFT JOIN cuentas c ON c.id=a.cuenta_id ORDER BY a.id DESC LIMIT ?", (int(limite),)))


# ------------------------------------------------------------------ cuentas
def obtener_cuenta(con, cid):
    r = con.execute("SELECT * FROM cuentas WHERE id=?", (cid,)).fetchone()
    return dict(r) if r else None


def cuenta_por_correo(con, correo):
    r = con.execute("SELECT * FROM cuentas WHERE correo=?", ((correo or "").strip().lower(),)).fetchone()
    return dict(r) if r else None


def _existe(con, correo):
    if cuenta_por_correo(con, correo):
        raise db.ValidationError("Ya existe una cuenta con ese correo. Inicie sesión o use otro correo.")


def registrar_paciente(con, correo, clave, nombre, edad, sexo, acepta_datos: bool, acepta_terminos: bool, ciudad=None, medicamento=None):
    correo = _correo(correo)
    validar_clave(clave)
    if not acepta_datos:
        raise db.ValidationError("Para crear la cuenta debe autorizar el tratamiento de sus datos personales y de salud.")
    if not acepta_terminos:
        raise db.ValidationError("Debe aceptar los términos de uso.")
    _existe(con, correo)
    try:
        with db.tx(con):
            uid = db.crear_usuario(con, nombre, edad, sexo, ciudad=ciudad, correo_demo=correo, medicamento_declarado=medicamento, commit=False)
            cur = con.execute("INSERT INTO cuentas (correo, clave_hash, rol, usuario_id, consentimiento_fecha, politica_version, creado) VALUES (?,?,?,?,?,?,?)",
                              (correo, hash_clave(clave), "paciente", uid, db.now(), POLITICA_VERSION, db.now()))
            cid = cur.lastrowid
    except db.IntegrityError:
        raise db.ValidationError("Ya existe una cuenta con ese correo.")
    auditar(con, cid, "registro", "paciente")
    return cid


def registrar_profesional(con, correo, clave, nombre, especialidad, registro_profesional, experiencia, perfil, ciudad, modalidades, dias,
                          acepta_datos: bool, acepta_terminos: bool):
    correo = _correo(correo)
    validar_clave(clave)
    if not (registro_profesional or "").strip():
        raise db.ValidationError("Indique su número de registro profesional (ReTHUS o tarjeta profesional) para la verificación.")
    if not acepta_datos or not acepta_terminos:
        raise db.ValidationError("Debe aceptar la política de tratamiento de datos y los términos de uso.")
    _existe(con, correo)
    try:
        with db.tx(con):
            pid = db.crear_profesional(con, nombre, especialidad, experiencia, perfil, ciudad, modalidades, dias,
                                       registro_profesional=registro_profesional, correo=correo, estado="pendiente", commit=False)
            cur = con.execute("INSERT INTO cuentas (correo, clave_hash, rol, profesional_id, consentimiento_fecha, politica_version, creado) VALUES (?,?,?,?,?,?,?)",
                              (correo, hash_clave(clave), "profesional", pid, db.now(), POLITICA_VERSION, db.now()))
            cid = cur.lastrowid
    except db.IntegrityError:
        raise db.ValidationError("Ya existe una cuenta con ese correo.")
    auditar(con, cid, "registro", "profesional (pendiente de aprobación)")
    return cid


def crear_admin(con, correo, clave, debe_cambiar=False):
    correo = _correo(correo)
    validar_clave(clave)
    _existe(con, correo)
    with db.tx(con):
        cid = con.execute("INSERT INTO cuentas (correo, clave_hash, rol, debe_cambiar_clave, creado) VALUES (?,?,?,?,?)",
                          (correo, hash_clave(clave), "admin", int(debe_cambiar), db.now())).lastrowid
    auditar(con, cid, "registro", "administrador")
    return cid


def asegurar_admin(con):
    """Crea la cuenta de administrador indicada en ADMIN_EMAIL / ADMIN_PASSWORD si todavía no existe.
    Devuelve True si hay al menos un administrador."""
    correo, clave = config("ADMIN_EMAIL"), config("ADMIN_PASSWORD")
    if correo and clave and not cuenta_por_correo(con, correo):
        try:
            crear_admin(con, correo, clave)
        except db.ValidationError:
            pass
    return con.execute("SELECT COUNT(*) FROM cuentas WHERE rol='admin'").fetchone()[0] > 0


def iniciar_sesion(con, correo, clave):
    """Devuelve la cuenta si las credenciales son correctas. Mensajes genéricos para no revelar qué correos existen."""
    generico = "Correo o contraseña incorrectos."
    c = cuenta_por_correo(con, correo)
    if not c:
        verificar_clave(clave or "", hash_clave("x"))   # tiempo de respuesta similar exista o no la cuenta
        raise db.ValidationError(generico)
    ahora = datetime.now()
    if c["bloqueada_hasta"] and datetime.fromisoformat(c["bloqueada_hasta"]) > ahora:
        mins = int((datetime.fromisoformat(c["bloqueada_hasta"]) - ahora).total_seconds() // 60) + 1
        raise db.ValidationError(f"Cuenta bloqueada temporalmente por intentos fallidos. Intente de nuevo en {mins} minuto(s).")
    if not verificar_clave(clave or "", c["clave_hash"]):
        n = c["intentos_fallidos"] + 1
        hasta = (ahora + timedelta(minutes=MINUTOS_BLOQUEO)).isoformat(timespec="seconds") if n >= MAX_INTENTOS else None
        with db.tx(con):
            con.execute("UPDATE cuentas SET intentos_fallidos=?, bloqueada_hasta=? WHERE id=?", (0 if hasta else n, hasta, c["id"]))
        auditar(con, c["id"], "login_fallido", "bloqueo temporal" if hasta else f"intento {n}")
        if hasta:
            raise db.ValidationError(f"Demasiados intentos fallidos. La cuenta queda bloqueada {MINUTOS_BLOQUEO} minutos.")
        raise db.ValidationError(generico)
    if not c["activa"]:
        raise db.ValidationError("Esta cuenta está desactivada. Escriba al equipo de The Reset para más información.")
    with db.tx(con):
        con.execute("UPDATE cuentas SET intentos_fallidos=0, bloqueada_hasta=NULL, ultimo_acceso=? WHERE id=?", (db.now(), c["id"]))
    auditar(con, c["id"], "login")
    return obtener_cuenta(con, c["id"])


def cambiar_clave(con, cid, actual, nueva, confirmar):
    c = obtener_cuenta(con, cid)
    if not c or not verificar_clave(actual or "", c["clave_hash"]):
        raise db.ValidationError("La contraseña actual no es correcta.")
    if nueva != confirmar:
        raise db.ValidationError("La nueva contraseña y su confirmación no coinciden.")
    if nueva == actual:
        raise db.ValidationError("La nueva contraseña debe ser distinta de la actual.")
    validar_clave(nueva)
    with db.tx(con):
        con.execute("UPDATE cuentas SET clave_hash=?, debe_cambiar_clave=0 WHERE id=?", (hash_clave(nueva), cid))
    auditar(con, cid, "cambio_clave")


def restablecer_clave(con, admin_id, cid) -> str:
    """El administrador genera una contraseña temporal; el usuario deberá cambiarla al ingresar."""
    temp = clave_temporal()
    with db.tx(con):
        con.execute("UPDATE cuentas SET clave_hash=?, debe_cambiar_clave=1, intentos_fallidos=0, bloqueada_hasta=NULL WHERE id=?", (hash_clave(temp), cid))
    auditar(con, admin_id, "restablecer_clave", f"cuenta {cid}")
    return temp


def activar_cuenta(con, admin_id, cid, activa: bool):
    c = obtener_cuenta(con, cid)
    if not c:
        raise db.ValidationError("Cuenta no encontrada.")
    if c["rol"] == "admin" and not activa:
        n = con.execute("SELECT COUNT(*) FROM cuentas WHERE rol='admin' AND activa=1").fetchone()[0]
        if n <= 1:
            raise db.ValidationError("No puede desactivar al único administrador activo.")
    with db.tx(con):
        con.execute("UPDATE cuentas SET activa=? WHERE id=?", (int(activa), cid))
    auditar(con, admin_id, "activar_cuenta" if activa else "desactivar_cuenta", f"cuenta {cid}")


def eliminar_cuenta_paciente(con, cid, clave):
    """Derecho de supresión: el paciente borra su cuenta y todos sus datos."""
    c = obtener_cuenta(con, cid)
    if not c or c["rol"] != "paciente":
        raise db.ValidationError("Cuenta no encontrada.")
    if not verificar_clave(clave or "", c["clave_hash"]):
        raise db.ValidationError("La contraseña no es correcta.")
    with db.tx(con):
        con.execute("DELETE FROM cuentas WHERE id=?", (cid,))
        con.execute("DELETE FROM usuarios WHERE id=?", (c["usuario_id"],))
    auditar(con, None, "supresion_cuenta", f"cuenta {cid} eliminada por su titular")


def listar_cuentas(con, rol=None, buscar=None):
    q = ("SELECT c.id, c.correo, c.rol, c.activa, c.debe_cambiar_clave, c.creado, c.ultimo_acceso, c.bloqueada_hasta, "
         "COALESCE(u.nombre, p.nombre) AS nombre, p.estado AS estado_profesional FROM cuentas c "
         "LEFT JOIN usuarios u ON u.id=c.usuario_id LEFT JOIN profesionales p ON p.id=c.profesional_id WHERE 1=1")
    args = []
    if rol:
        q += " AND c.rol=?"; args.append(rol)
    if buscar:
        q += " AND (LOWER(c.correo) LIKE ? OR LOWER(COALESCE(u.nombre, p.nombre, '')) LIKE ?)"; args += [f"%{buscar.lower()}%"] * 2
    return db.rows(con.execute(q + " ORDER BY c.id DESC", args))


def profesionales_por_estado(con, estado):
    return db.rows(con.execute(
        "SELECT p.*, c.correo AS correo_cuenta, c.id AS cuenta_id FROM profesionales p LEFT JOIN cuentas c ON c.profesional_id=p.id "
        "WHERE p.estado=? ORDER BY p.id", (estado,)))


def resumen_admin(con):
    q = lambda sql, *a: con.execute(sql, a).fetchone()[0]
    return {
        "pacientes": q("SELECT COUNT(*) FROM cuentas WHERE rol='paciente'"),
        "profesionales_aprobados": q("SELECT COUNT(*) FROM profesionales WHERE estado='aprobado'"),
        "profesionales_pendientes": q("SELECT COUNT(*) FROM profesionales WHERE estado='pendiente'"),
        "citas_programadas": q("SELECT COUNT(*) FROM citas WHERE estado='programada'"),
        "citas_atendidas": q("SELECT COUNT(*) FROM citas WHERE estado='completada'"),
        "programas_activos": q("SELECT COUNT(*) FROM inscripciones WHERE estado='activo'"),
    }


def crear_cuentas_demo(con, clave="Demo12345"):
    """Solo para la demostración (THE_RESET_DEMO=1): da acceso a los pacientes y profesionales de ejemplo.
    Nunca toca cuentas reales: solo usuarios marcados como demo y profesionales sin correo propio (los del archivo seed)."""
    for u in db.rows(con.execute("SELECT * FROM usuarios WHERE es_demo=1 ORDER BY id")):
        correo = (u["correo_demo"] or f"usuario{u['id']}@demo.thereset").lower()
        if not cuenta_por_correo(con, correo):
            con.execute("INSERT INTO cuentas (correo, clave_hash, rol, usuario_id, consentimiento_fecha, politica_version, creado) VALUES (?,?,?,?,?,?,?)",
                        (correo, hash_clave(clave), "paciente", u["id"], db.now(), POLITICA_VERSION, db.now()))
    demo_prof = db.rows(con.execute(
        "SELECT p.id FROM profesionales p WHERE p.correo IS NULL AND p.registro_profesional IS NULL "
        "AND NOT EXISTS (SELECT 1 FROM cuentas c WHERE c.profesional_id=p.id) ORDER BY p.id"))
    usados = {c["correo"] for c in db.rows(con.execute("SELECT correo FROM cuentas WHERE correo LIKE 'profesional%@demo.thereset'"))}
    n = 1
    for p in demo_prof:
        while f"profesional{n}@demo.thereset" in usados:
            n += 1
        correo = f"profesional{n}@demo.thereset"; usados.add(correo)
        con.execute("INSERT INTO cuentas (correo, clave_hash, rol, profesional_id, consentimiento_fecha, politica_version, creado) VALUES (?,?,?,?,?,?,?)",
                    (correo, hash_clave(clave), "profesional", p["id"], db.now(), POLITICA_VERSION, db.now()))
    con.commit()
