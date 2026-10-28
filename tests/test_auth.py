"""Cuentas, contraseñas, roles y derechos del titular (SQLite)."""
import pytest

from core import auth, db


@pytest.fixture
def con():
    c = db.connect(":memory:")
    yield c
    c.close()


def paciente(con, correo="ana@prueba.co", clave="clave1234"):
    return auth.registrar_paciente(con, correo, clave, "Ana Prueba", 40, "Femenino", True, True, "Bogotá")


def profesional(con, correo="dra@prueba.co"):
    return auth.registrar_profesional(con, correo, "Medica2027", "Dra. Prueba", "Endocrinología", "RETHUS-1", 8, "Endocrinóloga", "Bogotá",
                                      ["Virtual"], ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"], True, True)


def test_hash_no_guarda_texto_plano(con):
    cid = paciente(con)
    h = auth.obtener_cuenta(con, cid)["clave_hash"]
    assert "clave1234" not in h and h.startswith("pbkdf2_sha256$")
    assert auth.verificar_clave("clave1234", h) and not auth.verificar_clave("otra1234", h)


def test_registro_valida_clave_correo_consentimiento_y_edad(con):
    with pytest.raises(db.ValidationError):
        auth.registrar_paciente(con, "x@y.co", "corta1", "Ana", 40, "Femenino", True, True)
    with pytest.raises(db.ValidationError):
        auth.registrar_paciente(con, "x@y.co", "sololetras", "Ana", 40, "Femenino", True, True)
    with pytest.raises(db.ValidationError):
        auth.registrar_paciente(con, "no-es-correo", "clave1234", "Ana", 40, "Femenino", True, True)
    with pytest.raises(db.ValidationError, match="autorizar"):
        auth.registrar_paciente(con, "x@y.co", "clave1234", "Ana", 40, "Femenino", False, True)
    with pytest.raises(db.ValidationError, match="adultas"):
        auth.registrar_paciente(con, "x@y.co", "clave1234", "Ana", 16, "Femenino", True, True)
    assert con.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0] == 0     # nada queda a medias


def test_correo_unico_sin_distinguir_mayusculas(con):
    paciente(con, "Ana@Prueba.co")
    with pytest.raises(db.ValidationError, match="Ya existe"):
        paciente(con, "ana@prueba.co")


def test_login_y_mensaje_generico(con):
    paciente(con)
    assert auth.iniciar_sesion(con, "ANA@prueba.co", "clave1234")["rol"] == "paciente"
    for correo in ("ana@prueba.co", "nadie@prueba.co"):
        with pytest.raises(db.ValidationError, match="Correo o contraseña incorrectos"):
            auth.iniciar_sesion(con, correo, "mala1234")


def test_bloqueo_tras_5_intentos(con):
    paciente(con)
    for _ in range(4):
        with pytest.raises(db.ValidationError):
            auth.iniciar_sesion(con, "ana@prueba.co", "mala1234")
    with pytest.raises(db.ValidationError, match="bloqueada"):
        auth.iniciar_sesion(con, "ana@prueba.co", "mala1234")
    with pytest.raises(db.ValidationError, match="bloqueada"):       # ni con la clave correcta mientras dura el bloqueo
        auth.iniciar_sesion(con, "ana@prueba.co", "clave1234")


def test_cuenta_desactivada_no_entra(con):
    cid = paciente(con)
    auth.crear_admin(con, "adm@prueba.co", "AdminPrueba1")
    adm = auth.cuenta_por_correo(con, "adm@prueba.co")["id"]
    auth.activar_cuenta(con, adm, cid, False)
    with pytest.raises(db.ValidationError, match="desactivada"):
        auth.iniciar_sesion(con, "ana@prueba.co", "clave1234")
    with pytest.raises(db.ValidationError, match="único administrador"):
        auth.activar_cuenta(con, adm, adm, False)


