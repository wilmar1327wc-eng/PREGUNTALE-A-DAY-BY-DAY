# -*- coding: utf-8 -*-
"""
motor_nube.py — Cerebro de la app PÚBLICA de "Pregúntale a DayByDay".

Igual que motor.py, pero lee del CUBO en Postgres (Neon), no de Oracle.
No tiene ninguna dependencia de Oracle ni de config.py: solo necesita
  - DATABASE_URL  (cadena de Postgres)
  - GEMINI_API_KEY  (o GOOGLE_API_KEY)
como variables de entorno.

Las métricas se recomponen desde las medidas agregadas del cubo
(base, agotado_num, visitado_num, precio_sum/cnt, propia_num, venta_sum, unidades_sum).
"""

import os
import json
import psycopg2
import pandas as pd

MODELO_GEMINI = "gemini-3.8-flash"


# ===================================================================
# CONEXIÓN AL CUBO (Postgres)
# ===================================================================
def _url():
    return os.environ.get("DATABASE_URL")


def run_df(sql, binds=None):
    url = _url()
    if not url:
        raise RuntimeError(
            'No encuentro DATABASE_URL. Revisa que .streamlit/secrets.toml tenga la línea '
            'DATABASE_URL = "postgresql://..." en UNA sola línea y con comillas.'
        )
    conn = psycopg2.connect(url)
    try:
        cur = conn.cursor()
        cur.execute(sql, binds or {})
        cols = [d[0].lower() for d in cur.description]
        rows = cur.fetchall()
        return pd.DataFrame(rows, columns=cols)
    finally:
        conn.close()


# ===================================================================
# CATÁLOGO (lado nube): métricas recompuestas desde medidas del cubo
# ===================================================================
DOMINIOS = {
    "agotados": {
        "nombre": "Agotados", "tabla": "cubo_agotados",
        "metrica_default": "pct_agotado", "dimension_default": "regional",
        "metricas": {
            "pct_agotado": {"label": "% agotado", "fmt": "pct", "tipo": "ratio", "num": "agotado_num"},
            "num_agotados": {"label": "# agotados", "fmt": "num", "tipo": "sum", "col": "agotado_num"},
            "registros": {"label": "# registros", "fmt": "num", "tipo": "count"},
        },
        "dimensiones": ["regional", "departamento", "municipio", "canal", "cadena", "categoria",
                        "subcategoria", "marca", "producto", "cargo", "pdv", "causal", "tipo"],
    },
    "cobertura": {
        "nombre": "Cobertura", "tabla": "cubo_cobertura",
        "metrica_default": "pct_cobertura", "dimension_default": "regional",
        "metricas": {
            "pct_cobertura": {"label": "% cobertura", "fmt": "pct", "tipo": "ratio", "num": "visitado_num"},
            "programados": {"label": "# programados", "fmt": "num", "tipo": "count"},
            "visitados": {"label": "# visitados", "fmt": "num", "tipo": "sum", "col": "visitado_num"},
        },
        "dimensiones": ["regional", "departamento", "municipio", "canal", "cadena", "categoria_pdv",
                        "cargo", "pdv", "causal", "jefe"],
    },
    "precios": {
        "nombre": "Precios", "tabla": "cubo_precios",
        "metrica_default": "precio_promedio", "dimension_default": "marca",
        "metricas": {
            "precio_promedio": {"label": "Precio promedio", "fmt": "money", "tipo": "avg",
                                "num": "precio_sum", "den": "precio_cnt"},
            "capturas": {"label": "# capturas", "fmt": "num", "tipo": "count"},
        },
        "dimensiones": ["regional", "departamento", "municipio", "canal", "cadena", "categoria",
                        "marca", "producto", "cargo", "pdv"],
    },
    "actividades": {
        "nombre": "Actividades", "tabla": "cubo_actividades",
        "metrica_default": "num_actividades", "dimension_default": "tipo",
        "metricas": {
            "num_actividades": {"label": "# actividades", "fmt": "num", "tipo": "count"},
            "pct_propia": {"label": "% actividad propia", "fmt": "pct", "tipo": "ratio", "num": "propia_num"},
        },
        "dimensiones": ["regional", "departamento", "municipio", "canal", "cadena", "tipo",
                        "marca", "categoria", "propia", "cargo", "pdv"],
    },
    "ventas": {
        "nombre": "Ventas", "tabla": "cubo_ventas",
        "metrica_default": "venta_total", "dimension_default": "zona",
        "metricas": {
            "venta_total": {"label": "Venta total", "fmt": "money", "tipo": "sum", "col": "venta_sum"},
            "unidades": {"label": "Unidades vendidas", "fmt": "num", "tipo": "sum", "col": "unidades_sum"},
            "registros": {"label": "# registros", "fmt": "num", "tipo": "count"},
        },
        "dimensiones": ["zona", "departamento", "municipio", "canal", "cadena", "categoria",
                        "subcategoria", "marca", "producto", "pdv"],
    },
}

