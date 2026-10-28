"""Identidad visual de The Reset: CSS mobile-first y componentes HTML reutilizables."""
from __future__ import annotations

import html
from datetime import date, timedelta

import inspect

import streamlit as st

# Compatibilidad entre versiones de Streamlit: «width='stretch'» reemplaza a «use_container_width=True» en versiones nuevas
FULL = {"width": "stretch"} if "width" in inspect.signature(st.button).parameters else {"use_container_width": True}
FULL_CHART = {"width": "stretch"} if "width" in inspect.signature(st.plotly_chart).parameters else {"use_container_width": True}

DARK, MID, SAGE, SAGE_L, CREAM, CREAM_2, LIME, WHITE = "#1F2E27", "#4F6F5F", "#8FA89A", "#DDE7D7", "#F6F3E8", "#EFEADB", "#D7E8B0", "#FFFFFF"
INK, MUTED, ALERT = "#1F2E27", "#6B7468", "#B5523B"
e = html.escape

MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
MESES_L = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
html, body, .stApp, [class*="css"], button, input, textarea, select {{ font-family: 'Plus Jakarta Sans', 'Segoe UI', system-ui, sans-serif !important; }}
.stApp {{ background: linear-gradient(180deg, {CREAM} 0%, #EEF2E6 100%); }}
[data-testid="stHeaderActionElements"], header[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"], #MainMenu, footer {{ display: none !important; }}
section[data-testid="stSidebar"], [data-testid="collapsedControl"], [data-testid="stSidebarCollapsedControl"] {{ display: none !important; }}
.block-container {{ max-width: 480px; padding: 0.9rem 1rem 7.5rem 1rem !important; }}
@media (min-width: 900px) {{ .block-container {{ max-width: 860px; padding-top: 1.4rem !important; }} }}
h1, h2, h3 {{ color: {INK}; letter-spacing: -0.02em; }}
h1 {{ font-size: 1.65rem !important; font-weight: 800 !important; }} h2 {{ font-size: 1.25rem !important; }} h3 {{ font-size: 1.08rem !important; }}
p, li, label, .stMarkdown {{ color: {INK}; }}

/* Tarjetas nativas (st.container(border=True)) */
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]) {{ border-radius: 22px; }}
div[data-testid="stVerticalBlockBorderWrapper"] {{ border-radius: 22px !important; border-color: #E6E9DF !important; background: {WHITE}; }}

/* Botones */
.stButton > button, .stFormSubmitButton > button, .stDownloadButton > button {{ border-radius: 999px !important; min-height: 2.65rem; font-weight: 600; border: 1px solid #D9DED3; background: {WHITE}; color: {INK}; }}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"], .stFormSubmitButton > button[kind="primaryFormSubmit"] {{ background: {DARK} !important; border-color: {DARK} !important; color: #fff !important; }}
.stButton > button[kind="primary"] p, .stFormSubmitButton > button[kind="primary"] p, .stFormSubmitButton > button[kind="primaryFormSubmit"] p {{ color: #fff !important; }}
.stButton > button:hover {{ border-color: {MID}; color: {MID}; }}
.stButton > button[kind="primary"]:hover {{ background: {MID} !important; border-color: {MID} !important; }}

/* Entradas */
[data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="textarea"], .stDateInput > div > div, .stNumberInput > div > div {{ border-radius: 14px !important; }}
.stTextInput input, .stNumberInput input, .stTextArea textarea, [data-baseweb="select"] > div {{ background: #FAFAF6 !important; }}

/* Radio como píldoras (selector de semana, filtros) */
div[role="radiogroup"] {{ gap: .35rem; flex-wrap: wrap; }}
div[role="radiogroup"] > label {{ background: {WHITE}; border: 1px solid #DDE2D6; border-radius: 999px; padding: .28rem .85rem !important; margin: 0 !important; }}
div[role="radiogroup"] > label:has(input:checked) {{ background: {DARK}; border-color: {DARK}; }}
div[role="radiogroup"] > label:has(input:checked) p {{ color: #fff !important; }}
div[role="radiogroup"] > label > div:first-child {{ display: none; }}
/* Estructura de radios en versiones recientes de Streamlit (react-aria) */
[data-testid="stRadioGroup"] {{ gap: .35rem !important; flex-wrap: wrap; }}
[data-testid="stRadioGroup"] label[data-testid="stRadioOption"] {{ background: {WHITE}; border: 1px solid #DDE2D6; border-radius: 999px; padding: .3rem .9rem; cursor: pointer; }}
[data-testid="stRadioGroup"] label[data-testid="stRadioOption"][data-selected="true"] {{ background: {DARK}; border-color: {DARK}; }}
[data-testid="stRadioGroup"] label[data-testid="stRadioOption"][data-selected="true"] p {{ color: #fff !important; }}
[data-testid="stRadioGroup"] label[data-testid="stRadioOption"] > div > div:first-child {{ display: none !important; }}

/* Pestañas */
.stTabs [data-baseweb="tab-list"] {{ gap: .3rem; background: #E9EDE3; padding: .25rem; border-radius: 999px; }}
.stTabs [data-baseweb="tab"] {{ border-radius: 999px; padding: .35rem .9rem; height: auto; }}
.stTabs [aria-selected="true"] {{ background: {WHITE}; }}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {{ display: none; }}

/* Expanders */
[data-testid="stExpander"] details {{ border-radius: 18px !important; border-color: #E6E9DF !important; background: {WHITE}; }}

/* Filas que NO deben apilarse en móvil (contenedores con key que empieza por row_) */
[class*="st-key-row_"] [data-testid="stHorizontalBlock"] {{ flex-wrap: nowrap !important; gap: .5rem !important; align-items: center; }}
[class*="st-key-row_"] [data-testid="stHorizontalBlock"] > div {{ min-width: 0 !important; }}
[class*="st-key-row_"] [data-testid="column"], [class*="st-key-row_"] [data-testid="stColumn"] {{ min-width: 0 !important; width: auto !important; }}

[class*="st-key-row_act_"] .stButton > button {{ padding-left: .4rem !important; padding-right: .4rem !important; }}
[class*="st-key-row_act_"] .stButton > button p, [class*="st-key-row_pend_"] .stButton > button p {{ white-space: nowrap; font-size: .8rem; }}

/* Barra de navegación inferior */
.st-key-bottom_nav {{ position: fixed; bottom: 10px; left: 50%; transform: translateX(-50%); width: min(460px, 96vw); z-index: 1000;
  background: rgba(255,255,255,.96); backdrop-filter: blur(10px); border-radius: 26px; box-shadow: 0 8px 28px rgba(31,46,39,.16); padding: 6px 6px; }}
.st-key-bottom_nav [data-testid="stHorizontalBlock"] {{ gap: 2px !important; flex-wrap: nowrap !important; }}
.st-key-bottom_nav [data-testid="stColumn"], .st-key-bottom_nav [data-testid="column"] {{ min-width: 0 !important; flex: 1 1 0 !important; width: auto !important; }}
.st-key-bottom_nav [data-testid="stVerticalBlock"] {{ gap: 0 !important; }}
.st-key-bottom_nav button span[data-has-shortcut] {{ display: flex !important; flex-direction: column !important; align-items: center; gap: 1px; }}
.st-key-bottom_nav button [data-testid="stMarkdownContainer"] p {{ overflow: visible; text-overflow: clip; }}
.st-key-bottom_nav .stButton > button {{ border: none !important; background: transparent; min-height: 3.4rem; padding: 4px 0 !important; border-radius: 20px !important; width: 100%; }}
.st-key-bottom_nav .stButton > button > div {{ flex-direction: column !important; gap: 0 !important; }}
.st-key-bottom_nav .stButton > button p {{ font-size: .64rem !important; font-weight: 600; margin: 0; white-space: nowrap; letter-spacing: -.01em; }}
@media (max-width: 380px) {{ .st-key-bottom_nav .stButton > button p {{ font-size: .58rem !important; }} }}
.st-key-bottom_nav .stButton > button[kind="primary"] {{ background: {DARK} !important; }}
.st-key-bottom_nav .stButton > button span[data-testid="stIconMaterial"] {{ font-size: 1.35rem; }}

/* Componentes HTML */
.tr-top {{ display:flex; align-items:center; justify-content:space-between; }}
.tr-hello {{ display:flex; align-items:center; gap:.7rem; }}
.tr-avatar {{ width:46px; height:46px; border-radius:50%; background:{SAGE}; color:#fff; display:flex; align-items:center; justify-content:center; font-weight:800; font-size:1.05rem; border:3px solid #fff; box-shadow:0 2px 8px rgba(0,0,0,.08); }}
.tr-hello small {{ color:{MUTED}; display:block; font-size:.78rem; }} .tr-hello b {{ font-size:1rem; }}
.tr-card {{ background:{WHITE}; border-radius:24px; padding:1rem 1.1rem; box-shadow:0 2px 10px rgba(31,46,39,.05); border:1px solid #EBEEE5; margin-bottom:.7rem; }}
.tr-card.lime {{ background: linear-gradient(135deg, #E9F3D2 0%, #D7E8B0 100%); border-color:#D3E4AE; }}
.tr-card.cream {{ background:{CREAM_2}; border-color:#E6DFC8; }}
.tr-card.dark {{ background: linear-gradient(135deg, {DARK} 0%, {MID} 100%); color:#fff; border:none; }}
.tr-card.dark * {{ color:#fff; }}
.tr-label {{ font-size:.72rem; letter-spacing:.06em; text-transform:uppercase; color:{MUTED}; font-weight:700; }}
.tr-big {{ font-size:1.9rem; font-weight:800; line-height:1.1; color:{INK}; }}
.tr-muted {{ color:{MUTED}; font-size:.84rem; }}
.tr-chip {{ display:inline-block; padding:.18rem .65rem; border-radius:999px; font-size:.74rem; font-weight:700; margin:.1rem .25rem .1rem 0; background:#EEF1EA; color:{INK}; }}
.tr-chip.ok {{ background:#DDEBD9; color:#2E5B3B; }} .tr-chip.miss {{ background:#F6E1D9; color:#8A3B1E; }} .tr-chip.lime {{ background:{LIME}; color:{DARK}; }}
.tr-chip.dark {{ background:{DARK}; color:#fff; }} .tr-chip.warn {{ background:#FFF1CC; color:#7A5B00; }}
.tr-row {{ display:flex; align-items:center; gap:.8rem; }}
.tr-grow {{ flex:1; min-width:0; }}
.tr-title {{ font-weight:700; font-size:1rem; color:{INK}; margin:0; }}
.tr-sub {{ color:{MUTED}; font-size:.82rem; margin:.1rem 0 0 0; }}
.tr-icon {{ width:44px; height:44px; border-radius:14px; display:flex; align-items:center; justify-content:center; font-size:1.3rem; background:{SAGE_L}; flex-shrink:0; }}
.tr-week {{ display:flex; justify-content:space-between; gap:.25rem; margin:.4rem 0 .2rem; }}
.tr-day {{ flex:1; text-align:center; }}
.tr-day small {{ display:block; color:{MUTED}; font-size:.7rem; margin-bottom:.25rem; }}
.tr-day span {{ display:inline-flex; width:2.1rem; height:2.1rem; border-radius:50%; align-items:center; justify-content:center; font-size:.85rem; font-weight:600; border:1px solid #E1E5DB; background:#fff; }}
.tr-day span.today {{ background:{DARK}; color:#fff; border-color:{DARK}; }}
.tr-day span.done {{ background:{LIME}; border-color:{LIME}; }}
.tr-day i {{ display:block; height:6px; }} .tr-day i b {{ display:inline-block; width:5px; height:5px; border-radius:50%; background:{MID}; margin:0 1px; }}
.tr-bar {{ height:8px; background:#E7EBE2; border-radius:99px; overflow:hidden; }} .tr-bar > div {{ height:100%; background:{MID}; border-radius:99px; }}
.tr-bar.lime > div {{ background:#9BC26A; }}
.tr-banner {{ background:#EAF0E2; border-radius:16px; padding:.55rem .85rem; font-size:.78rem; color:{INK}; margin-bottom:.8rem; border:1px solid #DCE5D2; }}
.tr-warn {{ background:#FFF4D6; border:1px solid #F0DFA6; border-radius:16px; padding:.7rem .9rem; font-size:.85rem; margin:.4rem 0 .8rem; }}
.tr-alert {{ background:#FBEAE4; border:1px solid #EFC9BC; border-radius:16px; padding:.7rem .9rem; font-size:.85rem; margin:.4rem 0 .8rem; }}
.tr-kv {{ display:flex; justify-content:space-between; padding:.38rem 0; border-bottom:1px solid #F0F2EC; font-size:.88rem; }}
.tr-kv:last-child {{ border-bottom:none; }}
.tr-grid2 {{ display:grid; grid-template-columns:1fr 1fr; gap:.6rem; }}
.tr-stat {{ background:#fff; border-radius:20px; padding:.8rem .9rem; border:1px solid #EBEEE5; }}
.tr-stat .v {{ font-size:1.45rem; font-weight:800; }} .tr-stat .l {{ font-size:.75rem; color:{MUTED}; }}
.tr-brand {{ font-weight:800; font-size:1.05rem; color:{DARK}; letter-spacing:-.01em; }}
</style>
"""


def inject():
    st.markdown(CSS, unsafe_allow_html=True)


def num(x, d=1):
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fecha_corta(s):
    if not s:
        return "—"
    d = s if isinstance(s, date) else date.fromisoformat(str(s)[:10])
    return f"{DIAS[d.weekday()]} {d.day} {MESES[d.month - 1]}"


def fecha_larga(s):
    d = s if isinstance(s, date) else date.fromisoformat(str(s)[:10])
    return f"{d.day} de {MESES_L[d.month - 1]} de {d.year}"


def iniciales(nombre):
    p = [x for x in nombre.split() if x]
    return (p[0][0] + (p[1][0] if len(p) > 1 else "")).upper() if p else "?"


def ring(pct, size=118, stroke=11, color=MID, track="#E5EADF", label=None, sub=None, text_color=INK):
    r = (size - stroke) / 2
    c = 2 * 3.14159 * r
    off = c * (1 - max(0, min(100, pct)) / 100)
    label = label if label is not None else f"{num(pct, 0)}%"
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" style="flex-shrink:0">'
            f'<circle cx="{size/2}" cy="{size/2}" r="{r}" fill="none" stroke="{track}" stroke-width="{stroke}"/>'
            f'<circle cx="{size/2}" cy="{size/2}" r="{r}" fill="none" stroke="{color}" stroke-width="{stroke}" stroke-linecap="round" '
            f'stroke-dasharray="{c:.1f}" stroke-dashoffset="{off:.1f}" transform="rotate(-90 {size/2} {size/2})"/>'
            f'<text x="50%" y="{"47%" if sub else "53%"}" text-anchor="middle" dominant-baseline="middle" font-size="{size*0.2:.0f}" font-weight="800" fill="{text_color}" font-family="Plus Jakarta Sans, sans-serif">{e(label)}</text>'
            + (f'<text x="50%" y="66%" text-anchor="middle" font-size="{size*0.095:.0f}" fill="{text_color}" opacity=".75" font-family="Plus Jakarta Sans, sans-serif">{e(sub)}</text>' if sub else "")
            + "</svg>")


def bar(pct, cls=""):
    return f'<div class="tr-bar {cls}"><div style="width:{max(0, min(100, pct)):.0f}%"></div></div>'


def week_strip(inicio: date, actividades_semana: list, hoy: date | None = None):
    """Fila de 7 días (estilo calendario semanal) con puntos por actividad y estado."""
    hoy = hoy or date.today()
    out = []
    for i in range(7):
        d = inicio + timedelta(days=i)
        acts = [a for a in actividades_semana if a["fecha"] == d.isoformat()]
        cls = "today" if d == hoy else ("done" if acts and all(a["completada"] for a in acts) else "")
        dots = "".join("<b></b>" for _ in acts[:3])
        out.append(f'<div class="tr-day"><small>{DIAS[d.weekday()]}</small><span class="{cls}">{d.day}</span><i>{dots}</i></div>')
    return f'<div class="tr-week">{"".join(out)}</div>'


def card(inner, cls=""):
    st.markdown(f'<div class="tr-card {cls}">{inner}</div>', unsafe_allow_html=True)


def banner():
    st.markdown('<div class="tr-banner">🩺 The Reset no reemplaza a su profesional de salud ni prescribe medicamentos o dosis. '
                'Ante una emergencia llame al <b>123</b>.</div>', unsafe_allow_html=True)


CAT_ICON = {"Educación": "📘", "Control": "🩺", "Registro": "📝", "Seguimiento": "📈", "Nutrición": "🥗", "Actividad": "👟"}
