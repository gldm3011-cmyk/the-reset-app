"""Vistas del profesional de salud: agenda, pacientes y perfil."""
from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from core import auth, db
from ui import acceso, nav
from ui.estilo import FULL, card, e, fecha_corta, num, ring
from ui.vistas import chips, titulo

ESTADO_TXT = {"pendiente": "En revisión", "aprobado": "Aprobado", "rechazado": "No aprobado", "suspendido": "Suspendido"}


def _completar(con, cid, pid):
    try:
        db.completar_cita(con, cid, pid); nav.flash("Cita marcada como atendida.")
    except db.ValidationError as ex:
        nav.flash(str(ex), "warning")


def _cancelar(con, cid, pid, cuenta_id):
    c = db.obtener_cita(con, cid)
    if not c or c["profesional_id"] != pid:
        nav.flash("Cita no encontrada.", "warning"); return
    try:
        db.cancelar_cita(con, cid); auth.auditar(con, cuenta_id, "cancelar_cita_profesional", f"cita {cid}")
        nav.flash("Cita cancelada. El paciente la verá como cancelada en su app.", "info")
    except db.ValidationError as ex:
        nav.flash(str(ex), "warning")


def estado_pendiente(prof):
    est = prof.get("estado", "pendiente")
    if est == "aprobado":
        return False
    msg = {"pendiente": "Su solicitud está en revisión. Verificaremos su registro profesional y le avisaremos al correo de su cuenta.",
           "rechazado": "Su solicitud no fue aprobada. Escriba al equipo de The Reset si cree que se trata de un error.",
           "suspendido": "Su perfil está suspendido y no aparece en el directorio. Escriba al equipo de The Reset."}[est]
    card(f'<span class="tr-label">Estado de su perfil · {e(ESTADO_TXT[est])}</span><p style="margin:.4rem 0 0">{e(msg)}</p>', "cream")
    return True


def agenda(con, cuenta, prof):
    titulo("Mi agenda", prof["nombre"])
    if estado_pendiente(prof):
        return
    vista = st.radio("Vista", ["proximas", "historial"], key="ag_tab", horizontal=True, label_visibility="collapsed",
                     format_func=lambda v: {"proximas": "Próximas", "historial": "Historial"}[v])
    citas = db.listar_citas(con, profesional_id=prof["id"])
    if vista == "proximas":
        prox = [c for c in citas if c["estado"] == "programada"]
        hoy = [c for c in prox if c["fecha"] == date.today().isoformat()]
        st.markdown(f'<div class="tr-grid2"><div class="tr-stat"><div class="v">{len(hoy)}</div><div class="l">citas hoy</div></div>'
                    f'<div class="tr-stat"><div class="v">{len(prox)}</div><div class="l">citas programadas</div></div></div>', unsafe_allow_html=True)
        if not prox:
            card('<p class="tr-title">No tiene citas programadas</p><p class="tr-sub">Los pacientes agendan desde su app según sus días y modalidades.</p>', "lime")
        for c in prox:
            with st.container(border=True, key=f"row_ag_{c['id']}"):
                st.markdown(f'<p class="tr-title">{fecha_corta(c["fecha"])} · {e(c["hora"])} · {e(c["paciente"])}</p>'
                            f'<p class="tr-sub">{e(c["modalidad"])} · {e(c["motivo"] or "Sin motivo")}</p>', unsafe_allow_html=True)
                if c["modalidad"] == "Virtual":
                    with st.form(f"enl_{c['id']}"):
                        enl = st.text_input("Enlace de la consulta virtual", value=c["enlace"] or "", placeholder="https://meet.google.com/…")
                        if st.form_submit_button("Guardar enlace", **FULL):
                            try:
                                db.guardar_enlace(con, c["id"], prof["id"], enl); nav.flash("Enlace guardado: el paciente lo verá en su cita."); st.rerun()
                            except db.ValidationError as ex:
                                st.error(str(ex))
                with st.container(key=f"row_agb_{c['id']}"):
                    a, b, d = st.columns(3)
                    a.button("Atendida", key=f"ok_{c['id']}", type="primary", on_click=_completar, args=(con, c["id"], prof["id"]), **FULL)
                    b.button("Ver paciente", key=f"vp_{c['id']}", on_click=nav.ir, args=("pacientes",), kwargs={"pac_sel": c["usuario_id"]}, **FULL)
                    d.button("Cancelar", key=f"cx_{c['id']}", on_click=_cancelar, args=(con, c["id"], prof["id"], cuenta["id"]), **FULL)
    else:
        otras = [c for c in citas if c["estado"] != "programada"]
        if not otras:
            st.info("Aún no hay citas atendidas o canceladas.")
        for c in reversed(otras):
            st.markdown(f'<div class="tr-kv"><span>{fecha_corta(c["fecha"])} · {e(c["hora"])} · {e(c["paciente"])}</span>'
                        f'<span class="tr-chip">{e("atendida" if c["estado"] == "completada" else c["estado"])}</span></div>', unsafe_allow_html=True)


