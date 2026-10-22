"""The Reset — Prototipo funcional (académico), interfaz mobile-first en Streamlit.

Ejecutar:  streamlit run app.py
No es un servicio médico. No prescribe medicamentos ni dosis. Todos los usuarios y profesionales son ficticios.
"""
from __future__ import annotations

from datetime import date

import streamlit as st

from core import db, seed
from ui import nav, vistas, vistas_planes
from ui.estilo import FULL, FULL_CHART, MESES_L, DIAS, banner, e, iniciales, inject

st.set_page_config(page_title="The Reset", page_icon="🌿", layout="centered", initial_sidebar_state="collapsed")
inject()


@st.cache_resource
def get_con():
    con = db.connect()
    seed.poblar(con)
    seed.poblar_planes(con)        # migración: bases de la versión anterior reciben planes de demostración
    return con


con = get_con()

# Restablecer demostración (se procesa antes de crear cualquier widget)
if st.session_state.pop("_reset", False):
    con.close(); db.reset_db(); get_con.clear()
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    nav.flash("Demostración restablecida con los datos de ejemplo.", "info")
    st.rerun()

usuarios = db.listar_usuarios(con)
if "_pending_uid" in st.session_state:
    st.session_state["uid"] = st.session_state.pop("_pending_uid")
# Al recargar la página se recupera el usuario y la sección desde la URL (?u=…&p=…&i=…)
qp = st.query_params
if "uid" not in st.session_state and qp.get("u", "").isdigit():
    st.session_state["uid"] = int(qp["u"])
    if qp.get("p") in [t[0] for t in nav.TABS] + list(nav.EXTRA):
        st.session_state["nav"] = qp["p"]
    if qp.get("p") == "planes" and qp.get("i", "").isdigit():
        st.session_state["planes_vista"], st.session_state["insc_sel"] = "plan", int(qp["i"])
if "uid" not in st.session_state or not db.obtener_usuario(con, st.session_state["uid"]):
    st.session_state["uid"] = usuarios[0]["id"] if usuarios else None
st.session_state.setdefault("nav", "inicio")
st.session_state.setdefault("planes_vista", "lista")
user = db.obtener_usuario(con, st.session_state["uid"]) if st.session_state["uid"] else None
pagina = st.session_state["nav"]
nuevos_qp = {"u": str(st.session_state["uid"]), "p": pagina}
if pagina == "planes" and st.session_state.get("planes_vista") == "plan" and st.session_state.get("insc_sel"):
    nuevos_qp["i"] = str(st.session_state["insc_sel"])
if dict(st.query_params) != nuevos_qp:
    st.query_params.clear()
    st.query_params.update(nuevos_qp)

# ------------------------------------------------------------------ encabezado compacto
with st.container(key="row_header"):
    c1, c2 = st.columns([4, 1.7])
    hoy = date.today()
    if pagina == "inicio" and user:
        c1.markdown(f'<div class="tr-hello"><div class="tr-avatar">{e(iniciales(user["nombre"]))}</div><div><small>{DIAS[hoy.weekday()]}, {hoy.day} de {MESES_L[hoy.month - 1]}</small>'
                    f'<b>Hola, {e(user["nombre"].split()[0])}</b></div></div>', unsafe_allow_html=True)
    else:
        c1.markdown('<div class="tr-hello"><span class="tr-brand">🌿 The Reset</span></div>', unsafe_allow_html=True)
    c2.button("Más", key="btn_mas", icon=":material/apps:", on_click=nav.ir, args=("mas",), **FULL,
              type="primary" if pagina in nav.EXTRA else "secondary")
banner()
nav.mostrar_flash()

# ------------------------------------------------------------------ contenido
if not user:
    st.info("No hay usuarios. Restablezca la demostración desde «Más».")
else:
    try:
        if pagina == "inicio":
            vistas.inicio(con, user)
        elif pagina == "planes":
            vistas_planes.render(con, user)
        elif pagina == "citas":
            vistas.citas(con, user)
        elif pagina == "seguimiento":
            vistas.seguimiento(con, user)
        elif pagina == "perfil":
            vistas.perfil(con, user, usuarios)
        elif pagina == "mas":
            vistas.mas(con, user)
        elif pagina == "profesionales":
            vistas.profesionales(con, user)
        elif pagina == "eventos":
            vistas.eventos(con, user)
        elif pagina == "panel":
            vistas.panel(con, user)
        elif pagina == "acerca":
            vistas.acerca(con, user)
        else:
            nav.ir("inicio"); st.rerun()
    except db.ValidationError as ex:
        st.error(str(ex))

# ------------------------------------------------------------------ barra de navegación inferior
with st.container(key="bottom_nav"):
    cols = st.columns(len(nav.TABS))
    for col, (k, label, icon) in zip(cols, nav.TABS):
        kwargs = {"planes_vista": "lista"} if k == "planes" else {}
        col.button(label, key=f"nav_{k}", icon=icon, type="primary" if pagina == k else "secondary", **FULL,
                   on_click=nav.ir, args=(k,), kwargs=kwargs)
