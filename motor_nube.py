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
# Groq: 30 req/min gratis. Prueba varios modelos y se queda con el primero que funcione.
MODELOS_GROQ = ["llama-3.3-70b-versatile", "openai/gpt-oss-20b",
                "openai/gpt-oss-120b", "llama-3.1-8b-instant"]
_GROQ_OK = {"modelo": None}   # recuerda el que sirvió


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
    "encuestas": {
        "nombre": "Encuestas", "tabla": "cubo_encuestas",
        "metrica_default": "num_encuestas", "dimension_default": "regional",
        "metricas": {
            "num_encuestas": {"label": "# encuestas", "fmt": "num", "tipo": "count"},
        },
        "dimensiones": ["regional", "departamento", "municipio", "canal", "cadena",
                        "categoria_pdv", "zona", "cargo", "titulo", "estado", "pdv"],
    },
    "ingresos": {
        "nombre": "Ingresos", "tabla": "cubo_ingresos",
        "metrica_default": "pct_asistencia", "dimension_default": "regional",
        "metricas": {
            # base = total programado · ingresaron = VISITADO · pendientes = PROGRAMADO
            "pct_asistencia": {"label": "% asistencia", "fmt": "pct", "tipo": "ratio", "num": "ingresaron"},
            "num_ingresaron": {"label": "# ingresaron", "fmt": "num", "tipo": "sum", "col": "ingresaron"},
            "num_pendientes": {"label": "# pendientes", "fmt": "num", "tipo": "sum", "col": "pendientes"},
            "programados": {"label": "# programados", "fmt": "num", "tipo": "count"},
        },
        "dimensiones": ["regional", "municipio", "canal", "cadena", "categoria_pdv",
                        "zona", "cargo", "pdv"],
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
    hit = True   # ¿la pregunta menciona algún indicador de DBD?
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
    elif any(w in q for w in ["encuest", "survey", "sondeo"]):
        dom = "encuestas"
    elif any(w in q for w in ["ingres", "asistenc", "checkin", "check-in", "fichaj", "ya entraron"]):
        dom = "ingresos"
    else:
        hit = False

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

    # En tema si menciona un indicador de DBD o uno de los clientes gestionados.
    return {"dominio": dom, "cliente_ids": cids, "cliente_nombre": cname,
            "metrica": None, "dimension": dim, "ventana": ven,
            "en_tema": bool(hit or cname)}


def _prompt(pregunta, marcas):
    cat = {d: {"metricas": list(DOMINIOS[d]["metricas"].keys()),
               "dimensiones": DOMINIOS[d]["dimensiones"]} for d in DOMINIOS}
    return (
        "Eres un intérprete que SOLO traduce preguntas sobre la operación comercial de "
        "'Day by Day' (cobertura, agotados, precios, ventas y actividades de merchandising "
        "de los clientes listados) a un JSON de consulta. No respondes nada más: ni cultura "
        "general, ni opiniones, ni código, ni otras empresas o temas ajenos. Responde SOLO JSON.\n"
        f"Dominios con métricas y dimensiones válidas: {json.dumps(cat, ensure_ascii=False)}\n"
        f"Clientes disponibles (nombre EXACTO): {list(marcas.keys())}\n"
        f"Ventanas válidas: {VENTANAS}\n"
        "Devuelve: en_dominio (true SOLO si la pregunta trata de esos indicadores/clientes; "
        "false si es ajena, p.ej. saludos, chistes, cultura general, código, otra empresa), "
        "dominio (uno válido), cliente (nombre exacto o null), "
        "metrica (clave válida del dominio o null), dimension (clave válida o null), "
        'ventana (de la lista; si no se menciona "6m").\n\n'
        f'Pregunta: "{pregunta}"'
    )


def _parse(data, marcas):
    dom = data.get("dominio") if data.get("dominio") in DOMINIOS else "agotados"
    cname = data.get("cliente")
    cids = marcas.get(cname) if cname in marcas else None
    return {"dominio": dom, "cliente_ids": cids, "cliente_nombre": cname if cids else None,
            "metrica": data.get("metrica"), "dimension": data.get("dimension"),
            "ventana": data.get("ventana") if data.get("ventana") in VENTANAS else "6m",
            "en_tema": bool(data.get("en_dominio", True))}


def _groq(pregunta, marcas, key):
    from groq import Groq
    client = Groq(api_key=key)
    prompt = _prompt(pregunta, marcas)
    candidatos = MODELOS_GROQ
    if _GROQ_OK["modelo"] in MODELOS_GROQ:   # el que ya sirvió va de primero
        candidatos = [_GROQ_OK["modelo"]] + [m for m in MODELOS_GROQ if m != _GROQ_OK["modelo"]]
    ultimo = None
    for modelo in candidatos:
        try:
            resp = client.chat.completions.create(
                model=modelo,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}, temperature=0,
            )
            _GROQ_OK["modelo"] = modelo
            return _parse(json.loads(resp.choices[0].message.content), marcas)
        except Exception as e:
            ultimo = e
    raise ultimo


