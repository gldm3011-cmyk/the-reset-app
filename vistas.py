"""Vistas: Inicio, Citas, Seguimiento, Perfil, Más, Profesionales, Eventos adversos, Panel y Acerca."""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from core import db, planes
from core.programas import MEDICAMENTOS_DECLARABLES, PROGRAMAS, ruta_sugerida
from ui import nav
from ui.estilo import (FULL, FULL_CHART, CAT_ICON, DARK, LIME, MID, SAGE, bar, card, e, fecha_corta, fecha_larga, iniciales, num, ring, week_strip)

HIST_CSV = Path(__file__).resolve().parent.parent / "data" / "historico_resumen.csv"
SAND = "#C9B79C"


def plot_style(fig, h=280):
    fig.update_layout(separators=",.", height=h, margin=dict(l=8, r=8, t=36, b=8), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(color=DARK, family="Plus Jakarta Sans, sans-serif"), legend=dict(orientation="h", y=-0.25), title_font_size=14)
    fig.update_xaxes(gridcolor="#E9ECE4"); fig.update_yaxes(gridcolor="#E9ECE4")
    return fig


def chart(fig, h=280):
    st.plotly_chart(plot_style(fig, h), **FULL_CHART, config={"displayModeBar": False})


def titulo(t, sub=None):
    st.markdown(f"<h1 style='margin-bottom:.1rem'>{e(t)}</h1>" + (f"<p class='tr-muted' style='margin-top:0'>{e(sub)}</p>" if sub else ""), unsafe_allow_html=True)


def sparkline(vals, w=150, h=46, color=MID):
    if len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1
    pts = " ".join(f"{i * w / (len(vals) - 1):.1f},{h - 6 - (v - lo) / rng * (h - 12):.1f}" for i, v in enumerate(vals))
    return f'<svg width="{w}" height="{h}"><polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>'


# ------------------------------------------------------------------ INICIO
def inicio(con, user):
    uid = user["id"]
    activos = planes.listar(con, uid)
    principal = next((i for i in activos if i["estado"] == "activo" and i["programa"]["medicamento"]), None) or next((i for i in activos if i["estado"] == "activo"), None) or (activos[0] if activos else None)
    if principal:
        pr = planes.progreso(con, principal["id"])
        p = principal["programa"]
        med = f'<span class="tr-chip lime">💊 {e(user["medicamento_declarado"])}</span>' if p["medicamento"] and user["medicamento_declarado"] else ""
        estado = '<span class="tr-chip warn">En pausa</span>' if principal["estado"] == "pausado" else ""
        st.markdown(f'<div class="tr-card dark"><span class="tr-label" style="color:#D7E8B0">Plan activo</span>'
                    f'<div class="tr-row" style="margin-top:.4rem">{ring(pr["pct"], 104, 10, "#D7E8B0", "rgba(255,255,255,.18)", sub="avance", text_color="#fff")}'
                    f'<div class="tr-grow">{med}{estado}<h2 style="margin:.25rem 0 0;color:#fff">{e(p["nombre"])}</h2>'
                    f'<p style="margin:.2rem 0 0;opacity:.85;font-size:.85rem">Semana {pr["semana_actual"]} de 4 · {len(pr["pendientes_semana"])} pendientes esta semana</p>'
                    f'</div></div></div>', unsafe_allow_html=True)
        st.button("Continuar mi plan", key="home_plan", type="primary", **FULL, icon=":material/arrow_forward:",
                  on_click=nav.ver_plan, args=(principal["id"],))
    else:
        sug = ruta_sugerida(user["medicamento_declarado"])
        card(f'<span class="tr-label">Comience aquí</span><h2 style="margin:.3rem 0">Elija su ruta de acompañamiento</h2>'
             f'<p class="tr-sub">Sugerida según su perfil: <b>{e(PROGRAMAS[sug]["nombre"])}</b>. Organiza controles, registros y educación; no prescribe.</p>', "lime")
        st.button("Explorar planes", key="home_explorar", type="primary", **FULL, on_click=nav.ver_programa, args=(sug,))

    # Próxima cita + resumen de salud
    citas = db.listar_citas(con, uid, solo_futuras=True, estado="programada")
    segs = db.listar_seguimientos(con, uid)
    pesos = [s["peso_kg"] for s in segs if s["peso_kg"] is not None]
    c1, c2 = st.columns(2)
    with c1:
        if citas:
            c = citas[0]
            card(f'<span class="tr-label">Próxima cita</span><p class="tr-title" style="margin-top:.35rem">{fecha_corta(c["fecha"])} · {e(c["hora"])}</p>'
                 f'<p class="tr-sub">{e(c["profesional"])}<br>{e(c["especialidad"])} · {e(c["modalidad"])}</p>')
        else:
            card('<span class="tr-label">Próxima cita</span><p class="tr-title" style="margin-top:.35rem">Sin citas</p><p class="tr-sub">Agende un control con su profesional.</p>')
    with c2:
        delta = ""
        if len(pesos) > 1:
            d = pesos[-1] - pesos[0]
            delta = f'{"+" if d >= 0 else "−"}{num(abs(d))} kg desde el inicio'
        ult = segs[-1] if segs else None
        card(f'<span class="tr-label">Seguimiento</span><p class="tr-title" style="margin-top:.35rem">{num(pesos[-1]) + " kg" if pesos else "Peso no registrado"}</p>'
             f'<p class="tr-sub">{delta or "Peso opcional"}<br>{len(segs)} registros · último {fecha_corta(ult["fecha"]) if ult else "—"}</p>{sparkline(pesos[-8:])}')

    # Accesos rápidos
    st.markdown("<h3>Accesos rápidos</h3>", unsafe_allow_html=True)
    with st.container(key="row_quick1"):
        a, b = st.columns(2)
        a.button("Registrar síntomas", key="q_sint", icon=":material/stethoscope:", on_click=nav.ir, args=("seguimiento",), **FULL)
        b.button("Agendar cita", key="q_cita", icon=":material/event_available:", on_click=nav.ir, args=("citas",), kwargs={"citas_tab": "agendar"}, **FULL)
    with st.container(key="row_quick2"):
        a, b = st.columns(2)
        a.button("Profesionales", key="q_prof", icon=":material/groups:", on_click=nav.ir, args=("profesionales",), **FULL)
        b.button("Reportar evento", key="q_ev", icon=":material/edit_note:", on_click=nav.ir, args=("eventos",), **FULL)

    # Pendientes de la semana
    pend = planes.pendientes_usuario(con, uid, 4)
    st.markdown("<h3>Pendientes de esta semana</h3>", unsafe_allow_html=True)
    if not pend:
        st.markdown('<p class="tr-muted">No tiene actividades pendientes esta semana. 🎉</p>', unsafe_allow_html=True)
    for a in pend:
        with st.container(border=True, key=f"row_pend_{a['id']}"):
            c1, c2 = st.columns([4, 1.3])
            c1.markdown(f'<p class="tr-title" style="font-size:.92rem">{CAT_ICON.get(a["categoria"], "•")} {e(a["titulo"])}</p>'
                        f'<p class="tr-sub">{e(a["programa"])} · {fecha_corta(a["fecha"])}</p>', unsafe_allow_html=True)
            c2.button("Hecha", key=f"home_chk_{a['id']}", on_click=_marcar, args=(con, a["id"]), **FULL)

    reps = db.listar_reportes(con, uid)
    bor = sum(r["estado"] == "borrador" for r in reps)
    if bor:
        st.markdown(f'<div class="tr-warn">📝 Tiene <b>{bor}</b> reporte(s) de eventos en borrador. Completar los datos (edad, sexo, peso y desenlace) mejora su seguimiento.</div>', unsafe_allow_html=True)
        st.button("Completar reportes", key="home_rep", on_click=nav.ir, args=("eventos",), kwargs={"eventos_tab": "mis"}, **FULL)