def test_restablecer_y_cambio_obligatorio(con):
    cid = paciente(con)
    temp = auth.restablecer_clave(con, None, cid)
    c = auth.iniciar_sesion(con, "ana@prueba.co", temp)
    assert c["debe_cambiar_clave"] == 1
    with pytest.raises(db.ValidationError, match="no coinciden"):
        auth.cambiar_clave(con, cid, temp, "Nueva12345", "Otra12345")
    auth.cambiar_clave(con, cid, temp, "Nueva12345", "Nueva12345")
    assert auth.iniciar_sesion(con, "ana@prueba.co", "Nueva12345")["debe_cambiar_clave"] == 0


def test_profesional_pendiente_no_aparece_hasta_aprobacion(con):
    cid = profesional(con)
    pid = auth.obtener_cuenta(con, cid)["profesional_id"]
    assert db.listar_profesionales(con) == []
    u = auth.obtener_cuenta(con, paciente(con))["usuario_id"]
    from datetime import date, timedelta
    with pytest.raises(db.ValidationError, match="profesional válido"):
        db.crear_cita(con, u, pid, date.today() + timedelta(days=1), "10:00", "Virtual")
    db.cambiar_estado_profesional(con, pid, "aprobado")
    assert [p["id"] for p in db.listar_profesionales(con)] == [pid]
    db.cambiar_estado_profesional(con, pid, "suspendido")
    assert db.listar_profesionales(con) == []


def test_profesional_solo_ve_sus_pacientes(con):
    from datetime import date, timedelta
    pid = auth.obtener_cuenta(con, profesional(con))["profesional_id"]
    db.cambiar_estado_profesional(con, pid, "aprobado")
    u1 = auth.obtener_cuenta(con, paciente(con))["usuario_id"]
    u2 = auth.obtener_cuenta(con, paciente(con, "otro@prueba.co"))["usuario_id"]
    cid = db.crear_cita(con, u1, pid, date.today() + timedelta(days=2), "10:00", "Virtual")
    assert [p["id"] for p in db.pacientes_de_profesional(con, pid)] == [u1]
    assert db.profesional_atiende_a(con, pid, u1) and not db.profesional_atiende_a(con, pid, u2)
    with pytest.raises(db.ValidationError, match="https"):
        db.guardar_enlace(con, cid, pid, "http://inseguro.co")
    with pytest.raises(db.ValidationError):
        db.completar_cita(con, cid, pid + 99)          # otro profesional no puede tocar la cita
    db.guardar_enlace(con, cid, pid, "https://meet.google.com/abc")
    db.completar_cita(con, cid, pid)
    assert db.obtener_cita(con, cid)["estado"] == "completada"


def test_exportar_y_suprimir_datos(con):
    cid = paciente(con)
    uid = auth.obtener_cuenta(con, cid)["usuario_id"]
    db.crear_seguimiento(con, uid, "2026-10-01", 80, ["Náuseas"], 3, "nota")
    import json
    datos = json.loads(db.exportar_datos(con, uid))
    assert datos["perfil"]["nombre"] == "Ana Prueba" and len(datos["seguimientos"]) == 1
    with pytest.raises(db.ValidationError):
        auth.eliminar_cuenta_paciente(con, cid, "mala1234")
    auth.eliminar_cuenta_paciente(con, cid, "clave1234")
    assert auth.obtener_cuenta(con, cid) is None
    assert con.execute("SELECT COUNT(*) FROM seguimientos").fetchone()[0] == 0


def test_admin_desde_configuracion(con, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAIL", "jefe@prueba.co"); monkeypatch.setenv("ADMIN_PASSWORD", "JefePrueba9")
    assert auth.asegurar_admin(con)
    assert auth.asegurar_admin(con)                     # idempotente
    assert con.execute("SELECT COUNT(*) FROM cuentas WHERE rol='admin'").fetchone()[0] == 1
    assert auth.iniciar_sesion(con, "jefe@prueba.co", "JefePrueba9")["rol"] == "admin"


def test_auditoria_registra_accesos(con):
    paciente(con)
    auth.iniciar_sesion(con, "ana@prueba.co", "clave1234")
    acciones = [a["accion"] for a in auth.listar_auditoria(con)]
    assert "registro" in acciones and "login" in acciones