VENTANAS = ["hoy", "semana", "mes", "30d", "3m", "6m", "anio"]
VENTANA_LABEL = {
    "hoy": "hoy", "semana": "esta semana", "mes": "este mes", "30d": "últimos 30 días",
    "3m": "últimos 3 meses", "6m": "últimos 6 meses", "anio": "este año",
}

# Cortes de fecha en sintaxis Postgres (el cubo guarda 'dia' por día)
_FECHA = {
    "hoy": "CURRENT_DATE",
    "semana": "date_trunc('week', CURRENT_DATE)",
    "mes": "date_trunc('month', CURRENT_DATE)",
    "30d": "CURRENT_DATE - 30",
    "3m": "CURRENT_DATE - interval '3 months'",
    "6m": "CURRENT_DATE - interval '6 months'",
    "anio": "date_trunc('year', CURRENT_DATE)",
}


# ===================================================================
# CLIENTES (desde el cubo)
# ===================================================================
def clientes():
    df = run_df("SELECT marca, cliente_id FROM cubo_clientes")
    out = {}
    for _, r in df.iterrows():
        out.setdefault(r["marca"], set()).add(int(r["cliente_id"]))
    return {k: sorted(v) for k, v in sorted(out.items())}


# ===================================================================
# INTÉRPRETE (idéntico en espíritu a motor.py)
# ===================================================================
def api_key():
    for k in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        if os.environ.get(k):
            return os.environ[k]
    return None


def _match_cliente(texto, marcas):
    t = (texto or "").lower()
    for disp, ids in marcas.items():
        if disp.lower() in t:
            return disp, ids
    return None, None


def _heuristica(pregunta, marcas):
    q = (pregunta or "").lower()
    dom = "agotados"
    if any(w in q for w in ["cobertur", "visit", "sin visitar", "ingres"]):
        dom = "cobertura"
    elif any(w in q for w in ["precio", "competencia", "oferta"]):
        dom = "precios"
    elif any(w in q for w in ["activ", "merchand", "exhib", "descuento"]):
        dom = "actividades"
    elif any(w in q for w in ["venta", "vendid", "sell", "unidad"]):
        dom = "ventas"
    elif any(w in q for w in ["agotad", "quiebre", "faltante", "disponible", "stock"]):
        dom = "agotados"

    cname, cids = _match_cliente(q, marcas)

    mapd = {
        "regional": ["regional", "región", "region"], "marca": ["marca"], "cadena": ["cadena"],
        "canal": ["canal"], "categoria": ["categoría", "categoria"], "producto": ["producto", "sku"],
        "municipio": ["municipio", "ciudad"], "departamento": ["departamento", "depto"],
        "cargo": ["cargo", "rol"], "pdv": ["pdv", "punto de venta", "tienda"], "zona": ["zona"],
        "tipo": ["tipo"], "causal": ["causal", "motivo"],
    }
    dim = None
    for k, ws in mapd.items():
        if any(w in q for w in ws):
            dim = k
            break

    ven = "6m"
    if "hoy" in q:
        ven = "hoy"
    elif "semana" in q:
        ven = "semana"
    elif "mes" in q:
        ven = "mes"
    elif "año" in q or "anio" in q:
        ven = "anio"
    elif "trimestre" in q or "3 mes" in q:
        ven = "3m"
    elif "30" in q:
        ven = "30d"

    return {"dominio": dom, "cliente_ids": cids, "cliente_nombre": cname,
            "metrica": None, "dimension": dim, "ventana": ven}


def _gemini(pregunta, marcas, key):
    import google.generativeai as genai
    genai.configure(api_key=key)
    cat = {d: {"metricas": list(DOMINIOS[d]["metricas"].keys()),
               "dimensiones": DOMINIOS[d]["dimensiones"]} for d in DOMINIOS}
    prompt = (
        "Eres un intérprete que traduce una pregunta de negocio a JSON. Responde SOLO JSON.\n"
        f"Dominios con métricas y dimensiones válidas: {json.dumps(cat, ensure_ascii=False)}\n"
        f"Clientes disponibles (nombre EXACTO): {list(marcas.keys())}\n"
        f"Ventanas válidas: {VENTANAS}\n\n"
        f'Pregunta: "{pregunta}"\n\n'
        "Devuelve: dominio (uno válido), cliente (nombre exacto o null), "
        "metrica (clave válida del dominio o null), dimension (clave válida o null), "
        'ventana (de la lista; si no se menciona "6m").'
    )
    model = genai.GenerativeModel(MODELO_GEMINI)
    resp = model.generate_content(
        prompt, generation_config={"response_mime_type": "application/json", "temperature": 0}
    )
    data = json.loads(resp.text)
    dom = data.get("dominio") if data.get("dominio") in DOMINIOS else "agotados"
    cname = data.get("cliente")
    cids = marcas.get(cname) if cname in marcas else None
    return {"dominio": dom, "cliente_ids": cids, "cliente_nombre": cname if cids else None,
            "metrica": data.get("metrica"), "dimension": data.get("dimension"),
            "ventana": data.get("ventana") if data.get("ventana") in VENTANAS else "6m"}


