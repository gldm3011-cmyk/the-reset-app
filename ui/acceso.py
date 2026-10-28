"""Pantallas de acceso: iniciar sesión, crear cuenta (paciente o profesional) y cambio obligatorio de contraseña."""
from __future__ import annotations

import streamlit as st

from core import auth, db
from core.programas import MEDICAMENTOS_DECLARABLES
from ui import legal, nav
from ui.estilo import FULL, e


def _marca():
    st.markdown('<div style="text-align:center;margin:1.2rem 0 .6rem"><div style="font-size:2.4rem">🌿</div>'
                '<h1 style="margin:.2rem 0 0">The Reset</h1>'
                '<p class="tr-muted" style="margin:.2rem 0 0">Acompañamiento para personas que usan medicamentos GLP-1 bajo supervisión médica</p></div>',
                unsafe_allow_html=True)


def entrar(cuenta):
    """Inicia la sesión en Streamlit con la cuenta validada."""
    for k in list(st.session_state.keys()):
        if k not in ("_flash",):
            del st.session_state[k]
    st.session_state["cuenta_id"] = cuenta["id"]
    st.session_state["nav"] = {"paciente": "inicio", "profesional": "agenda", "admin": "resumen"}[cuenta["rol"]]
    st.session_state["planes_vista"] = "lista"


def pantalla(con, hay_admin: bool):
    _marca()
    if not hay_admin:
        st.warning("Falta configurar la cuenta de administrador: defina ADMIN_EMAIL y ADMIN_PASSWORD en los secretos de la app y recárguela.")
    nav.mostrar_flash()
    modo = st.radio("Acceso", ["login", "paciente", "profesional"], key="acceso_tab", horizontal=True, label_visibility="collapsed",
                    format_func=lambda v: {"login": "Iniciar sesión", "paciente": "Crear cuenta", "profesional": "Soy profesional"}[v])
    if modo == "login":
        with st.form("form_login"):
            correo = st.text_input("Correo electrónico", key="login_correo", autocomplete="email")
            clave = st.text_input("Contraseña", type="password", key="login_clave", autocomplete="current-password")
            if st.form_submit_button("Iniciar sesión", type="primary", **FULL):
                try:
                    entrar(auth.iniciar_sesion(con, correo, clave)); st.rerun()
                except db.ValidationError as ex:
                    st.error(str(ex))
        r = legal.responsable()
        st.caption(f"¿Olvidó su contraseña? Escriba a {r['correo']} desde el correo de su cuenta y le enviaremos una contraseña temporal.")
    elif modo == "paciente":
        st.markdown('<p class="tr-sub">Cuenta para personas mayores de 18 años. Los campos con * son obligatorios.</p>', unsafe_allow_html=True)
        with st.form("form_reg_paciente"):
            nombre = st.text_input("Nombre *", max_chars=80, key="rp_nombre")
            correo = st.text_input("Correo electrónico *", key="rp_correo", autocomplete="email")
            c1, c2 = st.columns(2)
            clave = c1.text_input("Contraseña *", type="password", help="Mínimo 8 caracteres con letras y números.", key="rp_clave", autocomplete="new-password")
            clave2 = c2.text_input("Repita la contraseña *", type="password", key="rp_clave2", autocomplete="new-password")
            c3, c4 = st.columns(2)
            edad = c3.number_input("Edad *", min_value=0, max_value=120, value=None, step=1, key="rp_edad", placeholder="Años")
            sexo = c4.selectbox("Sexo *", db.SEXOS, index=None, placeholder="Seleccione", key="rp_sexo")
            ciudad = st.text_input("Ciudad", max_chars=60, key="rp_ciudad")
            med = st.selectbox("Medicamento que usa bajo supervisión médica (opcional)", MEDICAMENTOS_DECLARABLES, key="rp_med")
            datos = st.checkbox("Autorizo el tratamiento de mis datos personales, incluidos mis datos de salud, según la Política de tratamiento de datos *", key="rp_datos")
            term = st.checkbox("Acepto los Términos de uso y entiendo que The Reset no reemplaza la atención médica *", key="rp_term")
            if st.form_submit_button("Crear mi cuenta", type="primary", **FULL):
                try:
                    if clave != clave2:
                        raise db.ValidationError("Las contraseñas no coinciden.")
                    if edad is None or sexo is None:
                        raise db.ValidationError("Indique su edad y su sexo.")
                    auth.registrar_paciente(con, correo, clave, nombre, edad, sexo, datos, term, ciudad or None,
                                            None if med == "No declaro" else med)
                    entrar(auth.iniciar_sesion(con, correo, clave))
                    nav.flash("¡Le damos la bienvenida a The Reset! Empiece eligiendo su ruta de acompañamiento.")
                    st.rerun()
                except db.ValidationError as ex:
                    st.error(str(ex))
        legal.enlaces()
    else:
        st.markdown('<p class="tr-sub">Su perfil aparecerá en el directorio cuando el equipo de The Reset verifique su registro profesional.</p>',
                    unsafe_allow_html=True)
        with st.form("form_reg_prof"):
            nombre = st.text_input("Nombre como aparecerá en el directorio *", max_chars=80, placeholder="Ej.: Dra. Laura Gil", key="rf_nombre")
            correo = st.text_input("Correo electrónico *", key="rf_correo", autocomplete="email")
            c1, c2 = st.columns(2)
            clave = c1.text_input("Contraseña *", type="password", help="Mínimo 8 caracteres con letras y números.", key="rf_clave", autocomplete="new-password")
            clave2 = c2.text_input("Repita la contraseña *", type="password", key="rf_clave2", autocomplete="new-password")
            c3, c4 = st.columns(2)
            esp = c3.selectbox("Especialidad *", db.ESPECIALIDADES, key="rf_esp")
            exp = c4.number_input("Años de experiencia *", min_value=0, max_value=60, value=None, step=1, key="rf_exp", placeholder="Años")
            reg = st.text_input("Número de registro profesional (ReTHUS o tarjeta profesional) *", max_chars=40, key="rf_reg")
            ciudad = st.text_input("Ciudad *", max_chars=60, key="rf_ciudad")
            mods = st.multiselect("Modalidades de atención *", db.MODALIDADES, default=["Virtual"], key="rf_mods")
            dias = st.multiselect("Días de atención *", db.DIAS, default=["Lun", "Mar", "Mié", "Jue", "Vie"], key="rf_dias")
            perfil = st.text_area("Perfil profesional breve *", max_chars=400, placeholder="Formación y enfoque de su atención", key="rf_perfil")
            datos = st.checkbox("Autorizo el tratamiento de mis datos según la Política de tratamiento de datos *", key="rf_datos")
            term = st.checkbox("Acepto los Términos de uso *", key="rf_term")
            if st.form_submit_button("Enviar solicitud", type="primary", **FULL):
                try:
                    if clave != clave2:
                        raise db.ValidationError("Las contraseñas no coinciden.")
                    if exp is None:
                        raise db.ValidationError("Indique sus años de experiencia.")
                    auth.registrar_profesional(con, correo, clave, nombre, esp, reg, exp, perfil, ciudad, mods, dias, datos, term)
                    entrar(auth.iniciar_sesion(con, correo, clave))
                    nav.flash("Solicitud enviada. Le avisaremos cuando su perfil sea aprobado.", "info")
                    st.rerun()
                except db.ValidationError as ex:
                    st.error(str(ex))
        legal.enlaces()


