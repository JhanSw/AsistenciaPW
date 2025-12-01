
import io
import re
import pandas as pd
import streamlit as st
from reportlab.pdfgen import canvas
from pypdf import PdfReader, PdfWriter
from pathlib import Path

TEMPLATE_PATH = Path(__file__).resolve().parents[1] / "assets" / "certificado_template.pdf"

def _clean_doc(x:str)->str:
    if x is None:
        return ""
    return re.sub(r"\D+", "", str(x)).lstrip("0")

def _find_cols(df: pd.DataFrame):
    cols = list(df.columns)
    doc_col = next((c for c in cols if re.search(r"(doc|c[eÉé]d)", c, re.I)), None)
    pct_col = next((c for c in cols if re.search(r"(porc|%|asist)", c, re.I)), None)
    name_col = next((c for c in cols if re.search(r"(nombre|name)", c, re.I)), None)
    return doc_col, pct_col, name_col

def _make_overlay(name:str, doc:str, w:float, h:float)->bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(w, h))
    c.setFillColorRGB(1,1,1)
    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(w/2, h*0.60, name)
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(w/2, h*0.54, doc)
    c.showPage(); c.save()
    return buf.getvalue()

def _compose_pdf(name:str, doc:str)->bytes:
    reader = PdfReader(str(TEMPLATE_PATH))
    page = reader.pages[0]
    w = float(page.mediabox.width)
    h = float(page.mediabox.height)
    overlay_reader = PdfReader(io.BytesIO(_make_overlay(name, doc, w, h)))
    page.merge_page(overlay_reader.pages[0])
    writer = PdfWriter()
    writer.add_page(page)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()

def page():
    st.header("Certificados de asistencia")
    st.caption("Cargue el Excel con **Documento** y **Porcentaje** de asistencia. Ingrese el documento para validar y descargar.")
    if not TEMPLATE_PATH.exists():
        st.error("No se encontró la plantilla del certificado en: %s" % TEMPLATE_PATH)
        return

    up = st.file_uploader("Excel de asistencia (XLSX)", type=["xlsx"])
    if up is None:
        st.info("Suba el Excel primero.")
        return

    try:
        df = pd.read_excel(up)
    except Exception as e:
        st.error(f"No se pudo leer el Excel: {e}")
        return

    doc_col, pct_col, name_col = _find_cols(df)
    if not doc_col or not pct_col:
        st.error("No se reconocieron las columnas de **documento** y **porcentaje**. Renombre sus columnas para incluir 'doc'/'céd' y 'porc'/'%'/'asist'.")
        st.write("Columnas detectadas:", list(df.columns))
        return

    df = df.copy()
    df[doc_col] = df[doc_col].map(_clean_doc)
    df[pct_col] = pd.to_numeric(df[pct_col], errors="coerce").fillna(0)

    st.subheader("Descarga por documento")
    doc_input = st.text_input("Documento de identidad", placeholder="Solo números")
    if not doc_input:
        return

    query_doc = _clean_doc(doc_input)
    row = df.loc[df[doc_col] == query_doc]
    if row.empty:
        st.warning("No se encontró el documento en la base de datos de asistencia. Por favor contacte al correo del mensaje que recibió.")
        return

    pct = float(row.iloc[0][pct_col])
    name = str(row.iloc[0][name_col]) if name_col else "(SIN NOMBRE)"
    name = re.sub(r"\s+", " ", name).strip().upper() or "(SIN NOMBRE)"

    if pct >= 75:
        st.success(f"Asistencia {pct:.0f}%. Puede descargar su certificado.")
        if st.button("Generar y descargar certificado"):
            pdf_bytes = _compose_pdf(name=name, doc=query_doc)
            st.download_button(
                label="Descargar certificado (PDF)",
                data=pdf_bytes,
                file_name=f"certificado_{query_doc}.pdf",
                mime="application/pdf"
            )
    else:
        st.error(f"El certificado no es posible generarlo. Su porcentaje de asistencia es de {pct:.0f}% y el mínimo requerido es 75%.\n\nPara cualquier inquietud, comuníquese al correo remitente del enlace.")
