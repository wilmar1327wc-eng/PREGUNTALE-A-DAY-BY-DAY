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
    import reporte_excel
    _xlsx_err = None
except Exception as _e:
    reporte_excel = None
    _xlsx_err = str(_e)
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

# Dirección "buena" de cada métrica, para colorear la variación sin mentir:
#  - en agotados, que SUBA es malo;  - en precios no hay juicio bueno/malo.
_PEOR_SI_SUBE = {"pct_agotado", "num_agotados"}
_SIN_JUICIO = {"precio_promedio"}

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

  /* ---- cifras clave (tiles) ---- */
  .kpis {{ display:grid; grid-template-columns:1.5fr 1fr 1fr 1fr; gap:12px; margin:18px 0 6px; }}
  .tile {{ background:{SURF2}; border:1px solid {LINE}; border-radius:14px; padding:14px 16px; }}
  .tile.big {{ border-left:4px solid {TEAL}; }}
  .tile .tl {{ color:{MUTED}; font-size:.72rem; text-transform:uppercase; letter-spacing:.05em; margin-bottom:7px; }}
  .tile .tv {{ font-family:'Space Grotesk'; color:#fff; font-size:2.15rem; font-weight:700; line-height:1; letter-spacing:-.02em; }}
  .tile .tv2 {{ font-family:'Space Grotesk'; color:#fff; font-size:1.32rem; font-weight:700; line-height:1.12; }}
  .tile .tsub {{ color:{MUTED}; font-size:.82rem; margin-top:5px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
  .tvar {{ font-size:.83rem; font-weight:600; margin-top:9px; }}
  .tvar .vs {{ color:{MUTED}; font-weight:400; font-size:.76rem; }}
  .tvar.good {{ color:{TEAL_HI}; }} .tvar.bad {{ color:#FF9478; }} .tvar.flat {{ color:{MUTED}; }}

  /* ---- tendencia ---- */
  .trendwrap {{ margin:22px 0 2px; }}
  .trend {{ width:100%; height:auto; display:block; }}
  .trendx {{ display:flex; justify-content:space-between; color:{MUTED}; font-size:.78rem; margin-top:2px; }}
  .trendx b {{ color:#AFE9E2; font-weight:600; }}

  /* ---- top / bottom ---- */
  .tb {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; margin:20px 0 4px; }}
  .tbcol {{ background:{SURF2}; border:1px solid {LINE}; border-radius:14px; padding:13px 16px; }}
  .tbcol h4 {{ margin:0 0 10px; font-size:.82rem; font-weight:600; display:flex; align-items:center; gap:7px; }}
  .tbcol.hi h4 {{ color:{TEAL_HI}; }} .tbcol.lo h4 {{ color:{MUTED}; }}
  .tbrow {{ display:flex; justify-content:space-between; gap:10px; padding:6px 0;
            border-bottom:1px solid rgba(255,255,255,.05); font-size:.88rem; }}
  .tbrow:last-child {{ border-bottom:none; }}
  .tbrow .nm {{ color:{INK}; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
  .tbrow .nm .rk {{ color:{MUTED}; margin-right:8px; font-variant-numeric:tabular-nums; }}
  .tbrow .vl {{ color:#fff; font-variant-numeric:tabular-nums; font-weight:600; white-space:nowrap; }}

  /* ---- hallazgos ---- */
  .find {{ background:{SURF}; border:1px solid {LINE}; border-left:4px solid {TEAL};
           border-radius:12px; padding:15px 19px; margin:22px 0 0; }}
  .find h4 {{ margin:0 0 9px; color:{INK}; font-size:.95rem; font-weight:600; }}
  .find .fi {{ color:{INK}; font-size:.93rem; line-height:1.5; padding:4px 0 4px 18px; position:relative; }}
  .find .fi::before {{ content:"●"; color:{TEAL}; position:absolute; left:0; font-size:.62rem; top:.42em; }}
  .find .fi b {{ color:#fff; }}

  @media (max-width:820px) {{
    [data-testid="stImage"] img {{ max-width:100%; }}
    .kpis {{ grid-template-columns:1fr 1fr; }} .tb {{ grid-template-columns:1fr; }}
  }}
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
def _pdf_bytes(firma, indicador, cliente, periodo, metrica_label, valor_txt, base_txt, filas, insights, fecha,
               var_txt=None, var_signo="flat", serie=()):
    return reporte.construir_pdf(
        indicador=indicador, cliente=cliente, periodo=periodo, metrica_label=metrica_label,
        valor_txt=valor_txt, base_txt=base_txt, filas=list(filas), insights=list(insights),
        jt_datauri=JOBTALENT, cli_datauri=LOGOS.get((cliente or "").strip().upper()), fecha_txt=fecha,
        var_txt=var_txt, var_signo=var_signo, serie=list(serie))


@st.cache_data(ttl=1800, show_spinner=False)
def _xlsx_bytes(firma, indicador, cliente, periodo, metrica_label, fmt_m, tipo, valor, base,
                var, var_cls, filas, dim_label, serie, insights, fecha):
    return reporte_excel.construir_xlsx(
        indicador=indicador, cliente=cliente, periodo=periodo, metrica_label=metrica_label,
        fmt=fmt_m, tipo=tipo, valor=valor, base=base, var=var, var_cls=var_cls,
        filas=list(filas), dim_label=dim_label, serie=list(serie),
        insights=list(insights), fecha_txt=fecha)

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

def fmt_c(v, f):
    """Formato compacto ejecutivo ($ 4,8 mil M · 128,6 mil · 94,8%); respaldo si el motor es viejo."""
    fn = getattr(motor, "fmt_compacto", None)
    try:
        return fn(v, f) if fn else fmt(v, f)
    except Exception:
        return fmt(v, f)

def _plural(w):
    """Plural en español sencillo: regional->regionales, cadena->cadenas, zona->zonas."""
    w = str(w)
    if not w or w[-1] in "sv":
        return w
    if w[-1] in "aeiouáéíóú":
        return w + "s"
    if w.endswith("z"):
        return w[:-1] + "ces"
    return w + "es"

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


def _svg_tendencia(serie, f):
    """Mini gráfico de área + línea (SVG) de la evolución en el período.
    Devuelve (html, pico_txt, f0, f1) o ("", "", "", "") si no hay suficientes puntos."""
    try:
        pts = [(r["FECHA"], float(r["VALOR"])) for _, r in serie.iterrows()]
    except Exception:
        return "", "", "", ""
    pts = [(d, v) for d, v in pts if v == v]  # quita NaN
    if len(pts) < 2:
        return "", "", "", ""
    Wv, Hv = 680.0, 120.0
    pl, pr, pt_, pb = 6.0, 6.0, 12.0, 10.0
    vals = [v for _, v in pts]
    vmin, vmax = min(vals), max(vals)
    rng = (vmax - vmin) or 1.0
    n = len(pts)
    def X(i): return pl + (Wv - pl - pr) * (i / (n - 1))
    def Y(v): return pt_ + (Hv - pt_ - pb) * (1 - (v - vmin) / rng)
    line = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, (_, v) in enumerate(pts))
    area = f"{X(0):.1f},{Hv - pb:.1f} {line} {X(n - 1):.1f},{Hv - pb:.1f}"
    lx, ly = X(n - 1), Y(pts[-1][1])
    ipk = max(range(n), key=lambda i: pts[i][1])
    pkx, pky = X(ipk), Y(pts[ipk][1])
    svg = (
        f'<svg viewBox="0 0 {Wv:.0f} {Hv:.0f}" class="trend">'
        f'<defs><linearGradient id="tg" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{TEAL}" stop-opacity="0.30"/>'
        f'<stop offset="1" stop-color="{TEAL}" stop-opacity="0"/></linearGradient></defs>'
        f'<polygon points="{area}" fill="url(#tg)"/>'
        f'<polyline points="{line}" fill="none" stroke="{TEAL}" stroke-width="2.4" '
        f'stroke-linejoin="round" stroke-linecap="round"/>'
        f'<circle cx="{pkx:.1f}" cy="{pky:.1f}" r="3.2" fill="{TEAL}" opacity="0.55"/>'
        f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="4.2" fill="{TEAL_HI}" stroke="{BG}" stroke-width="2"/>'
        f'</svg>'
    )
    return svg, fmt_c(pts[ipk][1], f), fmt_fecha(pts[0][0]), fmt_fecha(pts[-1][0])


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

# --- Sin datos: KPI simple y salir ---
if dfg.empty:
    st.markdown(
        f'<div class="kpi"><div class="ctx">{m["label"]} de {cname}, {vlabel}</div>'
        f'<div class="val">{fmt(valor, m["fmt"])}</div>'
        f'<div class="base">sobre {fmt(base, "num")} registros</div></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="lectura">No hay registros para esto en el período elegido. '
                'Amplía el período o cambia la marca.</div>', unsafe_allow_html=True)
    st.markdown(PIE, unsafe_allow_html=True)
    st.stop()

# --- Variación vs período anterior + serie de tiempo (con degradación elegante) ---
var = None
try:
    var = motor.kpi_var(dom, ids, ventana, metrica).get("var")
except Exception:
    var = None
try:
    _vtxt, _vsig = motor.fmt_var(var)
except Exception:
    _vtxt, _vsig = "—", "flat"
_vcls = "flat"
if _vsig != "flat" and mkey not in _SIN_JUICIO:
    _vcls = "good" if ((_vsig == "up") != (mkey in _PEOR_SI_SUBE)) else "bad"

serie = None
try:
    serie = motor.serie_tiempo(dom, ids, ventana, metrica)
except Exception:
    serie = None

alto, bajo = dfg.iloc[0], dfg.iloc[-1]
n_dim = len(dfg)
if m["tipo"] in ("sum", "count"):
    _t4lbl, _t4val = f"Prom. por {dim_label}", fmt_c(float(valor) / n_dim if n_dim else 0, m["fmt"])
    _t4sub = f"entre {n_dim} {_plural(dim_label)}"
else:
    _t4lbl, _t4val, _t4sub = f"{_plural(dim_label).capitalize()} con dato", f"{n_dim}", f"en {vlabel}"

# --- Cifras clave (4 tiles) ---
st.markdown(
    f'<div class="kpis">'
    f'<div class="tile big"><div class="tl">{m["label"]}</div>'
    f'<div class="tv">{fmt_c(valor, m["fmt"])}</div>'
    f'<div class="tvar {_vcls}">{_vtxt} <span class="vs">vs. período anterior</span></div></div>'
    f'<div class="tile"><div class="tl">Más alto</div>'
    f'<div class="tv2">{fmt_c(alto["VALOR"], m["fmt"])}</div>'
    f'<div class="tsub">{_html.escape(str(alto["DIMENSION"]))}</div></div>'
    f'<div class="tile"><div class="tl">Más bajo</div>'
    f'<div class="tv2">{fmt_c(bajo["VALOR"], m["fmt"])}</div>'
    f'<div class="tsub">{_html.escape(str(bajo["DIMENSION"]))}</div></div>'
    f'<div class="tile"><div class="tl">{_t4lbl}</div>'
    f'<div class="tv2">{_t4val}</div><div class="tsub">{_t4sub}</div></div>'
    f'</div>',
    unsafe_allow_html=True,
)

# --- Exportables: PDF + Excel (mismo informe, dos formatos) ---
_maxv = float(dfg["VALOR"].max()) or 1.0
_filas = tuple((str(r["DIMENSION"]), fmt(r["VALOR"], m["fmt"]),
                float(r["VALOR"]) / _maxv, fmt(r["BASE"], "num"))
               for _, r in dfg.head(14).iterrows())
_filas_raw = tuple((str(r["DIMENSION"]), float(r["VALOR"]), int(r["BASE"])) for _, r in dfg.iterrows())
_ins = tuple(_insights(m, dfg, valor, base, cname, vlabel, dim_label))
_serie_vals, _serie_raw = (), ()
if serie is not None and not serie.empty:
    _serie_vals = tuple(float(x) for x in serie["VALOR"].tolist() if x == x)
    _serie_raw = tuple((r["FECHA"], float(r["VALOR"])) for _, r in serie.iterrows() if r["VALOR"] == r["VALOR"])
_var_pdf = (f"{var * 100:+.1f}%".replace(".", ",")) if var is not None else None
_hoy = fmt_fecha(date.today())

_cpdf, _cxls, _ = st.columns([0.3, 0.3, 0.4])
try:
    _pdf = _pdf_bytes((dom, tuple(ids), ventana, metrica, dimension, cname),
                      meta["nombre"], cname, vlabel, m["label"],
                      fmt(valor, m["fmt"]), fmt(base, "num"), _filas, _ins, _hoy,
                      _var_pdf, _vcls, _serie_vals)
    _cpdf.download_button("⬇  Informe PDF", data=_pdf,
                          file_name=f"Informe {meta['nombre']} - {cname}.pdf",
                          mime="application/pdf", type="primary")
except Exception:
    _cpdf.caption("PDF no disponible.")
if reporte_excel is not None:
    try:
        _xls = _xlsx_bytes((dom, tuple(ids), ventana, metrica, dimension, cname),
                           meta["nombre"], cname, vlabel, m["label"], m["fmt"], m["tipo"],
                           float(valor), int(base), var, _vcls, _filas_raw, dim_label, _serie_raw,
                           _ins, _hoy)
        _cxls.download_button("⬇  Datos en Excel", data=_xls,
                              file_name=f"Informe {meta['nombre']} - {cname}.xlsx",
                              mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                              type="primary")
    except Exception:
        _cxls.caption("Excel no disponible.")

# --- Tendencia en el tiempo ---
_svg, _pico, _f0, _f1 = _svg_tendencia(serie, m["fmt"]) if serie is not None else ("", "", "", "")
if _svg:
    st.markdown(
        f'<div class="trendwrap"><div class="btitle">Cómo viene {m["label"].lower()} en {vlabel}</div>'
        f'{_svg}<div class="trendx"><span>{_f0}</span>'
        f'<span>pico: <b>{_pico}</b></span><span>{_f1}</span></div></div>',
        unsafe_allow_html=True,
    )

# --- Top 5 / Bottom 5 ---
def _tbrows(df_):
    out = ""
    for i, (_, r) in enumerate(df_.iterrows(), 1):
        out += (f'<div class="tbrow"><span class="nm"><span class="rk">{i}</span>'
                f'{_html.escape(str(r["DIMENSION"]))}</span>'
                f'<span class="vl">{fmt(r["VALOR"], m["fmt"])}</span></div>')
    return out
# Con pocas dimensiones, partimos sin repetir (top ⌈n/2⌉ / bottom ⌊n/2⌋); con muchas, 5 y 5.
if n_dim >= 10:
    _kt = _kb = 5
else:
    _kt, _kb = (n_dim + 1) // 2, n_dim // 2
if _kb >= 1:
    st.markdown(
        f'<div class="tb">'
        f'<div class="tbcol hi"><h4>▲ Top {_kt} más alto · {dim_label}</h4>{_tbrows(dfg.head(_kt))}</div>'
        f'<div class="tbcol lo"><h4>▼ {_kb} más bajo · {dim_label}</h4>{_tbrows(dfg.tail(_kb).iloc[::-1])}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

# --- Desglose (barras) ---
top = dfg.head(12)
maxv = float(top["VALOR"].max()) or 1.0
_bars = ""
for _, r in top.iterrows():
    w = max(3.0, float(r["VALOR"]) / maxv * 100.0)
    _bars += (f'<div class="bar"><span class="blab">{_html.escape(str(r["DIMENSION"]))}</span>'
              f'<span class="btrack"><span class="bfill" style="width:{w:.1f}%"></span></span>'
              f'<span class="bval">{fmt(r["VALOR"], m["fmt"])}</span></div>')
st.markdown(f'<div class="btitle">{m["label"]} por {dim_label} ({cname})</div>{_bars}', unsafe_allow_html=True)

# --- Hallazgos (ahora visibles en la app, no solo en el PDF) ---
_fi = "".join(f'<div class="fi">{_html.escape(t)}</div>' for t in _ins)
st.markdown(f'<div class="find"><h4>Hallazgos</h4>{_fi}</div>', unsafe_allow_html=True)

# --- Tabla completa (plegable, para no alargar) ---
with st.expander(f"Ver tabla completa · {n_dim} {_plural(dim_label)}"):
    _tfilas = "".join(
        f'<tr><td>{_html.escape(str(r["DIMENSION"]))}</td>'
        f'<td class="n">{fmt(r["VALOR"], m["fmt"])}</td>'
        f'<td class="n">{fmt(r["BASE"], "num")}</td></tr>'
        for _, r in dfg.iterrows()
    )
    st.markdown(
        f'<table class="dt"><thead><tr><th>{_html.escape(dim_label.capitalize())}</th>'
        f'<th class="n">{m["label"]}</th><th class="n">Registros</th></tr></thead>'
        f'<tbody>{_tfilas}</tbody></table>',
        unsafe_allow_html=True,
    )

st.markdown(PIE, unsafe_allow_html=True)
