# -*- coding: utf-8 -*-
"""
Pregúntale a DayByDay — APP PÚBLICA (identidad job&talent, lee el cubo en Neon).

Esencia: preguntar y obtener UNA respuesta clara.
- MENÚ (Marca · Indicador · Período · Ver por): arma la consulta y responde directo
  del cubo = 0 tokens de IA.
- PREGUNTA LIBRE: lo único que usa IA (Groq -> Gemini -> heurístico).

Deploy en Streamlit Community Cloud. Secrets:
    DATABASE_URL   = "postgresql://..."
    GROQ_API_KEY   = "gsk_..."
    GEMINI_API_KEY = "..."   (respaldo, opcional)
Archivos en el repo: app_publica.py, motor_nube.py, logos.py, marca.py,
fondo.jpg, requirements.txt y .streamlit/config.toml
"""

import os
import html as _html
from datetime import date
import streamlit as st

# Puente: Secrets de Streamlit -> variables de entorno (para motor_nube)
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
import reporte
try:
    from fondo_app import FONDO
except Exception:
    FONDO = ""

# ---------- Paleta job&talent (teal #00D0C0 sacado del propio logo) ----------
BG = "#0A1628"
SURF = "#0F2146"
SURF2 = "#0C1B3C"
LINE = "#22406E"
TEAL = "#00D0C0"
TEAL_HI = "#35ECD9"
INK = "#ECF3FF"
MUTED = "#9DB4DA"

MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

# Indicadores del menú (etiqueta -> dominio, métrica). Se define AQUÍ para no depender
# de que motor_nube tenga PRESET_METRICAS: así la app corre aunque el motor sea el viejo.
PRESET_METRICAS = {
    "Ventas": ("ventas", "venta_total"),
    "Cobertura": ("cobertura", "pct_cobertura"),
    "Agotados": ("agotados", "pct_agotado"),
    "Precios": ("precios", "precio_promedio"),
    "Actividades": ("actividades", "num_actividades"),
    "Encuestas": ("encuestas", "num_encuestas"),
}

PIE = ('<div class="pie">Centro de Inteligencia de Negocios de job&amp;talent · '
       'Datos agregados al último refresco; sin información personal ni registros individuales.</div>')

st.set_page_config(page_title="Pregúntale a Day by Day", page_icon="◆", layout="wide")

# Papel tapiz: la imagen de fondo + una capa oscura encima para que todo siga legible.
if FONDO:
    _appbg = (f'linear-gradient(rgba(9,20,38,.50), rgba(9,20,38,.68)), '
              f'url("{FONDO}") center center / cover fixed no-repeat, {BG}')
else:
    _appbg = (f'radial-gradient(1000px 440px at 88% -8%, rgba(0,208,192,.12), transparent 60%), '
              f'radial-gradient(760px 360px at -5% 8%, rgba(0,208,192,.05), transparent 55%), {BG}')