def _marcar(con, aid):
    try:
        planes.marcar(con, aid, True); nav.flash("Actividad marcada como realizada.")
    except db.ValidationError as ex:
        nav.flash(str(ex), "warning")


# ------------------------------------------------------------------ CITAS
def proxima_fecha_valida(con, prof, uid):
    d = date.today()
    for _ in range(30):
        if db.atiende_ese_dia(prof, d) and db.horarios_disponibles(con, prof["id"], d, uid):
            return d
        d += timedelta(days=1)
    return date.today()


def _cancelar(con, cid):
    try:
        db.cancelar_cita(con, cid); nav.flash("Cita cancelada.", "info")
    except db.ValidationError as ex:
        nav.flash(str(ex), "warning")


def citas(con, user):
    uid = user["id"]
    titulo("Citas", "Agende, reprograme o cancele sus citas de demostración")
    vista = st.radio("Vista", ["agendar", "mis"], key="citas_tab", horizontal=True, label_visibility="collapsed",
                     format_func=lambda v: {"agendar": "Agendar", "mis": "Mis citas"}[v])
    if vista == "agendar":
        if st.session_state.get("cita_esp") not in db.ESPECIALIDADES:
            st.session_state["cita_esp"] = db.ESPECIALIDADES[0]
        esp = st.radio("Especialidad", db.ESPECIALIDADES, key="cita_esp", horizontal=True)
        profs = db.listar_profesionales(con, esp)
        ids = [p["id"] for p in profs]
        pre = st.session_state.get("prof_sel")
        pid = st.selectbox("Profesional", ids, index=ids.index(pre) if pre in ids else 0, key="cita_prof",
                           format_func=lambda i: next(p["nombre"] for p in profs if p["id"] == i))
        prof = db.obtener_profesional(con, pid)
        st.markdown(f'<p class="tr-sub">Atiende: {e(prof["dias"].replace(",", ", "))} · {e(prof["modalidades"].replace(",", " / "))} · {e(prof["ciudad"])}</p>', unsafe_allow_html=True)
        fecha = st.date_input("Fecha", value=proxima_fecha_valida(con, prof, uid), min_value=date.today(), max_value=date.today() + timedelta(days=90),
                              key=f"cita_fecha_{pid}", format="DD/MM/YYYY")
        lunes = fecha - timedelta(days=fecha.weekday())
        st.markdown(f'<div class="tr-card" style="padding:.6rem .7rem">{week_strip(lunes, [], hoy=fecha)}</div>', unsafe_allow_html=True)
        hora = None
        if not db.atiende_ese_dia(prof, fecha):
            st.warning("El profesional no atiende ese día. Elija otra fecha.")
        else:
            libres = db.horarios_disponibles(con, pid, fecha, uid)
            if not libres:
                st.warning("No hay horarios libres ese día.")
            else:
                hora = st.radio("Horario disponible", libres, key="cita_hora", horizontal=True)
        modalidad = st.radio("Modalidad", prof["modalidades"].split(","), key="cita_mod", horizontal=True)
        motivo = st.text_input("Motivo (opcional)", key="cita_motivo", placeholder="Ej.: control de seguimiento")
        if st.button("Confirmar cita", type="primary", disabled=hora is None, key="btn_confirmar_cita", **FULL):
            try:
                db.crear_cita(con, uid, pid, fecha, hora, modalidad, motivo)
                st.session_state.pop("prof_sel", None)
                nav.flash(f"✅ Cita confirmada con {prof['nombre']} el {fecha_corta(fecha)} a las {hora}.")
                st.rerun()
            except db.ValidationError as ex:
                st.error(str(ex))
        return
    todas = db.listar_citas(con, uid)
    prog = [c for c in todas if c["estado"] == "programada"]
    if not prog:
        card('<p class="tr-title">No tiene citas programadas</p><p class="tr-sub">Use «Agendar» para reservar una.</p>', "lime")
    for c in prog:
        d = date.fromisoformat(c["fecha"])
        with st.container(border=True, key=f"row_cita_{c['id']}"):
            st.markdown(f'<div class="tr-row"><div style="text-align:center;background:#D7E8B0;border-radius:16px;padding:.45rem .7rem;min-width:58px">'
                        f'<div style="font-size:.7rem">{["Lun","Mar","Mié","Jue","Vie","Sáb","Dom"][d.weekday()]}</div><div style="font-weight:800;font-size:1.25rem">{d.day}</div>'
                        f'<div style="font-size:.7rem">{["ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic"][d.month-1]}</div></div>'
                        f'<div class="tr-grow"><p class="tr-title">{e(c["hora"])} · {e(c["profesional"])}</p><p class="tr-sub">{e(c["especialidad"])} · {e(c["modalidad"])}'
                        f'{" · reprogramada " + str(c["veces_reprogramada"]) + " vez/veces" if c["veces_reprogramada"] else ""}</p>'
                        f'<p class="tr-sub">{e(c["motivo"] or "Sin motivo")}</p></div></div>', unsafe_allow_html=True)
            prof = db.obtener_profesional(con, c["profesional_id"])
            with st.expander("Reprogramar o cancelar"):
                nf = st.date_input("Nueva fecha", value=d, min_value=date.today(), key=f"rf_{c['id']}", format="DD/MM/YYYY")
                op = db.horarios_disponibles(con, c["profesional_id"], nf, uid, excluir_cita=c["id"]) if db.atiende_ese_dia(prof, nf) else []
                nh = st.radio("Nuevo horario", op, key=f"rh_{c['id']}", horizontal=True) if op else None
                if not op:
                    st.caption("El profesional no tiene horarios ese día.")
                if st.button("Reprogramar", key=f"rp_{c['id']}", disabled=nh is None, type="primary", **FULL):
                    try:
                        db.reprogramar_cita(con, c["id"], nf, nh); nav.flash("Cita reprogramada."); st.rerun()
                    except db.ValidationError as ex:
                        st.error(str(ex))
            st.button("Cancelar cita", key=f"cc_{c['id']}", on_click=_cancelar, args=(con, c["id"]), **FULL)
    otras = [c for c in todas if c["estado"] != "programada"]
    if otras:
        with st.expander(f"Historial ({len(otras)})"):
            for c in otras:
                st.markdown(f'<div class="tr-kv"><span>{fecha_corta(c["fecha"])} · {e(c["hora"])} · {e(c["profesional"])}</span><span class="tr-chip">{e(c["estado"])}</span></div>', unsafe_allow_html=True)