def _gemini(pregunta, marcas, key):
    import google.generativeai as genai
    genai.configure(api_key=key)
    model = genai.GenerativeModel(MODELO_GEMINI)
    resp = model.generate_content(
        _prompt(pregunta, marcas),
        generation_config={"response_mime_type": "application/json", "temperature": 0},
    )
    return _parse(json.loads(resp.text), marcas)


def interpretar(pregunta, marcas):
    # Prioridad: Groq (30/min) -> Gemini (5/min) -> heurístico
    errs = []
    gk = os.environ.get("GROQ_API_KEY")
    if gk:
        try:
            return _groq(pregunta, marcas, gk), "Groq"
        except Exception as e:
            errs.append(f"Groq: {e}")
    gem = api_key()
    if gem:
        try:
            return _gemini(pregunta, marcas, gem), "Gemini"
        except Exception as e:
            errs.append(f"Gemini: {e}")
    suf = f" ({' | '.join(errs)})" if errs else ""
    return _heuristica(pregunta, marcas), "heurístico" + suf


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


def fmt_compacto(v, fmt):
    """Formato corto estilo ejecutivo: $ 4,82 mil M · 128,6 mil · 94,8%."""
    try:
        v = float(v)
    except Exception:
        return str(v)
    if fmt == "pct":
        return f"{v * 100:.1f}".replace(".", ",") + "%"
    a = abs(v)
    if fmt == "money":
        if a >= 1e9:
            return "$ " + f"{v / 1e9:.2f}".replace(".", ",") + " mil M"
        if a >= 1e6:
            return "$ " + f"{v / 1e6:.0f}".replace(",", ".") + " M"
        if a >= 1e3:
            return "$ " + f"{v / 1e3:.0f}".replace(",", ".") + " mil"
        return "$ " + f"{v:,.0f}".replace(",", ".")
    # número
    if a >= 1e6:
        return f"{v / 1e6:.1f}".replace(".", ",") + " M"
    if a >= 1e3:
        return f"{v / 1e3:.1f}".replace(".", ",") + " mil"
    return f"{v:,.0f}".replace(",", ".")


def fmt_var(var):
    """Variación con signo: +12,4% / -1,6% / — (si no hay periodo previo)."""
    if var is None:
        return "—", "flat"
    pct = var * 100
    signo = "flat"
    if pct > 0.05:
        signo = "up"
    elif pct < -0.05:
        signo = "down"
    flecha = "▲" if signo == "up" else ("▼" if signo == "down" else "—")
    return f"{flecha} {pct:+.1f}%".replace(".", ","), signo


# ===================================================================
# TABLERO EJECUTIVO — todo se calcula desde el cubo existente
# (marca + período + un desglose por dimensión). No toca el refresco.
# ===================================================================

# Inicio del periodo actual y del periodo anterior equivalente (SQL Postgres).
_RANGO = {
    "hoy":    ("CURRENT_DATE",                          "CURRENT_DATE - 1"),
    "semana": ("date_trunc('week', CURRENT_DATE)",      "date_trunc('week', CURRENT_DATE) - interval '1 week'"),
    "mes":    ("date_trunc('month', CURRENT_DATE)",     "date_trunc('month', CURRENT_DATE) - interval '1 month'"),
    "30d":    ("CURRENT_DATE - 30",                     "CURRENT_DATE - 60"),
    "3m":     ("CURRENT_DATE - interval '3 months'",    "CURRENT_DATE - interval '6 months'"),
    "6m":     ("CURRENT_DATE - interval '6 months'",    "CURRENT_DATE - interval '12 months'"),
    "anio":   ("date_trunc('year', CURRENT_DATE)",      "date_trunc('year', CURRENT_DATE) - interval '1 year'"),
}


def _ids_ph(ids, binds):
    """Placeholders parametrizados para los cliente_id (seguro, sin inyección)."""
    ph = []
    for i, cid in enumerate(ids):
        k = f"c{i}"
        binds[k] = int(cid)
        ph.append(f"%({k})s")
    return ",".join(ph)


def freshness():
    """Fecha del dato más reciente en el cubo (para 'datos actualizados a ...')."""
    try:
        df = run_df("SELECT MAX(dia) AS d FROM cubo_ventas")
        if not df.empty and df["d"].iloc[0] is not None:
            return df["d"].iloc[0]
    except Exception:
        pass
    return None