st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');

  .stApp {{ background:{_appbg}; }}
  html, body, [data-testid="stMarkdownContainer"], .stButton button, .stTextInput input,
  [data-baseweb="select"] {{ font-family:'IBM Plex Sans', system-ui, sans-serif; }}
  .block-container {{ max-width:1060px; padding-top:.7rem; padding-bottom:3rem; }}
  #MainMenu, footer, [data-testid="stToolbar"] {{ visibility:hidden; }}
  [data-testid="stHeader"] {{ background:transparent; }}

  /* ---- barra superior ---- */
  .top {{ display:flex; align-items:center; justify-content:space-between;
          padding-bottom:14px; border-bottom:1px solid {LINE}; margin-bottom:18px; }}
  .top .l {{ display:flex; align-items:center; gap:13px; }}
  .top .jt {{ height:28px; display:block; }}
  .top .cin {{ color:{MUTED}; font-size:.9rem; font-weight:500;
               border-left:1px solid {LINE}; padding-left:13px; }}
  .upd {{ color:{MUTED}; font-size:.8rem; display:flex; align-items:center; gap:7px; }}
  .upd .dot {{ width:8px; height:8px; border-radius:50%; background:{TEAL};
               box-shadow:0 0 0 3px rgba(0,208,192,.18); }}

  /* ---- hero ---- */
  .hero-title {{ font-family:'Space Grotesk', sans-serif; font-weight:700; color:#FFFFFF;
      font-size:clamp(2.1rem, 4.3vw, 3.25rem); line-height:1.03; letter-spacing:-.025em; margin:6px 0 0; }}
  .hero-title .ia {{ font-family:'Space Grotesk'; font-weight:700; font-size:.42em;
      background:{TEAL}; color:#042220; padding:.18em .5em; border-radius:.42em;
      vertical-align:.3em; margin-left:.28em; letter-spacing:0; }}
  .hero-sub {{ color:{MUTED}; font-size:1.05rem; line-height:1.5; margin:15px 0 0; max-width:44ch; }}
  [data-testid="stImage"] img {{ max-width:330px; margin-left:auto; border-radius:16px;
      box-shadow:0 0 0 1px {LINE}, 0 16px 38px rgba(0,0,0,.35); }}

  /* ---- clientes ---- */
  .clients {{ display:flex; flex-wrap:wrap; align-items:center; gap:10px; margin:20px 0 22px; }}
  .clients .lbl {{ color:{MUTED}; font-size:.84rem; margin-right:4px; }}
  .lchip {{ display:inline-flex; align-items:center; background:{SURF};
            border:1px solid {TEAL}; box-shadow:0 0 14px rgba(0,208,192,.18);
            border-radius:10px; padding:5px 6px; height:44px; }}
  .lchip img {{ height:24px; display:block; background:#fff; border-radius:6px; padding:5px 10px; }}

  /* ---- menú (contenedor con borde) ---- */
  [data-testid="stVerticalBlockBorderWrapper"] {{ background:{SURF2}; border:1px solid {LINE};
      border-radius:16px; padding:16px 20px 18px; box-shadow:inset 0 2px 0 rgba(0,208,192,.10); }}
  .eye {{ display:flex; align-items:center; gap:9px; margin:2px 0 12px; }}
  .eye .d {{ width:8px; height:8px; border-radius:50%; background:{TEAL}; }}
  .eye b {{ color:{INK}; font-size:1rem; font-weight:600; }}
  .eye span {{ color:{MUTED}; font-size:.85rem; }}
  .askq {{ color:{MUTED}; font-size:.9rem; margin:14px 0 6px; }}

  /* selects */
  /* Casillas de selección: navy + texto claro. El tema oscuro (config.toml) es lo principal;
     esto es respaldo por si no carga. Fondo y texto cambian JUNTOS para no quedar ilegibles. */
  [data-testid="stSelectbox"] > div > div {{ background:{SURF} !important;
      border:1px solid {LINE} !important; border-radius:10px !important; }}
  [data-testid="stSelectbox"] > div > div,
  [data-testid="stSelectbox"] > div > div * {{ color:{INK} !important; -webkit-text-fill-color:{INK} !important; }}
  [data-testid="stSelectbox"] > div > div svg {{ fill:{MUTED} !important; -webkit-text-fill-color:initial !important; }}
  ul[role="listbox"], li[role="option"] {{ background:{SURF} !important; color:{INK} !important; }}
  li[role="option"]:hover, li[aria-selected="true"] {{ background:#17315A !important; color:#FFFFFF !important; }}
  [data-testid="stWidgetLabel"] p {{ color:{MUTED}; font-size:.8rem; }}

  /* inputs */
  .stTextInput input {{ background:{SURF}; border-radius:10px; border:1px solid {LINE};
      font-size:.96rem; padding:12px 14px; color:{INK}; }}
  .stTextInput input:focus {{ border-color:{TEAL}; box-shadow:none; }}
  .stTextInput input::placeholder {{ color:#64789E; opacity:1; }}

  /* botones */
  .stButton button {{ border-radius:10px; font-weight:600; font-size:.92rem; padding:11px 18px;
      width:100%; }}
  .stButton button[kind="primary"] {{ font-family:'Space Grotesk'; background:{TEAL};
      color:#042220; border:none; font-weight:700; box-shadow:0 6px 18px rgba(0,208,192,.22); }}
  .stButton button[kind="primary"]:hover {{ background:{TEAL_HI}; color:#042220; }}
  .stButton button[kind="secondary"] {{ background:transparent; border:1px solid {TEAL};
      color:{TEAL}; }}
  .stButton button[kind="secondary"]:hover {{ background:rgba(0,208,192,.08); border-color:{TEAL_HI};
      color:{TEAL_HI}; }}
  [data-testid="stDownloadButton"] button {{ background:{TEAL}; color:#042220; border:none;
      border-radius:10px; font-weight:700; font-family:'Space Grotesk'; padding:11px 18px; width:100%; }}
  [data-testid="stDownloadButton"] button:hover {{ background:{TEAL_HI}; color:#042220; }}

  [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {{ color:{MUTED}; opacity:1; }}

  /* ---- respuesta ---- */
  .membrete {{ display:inline-flex; align-items:center; border-radius:12px; padding:6px 8px;
               background:{SURF}; border:1px solid {TEAL}; box-shadow:0 0 16px rgba(0,208,192,.2); }}
  .membrete img {{ height:30px; display:block; background:#fff; border-radius:7px; padding:6px 12px; }}
  .entendi {{ margin:14px 0 2px; display:flex; align-items:center; flex-wrap:wrap; gap:7px; }}
  .entendi .lbl {{ color:{MUTED}; font-size:.85rem; margin-right:3px; }}
  .pill {{ background:{SURF}; color:#AFE9E2; border:1px solid {LINE};
           padding:4px 11px; border-radius:8px; font-size:.8rem; font-weight:500; }}
  .kpi {{ border-left:4px solid {TEAL}; padding:2px 0 2px 20px; margin:18px 0 8px; }}
  .kpi .ctx {{ color:{MUTED}; font-size:.95rem; margin:0 0 7px; }}
  .kpi .val {{ font-family:'Space Grotesk'; font-size:3.3rem; font-weight:700; color:#FFFFFF;
               line-height:1; letter-spacing:-.02em; }}
  .kpi .base {{ color:{MUTED}; font-size:.9rem; margin-top:9px; }}

  .btitle {{ color:{INK}; font-weight:600; font-size:1rem; margin:22px 0 12px; }}
  .bar {{ display:grid; grid-template-columns:120px 1fr 92px; align-items:center; gap:12px; margin:9px 0; }}
  .blab {{ color:{INK}; font-size:.9rem; text-align:right; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
  .btrack {{ background:rgba(255,255,255,.06); border-radius:7px; height:22px; overflow:hidden; }}
  .bfill {{ display:block; height:100%; border-radius:7px; background:linear-gradient(90deg,#00B6AA,{TEAL}); }}
  .bval {{ color:{INK}; font-size:.9rem; font-variant-numeric:tabular-nums; }}

  .lectura {{ background:{SURF}; border:1px solid {LINE}; border-radius:12px;
              padding:15px 19px; color:{INK}; font-size:.96rem; line-height:1.55; margin:20px 0 0; }}
  .lectura b {{ color:#fff; }}
  table.dt {{ width:100%; border-collapse:collapse; margin-top:18px; }}
  table.dt th {{ text-align:left; color:{MUTED}; font-weight:500; font-size:.78rem;
                 padding:8px 8px; border-bottom:1px solid {LINE}; }}
  table.dt td {{ color:{INK}; font-size:.9rem; padding:9px 8px;
                 border-bottom:1px solid rgba(255,255,255,.06); }}
  table.dt td.n, table.dt th.n {{ text-align:right; font-variant-numeric:tabular-nums; }}
  table.dt tr:last-child td {{ border-bottom:none; }}
  .empty {{ background:{SURF}; border:1px dashed {LINE}; border-radius:14px;
            padding:22px 24px; color:{MUTED}; font-size:.98rem; margin-top:8px; line-height:1.5; }}
  .empty b {{ color:{INK}; }}
  .pie {{ color:{MUTED}; font-size:.8rem; margin-top:30px; padding-top:14px;
          border-top:1px solid {LINE}; line-height:1.6; }}

  @media (max-width:820px) {{ [data-testid="stImage"] img {{ max-width:100%; }} }}
</style>
""", unsafe_allow_html=True)


# ===================================================================
# Datos (cacheados)
# ===================================================================
@st.cache_data(ttl=1800, show_spinner="Cargando...")
def cargar_clientes():
    return motor.clientes()

@st.cache_data(ttl=1800, show_spinner=False)
def c_fresh():
    # Fecha del dato más reciente del cubo. Usa run_df (función de siempre del motor)
    # en vez de una función nueva, para no romper si el motor del repo es el viejo.
    try:
        df = motor.run_df("SELECT MAX(dia) AS d FROM cubo_ventas")
        if not df.empty and df["d"].iloc[0] is not None:
            return df["d"].iloc[0]
    except Exception:
        pass
    return None


@st.cache_data(ttl=1800, show_spinner=False)
def _pdf_bytes(firma, indicador, cliente, periodo, metrica_label, valor_txt, base_txt, filas, insights, fecha):
    return reporte.construir_pdf(
        indicador=indicador, cliente=cliente, periodo=periodo, metrica_label=metrica_label,
        valor_txt=valor_txt, base_txt=base_txt, filas=list(filas), insights=list(insights),
        jt_datauri=JOBTALENT, cli_datauri=LOGOS.get((cliente or "").strip().upper()), fecha_txt=fecha)

try:
    marcas = cargar_clientes()
except Exception as e:
    st.error(f"No pude leer el cubo. Revisa DATABASE_URL en Secrets. Detalle: {e}")
    st.stop()
if not marcas:
    st.error("El cubo está vacío. Corre el refresco (refrescar.bat) y recarga.")
    st.stop()


def fmt(v, f):
    s = motor.fmt_valor(v, f)
    return s.replace(".", ",") if f == "pct" else s

def fmt_fecha(d):
    try:
        return f"{d.day:02d} {MESES[d.month - 1]} {d.year}"
    except Exception:
        return "—"


def _insights(m, dfg, valor, base, cname, vlabel, dim_label):
    """Hallazgos automáticos (deterministas, sin IA) a partir de los datos."""
    out, tipo, f = [], m["tipo"], m["fmt"]
    out.append(f"El {m['label'].lower()} general de {cname} en {vlabel} es {fmt(valor, f)} "
               f"sobre {fmt(base, 'num')} registros.")
    if len(dfg) >= 1:
        b = dfg.iloc[0]
        out.append(f"El {dim_label} con mejor desempeño es {b['DIMENSION']} ({fmt(b['VALOR'], f)}).")
    if len(dfg) >= 2:
        b, w = dfg.iloc[0], dfg.iloc[-1]
        if f == "pct":
            gtxt = f"{(float(b['VALOR']) - float(w['VALOR'])) * 100:.1f}".replace(".", ",") + " puntos porcentuales"
        else:
            gtxt = fmt(float(b["VALOR"]) - float(w["VALOR"]), f) + " de diferencia"
        out.append(f"El más bajo es {w['DIMENSION']} ({fmt(w['VALOR'], f)}); "
                   f"la brecha con el más alto es de {gtxt}.")
    if tipo == "sum" and len(dfg) >= 3:
        tot = float(dfg["VALOR"].sum()) or 1.0
        t3 = dfg.head(3)
        sh = f"{float(t3['VALOR'].sum()) / tot * 100:.1f}".replace(".", ",")
        out.append(f"El top 3 ({', '.join(str(x) for x in t3['DIMENSION'])}) concentra el {sh}% del total.")
    elif tipo in ("ratio", "avg") and len(dfg) >= 2:
        below = dfg[dfg["VALOR"].astype(float) < float(valor)]
        lst = ", ".join(str(x) for x in below["DIMENSION"].head(4))
        extra = f": {lst}" if lst else ""
        out.append(f"{len(below)} de {len(dfg)} {dim_label}s están por debajo "
                   f"del promedio ({fmt(valor, f)}){extra}.")
    if len(dfg) >= 2:
        peores = ", ".join(str(x) for x in dfg.tail(2)["DIMENSION"].tolist()[::-1])
        out.append(f"Reforzar {peores}, con el menor aporte, ayudaría a subir el total."
                   if tipo == "sum" else f"Priorizar {peores} cerraría buena parte de la brecha.")
    return out


# ===================================================================
# Barra superior
# ===================================================================
_logo = f'<img class="jt" src="{JOBTALENT}" alt="job&amp;talent">' if JOBTALENT else '<b style="color:#fff">Day by Day</b>'
st.markdown(
    f'<div class="top"><div class="l">{_logo}'
    f'<span class="cin">Centro de Inteligencia de Negocios</span></div>'
    f'<div class="upd"><span class="dot"></span>Datos actualizados a {fmt_fecha(c_fresh())}</div></div>',
    unsafe_allow_html=True,
)


# ===================================================================
# Hero (título grande + fondo pequeño a la derecha)
# ===================================================================
hcol1, hcol2 = st.columns([1.45, 0.9], vertical_alignment="center")
with hcol1:
    st.markdown(
        '<div class="hero-title">Pregúntale a<br>Day by Day<span class="ia">+ IA</span></div>'
        '<div class="hero-sub">Escoge qué quieres ver y te respondo al instante. '
        'O pregúntame con tus propias palabras.</div>',
        unsafe_allow_html=True,
    )
with hcol2:
    _BANNER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fondo.jpg")
    if os.path.exists(_BANNER):
        st.image(_BANNER, width="stretch")

# Clientes (arriba)
if LOGOS:
    _r = "".join(f'<span class="lchip"><img src="{u}"></span>' for u in LOGOS.values())
    st.markdown(f'<div class="clients"><span class="lbl">Clientes</span>{_r}</div>', unsafe_allow_html=True)


# ===================================================================
# Menú de consulta (deterministico, sin IA) + pregunta libre (con IA)
# ===================================================================
if "consulta" not in st.session_state:
    st.session_state.consulta = None   # arranca limpio: nada hasta que el usuario pida

def do_menu():
    # Congela lo elegido en el momento de pulsar Consultar (no reacciona a cambios sueltos)
    st.session_state.consulta = {
        "via": "menu",
        "marca": st.session_state.get("m_marca"),
        "ind": st.session_state.get("m_ind"),
        "per": st.session_state.get("m_per"),
        "dim": st.session_state.get("m_dim"),
    }

def do_ia():
    q = (st.session_state.get("m_free") or "").strip()
    if not q:
        return
    intp, usado = motor.interpretar(q, marcas)
    st.session_state.consulta = {"via": "ia", "intp": intp, "usado": usado}

op_marca = list(marcas.keys()) + ["Todas las marcas"]
ind_labels = list(PRESET_METRICAS.keys())

with st.container(border=True):
    st.markdown(
        '<div class="eye"><span class="d"></span><b>Consulta rápida</b>'
        '<span>— respuesta al instante, sin gastar IA</span></div>',
        unsafe_allow_html=True,
    )
    c1, c2, c3, c4, c5 = st.columns([1.15, 1, 1, 1, 0.72], vertical_alignment="bottom")
    marca_sel = c1.selectbox("Marca / cliente", op_marca, key="m_marca")
    ind_sel = c2.selectbox("Indicador", ind_labels, key="m_ind")
    per_sel = c3.selectbox(
        "Período", motor.VENTANAS, index=motor.VENTANAS.index("3m"), key="m_per",
        format_func=lambda k: motor.VENTANA_LABEL.get(k, k).capitalize(),
    )
    _dom_sel = PRESET_METRICAS[ind_sel][0]
    _dims = motor.DOMINIOS[_dom_sel]["dimensiones"]
    _defdim = motor.DOMINIOS[_dom_sel]["dimension_default"]
    dim_sel = c4.selectbox(
        "Ver por", _dims, index=_dims.index(_defdim) if _defdim in _dims else 0, key="m_dim",
        format_func=lambda s: s.replace("_", " ").capitalize(),
    )
    c5.button("Consultar", type="primary", on_click=do_menu)

    st.markdown('<div class="askq">¿Algo más puntual? Pregúntame con tus palabras.</div>', unsafe_allow_html=True)
    f1, f2 = st.columns([1, 0.24], vertical_alignment="bottom")
    f1.text_input(
        "Pregunta libre", key="m_free", label_visibility="collapsed",
        placeholder="Ej: ¿cómo va el % de agotados de Derco por cadena este trimestre?",
    )
    f2.button("Preguntar con IA", type="secondary", on_click=do_ia)


# ===================================================================
# Resolver la consulta (menú o IA) -> intención
# ===================================================================
cons = st.session_state.get("consulta")
usado = None

# Página limpia: sin respuesta hasta que el usuario pida algo.
if not cons:
    st.markdown(
        '<div class="empty">Elige <b>marca</b>, <b>indicador</b> y <b>período</b>, y pulsa '
        '<b>Consultar</b>. O escríbeme una pregunta y dale <b>Preguntar con IA</b>.</div>',
        unsafe_allow_html=True,
    )
    st.markdown(PIE, unsafe_allow_html=True)
    st.stop()

if cons["via"] == "ia":
    intp = cons["intp"]
    if not intp.get("en_tema", True):
        st.markdown(
            '<div class="empty">Solo respondo sobre la operación de <b>Day by Day</b>: '
            'cobertura, agotados, precios, ventas y actividades de tus marcas. '
            'Prueba algo como <b>“cobertura de Henkel por cadena este trimestre”</b>.</div>',
            unsafe_allow_html=True,
        )
        st.markdown(PIE, unsafe_allow_html=True)
        st.stop()
    dom, metrica, dimension = intp["dominio"], intp["metrica"], intp["dimension"]
    cname, ids, ventana = intp["cliente_nombre"], intp["cliente_ids"], intp["ventana"]
    usado = cons.get("usado")
    if not ids:
        st.warning("¿De qué marca? Nómbrala en la pregunta, o úsala en el menú de arriba.")
        st.stop()
    logo = LOGOS.get((cname or "").strip().upper())
else:
    ind = cons.get("ind") or ind_labels[0]
    dom, metrica = PRESET_METRICAS[ind]
    ventana = cons.get("per") or "3m"
    dimension = cons.get("dim")
    dims_ok = motor.DOMINIOS[dom]["dimensiones"]
    if dimension not in dims_ok:
        dimension = motor.DOMINIOS[dom]["dimension_default"]
    marca_name = cons.get("marca") or op_marca[0]
    if marca_name == "Todas las marcas":
        ids = sorted({i for v in marcas.values() for i in v})
        cname, logo = "Todas las marcas", None
    else:
        ids, cname = marcas.get(marca_name, []), marca_name
        logo = LOGOS.get(marca_name.strip().upper())
    if not ids:
        st.warning("No encontré esa marca en el cubo.")
        st.stop()

meta = motor.DOMINIOS[dom]
vlabel = motor.VENTANA_LABEL.get(ventana, ventana)

try:
    valor, base, mkey, m, _ = motor.kpi(dom, ids, ventana, metrica)
    dfg, dkey, m2, _ = motor.por_dimension(dom, ids, ventana, metrica, dimension)
except Exception as e:
    st.error(f"Hubo un problema al consultar el cubo: {e}")
    st.stop()


# ===================================================================
# Respuesta
# ===================================================================
st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
if logo:
    st.markdown(f'<span class="membrete"><img src="{logo}"></span>', unsafe_allow_html=True)

dim_label = dkey.replace("_", " ")
_chips = "".join(f'<span class="pill">{t}</span>' for t in
                 [meta["nombre"], cname, m["label"], f"por {dim_label}", vlabel])
st.markdown(f'<div class="entendi"><span class="lbl">Entendí</span>{_chips}</div>', unsafe_allow_html=True)
st.caption(f"Interpretado con {usado.split(' ')[0]} (IA)" if usado else "Consulta directa al cubo · sin IA")

if not dfg.empty:
    _maxv = float(dfg["VALOR"].max()) or 1.0
    _filas = tuple((str(r["DIMENSION"]), fmt(r["VALOR"], m["fmt"]),
                    float(r["VALOR"]) / _maxv, fmt(r["BASE"], "num"))
                   for _, r in dfg.head(14).iterrows())
    _ins = tuple(_insights(m, dfg, valor, base, cname, vlabel, dim_label))
    try:
        _pdf = _pdf_bytes((dom, tuple(ids), ventana, metrica, dimension, cname),
                          meta["nombre"], cname, vlabel, m["label"],
                          fmt(valor, m["fmt"]), fmt(base, "num"), _filas, _ins, fmt_fecha(date.today()))
        _dc, _ = st.columns([0.42, 0.58])
        _dc.download_button("⬇  Descargar informe (PDF)", data=_pdf,
                            file_name=f"Informe {meta['nombre']} - {cname}.pdf",
                            mime="application/pdf", type="primary")
    except Exception:
        st.caption("No pude generar el PDF en este momento.")

st.markdown(
    f'<div class="kpi"><div class="ctx">{m["label"]} de {cname}, {vlabel}</div>'
    f'<div class="val">{fmt(valor, m["fmt"])}</div>'
    f'<div class="base">sobre {fmt(base, "num")} registros</div></div>',
    unsafe_allow_html=True,
)

if dfg.empty:
    st.markdown('<div class="lectura">No hay registros para esto en el período elegido. '
                'Amplía el período o cambia la marca.</div>', unsafe_allow_html=True)
    st.stop()

top = dfg.head(12)
maxv = float(top["VALOR"].max()) or 1.0
_bars = ""
for _, r in top.iterrows():
    w = max(3.0, float(r["VALOR"]) / maxv * 100.0)
    _bars += (f'<div class="bar"><span class="blab">{_html.escape(str(r["DIMENSION"]))}</span>'
              f'<span class="btrack"><span class="bfill" style="width:{w:.1f}%"></span></span>'
              f'<span class="bval">{fmt(r["VALOR"], m["fmt"])}</span></div>')
st.markdown(f'<div class="btitle">{m["label"]} por {dim_label} ({cname})</div>{_bars}', unsafe_allow_html=True)

alto, bajo = dfg.iloc[0], dfg.iloc[-1]
st.markdown(
    f'<div class="lectura">En {vlabel}, <b>{cname}</b> registra <b>{m["label"].lower()}</b> de '
    f'<b>{fmt(valor, m["fmt"])}</b>. El {dim_label} más alto es '
    f'<b>{_html.escape(str(alto["DIMENSION"]))}</b> ({fmt(alto["VALOR"], m["fmt"])}); '
    f'el más bajo, <b>{_html.escape(str(bajo["DIMENSION"]))}</b> ({fmt(bajo["VALOR"], m["fmt"])}).</div>',
    unsafe_allow_html=True,
)

_filas = "".join(
    f'<tr><td>{_html.escape(str(r["DIMENSION"]))}</td>'
    f'<td class="n">{fmt(r["VALOR"], m["fmt"])}</td>'
    f'<td class="n">{fmt(r["BASE"], "num")}</td></tr>'
    for _, r in dfg.iterrows()
)
st.markdown(
    f'<table class="dt"><thead><tr><th>{_html.escape(dim_label.capitalize())}</th>'
    f'<th class="n">{m["label"]}</th><th class="n">Registros</th></tr></thead>'
    f'<tbody>{_filas}</tbody></table>',
    unsafe_allow_html=True,
)

st.markdown(PIE, unsafe_allow_html=True)
