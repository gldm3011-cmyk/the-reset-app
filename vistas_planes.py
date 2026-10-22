"""Mis planes: explorar, ficha del programa, inscripción y plan activo (calendario de 4 semanas)."""
from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from core import db, planes
from core.programas import (AVISO_GENERAL, MEDICAMENTOS, NOTA_INDICACIONES, OBJETIVOS_GENERALES, ORDEN_PROGRAMAS, ORDEN_RUTAS, PREGUNTAS_CONSULTA,
                            PROGRAMAS, SENALES_ALARMA, TEXTO_ALARMA, programa, ruta_sugerida)
from ui import nav
from ui.estilo import FULL, FULL_CHART, CAT_ICON, DARK, bar, card, e, fecha_corta, fecha_larga, num, ring, week_strip

ESTADO_CHIP = {"activo": ("ok", "Activo"), "pausado": ("warn", "En pausa"), "finalizado": ("", "Finalizado")}


def volver(label="Volver", **estado):
    with st.container(key="row_back"):
        c1, _ = st.columns([2.2, 3])
        c1.button(label, icon=":material/arrow_back:", key="btn_back", on_click=nav.ir, args=("planes",), kwargs=estado)


def alarma_box():
    items = "".join(f"<li>{e(x)}</li>" for x in SENALES_ALARMA)
    st.markdown(f'<div class="tr-alert"><b>🚨 Señales de alarma</b><ul style="margin:.4rem 0 .3rem 1rem;padding:0">{items}</ul>{e(TEXTO_ALARMA)}</div>', unsafe_allow_html=True)


def preguntas_box():
    items = "".join(f"<li>{e(x)}</li>" for x in PREGUNTAS_CONSULTA)
    card(f'<b>📝 Preguntas sugeridas para su consulta</b><ul style="margin:.4rem 0 0 1rem;padding:0">{items}</ul>'
         '<p class="tr-sub">Anote sus propias preguntas en la observación de esta actividad.</p>', "cream")


# ------------------------------------------------------------------ lista
def tarjeta_programa(pid, sugerido=False):
    p = PROGRAMAS[pid]
    n = len(p["actividades"])
    chip = '<span class="tr-chip lime">Sugerida por su medicamento declarado</span>' if sugerido else ""
    with st.container(border=True, key=f"row_prog_{pid}"):
        st.markdown(f'<div class="tr-row"><div class="tr-icon" style="background:{p["color"]}">{p["icono"]}</div><div class="tr-grow">'
                    f'{chip}<p class="tr-title">{e(p["nombre"])}</p><p class="tr-sub">{e(p["subtitulo"])}</p>'
                    f'<p class="tr-sub">4 semanas · {n} actividades · {e(p["profesional"])}</p></div></div>', unsafe_allow_html=True)
        st.button("Ver programa", key=f"ver_{pid}", on_click=nav.ver_programa, args=(pid,), **FULL, type="primary" if sugerido else "secondary")


