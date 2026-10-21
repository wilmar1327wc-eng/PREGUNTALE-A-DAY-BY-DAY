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
try:
    from portada_fondo import PORTADA_BG
except Exception:
    PORTADA_BG = ""

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
MESES_LARGO = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
               "septiembre", "octubre", "noviembre", "diciembre"]

# Indicadores del menú (etiqueta -> dominio, métrica). Se define AQUÍ para no depender
# de que motor_nube tenga PRESET_METRICAS: así la app corre aunque el motor sea el viejo.
PRESET_METRICAS = {
    "Ventas": ("ventas", "venta_total"),
    "Cobertura": ("cobertura", "pct_cobertura"),
    "Agotados": ("agotados", "pct_agotado"),
    "Precios": ("precios", "precio_promedio"),
    "Actividades": ("actividades", "num_actividades"),
    "Encuestas": ("encuestas", "num_encuestas"),
    "Ingresos": ("ingresos", "pct_asistencia"),
}

PIE = ('<div class="pie">Centro de Inteligencia de Negocios de job&amp;talent · '
       'Datos agregados al último refresco; sin información personal ni registros individuales.</div>')

# Dirección "buena" de cada métrica, para colorear la variación sin mentir:
#  - en agotados, que SUBA es malo;  - en precios no hay juicio bueno/malo.
_PEOR_SI_SUBE = {"pct_agotado", "num_agotados"}
_SIN_JUICIO = {"precio_promedio"}

