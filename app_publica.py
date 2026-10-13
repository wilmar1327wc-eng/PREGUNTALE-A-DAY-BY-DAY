# -*- coding: utf-8 -*-
"""
Pregúntale a DayByDay — APP PÚBLICA (lee el cubo en Neon, sin VPN).

Deploy en Streamlit Community Cloud. Necesita dos "secrets":
    DATABASE_URL = "postgresql://..."
    GEMINI_API_KEY = "AIza..."  (o AQ...)
Localmente puedes ponerlos como variables de entorno o en .streamlit/secrets.toml
"""

import os
import streamlit as st
import plotly.express as px

# Puente: en Streamlit Cloud los secrets llegan por st.secrets -> los paso a entorno
try:
    for _k in ("DATABASE_URL", "GEMINI_API_KEY", "GOOGLE_API_KEY"):
        if _k in st.secrets and not os.environ.get(_k):
            os.environ[_k] = str(st.secrets[_k])
except Exception:
    pass

import motor_nube as motor

TEAL = "#00897B"
TEAL2 = "#00C4BA"
TINTA = "#1A2E35"

st.set_page_config(page_title="Pregúntale a DayByDay", page_icon="💬", layout="wide")

st.markdown(f"""
<style>
  .block-container {{ padding-top: 1.5rem; max-width: 1100px; }}
  .encab {{ background: linear-gradient(135deg, {TEAL} 0%, {TEAL2} 100%);
     color:#fff; padding:20px 26px; border-radius:16px; margin-bottom:14px; }}
  .encab h1 {{ margin:0; font-size:1.55rem; }}
  .encab p  {{ margin:4px 0 0; opacity:.92; font-size:.95rem; }}
  .chip {{ display:inline-block; background:#E6F6F4; color:{TEAL}; padding:3px 11px;
     border-radius:999px; font-size:.82rem; margin:2px 4px 2px 0; border:1px solid #CDEDE9; }}
  .kpi {{ background:#fff; border:1px solid #E6E9EC; border-left:6px solid {TEAL2};
     border-radius:14px; padding:18px 22px; margin:6px 0 14px; }}
  .kpi .val {{ font-size:2.6rem; font-weight:800; color:{TINTA}; line-height:1; }}
  .kpi .sub {{ color:#60707A; font-size:.92rem; margin-top:6px; }}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="encab">
  <h1>💬 Pregúntale a DayByDay</h1>
  <p>Escribe tu pregunta en español y te respondo con la cifra, el gráfico y una lectura rápida.</p>
</div>
""", unsafe_allow_html=True)


@st.cache_data(ttl=1800, show_spinner="Cargando...")
def cargar_clientes():
    return motor.clientes()


try:
    marcas = cargar_clientes()
except Exception as e:
    st.error(f"No pude leer el cubo. ¿Está configurada la base (DATABASE_URL)?\n\nDetalle: {e}")
    st.stop()

if not marcas:
    st.error("El cubo está vacío o no hay conexión. Corre el refresco e inténtalo de nuevo.")
    st.stop()

with st.sidebar:
    st.subheader("Ajustes")
    opciones_cli = ["(Detectar desde la pregunta)"] + list(marcas.keys())
    cliente_sel = st.selectbox("Cliente", opciones_cli)
    ventana_sel = st.selectbox(
        "Ventana de tiempo", ["(Auto)"] + motor.VENTANAS,
        format_func=lambda k: "Auto (según la pregunta)" if k == "(Auto)" else motor.VENTANA_LABEL.get(k, k),
    )
    topn = st.slider("Máximo de barras", 5, 20, 12)
    st.caption("Datos agregados al último refresco. Sin datos personales.")

if "pregunta" not in st.session_state:
    st.session_state.pregunta = ""

def set_q(q):
    st.session_state.pregunta = q

st.caption("Prueba con:")
ejemplos = [
    "¿Cómo va la cobertura de Henkel?",
    "¿Qué marcas tienen más agotados en Unilever?",
    "Ventas de Solla por zona este mes",
    "Actividades de Coltabaco por tipo",
]
cols = st.columns(len(ejemplos))
for c, ex in zip(cols, ejemplos):
    c.button(ex, on_click=set_q, args=(ex,), use_container_width=True)

