"""Pruebas de la interfaz con streamlit.testing (ejecuta app.py sin navegador), con inicio de sesión real."""
import os
from datetime import date, timedelta

from streamlit.testing.v1 import AppTest

from core import auth, db, planes

APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app.py")
TABS_PAC = ["inicio", "planes", "citas", "seguimiento", "perfil"]
EXTRA = ["profesionales", "eventos", "acerca"]


def con():
    return db.connect()


def ok(at):
    assert not at.exception, at.exception
    return at


def boton(at, etiqueta):
    next(b for b in at.button if b.label == etiqueta).click().run()
    return ok(at)


def abrir(cuenta_id=None):
    at = AppTest.from_file(APP, default_timeout=60)
    if cuenta_id:
        at.session_state["cuenta_id"] = cuenta_id
    at.run()
    return ok(at)


def login(at, correo, clave):
    at.text_input(key="login_correo").input(correo)
    at.text_input(key="login_clave").input(clave)
    return boton(at, "Iniciar sesión")


def ir(at, pagina):
    at.button(key=f"nav_{pagina}").click().run()
    return ok(at)


def cuenta_paciente(correo, nombre="Paciente Prueba", med=None):
    c = con()
    if not auth.cuenta_por_correo(c, correo):
        auth.registrar_paciente(c, correo, "clave1234", nombre, 45, "Femenino", True, True, "Bogotá", med)
    return auth.cuenta_por_correo(c, correo)


def test_sin_sesion_muestra_acceso_y_no_datos():
    at = abrir()
    assert at.radio(key="acceso_tab")
    assert not [b for b in at.button if (b.key or "").startswith("nav_")]


def test_registro_de_paciente_desde_la_interfaz():
    at = abrir()
    at.radio(key="acceso_tab").set_value("paciente").run()
    at.text_input(key="rp_nombre").input("Laura UI"); at.text_input(key="rp_correo").input("laura.ui@prueba.co")
    at.text_input(key="rp_clave").input("clave1234"); at.text_input(key="rp_clave2").input("clave1234")
    at.number_input(key="rp_edad").set_value(33); at.selectbox(key="rp_sexo").set_value("Femenino")
    at.checkbox(key="rp_term").check()
    boton(at, "Crear mi cuenta")                                          # sin autorizar datos: rechaza
    assert any("autorizar" in e.value for e in at.error) and "cuenta_id" not in at.session_state
    at.checkbox(key="rp_datos").check()
    boton(at, "Crear mi cuenta")
    assert at.session_state["nav"] == "inicio" and at.session_state["cuenta_id"]


def test_registro_rechaza_menor_de_edad():
    at = abrir()
    at.radio(key="acceso_tab").set_value("paciente").run()
    at.text_input(key="rp_nombre").input("Menor"); at.text_input(key="rp_correo").input("menor@prueba.co")
    at.text_input(key="rp_clave").input("clave1234"); at.text_input(key="rp_clave2").input("clave1234")
    at.number_input(key="rp_edad").set_value(16); at.selectbox(key="rp_sexo").set_value("Masculino")
    at.checkbox(key="rp_datos").check(); at.checkbox(key="rp_term").check()
    boton(at, "Crear mi cuenta")
    assert any("18 y 100" in e.value for e in at.error)


def test_login_correcto_e_incorrecto_y_cierre():
    cuenta_paciente("login@prueba.co")
    at = login(abrir(), "login@prueba.co", "mala1234")
    assert any("incorrectos" in e.value for e in at.error)
    at = login(abrir(), "login@prueba.co", "clave1234")
    assert at.session_state["nav"] == "inicio"
    ir(at, "perfil"); at.button(key="pac_salir").click().run(); ok(at)
    assert "cuenta_id" not in at.session_state and at.radio(key="acceso_tab")


def test_paciente_recorre_todas_las_secciones():
    at = abrir(cuenta_paciente("recorre@prueba.co")["id"])
    for p in TABS_PAC:
        ir(at, p); assert at.session_state["nav"] == p
    for p in EXTRA:
        at.button(key="btn_mas").click().run(); at.button(key=f"mas_{p}").click().run(); ok(at)
        assert at.session_state["nav"] == p


def test_paciente_no_puede_abrir_vistas_de_otro_rol():
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state["cuenta_id"] = cuenta_paciente("rol@prueba.co")["id"]
    at.session_state["nav"] = "cuentas"                                   # vista de administrador
    at.run(); ok(at)
    assert at.session_state["nav"] == "inicio"


def test_ruta_mounjaro_inscribir_avanzar_pausar():
    cta = cuenta_paciente("mounjaro@prueba.co", med="Mounjaro (tirzepatida)")
    uid = cta["usuario_id"]
    at = abrir(cta["id"]); ir(at, "planes")
    at.button(key="ver_ruta_tirzepatida").click().run(); ok(at)
    at.button(key="btn_inscribirme").click().run(); ok(at)
    next(cb for cb in at.checkbox if "programa educativo" in cb.label).check()
    boton(at, "Iniciar programa")
    insc = planes.vigente(con(), uid, "ruta_tirzepatida")
    assert insc and insc["estado"] == "activo"
    primera = planes.actividades(con(), insc["id"], 1)[0]
    at.button(key=f"chk_{primera['id']}").click().run(); ok(at)
    assert planes.progreso(con(), insc["id"])["hechas"] == 1
    at.button(key="btn_pausar").click().run(); ok(at)
    at.button(key="btn_reanudar").click().run(); ok(at)
    assert planes.obtener(con(), insc["id"])["estado"] == "activo"


