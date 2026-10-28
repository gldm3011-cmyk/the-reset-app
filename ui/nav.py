"""Navegación por rol y mensajes (todas las funciones son callbacks seguros para Streamlit)."""
import streamlit as st

TABS_ROL = {
    "paciente": [("inicio", "Inicio", ":material/home:"), ("planes", "Mis planes", ":material/self_improvement:"),
                 ("citas", "Citas", ":material/calendar_month:"), ("seguimiento", "Seguimiento", ":material/monitoring:"),
                 ("perfil", "Perfil", ":material/person:")],
    "profesional": [("agenda", "Agenda", ":material/calendar_month:"), ("pacientes", "Pacientes", ":material/groups:"),
                    ("perfil_pro", "Perfil", ":material/person:")],
    "admin": [("resumen", "Resumen", ":material/dashboard:"), ("verificar", "Verificar", ":material/verified_user:"),
              ("cuentas", "Cuentas", ":material/manage_accounts:"), ("datos", "Datos", ":material/insights:"),
              ("auditoria", "Auditoría", ":material/history:"), ("ajustes", "Mi cuenta", ":material/settings:")],
}
TABS = TABS_ROL["paciente"]
EXTRA = {"mas": "Más", "profesionales": "Profesionales", "eventos": "Eventos adversos", "acerca": "Acerca de The Reset"}


def ir(pagina, **estado):
    """Cambia de página y fija estados auxiliares (p. ej. programa seleccionado)."""
    st.session_state["nav"] = pagina
    for k, v in estado.items():
        if v is None:
            st.session_state.pop(k, None)
        else:
            st.session_state[k] = v


def ver_programa(pid):
    ir("planes", planes_vista="ficha", prog_sel=pid)


def ver_plan(iid):
    ir("planes", planes_vista="plan", insc_sel=iid)
    st.session_state.pop(f"semana_{iid}", None)


def agendar_con(especialidad):
    ir("citas", cita_esp=especialidad, prof_sel=None, citas_tab="agendar")
    st.session_state.pop("cita_prof", None)


def flash(msg, kind="success"):
    st.session_state["_flash"] = (msg, kind)


def mostrar_flash():
    if "_flash" in st.session_state:
        msg, kind = st.session_state.pop("_flash")
        {"success": st.success, "info": st.info, "warning": st.warning, "error": st.error}[kind](msg)
