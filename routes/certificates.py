
import io
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
=======
import os
>>>>>>> 19c2000 (fix error login)
import re
import pandas as pd
import streamlit as st
from reportlab.pdfgen import canvas
<<<<<<< HEAD
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
=======
=======
>>>>>>> dbe06bc (update changes)
import datetime as dt
import streamlit as st
from db import find_person_by_document, get_attendance_status, SLOTS
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

TEMPLATE_PATH = "assets/certificate_template.pdf"

def _compute_percentage(slot_status: dict) -> int:
    if not slot_status:
        return 0
    total = len(SLOTS)
    done = sum(1 for k in SLOTS if slot_status.get(k))
    return int(round(done * 100 / total))

def _make_overlay_pdf(width, height, full_name, document):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(width, height))

    # Texto centrado (ajusta coordenadas según tu diseño)
    name_y = height * 0.58
    doc_y = height * 0.48

    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(width/2.0, name_y, full_name)

    c.setFont("Helvetica", 16)
    c.drawCentredString(width/2.0, doc_y, f"C.C. {document}")
    c.save()
    buf.seek(0)
    return buf

def _merge_overlay(template_bytes: bytes, overlay_buf: io.BytesIO) -> bytes:
    base = PdfReader(io.BytesIO(template_bytes))
    out = PdfWriter()
    overlay_reader = PdfReader(overlay_buf)
    # asumir 1 página
    page = base.pages[0]
    page.merge_page(overlay_reader.pages[0])
    out.add_page(page)
    out_bytes = io.BytesIO()
    out.write(out_bytes)
    out_bytes.seek(0)
    return out_bytes.getvalue()

def page():
    st.title("Certificados")

    st.caption("Ingrese el documento para validar asistencia y generar su certificado (se requiere **75%** o más).")

    document = st.text_input("Documento (sin puntos ni comas)").strip()
    col1, col2 = st.columns([1,1])
    generated = None

    if col1.button("Validar y generar"):
        if not document:
            st.warning("Por favor ingrese un documento.")
        else:
            row = find_person_by_document(document)
            if not row:
                st.error("El documento no aparece en la base de datos. Si considera que es un error, escriba al correo desde el cual recibió el enlace.")
            else:
                person_id = row[0]
                names = row[5] if len(row) > 5 else ""  # names suele estar en índice 5
                # normaliza nombre
                full_name = (names or "").strip().upper()

                slots = get_attendance_status(person_id)
                pct = _compute_percentage(slots)

                if pct < 75:
                    st.error(f"No es posible generar el certificado. Su porcentaje de asistencia es **{pct}%** y el mínimo requerido es **75%**. Para cualquier inquietud, escriba al correo desde el cual recibió el enlace.")
                else:
                    # generar PDF
                    # leer plantilla
                    with open(TEMPLATE_PATH, "rb") as f:
                        template_bytes = f.read()

                    # obtener tamaño del PDF
                    reader = PdfReader(io.BytesIO(template_bytes))
                    media = reader.pages[0].mediabox
                    width = float(media.width)
                    height = float(media.height)

                    overlay = _make_overlay_pdf(width, height, full_name, document)
                    result = _merge_overlay(template_bytes, overlay)

                    st.success(f"¡Listo! Porcentaje de asistencia: **{pct}%**.")
                    st.download_button(
                        "Descargar certificado (PDF)",
                        data=result,
                        file_name=f"certificado_{document}.pdf",
                        mime="application/pdf"
                    )

    st.info("Solo los participantes con 75% o más de asistencia pueden generar su certificado.")
<<<<<<< HEAD
>>>>>>> 905d61f (update main)
=======
>>>>>>> dbe06bc (update changes)
=======
from reportlab.lib.pagesizes import A4, landscape
from PyPDF2 import PdfReader, PdfWriter

ASSETS_CANDIDATES = [
    os.path.join("assets", "certificado_base.pdf"),
    os.path.join("assets", "certificado.pdf"),
    "certificado_base.pdf",
]

def _find_base_pdf():
    for p in ASSETS_CANDIDATES:
        if os.path.exists(p):
            return p
    return None