def vista_lista(con, user):
    st.markdown("<h1>Mis planes</h1>", unsafe_allow_html=True)
    activos = planes.listar(con, user["id"])
    tab_mis, tab_exp = st.tabs([f"Mis programas ({len(activos)})", "Explorar"])
    with tab_mis:
        if not activos:
            card('<p class="tr-title">Aún no tiene programas</p><p class="tr-sub">Explore las rutas por medicamento y los programas de nutrición, actividad física y seguimiento.</p>', "lime")
        for i in activos:
            pr = planes.progreso(con, i["id"])
            cls, txt = ESTADO_CHIP[i["estado"]]
            with st.container(border=True, key=f"row_insc_{i['id']}"):
                st.markdown(f'<div class="tr-row">{ring(pr["pct"], 76, 8)}<div class="tr-grow"><span class="tr-chip {cls}">{txt}</span>'
                            f'<p class="tr-title">{e(i["programa"]["nombre"])}</p>'
                            f'<p class="tr-sub">Semana {pr["semana_actual"]} de 4 · {pr["hechas"]}/{pr["total"]} actividades · desde {fecha_corta(i["fecha_inicio"])}</p></div></div>',
                            unsafe_allow_html=True)
                st.button("Abrir mi plan", key=f"abrir_{i['id']}", on_click=nav.ver_plan, args=(i["id"],), **FULL, type="primary")
        fin = planes.listar(con, user["id"], ("finalizado",))
        if fin:
            with st.expander(f"Programas finalizados ({len(fin)})"):
                for i in fin:
                    pr = planes.progreso(con, i["id"])
                    st.markdown(f'<div class="tr-kv"><span>{e(i["programa"]["nombre"])}</span><b>{num(pr["pct"], 0)} %</b></div>', unsafe_allow_html=True)
    with tab_exp:
        sug = ruta_sugerida(user["medicamento_declarado"])
        st.markdown("<h3>Rutas según su medicamento</h3>", unsafe_allow_html=True)
        if user["medicamento_declarado"] and user["medicamento_declarado"] not in ("No declaro",):
            st.markdown(f'<p class="tr-muted">Medicamento declarado en su perfil: <b>{e(user["medicamento_declarado"])}</b>. La ruta sugerida solo organiza su acompañamiento; '
                        'no es una recomendación clínica.</p>', unsafe_allow_html=True)
        else:
            st.markdown('<p class="tr-muted">Puede declarar el medicamento que usa bajo supervisión médica en su perfil, o elegir la ruta de acompañamiento general.</p>', unsafe_allow_html=True)
        declarado = bool(user["medicamento_declarado"]) and user["medicamento_declarado"] != "No declaro"
        for pid in sorted(ORDEN_RUTAS, key=lambda x: x != sug):
            tarjeta_programa(pid, sugerido=declarado and pid == sug)
        st.markdown("<h3>Programas de acompañamiento</h3>", unsafe_allow_html=True)
        for pid in ORDEN_PROGRAMAS:
            tarjeta_programa(pid)


# ------------------------------------------------------------------ ficha
def ficha_medicamento(clave):
    m = MEDICAMENTOS[clave]
    marcas = "".join(f'<div class="tr-kv" style="display:block"><b>{e(n)}</b><p class="tr-sub">{e(t)}</p></div>' for n, t in m["marcas"])
    card(f'<span class="tr-label">Sobre el medicamento</span><p class="tr-title" style="margin-top:.2rem">{e(m["principio_activo"])}</p>'
         f'<p class="tr-sub">{e(m["clase"])}</p>{marcas}<p class="tr-sub" style="margin-top:.5rem">⚠️ {e(NOTA_INDICACIONES)}</p>')


def vista_ficha(con, user):
    pid = st.session_state.get("prog_sel")
    if pid not in PROGRAMAS:
        nav.ir("planes", planes_vista="lista"); st.rerun()
    p = programa(pid)
    volver(planes_vista="lista")
    acts = p["actividades"]
    st.markdown(f'<div class="tr-card" style="background:linear-gradient(135deg,{p["color"]} 0%,#FFFFFF 120%)">'
                f'<div class="tr-row"><div class="tr-icon" style="background:#fff;width:58px;height:58px;font-size:1.7rem">{p["icono"]}</div>'
                f'<div class="tr-grow"><span class="tr-chip dark">{e(p["tipo"])}</span><h2 style="margin:.25rem 0 0">{e(p["nombre"])}</h2>'
                f'<p class="tr-sub">{e(p["subtitulo"])}</p></div></div></div>', unsafe_allow_html=True)
    apoyo = ", ".join(p["apoyo"]) or "—"
    st.markdown(f'<div class="tr-grid2"><div class="tr-stat"><div class="v">4</div><div class="l">semanas</div></div>'
                f'<div class="tr-stat"><div class="v">{len(acts)}</div><div class="l">actividades</div></div>'
                f'<div class="tr-stat"><div class="v" style="font-size:1rem">{e(p["profesional"])}</div><div class="l">profesional principal</div></div>'
                f'<div class="tr-stat"><div class="v" style="font-size:1rem">{e(apoyo)}</div><div class="l">apoyo</div></div></div>', unsafe_allow_html=True)
    st.write("")
    card(f'<span class="tr-label">Descripción</span><p style="margin:.3rem 0 0">{e(p["descripcion"])}</p>')
    obj = "".join(f"<li>{e(o)}</li>" for o in p["objetivos"])
    card(f'<span class="tr-label">Objetivos</span><ul style="margin:.3rem 0 0 1rem;padding:0">{obj}</ul>')
    if p["medicamento"]:
        ficha_medicamento(p["medicamento"])
        card('<span class="tr-label">Por qué el acompañamiento especializado</span><p style="margin:.3rem 0 0">Estos medicamentos se usan con indicación y '
             'seguimiento profesional. Su especialista revisa sus antecedentes, define si el tratamiento es adecuado, lo ajusta cuando corresponde y '
             'evalúa los posibles efectos adversos. The Reset le ayuda a llegar a cada control con sus registros organizados.</p>')
    st.markdown("<h3>Semana a semana</h3>", unsafe_allow_html=True)
    tabs = st.tabs([f"Semana {s}" for s in range(1, 5)])
    for s, t in zip(range(1, 5), tabs):
        with t:
            for (sem, dia, cat, tit, desc, acc) in [a for a in acts if a[0] == s]:
                st.markdown(f'<div class="tr-kv" style="justify-content:flex-start;gap:.6rem"><span>{CAT_ICON.get(cat, "•")}</span>'
                            f'<span><b>{e(tit)}</b><br><span class="tr-sub">Día {dia} · {e(cat)}</span></span></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="tr-warn"><b>Lo que este programa no hace:</b> {e(AVISO_GENERAL)}</div>', unsafe_allow_html=True)
    if p["medicamento"] or pid == "prog_seguimiento":
        with st.expander("🚨 Señales de alarma"):
            alarma_box()
    vig = planes.vigente(con, user["id"], pid)
    if vig:
        st.button("Ir a mi plan", key="btn_ir_plan", type="primary", **FULL, on_click=nav.ver_plan, args=(vig["id"],))
    else:
        st.button("Inscribirme en este programa", key="btn_inscribirme", type="primary", **FULL, on_click=nav.ir, args=("planes",),
                  kwargs={"planes_vista": "inscribir"})