# Etiquetas más claras para algunas dimensiones (el resto se arma solo con replace/capitalize).
DIM_LABEL = {
    "titulo": "encuesta", "pdv": "punto de venta",
    "categoria_pdv": "categoría de PDV", "zona": "zona comercial",
}

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
  .bar {{ display:grid; grid-template-columns:180px minmax(0,1fr) 92px; align-items:center; gap:12px; margin:9px 0; }}
  .blab {{ color:{INK}; font-size:.86rem; line-height:1.18; text-align:right; overflow:hidden;
           display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; }}
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

  /* ---- pestañas (selectores ARIA, no dependen del tema interno de Streamlit) ---- */
  .stTabs button[role="tab"] {{ font-weight:600; }}
  .stTabs button[role="tab"] p {{ color:{MUTED} !important; font-weight:600; }}
  .stTabs button[role="tab"][aria-selected="true"] p {{ color:{TEAL_HI} !important; }}
  .stTabs button[role="tab"][aria-selected="true"] svg {{ fill:{TEAL_HI} !important; }}
  /* la barrita de subrayado activa (varios nombres según build) */
  .stTabs [data-baseweb="tab-highlight"],
  .stTabs [role="tablist"] [data-baseweb="tab-highlight"] {{ background-color:{TEAL} !important; }}
  .stTabs [data-baseweb="tab-border"] {{ background-color:{LINE} !important; }}

  /* ---- consulta por PDV ---- */
  .pdvhead {{ margin:4px 0 2px; }}
  .pdvhead .pt {{ font-family:'Space Grotesk'; font-size:1.9rem; font-weight:700; color:#fff; letter-spacing:-.02em; }}
  .pdvhead .ps {{ color:{MUTED}; font-size:.92rem; margin-top:4px; }}
  .pdvkpis {{ grid-template-columns:repeat(5, 1fr); }}
  .tile.off {{ opacity:.72; }}
  .tile.off .tv2 {{ color:{MUTED}; }}

  @media (max-width:820px) {{
    .pdvkpis {{ grid-template-columns:1fr 1fr; }}
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
def _xlsx_bytes(firma, _indicador, _cliente, _periodo, _metrica_label, _fmt_m, _tipo, _valor, _base,
                _var, _var_cls, _filas, _dim_label, _serie, _insights, _fecha):
    # Solo 'firma' entra al hash del caché; los demás parámetros llevan '_' para que
    # Streamlit NO los hashee (evita fallos al hashear tipos como pandas.Timestamp).
    return reporte_excel.construir_xlsx(
        indicador=_indicador, cliente=_cliente, periodo=_periodo, metrica_label=_metrica_label,
        fmt=_fmt_m, tipo=_tipo, valor=_valor, base=_base, var=_var, var_cls=_var_cls,
        filas=list(_filas), dim_label=_dim_label, serie=list(_serie),
        insights=list(_insights), fecha_txt=_fecha)

# ===================================================================
# LOGIN (portada) — toda la app queda detrás de usuario + clave
# ===================================================================
def _usuarios():
    """Usuarios válidos: sección [usuarios] en Secrets (usuario = "clave"),
    o un solo APP_USER / APP_PASSWORD. El usuario no distingue mayúsculas."""
    out = {}
    try:
        us = st.secrets.get("usuarios", None)
        if us:
            for k, v in dict(us).items():
                out[str(k).strip().lower()] = str(v)
    except Exception:
        pass
    if not out:
        try:
            u, p = st.secrets.get("APP_USER"), st.secrets.get("APP_PASSWORD")
            if u and p:
                out[str(u).strip().lower()] = str(p)
        except Exception:
            pass
    return out

def _check_login():
    u = (st.session_state.get("login_user") or "").strip().lower()
    p = str(st.session_state.get("login_pass") or "")
    us = _usuarios()
    if u and u in us and us[u] == p:
        st.session_state.auth_ok = True
        st.session_state.auth_user = u
        st.session_state.login_err = False
        try:
            motor.log_evento(u, "login")
        except Exception:
            pass
    else:
        st.session_state.auth_ok = False
        st.session_state.login_err = True

def _logout():
    st.session_state.auth_ok = False

def _render_portada():
    _logo_html = (f'<img class="logo" src="{JOBTALENT}" alt="job&amp;talent">' if JOBTALENT else "")
    _ic_chart = (f'<svg viewBox="0 0 24 24" fill="none" stroke="{TEAL}" stroke-width="2.1" '
                 'stroke-linecap="round"><path d="M3 21h18"/><rect x="5" y="11" width="3.2" height="7" rx="1"/>'
                 '<rect x="10.4" y="6" width="3.2" height="12" rx="1"/>'
                 '<rect x="15.8" y="13" width="3.2" height="5" rx="1"/></svg>')
    _ic_ai = (f'<svg viewBox="0 0 24 24" fill="none" stroke="{TEAL}" stroke-width="2.1" '
              'stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l1.7 4.3L18 9l-4.3 1.7L12 15'
              'l-1.7-4.3L6 9l4.3-1.7z"/><path d="M18.5 14l.9 2.1 2.1.9-2.1.9-.9 2.1-.9-2.1-2.1-.9 2.1-.9z"/></svg>')
    _ic_target = (f'<svg viewBox="0 0 24 24" fill="none" stroke="{TEAL}" stroke-width="2.1">'
                  '<circle cx="12" cy="12" r="8.2"/><circle cx="12" cy="12" r="3.4"/></svg>')
    _ic_bolt = (f'<svg viewBox="0 0 24 24" fill="none" stroke="{TEAL}" stroke-width="2.1" '
                'stroke-linejoin="round" stroke-linecap="round"><path d="M13 2L4 14h6l-1 8 9-12h-6z"/></svg>')
    _feats = (
        f'<div class="feat">{_ic_chart}<span>KPIs en<br>tiempo real</span></div>'
        f'<div class="feat">{_ic_ai}<span>Consultas con<br>IA avanzada</span></div>'
        f'<div class="feat">{_ic_target}<span>Todas tus marcas<br>y negocios</span></div>'
        f'<div class="feat">{_ic_bolt}<span>Decisiones más<br>rápidas y precisas</span></div>'
    )
    _css = (
        "<style>"
        ".pz{max-width:500px}"
        ".pz .logo{height:52px;margin-bottom:22px;border-radius:12px}"
        ".pz h1{font-family:'Space Grotesk',sans-serif;font-weight:700;color:#fff;font-size:3rem;"
        "line-height:1.03;letter-spacing:-.02em;margin:0}"
        ".pz h1 .tl{color:" + TEAL + "}"
        ".pz .sub{color:#C7D6EF;font-size:1.1rem;line-height:1.5;margin:16px 0 26px;max-width:40ch}"
        ".pz .feats{display:flex;flex-wrap:wrap;gap:14px 16px;margin-bottom:6px}"
        ".pz .feat{display:flex;align-items:center;gap:9px}"
        ".pz .feat svg{width:21px;height:21px;flex:none}"
        ".pz .feat span{color:#DCE8FB;font-size:.84rem;line-height:1.2}"
        ".lockhead{display:flex;align-items:center;gap:12px;margin:2px 0 12px}"
        ".lockhead .ic{width:42px;height:42px;border-radius:12px;background:rgba(0,208,192,.14);"
        "display:flex;align-items:center;justify-content:center;font-size:1.15rem}"
        ".lockhead h3{margin:0;color:#fff;font-family:'Space Grotesk';font-weight:700;font-size:1.25rem}"
        ".lockhead p{margin:3px 0 0;color:" + MUTED + ";font-size:.86rem}"
        ".pz .foot{color:" + MUTED + ";font-size:.85rem;margin-top:16px}"
        # --- tarjetas KPI flotantes (derecha, decorativas) ---
        ".kpiwrap{display:grid;grid-template-columns:1fr 1fr;gap:18px;max-width:500px;margin:0 auto;padding:6px}"
        ".kpiwrap .kpi:nth-child(2n){margin-top:40px}"
        ".kpi{background:rgba(12,27,60,.5);backdrop-filter:blur(7px);-webkit-backdrop-filter:blur(7px);"
        "border:1px solid rgba(53,236,217,.22);border-radius:18px;padding:18px;"
        "box-shadow:0 14px 44px rgba(0,0,0,.38)}"
        ".kpi .ktop{display:flex;align-items:center;gap:10px;margin-bottom:12px}"
        ".kpi .kic{width:38px;height:38px;border-radius:11px;background:rgba(0,208,192,.15);"
        "display:flex;align-items:center;justify-content:center}"
        ".kpi .kic svg{width:20px;height:20px}"
        ".kpi .klb{color:#C7D6EF;font-size:.92rem}"
        ".kpi .kvl{color:#fff;font-family:'Space Grotesk';font-weight:700;font-size:1.75rem;line-height:1}"
        ".kpi .ksub{color:#8FA6CC;font-size:.76rem;margin-top:5px}"
        "</style>"
    )
    # Fondo = tu imagen hero. El gradiente cubre la izquierda para que el login se lea,
    # y a la derecha se ve la imagen (laptop + KPIs). La tarjeta de login va opaca.
    if PORTADA_BG:
        st.markdown(
            "<style>[data-testid='stAppViewContainer']{background:"
            "linear-gradient(90deg,rgba(8,18,36,.97) 0%,rgba(8,18,36,.9) 36%,"
            "rgba(8,18,36,.55) 54%,rgba(8,18,36,.12) 74%,rgba(8,18,36,.25) 100%),"
            f"url('{PORTADA_BG}') center center / cover no-repeat fixed !important}}"
            "[data-testid='stHeader']{background:transparent !important}"
            "[data-testid='stVerticalBlockBorderWrapper']{background:rgba(9,19,38,.93) !important;"
            "border:1px solid rgba(53,236,217,.2) !important;border-radius:18px !important;"
            "box-shadow:0 22px 64px rgba(0,0,0,.5)}</style>",
            unsafe_allow_html=True)
    L, _R = st.columns([1.02, 0.98], vertical_alignment="center")
    with L:
        st.markdown(
            _css + f'<div class="pz">{_logo_html}'
            '<h1>Pregúntale a<br><span class="tl">Day by Day</span></h1>'
            '<div class="sub">Tu copiloto de Inteligencia de Negocios para tomar mejores decisiones.</div>'
            f'<div class="feats">{_feats}</div></div>',
            unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown('<div class="lockhead"><div class="ic">🔒</div>'
                        '<div><h3>Acceso restringido</h3><p>Ingresa con tu usuario y clave</p></div></div>',
                        unsafe_allow_html=True)
            if not _usuarios():
                st.caption("⚠️ Aún no hay usuarios configurados. Agrega la sección [usuarios] "
                           "al final de los Secrets de la app.")
            st.text_input("Usuario", key="login_user", placeholder="usuario")
            st.text_input("Clave", key="login_pass", type="password", placeholder="clave",
                          on_change=_check_login)
            st.button("Entrar  →", type="primary", on_click=_check_login, use_container_width=True)
            if st.session_state.get("login_err"):
                st.error("Usuario o clave incorrectos.")
        st.markdown('<div class="pz"><div class="foot">¿Sin acceso? Escríbele al '
                    'Centro de Inteligencia de Negocios.</div></div>', unsafe_allow_html=True)
    # _R queda vacío a propósito: ahí se ve la imagen de fondo (laptop + KPIs).

if "auth_ok" not in st.session_state:
    st.session_state.auth_ok = False
if not st.session_state.auth_ok:
    _render_portada()
    st.stop()

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
_spu, _lgu = st.columns([9, 1.1], vertical_alignment="center")
with _lgu:
    st.button(f"Salir", on_click=_logout, key="logout_btn", use_container_width=True,
              help=f"Cerrar sesión ({st.session_state.get('auth_user', '')})")
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

# ---------- Registro de actividad (solo ADMINISTRADOR) ----------
if st.session_state.get("auth_user") == "administrador":
    with st.expander("📋 Registro de actividad — quién entra y qué consulta"):
        _res = motor.log_resumen()
        _det = motor.log_listar(300)
        if _res is not None and not _res.empty:
            st.markdown("**Resumen por usuario**")
            st.dataframe(_res, width="stretch", hide_index=True)
        if _det is not None and not _det.empty:
            st.markdown("**Últimos movimientos**")
            st.dataframe(_det, width="stretch", hide_index=True)
        if (_res is None or _res.empty) and (_det is None or _det.empty):
            st.caption("Aún no hay actividad. La tabla se crea sola con el primer ingreso.")


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
        "pdv": st.session_state.get("m_pdv"),
        "func": st.session_state.get("m_func"),
    }
    try:
        _d = f"{st.session_state.get('m_marca')} · {st.session_state.get('m_ind')} · {st.session_state.get('m_per')}"
        motor.log_evento(st.session_state.get("auth_user"), "consulta", _d)
    except Exception:
        pass

def do_ia():
    q = (st.session_state.get("m_free") or "").strip()
    if not q:
        return
    intp, usado = motor.interpretar(q, marcas)
    st.session_state.consulta = {"via": "ia", "intp": intp, "usado": usado}
    try:
        motor.log_evento(st.session_state.get("auth_user"), "ia", q)
    except Exception:
        pass

def c_pdv_lista(marca):
    # Puntos de la marca para el selector. Sin caché: si construyes cubo_pdv después de
    # abrir el app, se recupera solo (no se queda pegado en "vacío").
    try:
        return motor.pdv_lista(marcas.get(marca, []))
    except Exception:
        return []


def _render_pdv_card(ids, pid, nm, marca, ventana, logo):
    """Tarjeta de un punto: qué indicadores capturó en el período (✅/❌)."""
    vlabel = motor.VENTANA_LABEL.get(ventana, ventana)
    try:
        est = motor.pdv_estado(ids, pid, ventana)
    except Exception as e:
        st.error(f"No pude consultar el punto: {e}")
        st.stop()
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    if logo:
        st.markdown(f'<span class="membrete"><img src="{logo}"></span>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="pdvhead"><div class="pt">📍 {_html.escape(str(nm))}</div>'
        f'<div class="ps">{_html.escape(str(marca))} &nbsp;·&nbsp; {vlabel} &nbsp;·&nbsp; ID {pid}</div></div>',
        unsafe_allow_html=True,
    )
    sub = {"agotados": "capturas", "precios": "capturas", "actividades": "capturas",
           "ventas": "ventas", "ingresos": "programaciones"}
    labels = getattr(motor, "PDV_IND_LABEL", {"agotados": "Agotados", "precios": "Precios",
                     "actividades": "Actividades", "ventas": "Ventas", "ingresos": "Ingresos"})
    tiles = ""
    for ind, lbl in labels.items():
        n = int(est.get(ind, 0))
        ok = n > 0
        val = ("✅ " + f"{n:,}".replace(",", ".")) if ok else "❌"
        tiles += (f'<div class="tile {"" if ok else "off"}"><div class="tl">{lbl}</div>'
                  f'<div class="tv2">{val}</div><div class="tsub">{sub.get(ind, "")}</div></div>')
    st.markdown(f'<div class="kpis pdvkpis">{tiles}</div>', unsafe_allow_html=True)
    hechos = sum(1 for ind in labels if int(est.get(ind, 0)) > 0)
    st.markdown(
        f'<div class="lectura">En <b>{vlabel}</b>, <b>{_html.escape(str(nm))}</b> registra actividad en '
        f'<b>{hechos}</b> de {len(labels)} indicadores. Los que salen en ❌ aún no tienen captura en el período.</div>',
        unsafe_allow_html=True,
    )
    st.markdown(PIE, unsafe_allow_html=True)
    st.stop()

# ===================================================================
# FILTRO POR FUNCIONARIO (normal, sin clave) — ficha de una persona.
# Lee la tabla cubo_funcionarios. Muestra el nombre (dato personal): hoy va en la
# parte pública; el login para ocultarlo queda para más adelante.
# ===================================================================
def c_func_lista(marca):
    try:
        return motor.func_lista(marcas.get(marca, []))
    except Exception:
        return []

def _render_func_card(ids, fid, nm, marca, ventana, logo):
    """Ficha de una persona: qué capturó/ingresó en el período (filtro por funcionario)."""
    vlabel = motor.VENTANA_LABEL.get(ventana, ventana)
    try:
        est = motor.func_estado(ids, fid, ventana)
    except Exception as e:
        st.error(f"No pude consultar a la persona: {e}")
        st.stop()
    if logo:
        st.markdown(f'<span class="membrete"><img src="{logo}"></span>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="pdvhead"><div class="pt">🧑‍💼 {_html.escape(str(nm))}</div>'
        f'<div class="ps">{_html.escape(str(marca))} &nbsp;·&nbsp; {vlabel} &nbsp;·&nbsp; ID {fid}</div></div>',
        unsafe_allow_html=True,
    )
    labels = getattr(motor, "FUN_IND_LABEL", {"ingresos": "Ingresos", "agotados": "Agotados",
                     "precios": "Precios", "actividades": "Actividades", "encuestas": "Encuestas"})
    tiles = ""
    for ind, lbl in labels.items():
        d = est.get(ind) or {}
        n = int(d.get("n", 0))
        base = d.get("base")
        if ind == "ingresos" and base:
            ok = n > 0
            val = f"{n} de {base}"
            sub = "ingresó / programados"
        else:
            ok = n > 0
            val = ("✅ " + f"{n:,}".replace(",", ".")) if ok else "❌"
            sub = "capturas"
        tiles += (f'<div class="tile {"" if ok else "off"}"><div class="tl">{lbl}</div>'
                  f'<div class="tv2">{val}</div><div class="tsub">{sub}</div></div>')
    st.markdown(f'<div class="kpis pdvkpis">{tiles}</div>', unsafe_allow_html=True)
    hechos = sum(1 for ind in labels if int((est.get(ind) or {}).get("n", 0)) > 0)
    st.markdown(
        f'<div class="lectura">En <b>{vlabel}</b>, <b>{_html.escape(str(nm))}</b> registra actividad en '
        f'<b>{hechos}</b> de {len(labels)} indicadores. En ❌ aún no hay captura en el período.</div>',
        unsafe_allow_html=True,
    )
    # Detalle: QUÉ encuestas capturó la persona (por nombre), si hay
    try:
        enc_det = motor.func_encuestas(ids, fid, ventana)
    except Exception:
        enc_det = []
    if enc_det:
        def _fmtn(x):
            return f"{int(x):,}".replace(",", ".")
        items = "".join(
            f'<li><span class="en">{_html.escape(str(t))}</span>'
            f'<span class="ec">{_fmtn(c)}</span></li>' for t, c in enc_det)
        st.markdown(
            "<style>.encd{margin-top:12px;border:1px solid #22406E;border-radius:12px;"
            "background:#0F2146;padding:10px 14px}.encd h4{margin:0 0 6px;"
            "font-family:'Space Grotesk';font-size:1rem;color:#35ECD9}"
            ".encd ul{list-style:none;margin:0;padding:0}.encd li{display:flex;"
            "justify-content:space-between;gap:12px;padding:4px 0;border-top:1px solid #16305A;"
            "color:#ECF3FF;font-size:.95rem}.encd li:first-child{border-top:none}"
            ".encd .ec{color:#9DB4DA;font-variant-numeric:tabular-nums}</style>"
            f'<div class="encd"><h4>Encuestas capturadas · {len(enc_det)}</h4><ul>{items}</ul></div>',
            unsafe_allow_html=True)
    st.markdown(
        '<div class="pie">Centro de Inteligencia de Negocios de job&amp;talent · '
        'ficha por funcionario; números agregados al último refresco.</div>', unsafe_allow_html=True)
    st.stop()

def _render_func_roster(ids, marca, ventana, logo):
    """Listado de ingresos: quién ya ingresó y quién falta, en el período."""
    vlabel = motor.VENTANA_LABEL.get(ventana, ventana)
    try:
        df = motor.func_roster(ids, ventana)
    except Exception as e:
        st.error(f"No pude armar el listado: {e}")
        st.stop()
    st.markdown(
        "<style>"
        ".rcard{border:1px solid #22406E;border-radius:14px;padding:14px 16px;background:#0F2146;}"
        ".rcard h4{margin:0 0 8px;font-family:'Space Grotesk';font-size:1.05rem;}"
        ".rcard.ok h4{color:#35ECD9;} .rcard.no h4{color:#FF8DA1;}"
        ".rlist{margin:0;padding-left:18px;max-height:360px;overflow:auto;}"
        ".rlist li{color:#ECF3FF;font-size:.95rem;margin:2px 0;}"
        ".rmiss{color:#9DB4DA;font-style:italic;} .rmore{color:#9DB4DA;font-size:.85rem;margin-top:6px;}"
        "</style>", unsafe_allow_html=True)
    if logo:
        st.markdown(f'<span class="membrete"><img src="{logo}"></span>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="pdvhead"><div class="pt">📋 Ingresos — {_html.escape(str(marca))}</div>'
        f'<div class="ps">{vlabel} &nbsp;·&nbsp; quién ya ingresó y quién falta</div></div>',
        unsafe_allow_html=True,
    )
    if df is None or df.empty:
        st.info("No hay programación de ingresos en el período para esta marca.")
        st.stop()
    df = df.copy()
    df["ingreso"] = df["ingreso"].fillna(0).astype(int)
    ya = df[df["ingreso"] > 0]
    faltan = df[df["ingreso"] == 0]
    def _names(d):
        if d.empty:
            return "<div class='rmiss'>— nadie —</div>"
        rows = "".join(f"<li>{_html.escape(str(r['funcionario']))}</li>" for _, r in d.head(60).iterrows())
        extra = f"<div class='rmore'>y {len(d) - 60} más…</div>" if len(d) > 60 else ""
        return f"<ul class='rlist'>{rows}</ul>{extra}"
    rc1, rc2 = st.columns(2)
    rc1.markdown(f'<div class="rcard ok"><h4>✅ Ya ingresaron · {len(ya)}</h4>{_names(ya)}</div>', unsafe_allow_html=True)
    rc2.markdown(f'<div class="rcard no"><h4>❌ Faltan por ingresar · {len(faltan)}</h4>{_names(faltan)}</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="pie">Vista interna de supervisión · contiene datos personales. '
        'Es el acumulado del período (grano mensual); para el seguimiento del día usa el Panel de Control de Llamadas. '
        'No compartas el enlace ni capturas de esta vista.</div>', unsafe_allow_html=True)
    st.stop()


op_marca = list(marcas.keys()) + ["Todas las marcas"]
ind_labels = list(PRESET_METRICAS.keys())

with st.container(border=True):
    st.markdown(
        '<div class="eye"><span class="d"></span><b>Consulta rápida</b>'
        '<span>— respuesta al instante, sin gastar IA</span></div>',
        unsafe_allow_html=True,
    )
    # Fila 1: define QUÉ ver (marca, indicador, período, ver por)
    c1, c2, c3, c4 = st.columns([1.3, 1, 1, 1], vertical_alignment="bottom")
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
        format_func=lambda s: DIM_LABEL.get(s, s.replace("_", " ")).capitalize(),
    )
    # Fila 2: acercar a UN punto o a UNA persona (opcional, depende de la marca)
    _tiene_marca = bool(marca_sel) and marca_sel != "Todas las marcas"
    d1, d2 = st.columns([1, 1], vertical_alignment="bottom")
    _pdvs = c_pdv_lista(marca_sel) if _tiene_marca else []
    _pdv_opts = ["(Todos los puntos)"] + [f"{nm}  ·  ID {pid}" for pid, nm in _pdvs]
    pdv_sel = d1.selectbox("Punto de venta", _pdv_opts, key="m_pdv",
                           help="Haz clic y escribe para buscar por nombre o ID.")
    _funcs = c_func_lista(marca_sel) if _tiene_marca else []
    _func_opts = ["(Todos los funcionarios)"] + [f"{nm}  ·  ID {fid}" for fid, nm in _funcs]
    func_sel = d2.selectbox("Funcionario", _func_opts, key="m_func",
                            help="Haz clic y escribe para buscar por nombre o ID.")

    bcol, _bsp = st.columns([0.32, 0.68])
    bcol.button("Consultar", type="primary", on_click=do_menu)

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
            'cobertura, agotados, precios, ventas, actividades, encuestas e ingresos de tus marcas. '
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
    # Si se eligió un FUNCIONARIO específico -> su ficha (tiene prioridad sobre el PDV)
    _funcsel = cons.get("func")
    if _funcsel and _funcsel != "(Todos los funcionarios)":
        try:
            _fnm, _fpid = _funcsel.rsplit("  ·  ID ", 1)
            _fpid = int(_fpid)
        except Exception:
            _fnm, _fpid = str(_funcsel), None
        if _fpid is not None:
            _render_func_card(ids, _fpid, _fnm, cname, ventana, logo)   # hace st.stop()

    # Si se eligió un punto de venta específico -> SU tarjeta
    _pdvsel = cons.get("pdv")
    if _pdvsel and _pdvsel != "(Todos los puntos)":
        try:
            _nm2, _pid2 = _pdvsel.rsplit("  ·  ID ", 1)
            _pid2 = int(_pid2)
        except Exception:
            _nm2, _pid2 = str(_pdvsel), None
        if _pid2 is not None:
            _render_pdv_card(ids, _pid2, _nm2, cname, ventana, logo)   # hace st.stop()

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

dim_label = DIM_LABEL.get(dkey, dkey.replace("_", " "))
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
    except Exception as _e:
        _cxls.caption(f"Excel: {type(_e).__name__}: {str(_e)[:140]}")
else:
    _cxls.caption(f"Excel no disponible — {_xlsx_err or 'falta reporte_excel.py en el repo'}")

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
    _nm = _html.escape(str(r["DIMENSION"]))
    _bars += (f'<div class="bar"><span class="blab" title="{_nm}">{_nm}</span>'
              f'<span class="btrack"><span class="bfill" style="width:{w:.1f}%"></span></span>'
              f'<span class="bval">{fmt(r["VALOR"], m["fmt"])}</span></div>')
st.markdown(f'<div class="btitle">{m["label"]} por {dim_label} ({cname})</div>{_bars}', unsafe_allow_html=True)

# --- 🏅 Top de funcionarios por el indicador real (si el indicador tiene data por persona) ---
try:
    _ftop = motor.func_top(ids, dom, ventana, metrica)
except Exception as _fe:
    _ftop = []
    # Si falla (p.ej. el cubo aún no tiene las columnas num/den), que NO quede mudo:
    st.caption(f"⚠️ Top funcionarios no disponible — reconstruye el cubo de funcionarios "
               f"con el refresco más reciente. Detalle: {_fe}")
if _ftop:
    _fmax = max((float(v) for _, v, _ in _ftop), default=0) or 1
    _frows = ""
    for _fn, _fv, _fb in _ftop:
        _fw = max(3.0, (float(_fv) / _fmax) * 100.0)
        _fnm = _html.escape(str(_fn))
        _frows += (f'<div class="bar"><span class="blab" title="{_fnm}">{_fnm}</span>'
                   f'<span class="btrack"><span class="bfill" style="width:{_fw:.1f}%"></span></span>'
                   f'<span class="bval">{fmt(_fv, m["fmt"])}</span></div>')
    st.markdown(f'<div class="btitle">🏅 Top funcionarios · {m["label"]} ({cname})</div>{_frows}',
                unsafe_allow_html=True)

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