def cambio_obligatorio(con, cuenta):
    _marca()
    st.info("Por seguridad, cambie la contraseña temporal antes de continuar.")
    with st.form("form_cambio_obligatorio"):
        actual = st.text_input("Contraseña temporal", type="password", key="co_actual")
        nueva = st.text_input("Nueva contraseña", type="password", help="Mínimo 8 caracteres con letras y números.", key="co_nueva")
        conf = st.text_input("Repita la nueva contraseña", type="password", key="co_conf")
        if st.form_submit_button("Guardar contraseña", type="primary", **FULL):
            try:
                auth.cambiar_clave(con, cuenta["id"], actual, nueva, conf)
                nav.flash("Contraseña actualizada."); st.rerun()
            except db.ValidationError as ex:
                st.error(str(ex))
    st.button("Cerrar sesión", key="co_salir", on_click=salir, **FULL)


def salir():
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    nav.flash("Sesión cerrada.", "info")


def form_cambiar_clave(con, cuenta, key="cc"):
    with st.form(f"form_{key}", clear_on_submit=True):
        actual = st.text_input("Contraseña actual", type="password", key=f"{key}_a")
        nueva = st.text_input("Nueva contraseña", type="password", help="Mínimo 8 caracteres con letras y números.", key=f"{key}_n")
        conf = st.text_input("Repita la nueva contraseña", type="password", key=f"{key}_c")
        if st.form_submit_button("Cambiar contraseña", type="primary", **FULL):
            try:
                auth.cambiar_clave(con, cuenta["id"], actual, nueva, conf); st.success("Contraseña actualizada.")
            except db.ValidationError as ex:
                st.error(str(ex))