# ------------------------------------------------------------------ inscripción
def vista_inscribir(con, user):
    pid = st.session_state.get("prog_sel")
    if pid not in PROGRAMAS:
        nav.ir("planes", planes_vista="lista"); st.rerun()
    p = programa(pid)
    volver(planes_vista="ficha")
    st.markdown(f"<h1>Inscribirme</h1><p class='tr-muted'>{e(p['nombre'])} · 4 semanas</p>", unsafe_allow_html=True)
    opciones = list(dict.fromkeys(p["objetivos"] + OBJETIVOS_GENERALES))
    with st.form("form_inscripcion"):
        f = st.date_input("Fecha de inicio", value=date.today(), min_value=date.today() - timedelta(days=28), max_value=date.today() + timedelta(days=30), format="DD/MM/YYYY")
        obj = st.multiselect("Objetivos generales *", opciones, default=p["objetivos"][:2], placeholder="Elija uno o varios objetivos")
        dias = st.multiselect("Días preferidos para registrar", planes.DIAS_SEMANA, default=["Lun", "Jue"], placeholder="Elija días")
        momento = st.radio("Momento del día preferido", planes.MOMENTOS, horizontal=True)
        modalidad = st.radio("Modalidad preferida para citas", planes.MODALIDAD_PREF, horizontal=True)
        rec = st.toggle("Mostrar recordatorios en la app (simulados)", value=True)
        st.markdown(f'<div class="tr-warn">{e(AVISO_GENERAL)}</div>', unsafe_allow_html=True)
        ok = st.checkbox("Entiendo que es un programa educativo y que mis decisiones clínicas las toma mi profesional de salud *")
        enviar = st.form_submit_button("Iniciar programa", type="primary", **FULL)
    if enviar:
        if not ok:
            st.error("Debe aceptar el aviso para iniciar el programa.")
            return
        try:
            iid = planes.inscribir(con, user["id"], pid, f, obj, {"dias": dias, "momento": momento, "modalidad": modalidad, "recordatorios": rec})
            nav.flash(f"¡Listo! Inició «{p['nombre']}». Su calendario de 4 semanas está preparado.")
            nav.ver_plan(iid); st.rerun()
        except db.ValidationError as ex:
            st.error(str(ex))