def _norm_cols(df: pd.DataFrame) -> pd.DataFrame:
    mapping = {
        "document":["document","documento","no_documento","cedula","cédula","id","identificacion","identificación"],
        "names":["names","nombre","nombres","nombre_completo","name"],
        "percent":["percent","porcentaje","asistencia","pct","%","porc"],
    }
    cols = {c:str(c).strip().lower() for c in df.columns}
    rename = {}
    for target, options in mapping.items():
        for c,cl in cols.items():
            if cl in options:
                rename[c]=target
                break
    df = df.rename(columns=rename)
    # enforce presence
    for need in ("document","names","percent"):
        if need not in df.columns:
            df[need] = None
    # clean
    df["document"] = df["document"].astype(str).str.replace(r"[^0-9]", "", regex=True)
    # uppercase names
    df["names"] = df["names"].astype(str).str.upper().str.replace(r"\s+"," ", regex=True).str.strip()
    # percent numeric
    def _coerce_pct(x):
        if pd.isna(x): return 0
        s=str(x)
        s=s.replace("%","").replace(",",".")
        try:
            return float(s)
        except:
            return 0.0
    df["percent"] = df["percent"].apply(_coerce_pct)
    return df[["document","names","percent"]]

def _draw_overlay(name: str, doc: str, w: float, h: float) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(w,h))
    # posiciones aproximadas; ajustar según plantilla
    x_name, y_name = w*0.33, h*0.56
    x_doc,  y_doc  = w*0.33, h*0.48
    c.setFont("Helvetica-Bold", 28)
    c.drawString(x_name, y_name, name)
    c.setFont("Helvetica", 18)
    c.drawString(x_doc, y_doc, f"CC {doc}")
    c.save()
    buf.seek(0)
    return buf.read()

def _render_certificate(name: str, doc: str, base_pdf: str) -> bytes:
    reader = PdfReader(base_pdf)
    page = reader.pages[0]
    w=float(page.mediabox.width)
    h=float(page.mediabox.height)
    overlay_bytes=_draw_overlay(name, doc, w, h)

    # merge overlay
    overlay_reader = PdfReader(io.BytesIO(overlay_bytes))
    writer = PdfWriter()
    base = reader.pages[0]
    base.merge_page(overlay_reader.pages[0])
    writer.add_page(base)

    out = io.BytesIO()
    writer.write(out)
    out.seek(0)
    return out.read()

def page():
    st.header("Certificados")
    base_pdf=_find_base_pdf()
    if not base_pdf:
        st.error("No se encontró la plantilla PDF. Coloca **assets/certificado_base.pdf** en el proyecto.")
        return

    st.write("Sube el Excel de asistencia (con columnas: documento, nombres, percent).")
    up = st.file_uploader("Excel", type=["xlsx","xls"])
    df = None
    if up:
        try:
            df = pd.read_excel(up)
            df = _norm_cols(df)
            st.success(f"Archivo cargado: {len(df)} filas")
        except Exception as e:
            st.error(f"No fue posible leer el Excel: {e}")

    st.divider()
    st.write("Valida por documento para generar/descargar certificado:")
    doc_in = st.text_input("Documento", value="", help="Solo números")
    btn = st.button("Verificar y generar")

    if btn:
        num = re.sub(r"[^0-9]","", doc_in or "")
        if not num:
            st.warning("Ingresa un documento válido.")
            return
        if df is None or df.empty:
            st.warning("Primero sube el Excel de asistencias.")
            return
        row = df[df["document"]==num]
        if row.empty:
            st.error("Documento no encontrado. Por favor verifica el número o contacta al soporte.")
            return
        name = row.iloc[0]["names"]
        pct  = float(row.iloc[0]["percent"])
        if pct < 75.0:
            st.warning(f"El certificado no es posible generarlo, su porcentaje de asistencia es de {pct:.0f}% y el mínimo requerido es de 75%. "
                       "Para cualquier inquietud comuníquese al correo desde el cual recibió este enlace.")
            return
        pdf_bytes = _render_certificate(name, num, base_pdf)
        st.success(f"Certificado listo para {name} ({num}).")
        st.download_button("Descargar certificado (PDF)",
                           data=pdf_bytes,
                           file_name=f"certificado_{num}.pdf",
                           mime="application/pdf")
>>>>>>> 19c2000 (fix error login)