# ------------------------------------------------------------------ SEGUIMIENTO
def seguimiento(con, user):
    uid = user["id"]
    titulo("Seguimiento", "Peso opcional, síntomas, energía y observaciones. No emite diagnósticos.")
    vista = st.radio("Vista", ["registrar", "evolucion", "editar"], key="seg_tab", horizontal=True, label_visibility="collapsed",
                     format_func=lambda v: {"registrar": "Registrar", "evolucion": "Evolución", "editar": "Editar"}[v])
    segs = db.listar_seguimientos(con, uid)
    if vista == "registrar":
        with st.form("form_seg", clear_on_submit=True):
            f = st.date_input("Fecha *", value=date.today(), max_value=date.today(), format="DD/MM/YYYY")
            p = st.number_input("Peso en kg (opcional)", min_value=0.0, max_value=300.0, value=None, step=0.1, placeholder="Opcional")
            en = st.slider("Energía percibida (1 = muy baja, 5 = muy alta)", 1, 5, 3)
            s = st.multiselect("Síntomas (opcional)", db.SINTOMAS, placeholder="Seleccione uno o varios síntomas")
            o = st.text_area("Observaciones (opcional)", max_chars=500)
            if st.form_submit_button("Guardar registro", type="primary", **FULL):
                try:
                    db.crear_seguimiento(con, uid, f, p or None, s, en, o)
                    nav.flash("Registro de seguimiento guardado."); st.rerun()
                except db.ValidationError as ex:
                    st.error(str(ex))
        st.markdown('<div class="tr-warn">Si un síntoma le preocupa, documéntelo también en <b>Eventos adversos</b> y consulte a su profesional de salud.</div>', unsafe_allow_html=True)
        st.button("Documentar un evento adverso", key="seg_ev", icon=":material/edit_note:", on_click=nav.ir, args=("eventos",), **FULL)
    elif vista == "evolucion":
        if not segs:
            st.info("Aún no hay registros."); return
        df = pd.DataFrame(segs)
        pesos = df.dropna(subset=["peso_kg"])
        st.markdown(f'<div class="tr-grid2"><div class="tr-stat"><div class="v">{len(segs)}</div><div class="l">registros</div></div>'
                    f'<div class="tr-stat"><div class="v">{num(pesos.peso_kg.iloc[-1]) + " kg" if len(pesos) else "—"}</div><div class="l">último peso</div></div></div>',
                    unsafe_allow_html=True)
        if len(pesos):
            fig = px.area(pesos, x="fecha", y="peso_kg", markers=True, title="Peso registrado (kg)", labels={"fecha": "", "peso_kg": "kg"})
            fig.update_traces(line_color=MID, marker_color=DARK, fillcolor="rgba(143,168,154,.18)")
            fig.update_yaxes(range=[pesos.peso_kg.min() - 2, pesos.peso_kg.max() + 2])
            chart(fig, 250)
        ss = df.sintomas.dropna().str.split(",").explode()
        if len(ss):
            cnt = ss.value_counts().reset_index(); cnt.columns = ["Síntoma", "Registros"]
            fig = px.bar(cnt, x="Registros", y="Síntoma", orientation="h", title="Síntomas registrados", color_discrete_sequence=[SAGE])
            chart(fig, 230)
        st.markdown("<h3>Historial</h3>", unsafe_allow_html=True)
        for s in reversed(segs[-10:]):
            sint = "".join(f'<span class="tr-chip">{e(x)}</span>' for x in (s["sintomas"] or "").split(",") if x)
            card(f'<div class="tr-row"><div class="tr-grow"><p class="tr-title" style="font-size:.92rem">{fecha_corta(s["fecha"])}</p>{sint}'
                 f'<p class="tr-sub">{e(s["observaciones"] or "")}</p></div><div style="text-align:right"><b>{num(s["peso_kg"]) + " kg" if s["peso_kg"] else "—"}</b>'
                 f'<p class="tr-sub">energía {s["energia"] or "—"}/5</p></div></div>')
    else:
        if not segs:
            st.info("Aún no hay registros."); return
        sid = st.selectbox("Registro a editar", [s["id"] for s in segs][::-1], key="seg_edit",
                           format_func=lambda i: next(f"{fecha_corta(s['fecha'])} · {num(s['peso_kg']) + ' kg' if s['peso_kg'] else 'sin peso'}" for s in segs if s["id"] == i))
        s0 = next(s for s in segs if s["id"] == sid)
        with st.form(f"form_edit_{sid}"):
            f = st.date_input("Fecha", value=date.fromisoformat(s0["fecha"]), max_value=date.today(), format="DD/MM/YYYY")
            p = st.number_input("Peso en kg", min_value=0.0, max_value=300.0, value=float(s0["peso_kg"]) if s0["peso_kg"] else None, step=0.1, placeholder="Opcional")
            en = st.slider("Energía (1–5)", 1, 5, int(s0["energia"] or 3))
            sv = st.multiselect("Síntomas", db.SINTOMAS, default=[x for x in (s0["sintomas"] or "").split(",") if x], placeholder="Seleccione síntomas")
            o = st.text_area("Observaciones", value=s0["observaciones"] or "", max_chars=500)
            guardar = st.form_submit_button("Guardar cambios", type="primary", **FULL)
            borrar = st.form_submit_button("Eliminar registro", **FULL)
        if guardar:
            try:
                db.actualizar_seguimiento(con, sid, f, p or None, sv, en, o); nav.flash("Registro actualizado."); st.rerun()
            except db.ValidationError as ex:
                st.error(str(ex))
        if borrar:
            db.eliminar_seguimiento(con, sid); nav.flash("Registro eliminado.", "info"); st.rerun()