def pacientes(con, cuenta, prof):
    titulo("Mis pacientes", "Personas que han agendado citas con usted")
    if estado_pendiente(prof):
        return
    lista = db.pacientes_de_profesional(con, prof["id"])
    if not lista:
        st.info("Todavía no tiene pacientes. Aparecerán aquí cuando agenden una cita con usted."); return
    ids = [p["id"] for p in lista]
    pre = st.session_state.get("pac_sel")
    uid = st.selectbox("Paciente", ids, index=ids.index(pre) if pre in ids else 0, key="pac_box",
                       format_func=lambda i: next(f"{p['nombre']} · última cita {fecha_corta(p['ultima_cita'])}" for p in lista if p["id"] == i))
    st.session_state["pac_sel"] = uid
    p = next(x for x in lista if x["id"] == uid)
    if not db.profesional_atiende_a(con, prof["id"], uid):
        st.error("No tiene acceso a este paciente."); return
    card(f'<p class="tr-title">{e(p["nombre"])}</p><p class="tr-sub">{p["edad"]} años · {e(p["sexo"])} · {e(p["ciudad"] or "Ciudad no indicada")}</p>'
         f'<span class="tr-chip dark">💊 {e(p["medicamento_declarado"] or "Medicamento no declarado")}</span>'
         f'<p class="tr-sub" style="margin-top:.4rem">{p["citas"]} cita(s) con usted</p>', "lime")
    if not p["compartir_registros"]:
        st.info("Este paciente no comparte sus registros de seguimiento y eventos. Puede consultarlos con él durante la cita."); return
    auth.auditar(con, cuenta["id"], "consulta_paciente", f"usuario {uid}")
    segs = db.listar_seguimientos(con, uid)
    st.markdown("<h3>Seguimiento</h3>", unsafe_allow_html=True)
    if not segs:
        st.caption("Sin registros de seguimiento.")
    else:
        df = pd.DataFrame(segs)[["fecha", "peso_kg", "energia", "sintomas", "observaciones"]]
        df.columns = ["Fecha", "Peso (kg)", "Energía (1–5)", "Síntomas", "Observaciones"]
        df = df.astype(object).where(df.notna(), "—")
        st.dataframe(df.iloc[::-1], hide_index=True, **FULL)
    st.markdown("<h3>Eventos adversos registrados</h3>", unsafe_allow_html=True)
    reps = db.listar_reportes(con, uid)
    if not reps:
        st.caption("Sin eventos registrados.")
    for r in reps:
        cp = db.completitud(r)
        with st.container(border=True, key=f"row_prep_{r['id']}"):
            st.markdown(f'<div class="tr-row">{ring(cp["pct"], 60, 7, label=str(cp["completos"]) + "/" + str(cp["total"]))}<div class="tr-grow">'
                        f'<p class="tr-title" style="font-size:.93rem">{e((r["descripcion"] or r["sintomas"] or "Sin descripción")[:90])}</p>'
                        f'<p class="tr-sub">{fecha_corta(r["fecha_evento"]) if r["fecha_evento"] else "Sin fecha"} · {e(r["medicamento"] or "—")} · '
                        f'grave: {e(r["grave"] or "—")} · desenlace: {e(r["desenlace"] or "—")}</p></div></div>'
                        f'<div style="margin-top:.3rem">{chips(cp["campos"])}</div>', unsafe_allow_html=True)


def perfil(con, cuenta, prof):
    titulo("Mi perfil profesional")
    estado = ESTADO_TXT.get(prof.get("estado"), "—")
    card(f'<p class="tr-title">{e(prof["nombre"])}</p><p class="tr-sub">{e(prof["especialidad"])} · Registro {e(prof.get("registro_profesional") or "—")}</p>'
         f'<span class="tr-chip {"ok" if prof.get("estado") == "aprobado" else "warn"}">{e(estado)}</span>'
         f'<p class="tr-sub" style="margin-top:.4rem">Cuenta: {e(cuenta["correo"])}</p>', "lime")
    with st.expander("Editar perfil y disponibilidad", expanded=False):
        with st.form("form_prof_edit"):
            nombre = st.text_input("Nombre", value=prof["nombre"], max_chars=80)
            esp = st.selectbox("Especialidad", db.ESPECIALIDADES, index=db.ESPECIALIDADES.index(prof["especialidad"]))
            exp = st.number_input("Años de experiencia", 0, 60, int(prof["experiencia_anios"]))
            ciudad = st.text_input("Ciudad", value=prof["ciudad"], max_chars=60)
            mods = st.multiselect("Modalidades", db.MODALIDADES, default=prof["modalidades"].split(","))
            dias = st.multiselect("Días de atención", db.DIAS, default=prof["dias"].split(","))
            perf = st.text_area("Perfil", value=prof["perfil"], max_chars=400)
            if st.form_submit_button("Guardar cambios", type="primary", **FULL):
                try:
                    db.actualizar_profesional(con, prof["id"], nombre, esp, exp, perf, ciudad, mods, dias)
                    nav.flash("Perfil actualizado."); st.rerun()
                except db.ValidationError as ex:
                    st.error(str(ex))
        st.caption("El número de registro profesional solo lo modifica el administrador, porque es la base de la verificación.")
    with st.expander("Cambiar contraseña"):
        acceso.form_cambiar_clave(con, cuenta, "pro_cc")
    st.button("Cerrar sesión", key="pro_salir", on_click=acceso.salir, icon=":material/logout:", **FULL)
