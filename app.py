"""The Reset — aplicación de acompañamiento para personas que usan medicamentos GLP-1 bajo supervisión médica.

Ejecutar:  streamlit run app.py
Configuración (secretos de Streamlit o variables de entorno): ver README.md y .streamlit/secrets.example.toml.
The Reset no prescribe medicamentos ni dosis y no reemplaza la atención médica.
"""
from __future__ import annotations

import time
from datetime import date

import streamlit as st

from core import auth, db, seed
from core.conexion import config
from ui import acceso, nav, vistas, vistas_admin, vistas_planes, vistas_pro
from ui.estilo import FULL, MESES_L, DIAS, banner, e, iniciales, inject

st.set_page_config(page_title="The Reset", page_icon="🌿", layout="centered", initial_sidebar_state="collapsed")
inject()
MINUTOS_INACTIVIDAD = int(config("SESION_MINUTOS", 30))


@st.cache_resource
def inicializar():
    """Una vez por servidor: crea o migra el esquema, crea el administrador y, solo en modo demostración, carga datos de ejemplo."""
    con = db.connect()
    hay_admin = auth.asegurar_admin(con)
    if config("THE_RESET_DEMO") == "1":
        seed.poblar(con); seed.poblar_planes(con); auth.crear_cuentas_demo(con)
    motor = con.motor
    if motor == "postgres":
        con.close()
        return {"hay_admin": hay_admin, "compartida": None}
    return {"hay_admin": hay_admin, "compartida": con}   # SQLite: una conexión compartida (check_same_thread=False)


def conexion():
    ini = inicializar()
    if ini["compartida"] is not None:
        return ini["compartida"]
    if "_con" not in st.session_state or st.session_state["_con"].raw.closed:
        st.session_state["_con"] = db.connect(init=False)       # PostgreSQL: una conexión por sesión
    return st.session_state["_con"]


con = conexion()

# ------------------------------------------------------------------ sesión
cuenta = auth.obtener_cuenta(con, st.session_state["cuenta_id"]) if "cuenta_id" in st.session_state else None
if cuenta and (not cuenta["activa"]):
    acceso.salir(); cuenta = None
ahora = time.time()
if cuenta and ahora - st.session_state.get("_ultimo", ahora) > MINUTOS_INACTIVIDAD * 60:
    acceso.salir(); nav.flash(f"Su sesión se cerró por inactividad ({MINUTOS_INACTIVIDAD} minutos). Ingrese de nuevo.", "info"); cuenta = None
st.session_state["_ultimo"] = ahora

if not cuenta:
    acceso.pantalla(con, inicializar()["hay_admin"])
    st.stop()
if cuenta["debe_cambiar_clave"]:
    acceso.cambio_obligatorio(con, cuenta)
    st.stop()

rol = cuenta["rol"]
tabs = nav.TABS_ROL[rol]
user = db.obtener_usuario(con, cuenta["usuario_id"]) if rol == "paciente" else None
prof = db.obtener_profesional(con, cuenta["profesional_id"]) if rol == "profesional" else None
validas = [t[0] for t in tabs] + (list(nav.EXTRA) if rol == "paciente" else [])
if st.session_state.get("nav") not in validas:
    st.session_state["nav"] = tabs[0][0]
st.session_state.setdefault("planes_vista", "lista")
pagina = st.session_state["nav"]

# ------------------------------------------------------------------ encabezado compacto
with st.container(key="row_header"):
    c1, c2 = st.columns([4, 1.7])
    hoy = date.today()
    nombre = user["nombre"] if user else (prof["nombre"] if prof else "Administración")
    if pagina == tabs[0][0]:
        c1.markdown(f'<div class="tr-hello"><div class="tr-avatar">{e(iniciales(nombre))}</div><div><small>{DIAS[hoy.weekday()]}, {hoy.day} de {MESES_L[hoy.month - 1]}</small>'
                    f'<b>Hola, {e(nombre.split()[0] if user else nombre)}</b></div></div>', unsafe_allow_html=True)
    else:
        c1.markdown('<div class="tr-hello"><span class="tr-brand">🌿 The Reset</span></div>', unsafe_allow_html=True)
    if rol == "paciente":
        c2.button("Más", key="btn_mas", icon=":material/apps:", on_click=nav.ir, args=("mas",), **FULL,
                  type="primary" if pagina in nav.EXTRA else "secondary")
    else:
        c2.button("Salir", key="btn_salir", icon=":material/logout:", on_click=acceso.salir, **FULL)
if rol == "paciente":
    banner()
nav.mostrar_flash()

# ------------------------------------------------------------------ contenido
try:
    if rol == "paciente":
        {"inicio": lambda: vistas.inicio(con, user), "planes": lambda: vistas_planes.render(con, user),
         "citas": lambda: vistas.citas(con, user), "seguimiento": lambda: vistas.seguimiento(con, user),
         "perfil": lambda: vistas.perfil(con, user, cuenta), "mas": lambda: vistas.mas(con, user),
         "profesionales": lambda: vistas.profesionales(con, user), "eventos": lambda: vistas.eventos(con, user),
         "acerca": lambda: vistas.acerca(con, user)}[pagina]()
    elif rol == "profesional":
        {"agenda": lambda: vistas_pro.agenda(con, cuenta, prof), "pacientes": lambda: vistas_pro.pacientes(con, cuenta, prof),
         "perfil_pro": lambda: vistas_pro.perfil(con, cuenta, prof)}[pagina]()
    else:
        {"resumen": lambda: vistas_admin.resumen(con, cuenta), "verificar": lambda: vistas_admin.verificar(con, cuenta),
         "cuentas": lambda: vistas_admin.cuentas(con, cuenta), "datos": lambda: vistas_admin.datos(con, cuenta),
         "auditoria": lambda: vistas_admin.auditoria(con, cuenta), "ajustes": lambda: vistas_admin.ajustes(con, cuenta)}[pagina]()
except db.ValidationError as ex:
    st.error(str(ex))

# ------------------------------------------------------------------ barra de navegación inferior
with st.container(key="bottom_nav"):
    cols = st.columns(len(tabs))
    for col, (k, label, icon) in zip(cols, tabs):
        kwargs = {"planes_vista": "lista"} if k == "planes" else {}
        col.button(label, key=f"nav_{k}", icon=icon, type="primary" if pagina == k else "secondary", **FULL,
                   on_click=nav.ir, args=(k,), kwargs=kwargs)
