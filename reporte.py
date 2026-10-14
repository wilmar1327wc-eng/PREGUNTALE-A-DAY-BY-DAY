# -*- coding: utf-8 -*-
"""
reporte.py — Arma el informe ejecutivo en PDF (una página, imprimible) del
resultado de una consulta de "Pregúntale a Day by Day".

Identidad job&talent: encabezado azul profundo + acentos teal. Fondo claro para
impresión/compartir. No tiene dependencias de la app: recibe todo ya calculado.
"""

import io
import base64

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.lib.enums import TA_RIGHT
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
                                Spacer, Table, TableStyle, Image)
from reportlab.graphics.shapes import Drawing, Rect

# ---- paleta (clara, para informe) ----
NAVY = colors.HexColor("#0E2A52")
NAVY2 = colors.HexColor("#0A2143")
TEAL = colors.HexColor("#07B6A6")
TEAL_D = colors.HexColor("#059B8E")
INK = colors.HexColor("#15233B")
MUTED = colors.HexColor("#5C6E88")
TINT = colors.HexColor("#E9F7F5")   # panel KPI
TRACK = colors.HexColor("#E6ECF3")  # fondo de barra
LINE = colors.HexColor("#D9E1EC")
ZEBRA = colors.HexColor("#F5F8FB")

W, H = LETTER
ML = MR = 1.9 * cm
BAND = 2.35 * cm          # alto del encabezado
TOPM = BAND + 0.9 * cm    # margen superior del cuerpo


def _raw(datauri):
    """data:image/...;base64,... -> bytes (o None)."""
    try:
        if not datauri or "base64," not in datauri:
            return None
        return base64.b64decode(datauri.split("base64,", 1)[1])
    except Exception:
        return None


def _fit(img, max_w, max_h):
    """Escala manteniendo proporción dentro de (max_w, max_h)."""
    iw, ih = img.getSize()
    r = min(max_w / iw, max_h / ih)
    return iw * r, ih * r


def _barra(frac, w=7.0 * cm, h=0.42 * cm):
    frac = max(0.0, min(1.0, float(frac)))
    d = Drawing(w, h)
    d.add(Rect(0, 0, w, h, rx=3, ry=3, fillColor=TRACK, strokeColor=None))
    d.add(Rect(0, 0, max(0.12 * cm, w * frac), h, rx=3, ry=3, fillColor=TEAL, strokeColor=None))
    return d