# ------------------------------------------------------------------ plan activo
def _accion(a, iid):
    acc = a["accion"]
    if not acc:
        return
    k = f"acc_{a['id']}"
    if acc.startswith("cita:"):
        st.button(f"Agendar con {acc[5:].lower()}", key=k, icon=":material/event:", on_click=nav.agendar_con, args=(acc[5:],))
    elif acc == "seguimiento":
        st.button("Ir a seguimiento", key=k, icon=":material/monitoring:", on_click=nav.ir, args=("seguimiento",))
    elif acc == "evento":
        st.button("Ir a eventos adversos", key=k, icon=":material/edit_note:", on_click=nav.ir, args=("eventos",))
    elif acc == "alarma":
        with st.expander("Ver señales de alarma"):
            alarma_box()
    elif acc == "preguntas":
        with st.expander("Ver preguntas sugeridas"):
            preguntas_box()
    elif acc.startswith("registro:"):
        st.markdown('<p class="tr-sub">↓ Use la sección «Mis registros» al final de esta pantalla.</p>', unsafe_allow_html=True)


def tarjeta_actividad(con, a, activo: bool, iid):
    hecha = bool(a["completada"])
    d = date.fromisoformat(a["fecha"])
    with st.container(border=True, key=f"row_act_{a['id']}"):
        c1, c2, c3 = st.columns([1.05, 4, 1.35])
        c1.markdown(f'<div style="text-align:center;background:{"#D7E8B0" if hecha else "#F2F4EE"};border-radius:16px;padding:.35rem 0">'
                    f'<div style="font-size:.68rem;color:#6B7468">{["Lun","Mar","Mié","Jue","Vie","Sáb","Dom"][d.weekday()]}</div>'
                    f'<div style="font-weight:800;font-size:1.1rem">{d.day}</div></div>', unsafe_allow_html=True)
        tachado = "text-decoration:line-through;opacity:.6" if hecha else ""
        c2.markdown(f'<p class="tr-title" style="font-size:.93rem;{tachado}">{CAT_ICON.get(a["categoria"], "•")} {e(a["titulo"])}</p>'
                    f'<p class="tr-sub">{e(a["descripcion"] or "")}</p>', unsafe_allow_html=True)
        c3.button("✓" if hecha else "Hecha", key=f"chk_{a['id']}", type="primary" if hecha else "secondary", disabled=not activo,
                  help="Desmarcar" if hecha else "Marcar como realizada", on_click=_toggle, args=(con, a["id"], not hecha), **FULL)
        _accion(a, iid)
        with st.expander("Observación" + (" ✎" if a["observacion"] else "")):
            txt = st.text_area("Observación", value=a["observacion"] or "", key=f"obs_{a['id']}", label_visibility="collapsed", max_chars=500,
                               placeholder="¿Cómo le fue? ¿Qué quiere comentar con su profesional?")
            if st.button("Guardar observación", key=f"gobs_{a['id']}"):
                planes.observar(con, a["id"], txt); nav.flash("Observación guardada."); st.rerun()


def _toggle(con, aid, hecha):
    try:
        planes.marcar(con, aid, hecha)
    except db.ValidationError as ex:
        nav.flash(str(ex), "warning")


def _cambiar_estado(con, iid, accion):
    try:
        if accion == "pausar":
            planes.pausar(con, iid); nav.flash("Programa en pausa. Sus avances quedan guardados.", "info")
        elif accion == "reanudar":
            d = planes.reanudar(con, iid); nav.flash(f"Programa reanudado. Las actividades pendientes se movieron {d} día(s)." if d else "Programa reanudado.")
        elif accion == "finalizar":
            planes.finalizar(con, iid); nav.flash("Programa finalizado. Puede consultarlo en «Programas finalizados».", "info")
            nav.ir("planes", planes_vista="lista")
    except db.ValidationError as ex:
        nav.flash(str(ex), "warning")


