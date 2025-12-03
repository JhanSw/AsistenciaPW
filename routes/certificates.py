# routes/certificates.py  — limpio y funcional

import io
import os
import re
from pathlib import Path

import pandas as pd
import streamlit as st
from reportlab.pdfgen import canvas

# Compatibilidad: intenta primero PyPDF2; si no está, usa pypdf
try:
    from PyPDF2 import PdfReader, PdfWriter  # PyPDF2 >= 3
except Exception:  # pragma: no cover
    from pypdf import PdfReader, PdfWriter    # pypdf

# Posibles ubicaciones de la plantilla PDF (usa la primera que exista)
ASSETS_CANDIDATES = [
    os.path.join("assets", "certificado_base.pdf"),
    os.path.join("assets", "certificado_template.pdf"),
    os.path.join("assets", "certificado.pdf"),
    "certificado_base.pdf",
    "certificado_template.pdf",
    "certificado.pdf",
]


def _find_base_pdf() -> str | None:
    """Devuelve la ruta del PDF de plantilla si existe, o None."""
    for p in ASSETS_CANDIDATES:
        if os.path.exists(p):
            return p
    return None


def _norm_cols(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza nombres de columnas para que el código trabaje siempre con:
      - document
      - names
      - percent
    Y limpia/convierte valores.
    """
    mapping = {
        "document": [
            "document", "documento", "no_documento",
            "cedula", "cédula", "id", "identificacion", "identificación"
        ],
        "names": [
            "names", "nombre", "nombres", "nombre_completo", "name"
        ],
        "percent": [
            "percent", "porcentaje", "asistencia", "pct", "%", "porc"
        ],
    }

    # mapa original -> lower
    lower_map = {c: str(c).strip().lower() for c in df.columns}
    # renombra a los estándar
    rename = {}
    for target, candidates in mapping.items():
        for original, lower in lower_map.items():
            if lower in candidates:
                rename[original] = target
                break

    df = df.rename(columns=rename).copy()

    # Asegura columnas requeridas
    for need in ("document", "names", "percent"):
        if need not in df.columns:
            df[need] = None

    # Limpieza
    df["document"] = (
        df["document"].astype(str)
        .str.replace(r"[^0-9]", "", regex=True)
        .str.strip()
    )

    df["names"] = (
        df["names"].astype(str)
        .str.upper()
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )

    def _coerce_pct(x):
        if pd.isna(x):
            return 0.0
        s = str(x).replace("%", "").replace(",", ".").strip()
        try:
            return float(s)
        except Exception:
            return 0.0

    df["percent"] = df["percent"].apply(_coerce_pct)

    # Devuelve solo las columnas estandarizadas
    return df[["document", "names", "percent"]]


def _draw_overlay(name: str, doc: str, w: float, h: float) -> bytes:
    """
    Crea un PDF (1 página) con texto en posiciones fijas.
    Ajusta coordenadas según tu plantilla.
    """
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(w, h))

    # Coordenadas aproximadas; AJÚSTALAS a tu diseño
    x_name, y_name = w * 0.33, h * 0.56
    x_doc,  y_doc  = w * 0.33, h * 0.48

    c.setFont("Helvetica-Bold", 28)
    c.drawString(x_name, y_name, name or "(SIN NOMBRE)")

    c.setFont("Helvetica", 18)
    c.drawString(x_doc, y_doc, f"CC {doc}")

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()


def _render_certificate(name: str, doc: str, base_pdf: str) -> bytes:
    """Fusiona el overlay de texto sobre la primera página de la plantilla."""
    reader = PdfReader(base_pdf)
    page = reader.pages[0]
    w = float(page.mediabox.width)
    h = float(page.mediabox.height)

    overlay_bytes = _draw_overlay(name, doc, w, h)
    overlay_reader = PdfReader(io.BytesIO(overlay_bytes))

    # Fusiona
    page.merge_page(overlay_reader.pages[0])
    writer = PdfWriter()
    writer.add_page(page)

    # (opcional) si tu plantilla tiene más páginas y quieres conservarlas:
    for i in range(1, len(reader.pages)):
        writer.add_page(reader.pages[i])

    out = io.BytesIO()
    writer.write(out)
    out.seek(0)
    return out.read()


def page():
    st.header("Certificados")

    base_pdf = _find_base_pdf()
    if not base_pdf:
        st.error(
            "No se encontró la plantilla PDF. "
            "Coloca **assets/certificado_base.pdf** (o alguno de los nombres soportados) en el proyecto."
        )
        return

    st.write("Sube el Excel de asistencia (con columnas equivalentes a: documento, nombres, percent).")
    up = st.file_uploader("Excel", type=["xlsx", "xls"])
    df = None
    if up:
        try:
            raw = pd.read_excel(up)
            df = _norm_cols(raw)
            st.success(f"Archivo cargado: {len(df)} filas")
            with st.expander("Vista previa"):
                st.dataframe(df.head(50), hide_index=True, use_container_width=True)
        except Exception as e:
            st.error(f"No fue posible leer el Excel: {e}")

    st.divider()
    st.write("Valida por documento para generar/descargar certificado:")
    doc_in = st.text_input("Documento", value="", help="Solo números")
    btn = st.button("Verificar y generar", type="primary")

    if not btn:
        return

    num = re.sub(r"[^0-9]", "", doc_in or "")
    if not num:
        st.warning("Ingresa un documento válido.")
        return

    if df is None or df.empty:
        st.warning("Primero sube el Excel de asistencias.")
        return

    row = df.loc[df["document"] == num]
    if row.empty:
        st.error(
            "El certificado no es posible generarlo: su documento no aparece en la base cargada. "
            "Si considera que es un error, escriba al correo desde el cual recibió el enlace."
        )
        return

    name = str(row.iloc[0]["names"]).strip() or "(SIN NOMBRE)"
    pct = float(row.iloc[0]["percent"])

    if pct < 75.0:
        st.warning(
            f"El certificado no es posible generarlo. Su porcentaje de asistencia es de **{pct:.0f}%** "
            "y el mínimo requerido es de **75%**. \n\n"
            "Para cualquier inquietud, comuníquese por medio del correo electrónico desde el cual recibió el enlace."
        )
        return

    # Genera PDF
    try:
        pdf_bytes = _render_certificate(name, num, base_pdf)
        st.success(f"Certificado listo para **{name}** ({num}).")
        st.download_button(
            "Descargar certificado (PDF)",
            data=pdf_bytes,
            file_name=f"certificado_{num}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    except Exception as e:
        st.error(f"Error generando el PDF: {e}")