# ------------------------------------------------------------------ PERFIL
def perfil(con, user, usuarios):
    uid = user["id"]
    med = user["medicamento_declarado"] or "No declarado"
    st.markdown(f'<div class="tr-card lime"><div class="tr-row"><div class="tr-avatar" style="width:64px;height:64px;font-size:1.4rem">{e(iniciales(user["nombre"]))}</div>'
                f'<div class="tr-grow"><h2 style="margin:0">{e(user["nombre"])}</h2><p class="tr-sub">{user["edad"]} años · {e(user["sexo"])} · {e(user["ciudad"] or "Ciudad no indicada")}</p>'
                f'<span class="tr-chip dark">💊 {e(med)}</span></div></div></div>', unsafe_allow_html=True)
    ind = db.indicadores(con, uid)
    n_planes = len(planes.listar(con, uid))
    st.markdown(f'<div class="tr-grid2"><div class="tr-stat"><div class="v">{n_planes}</div><div class="l">planes activos o en pausa</div></div>'
                f'<div class="tr-stat"><div class="v">{ind["citas_programadas"]}</div><div class="l">citas programadas</div></div>'
                f'<div class="tr-stat"><div class="v">{ind["seguimientos"]}</div><div class="l">registros de seguimiento</div></div>'
                f'<div class="tr-stat"><div class="v">{ind["reportes"]}</div><div class="l">reportes de eventos</div></div></div>', unsafe_allow_html=True)
    st.write("")
    with st.expander("Editar mi perfil", expanded=False):
        with st.form("form_perfil"):
            nombre = st.text_input("Nombre o alias *", value=user["nombre"])
            edad = st.number_input("Edad *", min_value=0, max_value=120, value=int(user["edad"]))
            sexo = st.selectbox("Sexo *", db.SEXOS, index=db.SEXOS.index(user["sexo"]))
            ciudad = st.text_input("Ciudad", value=user["ciudad"] or "")
            peso = st.number_input("Peso en kg (opcional)", min_value=0.0, max_value=300.0, value=float(user["peso_kg"]) if user["peso_kg"] else None, step=0.5, placeholder="Opcional")
            actual = user["medicamento_declarado"] if user["medicamento_declarado"] in MEDICAMENTOS_DECLARABLES else ("Otro" if user["medicamento_declarado"] else "No declaro")
            medsel = st.selectbox("Medicamento que usa bajo supervisión médica (opcional)", MEDICAMENTOS_DECLARABLES, index=MEDICAMENTOS_DECLARABLES.index(actual))
            otro = st.text_input("Si eligió «Otro», ¿cuál?", value=user["medicamento_declarado"] if actual == "Otro" else "")
            st.caption("Declararlo es opcional y solo sirve para sugerir una ruta de acompañamiento. The Reset no recomienda medicamentos ni dosis.")
            if st.form_submit_button("Guardar cambios", type="primary", **FULL):
                valor = None if medsel == "No declaro" else (otro.strip() or None if medsel == "Otro" else medsel)
                try:
                    db.actualizar_usuario(con, uid, nombre=nombre, edad=edad, sexo=sexo, ciudad=ciudad, peso_kg=peso or None, medicamento_declarado=valor)
                    nav.flash("Perfil actualizado."); st.rerun()
                except db.ValidationError as ex:
                    st.error(str(ex))
    st.markdown("<h3>Usuario de demostración</h3>", unsafe_allow_html=True)
    ids = [u["id"] for u in usuarios]
    # «uid» no es clave de widget: así el usuario activo se conserva al cambiar de sección
    st.selectbox("Usuario activo", ids, index=ids.index(uid) if uid in ids else 0, key="uid_sel",
                 format_func=lambda i: next(u["nombre"] for u in usuarios if u["id"] == i), on_change=_cambiar_usuario)
    with st.expander("Crear otro usuario de demostración"):
        st.caption("Campos con * son obligatorios. Peso y medicamento son opcionales.")
        with st.form("form_registro", clear_on_submit=True):
            nombre = st.text_input("Nombre o alias *", placeholder="Ej.: Usuario Prueba", key="reg_nombre")
            edad = st.number_input("Edad *", min_value=0, max_value=120, value=35, step=1, key="reg_edad")
            sexo = st.selectbox("Sexo *", db.SEXOS)
            correo = st.text_input("Correo (ficticio, opcional)", placeholder="usuario@ejemplo.com")
            ciudad = st.text_input("Ciudad (opcional)")
            peso = st.number_input("Peso en kg (opcional)", min_value=0.0, max_value=300.0, value=None, step=0.5, placeholder="Opcional")
            med = st.selectbox("Medicamento declarado (opcional)", MEDICAMENTOS_DECLARABLES)
            acepto = st.checkbox("Entiendo que es un prototipo académico y que no debo ingresar datos médicos reales *", key="reg_acepto")
            if st.form_submit_button("Crear usuario", type="primary", **FULL):
                if not acepto:
                    st.error("Debe aceptar la condición de prototipo académico.")
                else:
                    try:
                        nuevo = db.crear_usuario(con, nombre, edad, sexo, ciudad, correo or None, peso or None, None if med == "No declaro" else med)
                        st.session_state["_pending_uid"] = nuevo
                        nav.flash(f"Usuario «{nombre}» creado y activado.")
                        nav.ir("inicio"); st.rerun()
                    except db.ValidationError as ex:
                        st.error(str(ex))


