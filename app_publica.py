# -*- coding: utf-8 -*-
"""
Pregúntale a DayByDay — APP PÚBLICA (identidad job&talent, lee el cubo en Neon).

Deploy en Streamlit Community Cloud. Secrets:
    DATABASE_URL   = "postgresql://..."
    GROQ_API_KEY   = "gsk_..."
    GEMINI_API_KEY = "..."   (respaldo, opcional)
Archivos que deben ir en el repo: app_publica.py, motor_nube.py, logos.py,
marca.py, fondo.jpg, requirements.txt y .streamlit/config.toml
"""

import os
import html as _html
import streamlit as st
import plotly.express as px

try:
    for _k in ("DATABASE_URL", "GROQ_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"):
        if _k in st.secrets and not os.environ.get(_k):
            os.environ[_k] = str(st.secrets[_k])
except Exception:
    pass

import motor_nube as motor
try:
    from logos import LOGOS
except Exception:
    LOGOS = {}
try:
    from marca import JOBTALENT
except Exception:
    JOBTALENT = ""

# ---------- Paleta job&talent (azul oscuro + cian) ----------
BG = "#0A1730"
PANEL = "#10234B"
LINE = "#24417A"
CYAN = "#2EA6FF"
TEAL = "#00E0C7"
INK = "#EAF2FD"
MUTED = "#93A9CE"

st.set_page_config(page_title="Pregúntale a DayByDay", page_icon="◆", layout="wide")