def seccion_registros(con, i, activo):
    pid = i["programa_id"]
    tipos = {"prog_nutricion": ["comida", "habito"], "prog_actividad": ["actividad"], "prog_seguimiento": []}.get(pid, ["comida", "habito", "actividad"])
    if not tipos:
        card('<p class="tr-title">Registros clínicos</p><p class="tr-sub">Este programa usa sus registros de <b>Seguimiento de salud</b> (síntomas y peso opcional) '
             'y de <b>Eventos adversos</b> (estado de evolución).</p>')
        c1, c2 = st.columns(2)
        c1.button("Seguimiento de salud", key="go_seg", icon=":material/monitoring:", on_click=nav.ir, args=("seguimiento",), **FULL)
        c2.button("Eventos adversos", key="go_ev", icon=":material/edit_note:", on_click=nav.ir, args=("eventos",), **FULL)
        return
    st.markdown("<h3>Mis registros</h3>", unsafe_allow_html=True)
    nombres = {"comida": "Comidas", "habito": "Hábitos", "actividad": "Actividad realizada"}
    with st.form(f"form_reg_{i['id']}", clear_on_submit=True):
        c1, c2 = st.columns(2)
        tipo = c1.selectbox("Tipo de registro", tipos, format_func=lambda t: nombres[t])
        f = c2.date_input("Fecha", value=date.today(), max_value=date.today(), format="DD/MM/YYYY")
        det = st.text_input("¿Qué registró?", placeholder="Ej.: almuerzo con verduras · 6 vasos de agua · caminata en el parque", max_chars=300)
        c3, c4 = st.columns(2)
        mins = c3.number_input("Minutos (solo actividad)", min_value=0, max_value=600, value=None, placeholder="Opcional")
        nota = c4.text_input("Nota (opcional)", max_chars=300)
        if st.form_submit_button("Guardar registro", disabled=not activo, **FULL):
            try:
                planes.registrar(con, i["id"], tipo, f, det, mins if tipo == "actividad" else None, nota)
                nav.flash("Registro guardado."); st.rerun()
            except db.ValidationError as ex:
                st.error(str(ex))
    regs = planes.registros(con, i["id"])
    if not regs:
        st.markdown('<p class="tr-muted">Aún no hay registros.</p>', unsafe_allow_html=True)
    for r in regs[:6]:
        extra = f" · {r['minutos']} min" if r["minutos"] else ""
        st.markdown(f'<div class="tr-card" style="padding:.7rem .9rem"><span class="tr-chip">{e(nombres[r["tipo"]])}</span>'
                    f'<span class="tr-sub">{fecha_corta(r["fecha"])}{extra}</span><p style="margin:.25rem 0 0">{e(r["detalle"])}</p>'
                    + (f'<p class="tr-sub">{e(r["nota"])}</p>' if r["nota"] else "") + "</div>", unsafe_allow_html=True)


