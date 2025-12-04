import io
import os
import re
import pandas as pd
import streamlit as st
from reportlab.pdfgen import canvas
from pypdf import PdfReader, PdfWriter

# Busca automáticamente la plantilla en estas rutas
ASSETS_CANDIDATES = [
    os.path.join("assets", "Certificado Congreso Gobernación.pdf"),
    os.path.join("assets", "certificado_base.pdf"),
    os.path.join("assets", "certificado_template.pdf"),
]

def _find_base_pdf() -> str | None:
    for p in ASSETS_CANDIDATES:
        if os.path.exists(p):
            return p
    return None

def _norm_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza nombres de columnas para que el usuario pueda subir
    casi cualquier Excel con 'documento', 'nombre' y 'porcentaje'."""
    mapping = {
        "document": ["documento","doc","cedula","cédula","id","identificacion","identificación","numero","número"],
        "names": ["nombre completo","nombres","nombre","name"],
        "percent": ["asistencia","porcentaje","percent","%","pct"],
    }
    cols = {c: str(c).strip().lower() for c in df.columns}
    rename = {}
    for target, keys in mapping.items():
        for c, lc in cols.items():
            if lc in keys:
                rename[c] = target
                break
    df = df.rename(columns=rename)
    # columnas obligatorias
    for need in ("document","names","percent"):
        if need not in df.columns:
            df[need] = None

    # limpieza
    df["document"] = df["document"].astype(str).str.replace(r"[^0-9]", "", regex=True)
    df["names"] = (
        df["names"]
        .astype(str)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
        .str.upper()
    )
    def _pct(x):
        if pd.isna(x): return 0.0
        s = str(x).replace("%","").replace(",",".").strip()
        try:
            return float(s)
        except:
            return 0.0
    df["percent"] = df["percent"].apply(_pct)
    return df[["document","names","percent"]]

def _make_overlay(name: str, doc: str, w: float, h: float) -> bytes:
    """Dibuja el nombre y documento encima de la plantilla (coordenadas aproximadas).
    Ajusta los multiplicadores según tu diseño final."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(w, h))
    # Posiciones relativas (ajusta si hace falta)
    name_y = h * 0.58
    doc_y  = h * 0.50
    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(w/2.0, name_y, name)
    c.setFont("Helvetica", 18)
    c.drawCentredString(w/2.0, doc_y, f"C.C. {doc}")
    c.save()
    buf.seek(0)
    return buf.read()

def _render_certificate(name: str, doc: str, base_pdf: str) -> bytes:
    reader = PdfReader(base_pdf)
    page = reader.pages[0]
    w = float(page.mediabox.width)
    h = float(page.mediabox.height)
    overlay_bytes = _make_overlay(name, doc, w, h)
    overlay_reader = PdfReader(io.BytesIO(overlay_bytes))

    # Mezcla
    base = reader.pages[0]
    base.merge_page(overlay_reader.pages[0])

    out = PdfWriter()
    out.add_page(base)
    out_buf = io.BytesIO()
    out.write(out_buf)
    out_buf.seek(0)
    return out_buf.read()

def page():
    st.header("Certificados")
    st.caption("Sube el Excel de asistencia. Solo descargan certificado quienes tengan **75%** o más.")

    base_pdf = _find_base_pdf()
    if not base_pdf:
        st.error("No se encontró la plantilla PDF. Sube tu archivo a **assets/Certificado Congreso Gobernación.pdf**.")
        return

    up = st.file_uploader("Excel con columnas (Documento / Nombre completo / ASISTENCIA)", type=["xlsx","xls"])
    if not up:
        st.info("Primero sube el Excel de asistencia.")
        return

    try:
        df = pd.read_excel(up)
        df = _norm_cols(df)
    except Exception as e:
        st.error(f"No se pudo leer el Excel: {e}")
        return

    with st.expander("Ver muestra del archivo cargado"):
        st.dataframe(df.head(20))

    doc_in = st.text_input("Documento (solo números)")
    if st.button("Validar y generar"):
        num = re.sub(r"[^0-9]","", doc_in or "")
        if not num:
            st.warning("Ingresa un documento válido.")
            return

        row = df[df["document"] == num]
        if row.empty:
            st.error("El documento no aparece en la base de datos. Si crees que es un error, escribe al correo desde el cual recibiste el enlace.")
            return

        name = row.iloc[0]["names"]
        pct  = float(row.iloc[0]["percent"])
        if pct < 75.0:
            st.error(f"El certificado no es posible generarlo. Su porcentaje de asistencia es de {pct:.0f}% y el mínimo requerido es 75%. "
                     "Para cualquier inquietud comunícate al correo remitente del enlace.")
            return

        pdf_bytes = _render_certificate(name, num, base_pdf)
        st.success(f"Certificado listo para {name} ({num}).")
        st.download_button("Descargar certificado (PDF)",
                           data=pdf_bytes,
                           file_name=f"certificado_{num}.pdf",
                           mime="application/pdf")

    st.info("Este módulo es público; no requiere inicio de sesión.")