def _cambiar_usuario():
    st.session_state["uid"] = st.session_state["uid_sel"]
    st.session_state["planes_vista"] = "lista"


# ------------------------------------------------------------------ MÁS
def mas(con, user):
    titulo("Más opciones")
    items = [("profesionales", "Directorio de profesionales", "8 perfiles ficticios en 4 especialidades", ":material/groups:"),
             ("eventos", "Eventos adversos", "Documente síntomas con datos completos y su evolución", ":material/edit_note:"),
             ("panel", "Panel de análisis", "Indicadores de la app y datos históricos separados", ":material/insights:"),
             ("acerca", "Acerca del prototipo", "Alcance, límites y datos ficticios", ":material/info:")]
    for k, t, d, ic in items:
        with st.container(border=True, key=f"row_mas_{k}"):
            c1, c2 = st.columns([3, 1.5])
            c1.markdown(f'<p class="tr-title">{e(t)}</p><p class="tr-sub">{e(d)}</p>', unsafe_allow_html=True)
            c2.button("Abrir", key=f"mas_{k}", on_click=nav.ir, args=(k,), type="primary", **FULL)
    with st.expander("Restablecer la demostración"):
        st.caption("Borra todos los registros y vuelve a cargar los datos ficticios de ejemplo.")
        if st.button("Restablecer datos", key="btn_reset"):
            st.session_state["_reset"] = True; st.rerun()