def kpi_var(dom, ids, ventana, metrica=None):
    """Valor del periodo actual + variación vs el periodo anterior equivalente.
    Una sola consulta (sumas condicionales). var=None si no hay dato previo."""
    meta = DOMINIOS[dom]
    key, m = _metrica(dom, metrica)
    ini_act, ini_prev = _RANGO.get(ventana, _RANGO["6m"])
    binds = {}
    idsph = _ids_ph(ids, binds)
    binds["dim"] = meta["dimension_default"]
    meds = _medidas(m)
    sel = [
        f"SUM(base) FILTER (WHERE dia >= {ini_act}) AS base_act",
        f"SUM(base) FILTER (WHERE dia >= {ini_prev} AND dia < {ini_act}) AS base_prev",
    ]
    for c in meds:
        sel.append(f"SUM({c}) FILTER (WHERE dia >= {ini_act}) AS {c}_act")
        sel.append(f"SUM({c}) FILTER (WHERE dia >= {ini_prev} AND dia < {ini_act}) AS {c}_prev")
    sql = (f"SELECT {', '.join(sel)} FROM {meta['tabla']} "
           f"WHERE cliente_id IN ({idsph}) AND dimension = %(dim)s AND dia >= {ini_prev}")
    df = run_df(sql, binds)
    r = df.iloc[0] if not df.empty else None

    def _val(suf):
        if r is None:
            return 0.0, 0
        base = int(r.get(f"base_{suf}") or 0)
        if m["tipo"] == "ratio":
            num = float(r.get(f"{m['num']}_{suf}") or 0)
            return ((num / base) if base else 0.0), base
        if m["tipo"] == "sum":
            return float(r.get(f"{m['col']}_{suf}") or 0), base
        if m["tipo"] == "avg":
            num = float(r.get(f"{m['num']}_{suf}") or 0)
            den = float(r.get(f"{m['den']}_{suf}") or 0)
            return ((num / den) if den else 0.0), base
        return float(base), base  # count

    val, base = _val("act")
    valp, basep = _val("prev")
    var = ((val - valp) / valp) if (basep > 0 and valp) else None
    return {"valor": val, "base": base, "valor_prev": valp, "base_prev": basep,
            "var": var, "metrica": key, "m": m}


def serie_tiempo(dom, ids, ventana, metrica=None):
    """Serie temporal de la métrica. Por día si el rango es corto, por semana si es largo."""
    meta = DOMINIOS[dom]
    key, m = _metrica(dom, metrica)
    ini_act, _ = _RANGO.get(ventana, _RANGO["6m"])
    gran = "week" if ventana in ("3m", "6m", "anio") else "day"
    binds = {}
    idsph = _ids_ph(ids, binds)
    binds["dim"] = meta["dimension_default"]
    meds = _medidas(m)
    sel = [f"date_trunc('{gran}', dia) AS t", "SUM(base) AS base"] + [f"SUM({c}) AS {c}" for c in meds]
    sql = (f"SELECT {', '.join(sel)} FROM {meta['tabla']} "
           f"WHERE cliente_id IN ({idsph}) AND dimension = %(dim)s AND dia >= {ini_act} "
           f"GROUP BY t ORDER BY t")
    df = run_df(sql, binds)
    if df.empty:
        return df
    df["VALOR"] = df.apply(lambda row: _valor(m, row, int(row["base"] or 0)), axis=1)
    return df[["t", "VALOR", "base"]].rename(columns={"t": "FECHA", "base": "BASE"})


def por_cliente(dom, marcas, ids, ventana, metrica=None):
    """Métrica por CLIENTE (Unilever, Henkel, ...), agrupando por cliente_id -> nombre."""
    meta = DOMINIOS[dom]
    key, m = _metrica(dom, metrica)
    ini_act, _ = _RANGO.get(ventana, _RANGO["6m"])
    binds = {}
    idsph = _ids_ph(ids, binds)
    binds["dim"] = meta["dimension_default"]
    meds = _medidas(m)
    sel = ["cliente_id", "SUM(base) AS base"] + [f"SUM({c}) AS {c}" for c in meds]
    sql = (f"SELECT {', '.join(sel)} FROM {meta['tabla']} "
           f"WHERE cliente_id IN ({idsph}) AND dimension = %(dim)s AND dia >= {ini_act} "
           f"GROUP BY cliente_id")
    df = run_df(sql, binds)
    if df.empty:
        return df
    id2name = {int(cid): name for name, lst in marcas.items() for cid in lst}
    df["CLIENTE"] = df["cliente_id"].apply(lambda x: id2name.get(int(x), "(otro)"))
    agg = {"base": "sum"}
    for c in meds:
        agg[c] = "sum"
    g = df.groupby("CLIENTE", as_index=False).agg(agg)
    g["VALOR"] = g.apply(lambda row: _valor(m, row, int(row["base"] or 0)), axis=1)
    g = g.dropna(subset=["VALOR"]).sort_values("VALOR", ascending=False).reset_index(drop=True)
    return g.rename(columns={"base": "BASE"})[["CLIENTE", "VALOR", "BASE"]]


# Métricas rápidas para los chips/preselector (sin IA): etiqueta -> (dominio, metrica)
PRESET_METRICAS = {
    "Ventas": ("ventas", "venta_total"),
    "Cobertura": ("cobertura", "pct_cobertura"),
    "Agotados": ("agotados", "pct_agotado"),
    "Precios": ("precios", "precio_promedio"),
    "Actividades": ("actividades", "num_actividades"),
}