def interpretar(pregunta, marcas):
    key = api_key()
    if key:
        try:
            return _gemini(pregunta, marcas, key), "Gemini"
        except Exception as e:
            return _heuristica(pregunta, marcas), f"heurístico (Gemini no respondió: {e})"
    return _heuristica(pregunta, marcas), "heurístico"


# ===================================================================
# CONSULTA DEL CUBO + RECOMPOSICIÓN DE MÉTRICAS
# ===================================================================
def _metrica(dom, metrica):
    mets = DOMINIOS[dom]["metricas"]
    key = metrica if metrica in mets else DOMINIOS[dom]["metrica_default"]
    return key, mets[key]


def _medidas(m):
    if m["tipo"] == "ratio":
        return [m["num"]]
    if m["tipo"] == "sum":
        return [m["col"]]
    if m["tipo"] == "avg":
        return [m["num"], m["den"]]
    return []  # count


def _where(ids, ventana):
    binds, ph = {}, []
    for i, cid in enumerate(ids):
        k = f"c{i}"
        binds[k] = int(cid)
        ph.append(f"%({k})s")
    conds = [f"cliente_id IN ({','.join(ph)})",
             f"dia >= {_FECHA.get(ventana, _FECHA['6m'])}"]
    return " AND ".join(conds), binds


def _valor(m, row, base):
    if m["tipo"] == "ratio":
        num = float(row[m["num"]] or 0)
        return (num / base) if base else 0
    if m["tipo"] == "sum":
        return float(row[m["col"]] or 0)
    if m["tipo"] == "avg":
        den = float(row[m["den"]] or 0)
        return (float(row[m["num"]] or 0) / den) if den else float("nan")
    return base


def kpi(dom, ids, ventana, metrica):
    meta = DOMINIOS[dom]
    key, m = _metrica(dom, metrica)
    where, binds = _where(ids, ventana)
    binds["dim"] = meta["dimension_default"]   # una sola dimensión para no multiplicar
    sel = ["SUM(base) AS base"] + [f"SUM({c}) AS {c}" for c in _medidas(m)]
    sql = f"SELECT {', '.join(sel)} FROM {meta['tabla']} WHERE {where} AND dimension = %(dim)s"
    df = run_df(sql, binds)
    base = int(df["base"].iloc[0] or 0) if not df.empty else 0
    val = _valor(m, df.iloc[0], base) if not df.empty else 0
    if val != val:  # nan
        val = 0
    return val, base, key, m, sql


def por_dimension(dom, ids, ventana, metrica, dimension):
    meta = DOMINIOS[dom]
    key, m = _metrica(dom, metrica)
    dims = meta["dimensiones"]
    dkey = dimension if dimension in dims else meta["dimension_default"]
    where, binds = _where(ids, ventana)
    binds["dim"] = dkey
    sel = ["valor AS dimension", "SUM(base) AS base"] + [f"SUM({c}) AS {c}" for c in _medidas(m)]
    sql = (f"SELECT {', '.join(sel)} FROM {meta['tabla']} "
           f"WHERE {where} AND dimension = %(dim)s GROUP BY valor")
    df = run_df(sql, binds)
    if df.empty:
        return df, dkey, m, sql
    df["VALOR"] = df.apply(lambda r: _valor(m, r, int(r["base"] or 0)), axis=1)
    df = df.dropna(subset=["VALOR"]).sort_values("VALOR", ascending=False).reset_index(drop=True)
    df = df.rename(columns={"dimension": "DIMENSION", "base": "BASE"})
    return df, dkey, m, sql


# ===================================================================
# FORMATO
# ===================================================================
def fmt_valor(v, fmt):
    try:
        v = float(v)
    except Exception:
        return str(v)
    if fmt == "pct":
        return f"{v * 100:.1f}%"
    if fmt == "money":
        return "$ " + f"{v:,.0f}".replace(",", ".")
    return f"{v:,.0f}".replace(",", ".")