def vista_plan(con, user):
    iid = st.session_state.get("insc_sel")
    i = planes.obtener(con, iid) if iid else None
    if not i or i["usuario_id"] != user["id"]:
        nav.ir("planes", planes_vista="lista"); st.rerun()
    p, pr = i["programa"], planes.progreso(con, iid)
    activo = i["estado"] == "activo"
    volver("Mis planes", planes_vista="lista")
    cls, txt = ESTADO_CHIP[i["estado"]]
    med = f'<span class="tr-chip lime">💊 {e(i["medicamento_declarado"])}</span>' if p["medicamento"] and i["medicamento_declarado"] else ""
    st.markdown(f'<div class="tr-card dark"><div class="tr-row">{ring(pr["pct"], 104, 10, "#D7E8B0", "rgba(255,255,255,.18)", sub="total", text_color="#fff")}'
                f'<div class="tr-grow"><span class="tr-chip {cls}" style="color:#1F2E27">{txt}</span>{med}'
                f'<h2 style="margin:.3rem 0 0;color:#fff">{e(p["nombre"])}</h2>'
                f'<p style="margin:.2rem 0 0;opacity:.85;font-size:.85rem">Semana {pr["semana_actual"]} de 4 · {pr["hechas"]} de {pr["total"]} actividades · '
                f'inició el {fecha_larga(i["fecha_inicio"])}</p></div></div></div>', unsafe_allow_html=True)
    if not activo and i["estado"] == "pausado":
        st.markdown(f'<div class="tr-warn">⏸️ Programa en pausa desde {fecha_corta(i["fecha_pausa"])}. Reanúdelo para registrar avances.</div>', unsafe_allow_html=True)
    with st.container(key="row_estado"):
        b1, b2 = st.columns(2)
        if i["estado"] == "activo":
            b1.button("Pausar", key="btn_pausar", icon=":material/pause:", on_click=_cambiar_estado, args=(con, iid, "pausar"), **FULL)
        elif i["estado"] == "pausado":
            b1.button("Reanudar", key="btn_reanudar", icon=":material/play_arrow:", type="primary", on_click=_cambiar_estado, args=(con, iid, "reanudar"), **FULL)
        b2.button("Ver ficha", key="btn_ficha", icon=":material/info:", on_click=nav.ver_programa, args=(i["programa_id"],), **FULL)

    # Selector de semana + calendario
    st.markdown("<h3 style='margin-top:.6rem'>Calendario de 4 semanas</h3>", unsafe_allow_html=True)
    key = f"semana_{iid}"
    if key not in st.session_state:
        st.session_state[key] = pr["semana_actual"]
    sem = st.radio("Semana", [1, 2, 3, 4], key=key, horizontal=True, format_func=lambda s: f"Semana {s}" + (" · actual" if s == pr["semana_actual"] else ""),
                   label_visibility="collapsed")
    acts = planes.actividades(con, iid, sem)
    ps = pr["por_semana"][sem - 1]
    if acts:
        primera = acts[0]
        inicio_sem = date.fromisoformat(primera["fecha"]) - timedelta(days=primera["dia"] - 1)
        st.markdown(f'<div class="tr-card">{week_strip(inicio_sem, acts)}<div class="tr-row" style="margin-top:.5rem"><div class="tr-grow">{bar(ps["pct"])}</div>'
                    f'<b>{ps["hechas"]}/{ps["total"]}</b></div></div>', unsafe_allow_html=True)
    for a in acts:
        tarjeta_actividad(con, a, activo, iid)

    # Progreso semanal
    st.markdown("<h3>Progreso por semana</h3>", unsafe_allow_html=True)
    filas = "".join(f'<div style="margin:.35rem 0"><div class="tr-row"><span class="tr-grow" style="font-size:.85rem">Semana {w["semana"]}</span>'
                    f'<b style="font-size:.85rem">{w["hechas"]}/{w["total"]}</b></div>{bar(w["pct"], "lime" if w["semana"] != pr["semana_actual"] else "")}</div>'
                    for w in pr["por_semana"])
    card(filas)

    # Registros del programa
    seccion_registros(con, i, activo)

    # Observaciones
    st.markdown("<h3>Observaciones</h3>", unsafe_allow_html=True)
    with st.form(f"form_nota_{iid}", clear_on_submit=True):
        texto = st.text_area("Observación de la semana", max_chars=800, placeholder="¿Cómo fue esta semana? ¿Qué quiere comentar en su próximo control?")
        if st.form_submit_button(f"Guardar observación de la semana {sem}", **FULL):
            try:
                planes.agregar_nota(con, iid, sem, texto); nav.flash("Observación guardada."); st.rerun()
            except db.ValidationError as ex:
                st.error(str(ex))
    for n in planes.notas(con, iid)[:5]:
        st.markdown(f'<div class="tr-card cream" style="padding:.7rem .9rem"><span class="tr-chip">Semana {n["semana"]}</span>'
                    f'<span class="tr-sub">{fecha_corta(n["fecha"])}</span><p style="margin:.25rem 0 0">{e(n["texto"])}</p></div>', unsafe_allow_html=True)

    # Objetivos y preferencias
    with st.expander("Objetivos y preferencias"):
        opciones = list(dict.fromkeys(p["objetivos"] + OBJETIVOS_GENERALES + i["objetivos"]))
        obj = st.multiselect("Objetivos", opciones, default=i["objetivos"], key=f"obj_{iid}")
        pref = i["preferencias"]
        dias = st.multiselect("Días preferidos", planes.DIAS_SEMANA, default=[d for d in pref.get("dias", []) if d in planes.DIAS_SEMANA], key=f"dias_{iid}")
        mom = st.radio("Momento del día", planes.MOMENTOS, index=planes.MOMENTOS.index(pref["momento"]) if pref.get("momento") in planes.MOMENTOS else 0, horizontal=True, key=f"mom_{iid}")
        if st.button("Guardar objetivos", key=f"gobj_{iid}"):
            try:
                planes.actualizar_objetivos(con, iid, obj, {**pref, "dias": dias, "momento": mom}); nav.flash("Objetivos actualizados."); st.rerun()
            except db.ValidationError as ex:
                st.error(str(ex))
    if p["medicamento"] or i["programa_id"] == "prog_seguimiento":
        alarma_box()
    if i["estado"] != "finalizado":
        with st.expander("Finalizar programa"):
            st.caption("Finalizar cierra el programa; sus registros se conservan. Podrá inscribirse de nuevo más adelante.")
            st.button("Finalizar programa", key="btn_finalizar", on_click=_cambiar_estado, args=(con, iid, "finalizar"))


def render(con, user):
    vista = st.session_state.get("planes_vista", "lista")
    {"lista": vista_lista, "ficha": vista_ficha, "inscribir": vista_inscribir, "plan": vista_plan}.get(vista, vista_lista)(con, user)