pregunta = st.text_input(
    "Tu pregunta", key="pregunta",
    placeholder="Ej: ¿Cómo va el % de agotados de Derco por cadena en los últimos 3 meses?",
    label_visibility="collapsed",
)

if not pregunta.strip():
    st.info("Escribe una pregunta o toca uno de los ejemplos para empezar.")
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
dom = intencion["dominio"]
metrica = intencion["metrica"]
dimension = intencion["dimension"]
meta = motor.DOMINIOS[dom]

try:
    valor, base, mkey, m, sql_kpi = motor.kpi(dom, ids, ventana, metrica)
    dfg, dkey, m2, sql_grp = motor.por_dimension(dom, ids, ventana, metrica, dimension)
except Exception as e:
    st.error(f"Hubo un problema al consultar el cubo: {e}")
    st.stop()

dim_label = dkey.replace("_", " ")
chips = (
    f'<span class="chip">📂 {meta["nombre"]}</span>'
    f'<span class="chip">🏢 {cname}</span>'
    f'<span class="chip">📊 {m["label"]}</span>'
    f'<span class="chip">↕️ por {dim_label}</span>'
    f'<span class="chip">🗓️ {motor.VENTANA_LABEL.get(ventana, ventana)}</span>'
)
st.markdown("**Entendí:** " + chips, unsafe_allow_html=True)
st.caption(f"Motor de interpretación: {motor_usado}")

st.markdown(
    f'<div class="kpi"><div class="val">{motor.fmt_valor(valor, m["fmt"])}</div>'
    f'<div class="sub">{m["label"]} · {cname} · {motor.VENTANA_LABEL.get(ventana, ventana)} '
    f'· base: {motor.fmt_valor(base, "num")} registros</div></div>',
    unsafe_allow_html=True,
)

if dfg.empty:
    st.warning("No encontré registros para esto en la ventana elegida. Prueba ampliar la ventana.")
    st.stop()

top = dfg.head(topn).sort_values("VALOR", ascending=True)
top["ETIQUETA"] = top["VALOR"].apply(lambda x: motor.fmt_valor(x, m["fmt"]))
fig = px.bar(top, x="VALOR", y="DIMENSION", orientation="h", text="ETIQUETA",
             color_discrete_sequence=[TEAL2])
fig.update_traces(textposition="outside", cliponaxis=False)
fig.update_layout(
    title=f'{m["label"]} por {dim_label} — {cname}',
    plot_bgcolor="white", paper_bgcolor="white",
    margin=dict(l=10, r=30, t=50, b=10), height=max(320, 34 * len(top) + 90),
    xaxis_title=None, yaxis_title=None, font=dict(color=TINTA),
)
if m["fmt"] == "pct":
    fig.update_xaxes(tickformat=".0%")
st.plotly_chart(fig, use_container_width=True)

alto, bajo = dfg.iloc[0], dfg.iloc[-1]
st.markdown(
    f"**Lectura.** En {motor.VENTANA_LABEL.get(ventana, ventana)}, **{cname}** registra "
    f"**{m['label'].lower()}** de **{motor.fmt_valor(valor, m['fmt'])}** (base {motor.fmt_valor(base,'num')}). "
    f"El {dim_label} más alto es **{alto['DIMENSION']}** ({motor.fmt_valor(alto['VALOR'], m['fmt'])}); "
    f"el más bajo, **{bajo['DIMENSION']}** ({motor.fmt_valor(bajo['VALOR'], m['fmt'])})."
)

tabla = dfg.copy()
tabla["Valor"] = tabla["VALOR"].apply(lambda x: motor.fmt_valor(x, m["fmt"]))
tabla = tabla.rename(columns={"DIMENSION": dim_label.capitalize(), "BASE": "Base (registros)"})
st.dataframe(tabla[[dim_label.capitalize(), "Valor", "Base (registros)"]],
             use_container_width=True, hide_index=True)

with st.expander("Ver detalle técnico (intención + SQL)"):
    st.json({"dominio": dom, "cliente": cname, "ids": ids, "metrica": mkey,
             "dimension": dkey, "ventana": ventana})
    st.code(sql_kpi, language="sql")
    st.code(sql_grp, language="sql")