st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');

  .stApp {{ background:{BG}; }}
  .stApp, .block-container, [data-testid="stMarkdownContainer"],
  .stButton button, .stTextInput input, [data-testid="stSidebar"] {{
     font-family:'IBM Plex Sans', system-ui, sans-serif;
  }}
  .block-container {{ max-width:1080px; padding-top:.8rem; }}
  #MainMenu, footer, [data-testid="stToolbar"] {{ visibility:hidden; }}
  [data-testid="stHeader"] {{ background:transparent; }}

  /* barra superior con el logo job&talent */
  .topbar {{ display:flex; align-items:center; gap:14px; padding:2px 2px 14px; }}
  .topbar img {{ height:36px; border-radius:8px; display:block; }}
  .topbar .cin {{ color:{MUTED}; font-size:.9rem; font-weight:500; }}

  /* banner (fondo) con esquinas redondeadas */
  [data-testid="stImage"] img {{ max-width:820px; border-radius:16px; box-shadow:0 0 0 1px {LINE}; }}

  .hint {{ color:{MUTED}; font-size:.92rem; margin:22px 0 6px; }}

  .chips {{ margin:4px 0 2px; }}
  .chips .lbl {{ color:{MUTED}; font-size:.9rem; margin-right:8px; }}
  .chip {{ display:inline-block; background:{PANEL}; color:#BFE0FF; border:1px solid {LINE};
           padding:4px 12px; border-radius:8px; font-size:.82rem; font-weight:500;
           margin:3px 6px 3px 0; }}

  .logochip {{ display:inline-flex; align-items:center; background:#fff; border-radius:12px;
               padding:9px 18px; box-shadow:0 2px 10px rgba(0,0,0,.25); }}
  .logochip img {{ height:40px; display:block; }}
  .roster {{ display:flex; flex-wrap:wrap; align-items:center; gap:10px; margin:14px 0 2px; }}
  .roster .lbl {{ color:{MUTED}; font-size:.8rem; margin-right:2px; }}
  .rchip {{ display:inline-flex; align-items:center; background:#fff; border-radius:8px;
            padding:6px 12px; height:38px; }}
  .rchip img {{ height:22px; display:block; }}

  .kpi {{ border-left:4px solid {CYAN}; padding:4px 0 4px 22px; margin:20px 0 6px; }}
  .kpi .ctx  {{ color:{MUTED}; font-size:.96rem; margin:0 0 7px; }}
  .kpi .val  {{ font-size:3.2rem; font-weight:700; color:#F4F9FF; line-height:1;
                letter-spacing:-.025em; font-variant-numeric:tabular-nums; }}
  .kpi .base {{ color:{MUTED}; font-size:.9rem; margin-top:9px; }}

  .lectura {{ background:{PANEL}; border:1px solid {LINE}; border-radius:12px;
              padding:16px 20px; color:{INK}; font-size:.98rem; line-height:1.55; margin:6px 0 2px; }}
  .lectura b {{ color:#FFFFFF; }}

  .pie {{ color:{MUTED}; font-size:.82rem; margin-top:34px; padding-top:14px;
          border-top:1px solid {LINE}; line-height:1.6; }}

  .stButton button {{ background:{PANEL}; border:1px solid {LINE}; color:{INK};
                      border-radius:10px; font-weight:500; font-size:.88rem; padding:8px 10px; }}
  .stButton button:hover {{ border-color:{CYAN}; color:{CYAN}; }}
  .stTextInput input {{ background:{PANEL}; border-radius:12px; border:1.5px solid {LINE};
                        font-size:1.03rem; padding:14px 16px; color:{INK}; }}
  .stTextInput input:focus {{ border-color:{CYAN}; box-shadow:none; }}

  [data-testid="stSidebar"] {{ background:{PANEL}; border-right:1px solid {LINE}; }}
  [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{ color:{INK}; font-weight:600; }}
  [data-testid="stSidebar"] label, [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {{ color:{INK}; }}
  [data-testid="stSidebar"] [data-baseweb="select"] > div {{ background:{BG}; border-color:{LINE}; color:{INK}; }}
  .stTextInput input::placeholder {{ color:#8198C4; opacity:1; }}
  [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {{ color:{MUTED}; }}
  [data-testid="stExpander"] {{ border:1px solid {LINE}; border-radius:12px; background:{PANEL}; }}
  [data-testid="stExpander"] summary {{ color:{INK}; }}
  [data-testid="stExpander"] summary:hover {{ color:{CYAN}; }}
  [data-testid="stExpander"] summary svg {{ fill:{MUTED}; }}

  .dtitle {{ color:{INK}; font-weight:600; font-size:.98rem; margin:16px 0 8px; }}
  table.dt {{ width:100%; border-collapse:collapse; background:{PANEL};
              border:1px solid {LINE}; border-radius:12px; overflow:hidden; }}
  table.dt th {{ text-align:left; color:{MUTED}; font-weight:500; font-size:.8rem;
                 padding:9px 14px; border-bottom:1px solid {LINE}; }}
  table.dt td {{ color:{INK}; font-size:.9rem; padding:8px 14px;
                 border-bottom:1px solid rgba(255,255,255,.06); }}
  table.dt th.n, table.dt td.n {{ text-align:right; font-variant-numeric:tabular-nums; }}
  table.dt tr:last-child td {{ border-bottom:none; }}
</style>
""", unsafe_allow_html=True)

# ---------- Barra superior (job&talent) ----------
if JOBTALENT:
    st.markdown(
        f'<div class="topbar"><img src="{JOBTALENT}">'
        f'<span class="cin">Centro de Inteligencia de Negocios</span></div>',
        unsafe_allow_html=True,
    )

# ---------- Banner ----------
_BANNER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fondo.jpg")
if os.path.exists(_BANNER):
    st.image(_BANNER, use_container_width=True)
else:
    st.caption("Falta el banner: pon el archivo fondo.jpg junto a app_publica.py.")


@st.cache_data(ttl=1800, show_spinner="Cargando...")
def cargar_clientes():
    return motor.clientes()


try:
    marcas = cargar_clientes()
except Exception as e:
    st.error(f"No pude leer el cubo. Revisa la conexión (DATABASE_URL). Detalle: {e}")
    st.stop()

if not marcas:
    st.error("El cubo está vacío. Corre el refresco para llenarlo y recarga esta página.")
    st.stop()

with st.sidebar:
    st.subheader("Ajustes")
    cliente_sel = st.selectbox("Cliente", ["(Detectar desde la pregunta)"] + list(marcas.keys()))
    ventana_sel = st.selectbox(
        "Ventana de tiempo", ["(Auto)"] + motor.VENTANAS,
        format_func=lambda k: "Auto (según la pregunta)" if k == "(Auto)" else motor.VENTANA_LABEL.get(k, k),
    )
    topn = st.slider("Máximo de barras", 5, 20, 12)

if "pregunta" not in st.session_state:
    st.session_state.pregunta = ""

def set_q(q):
    st.session_state.pregunta = q

st.markdown('<div class="hint">Pregunta lo que necesites saber de la operación</div>', unsafe_allow_html=True)
pregunta = st.text_input(
    "Tu pregunta", key="pregunta",
    placeholder="Ej: ¿cómo va el % de agotados de Derco por cadena en los últimos 3 meses?",
    label_visibility="collapsed",
)

st.caption("O empieza con una de estas:")
ejemplos = [
    "¿Cómo va la cobertura de Henkel?",
    "¿Qué marcas tienen más agotados en Unilever?",
    "Ventas de Solla por zona este mes",
    "Actividades de Black & Decker por tipo",
]
cols = st.columns(len(ejemplos))
for c, ex in zip(cols, ejemplos):
    c.button(ex, on_click=set_q, args=(ex,), use_container_width=True)

if LOGOS:
    _rchips = "".join(f'<span class="rchip"><img src="{u}"></span>' for u in LOGOS.values())
    st.markdown(f'<div class="roster"><span class="lbl">Clientes</span>{_rchips}</div>',
                unsafe_allow_html=True)

if not pregunta.strip():
    st.stop()

intencion, motor_usado = motor.interpretar(pregunta, marcas)

if cliente_sel != "(Detectar desde la pregunta)":
    ids, cname = marcas[cliente_sel], cliente_sel
else:
    ids, cname = intencion["cliente_ids"], intencion["cliente_nombre"]

if not ids:
    st.warning("¿De qué cliente? Elígelo en la barra lateral o nómbralo en la pregunta.")
    st.stop()

ventana = intencion["ventana"] if ventana_sel == "(Auto)" else ventana_sel
dom, metrica, dimension = intencion["dominio"], intencion["metrica"], intencion["dimension"]
meta = motor.DOMINIOS[dom]
vlabel = motor.VENTANA_LABEL.get(ventana, ventana)

try:
    valor, base, mkey, m, sql_kpi = motor.kpi(dom, ids, ventana, metrica)
    dfg, dkey, m2, sql_grp = motor.por_dimension(dom, ids, ventana, metrica, dimension)
except Exception as e:
    st.error(f"Hubo un problema al consultar el cubo: {e}")
    st.stop()

dim_label = dkey.replace("_", " ")
chips = "".join(f'<span class="chip">{t}</span>' for t in
                [meta["nombre"], cname, m["label"], f"por {dim_label}", vlabel])
st.markdown(f'<div class="chips"><span class="lbl">Entendí</span>{chips}</div>', unsafe_allow_html=True)
st.caption(f"Interpretado con {motor_usado.split(' ')[0]}")

_logo = LOGOS.get(cname.strip().upper())
if _logo:
    st.markdown(
        f'<div style="margin:22px 0 -4px;"><span class="logochip"><img src="{_logo}"></span></div>',
        unsafe_allow_html=True,
    )

st.markdown(
    f'<div class="kpi"><div class="ctx">{m["label"]} de {cname}, {vlabel}</div>'
    f'<div class="val">{motor.fmt_valor(valor, m["fmt"])}</div>'
    f'<div class="base">sobre {motor.fmt_valor(base, "num")} registros</div></div>',
    unsafe_allow_html=True,
)

if dfg.empty:
    st.markdown('<div class="lectura">No hay registros para esto en la ventana elegida. '
                'Amplía la ventana de tiempo o cambia el cliente.</div>', unsafe_allow_html=True)
    st.stop()

top = dfg.head(topn).sort_values("VALOR", ascending=True)
top["ETIQUETA"] = top["VALOR"].apply(lambda x: motor.fmt_valor(x, m["fmt"]))
fig = px.bar(top, x="VALOR", y="DIMENSION", orientation="h", text="ETIQUETA",
             color_discrete_sequence=[CYAN])
fig.update_traces(textposition="outside", cliponaxis=False,
                  textfont=dict(color=INK, size=12), marker_line_width=0)
fig.update_layout(
    title=dict(text=f'{m["label"]} por {dim_label} ({cname})',
               font=dict(size=15, color=INK), x=0, xanchor="left"),
    font=dict(family="IBM Plex Sans, sans-serif", color=INK, size=13),
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=0, r=36, t=48, b=4), height=max(300, 36 * len(top) + 80),
)
fig.update_xaxes(visible=False)
fig.update_yaxes(showgrid=False, zeroline=False, title=None, ticksuffix="  ",
                 tickfont=dict(color=INK, size=12.5))
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

alto, bajo = dfg.iloc[0], dfg.iloc[-1]
st.markdown(
    f'<div class="lectura">En {vlabel}, <b>{cname}</b> registra '
    f'<b>{m["label"].lower()}</b> de <b>{motor.fmt_valor(valor, m["fmt"])}</b>. '
    f'El {dim_label} más alto es <b>{alto["DIMENSION"]}</b> '
    f'({motor.fmt_valor(alto["VALOR"], m["fmt"])}); el más bajo, <b>{bajo["DIMENSION"]}</b> '
    f'({motor.fmt_valor(bajo["VALOR"], m["fmt"])}).</div>',
    unsafe_allow_html=True,
)

st.markdown(f'<div class="dtitle">Detalle por {dim_label}</div>', unsafe_allow_html=True)
_filas = "".join(
    f'<tr><td>{_html.escape(str(r["DIMENSION"]))}</td>'
    f'<td class="n">{motor.fmt_valor(r["VALOR"], m["fmt"])}</td>'
    f'<td class="n">{motor.fmt_valor(r["BASE"], "num")}</td></tr>'
    for _, r in dfg.iterrows()
)
st.markdown(
    f'<table class="dt"><thead><tr><th>{_html.escape(dim_label.capitalize())}</th>'
    f'<th class="n">Valor</th><th class="n">Registros</th></tr></thead>'
    f'<tbody>{_filas}</tbody></table>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="pie">Centro de Inteligencia de Negocios de job&amp;talent. '
    'Datos agregados al último refresco; sin información personal.</div>',
    unsafe_allow_html=True,
)