def acerca(con, user):
    titulo("Acerca del prototipo")
    card('<p>The Reset es un <b>prototipo académico</b> del Proyecto Integrador de TIC. Conecta, de forma simulada, a personas adultas que usan o consideran '
         'medicamentos GLP-1 <b>bajo supervisión médica</b> con profesionales verificados, y organiza citas, planes de acompañamiento y seguimiento.</p>'
         '<ul style="margin:0 0 0 1rem;padding:0"><li>No prescribe medicamentos, dosis, frecuencias, dietas ni rutinas.</li>'
         '<li>No diagnostica ni sustituye a los profesionales de salud.</li>'
         '<li>Registrar un evento en la app no es una notificación oficial de farmacovigilancia.</li>'
         '<li>Usuarios y profesionales son ficticios; los datos se guardan en una base SQLite local.</li></ul>')
    card('<span class="tr-label">Relación con el problema central</span><p style="margin:.3rem 0 0">En los 54.170 reportes históricos analizados, el 90,46 % no tenía '
         'edad, peso, sexo y desenlace a la vez. El formulario estructurado de eventos adversos y los registros de los planes buscan que esos datos sí queden documentados.</p>', "cream")


# ------------------------------------------------------------------ PROFESIONALES
def profesionales(con, user):
    titulo("Profesionales", "Perfiles ficticios de demostración")
    esp = st.radio("Especialidad", ["Todas"] + db.ESPECIALIDADES, key="dir_esp", horizontal=True)
    profs = db.listar_profesionales(con, esp)
    for p in profs:
        with st.container(border=True, key=f"row_profcard_{p['id']}"):
            st.markdown(f'<div class="tr-row"><div class="tr-avatar">{e(iniciales(p["nombre"].replace("Dra. ", "").replace("Dr. ", "").replace("Nut. ", "")))}</div>'
                        f'<div class="tr-grow"><p class="tr-title">{e(p["nombre"])}</p><p class="tr-sub">{e(p["especialidad"])} · {p["experiencia_anios"]} años · {e(p["ciudad"])}</p>'
                        f'<span class="tr-chip ok">✓ Verificado (simulado)</span><span class="tr-chip warn">Demo</span></div></div>'
                        f'<p class="tr-sub" style="margin:.5rem 0">{e(p["perfil"])}</p>'
                        f'<p class="tr-sub">Atiende: {e(p["dias"].replace(",", ", "))} · {e(p["modalidades"].replace(",", " / "))}</p>', unsafe_allow_html=True)
            st.button("Agendar con este profesional", key=f"sel_{p['id']}", on_click=nav.ir, args=("citas",),
                      kwargs={"prof_sel": p["id"], "cita_esp": p["especialidad"], "citas_tab": "agendar"}, **FULL)


# ------------------------------------------------------------------ EVENTOS ADVERSOS
def chips(campos: dict):
    return "".join(f'<span class="tr-chip {"ok" if ok else "miss"}">{"✓" if ok else "✗"} {e(db.CAMPOS_REPORTE[k])}</span>' for k, ok in campos.items())


