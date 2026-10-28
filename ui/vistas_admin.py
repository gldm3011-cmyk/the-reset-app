"""Vistas del administrador: resumen, verificación de profesionales, cuentas, datos y auditoría."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from core import auth, db
from ui import acceso, legal, nav
from ui.estilo import FULL, MID, card, e, fecha_corta, num
from ui.vistas import chart, panel_historico, titulo


def resumen(con, cuenta):
    titulo("Administración", "Estado general de The Reset")
    if not legal.configurado():
        st.warning("Configure RESPONSABLE_NOMBRE, RESPONSABLE_NIT y RESPONSABLE_CORREO en los secretos: aparecen en la política de datos que aceptan los usuarios.")
    r = auth.resumen_admin(con)
    st.markdown(f'<div class="tr-grid2"><div class="tr-stat"><div class="v">{r["pacientes"]}</div><div class="l">pacientes registrados</div></div>'
                f'<div class="tr-stat"><div class="v">{r["profesionales_aprobados"]}</div><div class="l">profesionales aprobados</div></div>'
                f'<div class="tr-stat"><div class="v">{r["citas_programadas"]}</div><div class="l">citas programadas · {r["citas_atendidas"]} atendidas</div></div>'
                f'<div class="tr-stat"><div class="v">{r["programas_activos"]}</div><div class="l">programas activos</div></div></div>', unsafe_allow_html=True)
    if r["profesionales_pendientes"]:
        st.markdown(f'<div class="tr-warn">👩‍⚕️ Hay <b>{r["profesionales_pendientes"]}</b> profesional(es) esperando verificación.</div>', unsafe_allow_html=True)
        st.button("Revisar solicitudes", key="adm_ir_prof", type="primary", on_click=nav.ir, args=("verificar",), **FULL)
    ind = db.indicadores(con)
    st.markdown("<h3>Indicador central: calidad de los registros</h3>", unsafe_allow_html=True)
    st.caption("Mide el problema que The Reset busca resolver: reportes de eventos con edad, sexo, peso y desenlace conocido.")
    st.markdown(f'<div class="tr-grid2"><div class="tr-stat"><div class="v">{num(ind["pct_4_minimos"])} %</div><div class="l">reportes con los 4 datos mínimos</div></div>'
                f'<div class="tr-stat"><div class="v">{ind["reportes"]}</div><div class="l">reportes de eventos · {ind["borradores"]} borradores</div></div></div>',
                unsafe_allow_html=True)
    if ind["reportes"]:
        comp = pd.DataFrame({"Campo": ["Edad", "Sexo", "Peso", "Desenlace conocido"],
                             "%": [ind["pct_con_edad"], ind["pct_con_sexo"], ind["pct_con_peso"], ind["pct_con_desenlace"]]})
        fig = px.bar(comp, x="%", y="Campo", orientation="h", title="Completitud de los reportes registrados en la app", range_x=[0, 100], text="%",
                     color_discrete_sequence=[MID])
        fig.update_traces(texttemplate="%{text:.1f} %")
        chart(fig, 230)


def _estado_prof(con, admin_id, pid, estado):
    db.cambiar_estado_profesional(con, pid, estado)
    auth.auditar(con, admin_id, f"profesional_{estado}", f"profesional {pid}")
    nav.flash({"aprobado": "Profesional aprobado: ya aparece en el directorio.", "rechazado": "Solicitud rechazada.",
               "suspendido": "Profesional suspendido: ya no aparece en el directorio."}[estado], "info")


def verificar(con, cuenta):
    titulo("Profesionales", "Verifique el registro antes de aprobar (consulta ReTHUS en el portal del Ministerio de Salud)")
    estado = st.radio("Estado", ["pendiente", "aprobado", "suspendido", "rechazado"], key="adm_prof_tab", horizontal=True, label_visibility="collapsed",
                      format_func=lambda v: {"pendiente": "Pendientes", "aprobado": "Aprobados", "suspendido": "Suspendidos", "rechazado": "Rechazados"}[v])
    lista = auth.profesionales_por_estado(con, estado)
    if not lista:
        st.info("No hay profesionales en este estado.")
    for p in lista:
        with st.container(border=True, key=f"row_admp_{p['id']}"):
            st.markdown(f'<p class="tr-title">{e(p["nombre"])}</p><p class="tr-sub">{e(p["especialidad"])} · {p["experiencia_anios"]} años · {e(p["ciudad"])}</p>'
                        f'<p class="tr-sub">Registro profesional: <b>{e(p.get("registro_profesional") or "—")}</b> · Correo: {e(p.get("correo_cuenta") or "—")}</p>'
                        f'<p class="tr-sub">{e(p["perfil"])}</p><p class="tr-sub">Atiende: {e(p["dias"].replace(",", ", "))} · {e(p["modalidades"].replace(",", " / "))}</p>',
                        unsafe_allow_html=True)
            with st.container(key=f"row_admpb_{p['id']}"):
                a, b = st.columns(2)
                if estado in ("pendiente", "rechazado", "suspendido"):
                    a.button("Aprobar", key=f"apr_{p['id']}", type="primary", on_click=_estado_prof, args=(con, cuenta["id"], p["id"], "aprobado"), **FULL)
                if estado == "pendiente":
                    b.button("Rechazar", key=f"rec_{p['id']}", on_click=_estado_prof, args=(con, cuenta["id"], p["id"], "rechazado"), **FULL)
                if estado == "aprobado":
                    a.button("Suspender", key=f"sus_{p['id']}", on_click=_estado_prof, args=(con, cuenta["id"], p["id"], "suspendido"), **FULL)


def cuentas(con, cuenta):
    titulo("Cuentas", "Busque, active o desactive cuentas y restablezca contraseñas")
    c1, c2 = st.columns([2, 1])
    buscar = c1.text_input("Buscar por correo o nombre", key="adm_buscar")
    rol = c2.selectbox("Rol", ["Todos", "paciente", "profesional", "admin"], key="adm_rol")
    lista = auth.listar_cuentas(con, None if rol == "Todos" else rol, buscar or None)
    st.caption(f"{len(lista)} cuenta(s)")
    if "adm_temp" in st.session_state:
        correo, temp = st.session_state.pop("adm_temp")
        st.success(f"Contraseña temporal de {correo}: **{temp}** — compártala por un canal seguro. Se le pedirá cambiarla al ingresar.")
    for c in lista[:50]:
        with st.container(border=True, key=f"row_acc_{c['id']}"):
            estado = "Activa" if c["activa"] else "Desactivada"
            st.markdown(f'<p class="tr-title" style="font-size:.93rem">{e(c["nombre"] or "Administrador")} · <span class="tr-chip">{e(c["rol"])}</span>'
                        f'<span class="tr-chip {"ok" if c["activa"] else "miss"}">{estado}</span></p>'
                        f'<p class="tr-sub">{e(c["correo"])} · creada {fecha_corta(c["creado"][:10])} · último acceso '
                        f'{fecha_corta(c["ultimo_acceso"][:10]) if c["ultimo_acceso"] else "—"}</p>', unsafe_allow_html=True)
            if c["id"] == cuenta["id"]:
                continue
            with st.container(key=f"row_accb_{c['id']}"):
                a, b = st.columns(2)
                if a.button("Nueva clave", key=f"rst_{c['id']}", help="Genera una contraseña temporal que la persona deberá cambiar al ingresar", **FULL):
                    st.session_state["adm_temp"] = (c["correo"], auth.restablecer_clave(con, cuenta["id"], c["id"])); st.rerun()
                if b.button("Desactivar" if c["activa"] else "Activar", key=f"act_{c['id']}", **FULL):
                    try:
                        auth.activar_cuenta(con, cuenta["id"], c["id"], not c["activa"]); st.rerun()
                    except db.ValidationError as ex:
                        st.error(str(ex))


def datos(con, cuenta):
    titulo("Datos de referencia", "Diagnóstico histórico que sustenta el proyecto")
    panel_historico()


def auditoria(con, cuenta):
    titulo("Auditoría", "Últimos accesos y acciones sobre la plataforma")
    reg = auth.listar_auditoria(con, 300)
    if not reg:
        st.info("Sin registros."); return
    df = pd.DataFrame(reg)[["fecha", "correo", "accion", "detalle"]]
    nombres = {"login": "Inicio de sesión", "login_fallido": "Intento fallido", "registro": "Registro", "cambio_clave": "Cambio de contraseña",
               "restablecer_clave": "Contraseña temporal", "activar_cuenta": "Cuenta activada", "desactivar_cuenta": "Cuenta desactivada",
               "supresion_cuenta": "Cuenta eliminada por su titular", "consulta_paciente": "Consulta de paciente", "compartir_registros": "Privacidad",
               "profesional_aprobado": "Profesional aprobado", "profesional_rechazado": "Profesional rechazado", "profesional_suspendido": "Profesional suspendido",
               "cancelar_cita_profesional": "Cita cancelada por profesional"}
    df["accion"] = df["accion"].map(lambda a: nombres.get(a, a))
    df["correo"] = df["correo"].fillna("—")
    df.columns = ["Fecha", "Cuenta", "Acción", "Detalle"]
    df["Fecha"] = df["Fecha"].str.replace("T", " ")
    st.dataframe(df, hide_index=True, **FULL, height=520)


def ajustes(con, cuenta):
    titulo("Mi cuenta", cuenta["correo"])
    with st.expander("Cambiar contraseña", expanded=True):
        acceso.form_cambiar_clave(con, cuenta, "adm_cc")
    st.markdown("<h3>Política de datos y términos publicados</h3>", unsafe_allow_html=True)
    legal.enlaces()
    st.button("Cerrar sesión", key="adm_salir", on_click=acceso.salir, icon=":material/logout:", **FULL)