def test_agendar_cita_con_profesional_aprobado():
    cta = cuenta_paciente("cita@prueba.co")
    at = abrir(cta["id"]); ir(at, "citas")
    antes = len(db.listar_citas(con(), cta["usuario_id"], estado="programada"))
    at.button(key="btn_confirmar_cita").click().run(); ok(at)
    assert len(db.listar_citas(con(), cta["usuario_id"], estado="programada")) == antes + 1


def test_evento_adverso_borrador():
    cta = cuenta_paciente("evento@prueba.co")
    at = abrir(cta["id"])
    at.button(key="btn_mas").click().run(); at.button(key="mas_eventos").click().run(); ok(at)
    at.text_area(key="ae_desc_0").input("Náuseas leves (prueba)")
    at.button(key="ae_borrador").click().run(); ok(at)
    assert db.listar_reportes(con(), cta["usuario_id"])[0]["estado"] == "borrador"


def test_privacidad_compartir_y_eliminar_cuenta():
    cta = cuenta_paciente("borrar@prueba.co")
    at = abrir(cta["id"]); ir(at, "perfil")
    at.toggle(key="tg_compartir").set_value(False).run(); ok(at)
    assert db.obtener_usuario(con(), cta["usuario_id"])["compartir_registros"] == 0
    form_inputs = [t for t in at.text_input if t.label in ("Escriba ELIMINAR para confirmar", "Su contraseña")]
    form_inputs[0].input("ELIMINAR"); form_inputs[1].input("clave1234")
    boton(at, "Eliminar mi cuenta definitivamente")
    assert auth.obtener_cuenta(con(), cta["id"]) is None and db.obtener_usuario(con(), cta["usuario_id"]) is None


def test_profesional_pendiente_ve_estado_en_revision():
    c = con()
    cid = auth.registrar_profesional(c, "nueva.dra@prueba.co", "Medica2027", "Dra. Nueva", "Nutrición", "R-77", 3, "Nutricionista", "Cali",
                                     ["Virtual"], ["Lun"], True, True)
    at = abrir(cid)
    assert at.session_state["nav"] == "agenda"
    assert any("En revisión" in m.value for m in at.markdown)


def test_profesional_agenda_enlace_atendida_y_paciente():
    c = con()
    prof_cta = auth.cuenta_por_correo(c, "profesional1@demo.thereset")          # profesional de ejemplo aprobado
    pid = prof_cta["profesional_id"]
    pac = cuenta_paciente("con.prof@prueba.co")
    d = date.today() + timedelta(days=1)
    while not db.atiende_ese_dia(db.obtener_profesional(c, pid), d):
        d += timedelta(days=1)
    hora = db.horarios_disponibles(c, pid, d, pac["usuario_id"])[0]
    cita = db.crear_cita(c, pac["usuario_id"], pid, d, hora, "Virtual", "control")
    at = abrir(prof_cta["id"])
    assert at.session_state["nav"] == "agenda"
    enl = next(t for t in at.text_input if t.label == "Enlace de la consulta virtual" and t.value == "")
    enl.input("https://meet.google.com/xyz")
    next(b for b in at.button if b.label == "Guardar enlace").click().run(); ok(at)
    assert db.obtener_cita(c, cita)["enlace"] == "https://meet.google.com/xyz"
    at.button(key=f"vp_{cita}").click().run(); ok(at)
    assert at.session_state["nav"] == "pacientes" and at.session_state["pac_sel"] == pac["usuario_id"]
    ir(at, "agenda"); at.button(key=f"ok_{cita}").click().run(); ok(at)
    assert db.obtener_cita(c, cita)["estado"] == "completada"


def test_admin_aprueba_profesional_y_restablece_clave():
    c = con()
    cid = auth.registrar_profesional(c, "por.aprobar@prueba.co", "Medica2027", "Dr. Por Aprobar", "Medicina general", "R-88", 4, "Médico general",
                                     "Bogotá", ["Virtual"], ["Lun"], True, True)
    pid = auth.obtener_cuenta(c, cid)["profesional_id"]
    at = login(abrir(), "admin@prueba.co", "AdminPrueba1")
    assert at.session_state["nav"] == "resumen"
    ir(at, "verificar")
    at.button(key=f"apr_{pid}").click().run(); ok(at)
    assert db.obtener_profesional(c, pid)["estado"] == "aprobado"
    ir(at, "cuentas")
    at.text_input(key="adm_buscar").input("por.aprobar").run(); ok(at)
    at.button(key=f"rst_{cid}").click().run(); ok(at)
    assert auth.obtener_cuenta(c, cid)["debe_cambiar_clave"] == 1
    for p in ["datos", "auditoria", "ajustes", "resumen"]:
        ir(at, p)


def test_cambio_obligatorio_de_clave_temporal():
    c = con()
    cta = cuenta_paciente("temporal@prueba.co")
    temp = auth.restablecer_clave(c, None, cta["id"])
    assert auth.iniciar_sesion(c, "temporal@prueba.co", temp)["debe_cambiar_clave"] == 1
    at = abrir(cta["id"])                                  # sesión iniciada con la contraseña temporal
    assert at.text_input(key="co_actual")
    at.text_input(key="co_actual").input(temp); at.text_input(key="co_nueva").input("Nueva12345"); at.text_input(key="co_conf").input("Nueva12345")
    boton(at, "Guardar contraseña")
    assert auth.obtener_cuenta(c, cta["id"])["debe_cambiar_clave"] == 0
    assert at.session_state["nav"] == "inicio"