def eventos(con, user):
    uid = user["id"]
    titulo("Eventos adversos", "Documentación estructurada y seguimiento de la evolución")
    st.markdown('<div class="tr-warn">⚠️ Registrar un evento en The Reset <b>no equivale a una notificación oficial de farmacovigilancia</b>. '
                'Notifíquelo con su profesional o ante la autoridad sanitaria. Ante síntomas graves, busque atención médica inmediata (123 en Colombia).</div>', unsafe_allow_html=True)
    vista = st.radio("Vista", ["nuevo", "mis"], key="eventos_tab", horizontal=True, label_visibility="collapsed",
                     format_func=lambda v: {"nuevo": "Documentar", "mis": "Mis reportes"}[v])
    if vista == "nuevo":
        k = st.session_state.get("ae_form_k", 0)
        fe = st.date_input("Fecha del evento", value=None, max_value=date.today(), key=f"ae_fecha_{k}", format="DD/MM/YYYY")
        med = st.text_input("Medicamento declarado", value=user["medicamento_declarado"] or "", key=f"ae_med_{k}")
        with st.container(key="row_ae_1"):
            c1, c2 = st.columns(2)
            edad = c1.number_input("Edad", min_value=0, max_value=120, value=int(user["edad"]), key=f"ae_edad_{k}")
            sexo = c2.selectbox("Sexo", db.SEXOS, index=db.SEXOS.index(user["sexo"]), key=f"ae_sexo_{k}")
        with st.container(key="row_ae_2"):
            c3, c4 = st.columns(2)
            peso = c3.number_input("Peso (kg)", min_value=0.0, max_value=300.0, value=None, step=0.1, key=f"ae_peso_{k}", placeholder="Si lo conoce")
            grave = c4.selectbox("¿Fue grave?", db.GRAVEDAD, index=None, placeholder="Seleccione", key=f"ae_grave_{k}")
        sint = st.multiselect("Síntomas", db.SINTOMAS, key=f"ae_sint_{k}", placeholder="Seleccione uno o varios síntomas")
        desc = st.text_area("Descripción del evento", key=f"ae_desc_{k}", max_chars=1000, placeholder="¿Qué ocurrió, cuándo empezó y cuánto duró?")
        des = st.selectbox("Estado de evolución (desenlace)", db.DESENLACES, key=f"ae_des_{k}", help="Si aún no sabe cómo evolucionó, deje «Desconocido» y actualícelo después.")
        datos = {"fecha_evento": fe, "medicamento": med, "edad": edad or None, "sexo": sexo or None, "peso_kg": peso or None, "descripcion": desc,
                 "sintomas": sint, "grave": grave or None, "desenlace": des}
        comp = db.completitud({**datos, "fecha_evento": fe.isoformat() if fe else None})
        etq = f"{comp['completos']}/{comp['total']}"
        st.markdown(f'<div class="tr-card"><div class="tr-row">{ring(comp["pct"], 78, 8, label=etq)}'
                    f'<div class="tr-grow"><p class="tr-title">Completitud del registro</p><p class="tr-sub">'
                    f'{"✅ Tiene los 4 datos mínimos (edad, sexo, peso y desenlace)" if comp["minimos_ok"] else "⚠️ Faltan datos mínimos"}</p></div></div>'
                    f'<div style="margin-top:.5rem">{chips(comp["campos"])}</div></div>', unsafe_allow_html=True)
        with st.container(key="row_ae_btn"):
            b1, b2 = st.columns(2)
            if b1.button("Guardar borrador", key="ae_borrador", **FULL):
                try:
                    rid = db.guardar_reporte(con, uid, datos, como_borrador=True)
                    st.session_state["ae_form_k"] = k + 1
                    nav.flash(f"Guardado como {db.obtener_reporte(con, rid)['estado']}. Complételo después en «Mis reportes».", "info"); st.rerun()
                except db.ValidationError as ex:
                    st.error(str(ex))
            if b2.button("Guardar completo", type="primary", key="ae_completo", disabled=comp["completos"] < comp["total"], **FULL):
                try:
                    db.guardar_reporte(con, uid, datos, como_borrador=False)
                    st.session_state["ae_form_k"] = k + 1
                    nav.flash("Reporte completo guardado con los 7 campos."); st.rerun()
                except db.ValidationError as ex:
                    st.error(str(ex))
        if comp["completos"] < comp["total"]:
            st.caption("«Guardar completo» se habilita cuando todos los campos están completos y el desenlace es distinto de «Desconocido».")
        return
    reps = db.listar_reportes(con, uid)
    if not reps:
        st.info("No hay reportes."); return
    for r in reps:
        cp = db.completitud(r)
        estado = '<span class="tr-chip ok">Completo</span>' if r["estado"] == "completo" else '<span class="tr-chip warn">Borrador</span>'
        with st.container(border=True, key=f"row_rep_{r['id']}"):
            etq = f"{cp['completos']}/{cp['total']}"
            st.markdown(f'<div class="tr-row">{ring(cp["pct"], 64, 7, label=etq)}<div class="tr-grow">{estado}'
                        f'<p class="tr-title" style="font-size:.93rem">{e((r["descripcion"] or r["sintomas"] or "Sin descripción")[:70])}</p>'
                        f'<p class="tr-sub">{fecha_corta(r["fecha_evento"]) if r["fecha_evento"] else "Sin fecha"} · {e(r["medicamento"] or "—")} · desenlace: {e(r["desenlace"] or "—")}</p></div></div>'
                        f'<div style="margin-top:.4rem">{chips(cp["campos"])}</div>', unsafe_allow_html=True)
            with st.expander("Actualizar seguimiento"):
                with st.form(f"upd_{r['id']}"):
                    nd = st.selectbox("Desenlace", db.DESENLACES, index=db.DESENLACES.index(r["desenlace"]) if r["desenlace"] in db.DESENLACES else 0)
                    npeso = st.number_input("Peso (kg)", min_value=0.0, max_value=300.0, value=float(r["peso_kg"]) if r["peso_kg"] else None, step=0.1, placeholder="Si lo conoce")
                    nfe = st.date_input("Fecha del evento", value=date.fromisoformat(r["fecha_evento"]) if r["fecha_evento"] else None, max_value=date.today(), format="DD/MM/YYYY")
                    nedad = st.number_input("Edad", min_value=0, max_value=120, value=int(r["edad"]) if r["edad"] else None, placeholder="Edad")
                    nsexo = st.selectbox("Sexo", db.SEXOS, index=db.SEXOS.index(r["sexo"]) if r["sexo"] in db.SEXOS else None, placeholder="Seleccione")
                    if st.form_submit_button("Guardar actualización", type="primary", **FULL):
                        try:
                            est = db.actualizar_reporte(con, r["id"], {"desenlace": nd, "peso_kg": npeso or None, "fecha_evento": nfe, "edad": nedad or None, "sexo": nsexo or None})
                            nav.flash(f"Reporte actualizado. Estado: {est}."); st.rerun()
                        except db.ValidationError as ex:
                            st.error(str(ex))
                st.markdown("**Historial de cambios**")
                for h in db.historial_reporte(con, r["id"]):
                    st.caption(f"{h['fecha'].replace('T', ' ')} — {h['cambio']}")
                if r["estado"] == "borrador" and st.button("Eliminar borrador", key=f"del_{r['id']}"):
                    db.eliminar_reporte(con, r["id"]); nav.flash("Borrador eliminado.", "info"); st.rerun()