def construir_pdf(*, indicador, cliente, periodo, metrica_label, valor_txt, base_txt,
                  filas, insights, jt_datauri=None, cli_datauri=None, fecha_txt=""):
    """
    filas: lista de (dimension:str, valor_txt:str, frac:float, base_txt:str)
    insights: lista de str
    """
    buf = io.BytesIO()
    jt_bytes = _raw(jt_datauri)
    cli_bytes = _raw(cli_datauri)
    jt = ImageReader(io.BytesIO(jt_bytes)) if jt_bytes else None
    cli = ImageReader(io.BytesIO(cli_bytes)) if cli_bytes else None

    def _deco(canvas, doc):
        canvas.saveState()
        # banda del encabezado
        canvas.setFillColor(NAVY)
        canvas.rect(0, H - BAND, W, BAND, fill=1, stroke=0)
        canvas.setFillColor(TEAL)
        canvas.rect(0, H - BAND - 0.07 * cm, W, 0.07 * cm, fill=1, stroke=0)  # filete teal
        # logo job&talent
        if jt:
            lw, lh = _fit(jt, 3.2 * cm, 0.95 * cm)
            canvas.drawImage(jt, ML, H - BAND / 2 - lh / 2, lw, lh, mask="auto")
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica", 10.5)
        canvas.drawString(ML + 3.6 * cm, H - BAND / 2 - 3, "Centro de Inteligencia de Negocios")
        canvas.setFillColor(colors.HexColor("#AFE7E0"))
        canvas.setFont("Helvetica", 9)
        canvas.drawRightString(W - MR, H - BAND / 2 - 3, f"Informe generado · {fecha_txt}")
        # pie
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica", 7.5)
        canvas.drawString(ML, 1.1 * cm, "Centro de Inteligencia de Negocios de job&talent · "
                          "Datos agregados; sin información personal ni registros individuales.")
        canvas.drawRightString(W - MR, 1.1 * cm, "Pregúntale a Day by Day +IA")
        canvas.setStrokeColor(LINE)
        canvas.line(ML, 1.45 * cm, W - MR, 1.45 * cm)
        canvas.restoreState()

    doc = BaseDocTemplate(buf, pagesize=LETTER, leftMargin=ML, rightMargin=MR,
                          topMargin=TOPM, bottomMargin=1.7 * cm,
                          title=f"Informe {indicador} - {cliente}", author="job&talent CIN")
    frame = Frame(ML, 1.7 * cm, W - ML - MR, H - TOPM - 1.7 * cm, id="body")
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=_deco)])

    h1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=19, textColor=INK, leading=22)
    sub = ParagraphStyle("sub", fontName="Helvetica", fontSize=10.5, textColor=MUTED, leading=14, spaceBefore=2)
    kpibig = ParagraphStyle("kpibig", fontName="Helvetica-Bold", fontSize=33, textColor=NAVY, leading=34)
    kpictx = ParagraphStyle("kpictx", fontName="Helvetica", fontSize=9.5, textColor=MUTED, leading=12)
    sec = ParagraphStyle("sec", fontName="Helvetica-Bold", fontSize=11.5, textColor=INK, leading=14,
                         spaceBefore=8, spaceAfter=6)
    cellL = ParagraphStyle("cellL", fontName="Helvetica", fontSize=9.5, textColor=INK, leading=12)
    cellR = ParagraphStyle("cellR", fontName="Helvetica-Bold", fontSize=9.5, textColor=INK, leading=12, alignment=TA_RIGHT)
    cellM = ParagraphStyle("cellM", fontName="Helvetica", fontSize=9, textColor=MUTED, leading=12, alignment=TA_RIGHT)
    ins = ParagraphStyle("ins", fontName="Helvetica", fontSize=10, textColor=INK, leading=14)
    thL = ParagraphStyle("thL", fontName="Helvetica-Bold", fontSize=8, textColor=MUTED, leading=10)
    thR = ParagraphStyle("thR", fontName="Helvetica-Bold", fontSize=8, textColor=MUTED, leading=10, alignment=TA_RIGHT)

    story = []

    # --- Título + logo cliente ---
    titulo = Paragraph(f"Informe de {indicador}", h1)
    subt = Paragraph(f"{cliente} &nbsp;·&nbsp; {periodo}", sub)
    left = [titulo, subt]
    if cli:
        cw, ch = _fit(cli, 3.0 * cm, 1.2 * cm)
        head = Table([[left, Image(io.BytesIO(cli_bytes), cw, ch)]], colWidths=[(W - ML - MR) - cw - 0.3 * cm, cw + 0.3 * cm])
        head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                   ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                                   ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                                   ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
        story.append(head)
    else:
        story += left
    story.append(Spacer(1, 0.45 * cm))

    # --- Panel KPI ---
    kpi_inner = Table([[Paragraph(valor_txt, kpibig)],
                       [Paragraph(f"{metrica_label} de {cliente} · {periodo}", kpictx)],
                       [Paragraph(f"sobre {base_txt} registros", kpictx)]], colWidths=[W - ML - MR - 1.0 * cm])
    kpi_inner.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                                   ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
    kpi = Table([[kpi_inner]], colWidths=[W - ML - MR])
    kpi.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), TINT),
                             ("LINEBEFORE", (0, 0), (0, -1), 3, TEAL),
                             ("LEFTPADDING", (0, 0), (-1, -1), 0.55 * cm),
                             ("RIGHTPADDING", (0, 0), (-1, -1), 0.4 * cm),
                             ("TOPPADDING", (0, 0), (-1, -1), 0.4 * cm),
                             ("BOTTOMPADDING", (0, 0), (-1, -1), 0.4 * cm),
                             ("ROUNDEDCORNERS", [6, 6, 6, 6])]))
    story.append(kpi)
    story.append(Spacer(1, 0.5 * cm))

    # --- Desglose (barras) ---
    dimname = filas and "desglose" or "desglose"
    story.append(Paragraph(f"Desglose", sec))
    data = [[Paragraph("Categoría", thL), "", Paragraph(metrica_label, thR), Paragraph("Registros", thR)]]
    for dim, vtxt, frac, btxt in filas[:14]:
        data.append([Paragraph(str(dim), cellL), _barra(frac), Paragraph(vtxt, cellR), Paragraph(btxt, cellM)])
    tbl = Table(data, colWidths=[4.6 * cm, 7.3 * cm, 2.9 * cm, 2.4 * cm], repeatRows=1)
    ts = [("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
          ("LINEBELOW", (0, 0), (-1, 0), 0.6, LINE),
          ("LINEBELOW", (0, 1), (-1, -2), 0.4, colors.HexColor("#EEF2F7")),
          ("TOPPADDING", (0, 0), (-1, -1), 4.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
          ("LEFTPADDING", (0, 0), (-1, -1), 2), ("RIGHTPADDING", (0, 0), (-1, -1), 6)]
    for i in range(1, len(data)):
        if i % 2 == 0:
            ts.append(("BACKGROUND", (0, i), (-1, i), ZEBRA))
    tbl.setStyle(TableStyle(ts))
    story.append(tbl)
    story.append(Spacer(1, 0.5 * cm))

    # --- Hallazgos ---
    story.append(Paragraph("Hallazgos", sec))
    for t in insights[:6]:
        story.append(Table([[Paragraph("<font color='#07B6A6'>&#9679;</font>", ins), Paragraph(t, ins)]],
                           colWidths=[0.45 * cm, W - ML - MR - 0.45 * cm],
                           style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                             ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                                             ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)])))

    doc.build(story)
    return buf.getvalue()