# ------------------------------------------------------------------ PANEL
def panel(con, user):
    titulo("Panel de análisis")
    vista = st.radio("Vista", ["app", "hist"], key="panel_tab", horizontal=True, label_visibility="collapsed",
                     format_func=lambda v: {"app": "Datos de la app", "hist": "Datos históricos"}[v])
    if vista == "app":
        st.caption("Indicadores sobre los registros ficticios de esta demostración (todos los usuarios).")
        ind = db.indicadores(con)
        n_insc = con.execute("SELECT COUNT(*) FROM inscripciones WHERE estado IN ('activo','pausado')").fetchone()[0]
        st.markdown(f'<div class="tr-grid2"><div class="tr-stat"><div class="v">{num(ind["pct_4_minimos"])} %</div><div class="l">reportes con los 4 datos mínimos</div></div>'
                    f'<div class="tr-stat"><div class="v">{ind["reportes"]}</div><div class="l">reportes · {ind["borradores"]} borradores</div></div>'
                    f'<div class="tr-stat"><div class="v">{ind["citas_programadas"]}</div><div class="l">citas programadas · {ind["citas_canceladas"]} canceladas</div></div>'
                    f'<div class="tr-stat"><div class="v">{n_insc}</div><div class="l">planes activos o en pausa</div></div></div>', unsafe_allow_html=True)
        comp = pd.DataFrame({"Campo": ["Edad", "Sexo", "Peso", "Desenlace conocido"], "%": [ind["pct_con_edad"], ind["pct_con_sexo"], ind["pct_con_peso"], ind["pct_con_desenlace"]]})
        fig = px.bar(comp, x="%", y="Campo", orientation="h", title="Completitud de los reportes de la app", range_x=[0, 100], text="%", color_discrete_sequence=[MID])
        fig.update_traces(texttemplate="%{text:.1f} %")
        chart(fig, 240)
        insc = pd.read_sql_query("SELECT programa_id, estado FROM inscripciones", con)
        if len(insc):
            insc["Programa"] = insc.programa_id.map(lambda x: PROGRAMAS[x]["corto"])
            agg = insc.groupby(["Programa", "estado"]).size().reset_index(name="Inscripciones").rename(columns={"estado": "Estado"})
            fig = px.bar(agg, y="Programa", x="Inscripciones", color="Estado", orientation="h", title="Inscripciones por programa",
                         color_discrete_map={"activo": DARK, "pausado": SAND, "finalizado": SAGE}, labels={"Programa": ""})
            fig.update_xaxes(dtick=1)
            chart(fig, 260)
        return
    st.markdown('<div class="tr-banner"><b>Datos históricos, no usuarios de la app.</b> Resumen agregado de 54.170 reportes de eventos adversos de incretinas '
                '(base limpia del proyecto; 97,8 % de EE. UU.). No representan incidencia, riesgo ni causalidad y no se mezclan con la demostración.</div>', unsafe_allow_html=True)
    if not HIST_CSV.exists():
        st.warning("No se encontró data/historico_resumen.csv."); return
    h = pd.read_csv(HIST_CSV)
    tot = h[h.medicamento == "TOTAL"].iloc[0]
    st.markdown(f'<div class="tr-grid2"><div class="tr-stat"><div class="v">{num(tot.pct_incompletos, 2)} %</div><div class="l">reportes con información incompleta (KPI central)</div></div>'
                f'<div class="tr-stat"><div class="v">{num(tot.pct_sin_peso, 2)} %</div><div class="l">sin peso registrado</div></div>'
                f'<div class="tr-stat"><div class="v">{num(tot.pct_sin_desenlace, 2)} %</div><div class="l">sin desenlace conocido</div></div>'
                f'<div class="tr-stat"><div class="v">{num(tot.pct_graves_sin_desenlace, 2)} %</div><div class="l">graves sin desenlace</div></div></div>', unsafe_allow_html=True)
    hm = h[(h.medicamento != "TOTAL") & (h.reportes >= 30)]
    long = hm.melt(id_vars="medicamento", value_vars=["pct_sin_peso", "pct_sin_edad", "pct_sin_desenlace"], var_name="Indicador", value_name="%")
    long["Indicador"] = long.Indicador.map({"pct_sin_peso": "Sin peso", "pct_sin_edad": "Sin edad", "pct_sin_desenlace": "Sin desenlace"})
    fig = px.bar(long, y="medicamento", x="%", color="Indicador", barmode="group", orientation="h", title="Datos faltantes por principio activo",
                 color_discrete_sequence=[DARK, SAGE, SAND], labels={"medicamento": ""})
    chart(fig, 380)
    st.caption("Se excluye lixisenatida (19 reportes) por tamaño insuficiente para comparar.")
    for _, r in hm.iterrows():
        st.markdown(f'<div class="tr-card" style="padding:.7rem .9rem"><div class="tr-row"><div class="tr-grow"><p class="tr-title" style="font-size:.93rem">{e(r.medicamento.capitalize())}</p>'
                    f'<p class="tr-sub">{num(r.reportes, 0)} reportes</p></div><b>{num(r.pct_incompletos, 1)} % incompletos</b></div>{bar(r.pct_incompletos)}</div>', unsafe_allow_html=True)
