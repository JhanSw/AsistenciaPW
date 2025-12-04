# routes/certificates.py
import io
import os
import re
from typing import Optional

import pandas as pd
import streamlit as st
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.units import mm  # mm → puntos PDF

# -------------------------------------------------------------------
# Rutas y utilidades de archivo
# -------------------------------------------------------------------
ASSETS_TEMPLATE = os.path.join("assets", "certificado_base.pdf")
RUNTIME_CACHE = "/tmp/certificados_cache.parquet"  # cache del excel normalizado

def _template_exists() -> bool:
    return os.path.exists(ASSETS_TEMPLATE)

def _save_registry(df: pd.DataFrame) -> None:
    os.makedirs("/tmp", exist_ok=True)
    df.to_parquet(RUNTIME_CACHE, index=False)

def _load_registry() -> Optional[pd.DataFrame]:
    """
    Preferimos el cache de runtime (/tmp). Si no existe, intentamos assets/certificados.xlsx
    (opcional). Si tampoco hay, devolvemos None.
    """
    if os.path.exists(RUNTIME_CACHE):
        try:
            return pd.read_parquet(RUNTIME_CACHE)
        except Exception:
            pass
    # fallback: si dejas un excel fijo en assets
    assets_xlsx = os.path.join("assets", "certificados.xlsx")
    if os.path.exists(assets_xlsx):
        try:
            raw = pd.read_excel(assets_xlsx)
            return _normalize_registry(raw)
        except Exception:
            return None
    return None

# -------------------------------------------------------------------
# Normalización de columnas
# -------------------------------------------------------------------
def _only_digits(s: str) -> str:
    return re.sub(r"[^0-9]", "", str(s or ""))

def _parse_percent(x) -> float:
    """
    Acepta formatos como:
      - 75
      - "75 %"
      - "ASISTENCIA DEL 25%"
      - "25,5"
      - "25.5%"
    Devuelve float; si no hay números, 0.0
    """
    if pd.isna(x):
        return 0.0
    s = str(x)
    found = re.findall(r"\d+(?:[.,]\d+)?", s)  # toma números con coma o punto
    if not found:
        return 0.0
    val = found[-1].replace(",", ".")
    try:
        return float(val)
    except ValueError:
        return 0.0

def _normalize_registry(df: pd.DataFrame) -> pd.DataFrame:
    """
    Mapea columnas flexibles del excel a: document, names, percent
    """
    mapping = {
        "document": [
            "documento", "doc", "id", "identificacion", "identificación",
            "cedula", "cédula", "no_documento", "document"
        ],
        "names": [
            "nombre", "nombres", "nombre completo", "nombre_completo",
            "name", "names"
        ],
        "percent": [
            "porcentaje", "asistencia", "pct", "%", "porc",
            "asistencia (%)", "asist", "asistencia del"
        ],
    }

    cols_norm = {c: str(c).strip().lower() for c in df.columns}
    rename = {}

    for target, candidates in mapping.items():
        for orig, norm in cols_norm.items():
            if norm in candidates or any(key in norm for key in candidates):
                rename[orig] = target
                break

    df = df.rename(columns=rename).copy()

    # columnas faltantes
    for need in ("document", "names", "percent"):
        if need not in df.columns:
            df[need] = None

    # limpieza
    df["document"] = df["document"].map(_only_digits)
    df["names"] = (
        df["names"]
        .astype(str)
        .str.upper()
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )
    df["percent"] = df["percent"].apply(_parse_percent)

    return df[["document", "names", "percent"]]

# -------------------------------------------------------------------
# Composición del PDF (overlay + merge)
# -------------------------------------------------------------------

# Posiciones y límites relativos (ajustados al arte)
NAME_Y = 0.685      # altura del nombre (proporción de h)
DOC_Y  = 0.600      # altura del documento (proporción de h)
NAME_MAX_W = 0.80   # ancho máx. utilizable para el nombre (proporción de w)
DOC_MAX_W  = 0.80   # ancho máx. para documento (proporción de w)

# Desplazamiento horizontal del documento en milímetros (solo X)
DOC_X_SHIFT_MM = 10.0   # + derecha / - izquierda
DOC_X_SHIFT_PT = DOC_X_SHIFT_MM * mm

def _fit_text(text: str, font: str, base_size: int, max_w_px: float) -> int:
    """
    Reduce el tamaño hasta que quepa en max_w_px (en puntos PDF).
    """
    size = base_size
    w = stringWidth(text, font, size)
    while w > max_w_px and size > 10:  # evita que sea ilegible
        size -= 1
        w = stringWidth(text, font, size)
    return size

def _overlay_bytes(name: str, doc: str, w: float, h: float) -> bytes:
    """
    Dibuja nombre y documento en BLANCO y NEGRITA.
    - Nombre centrado.
    - Documento centrado + desplazamiento en X (mm).
    """
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(w, h))

    # Color BLANCO
    c.setFillColorRGB(1, 1, 1)

    # --- NOMBRE ---
    name_font = "Helvetica-Bold"
    name_size = _fit_text(
        text=name,
        font=name_font,
        base_size=40,             # ajusta si lo quieres más pequeño/grande
        max_w_px=w * NAME_MAX_W,
    )
    c.setFont(name_font, name_size)
    c.drawCentredString(w / 2.0, h * NAME_Y, name)

    # --- DOCUMENTO ---
    doc_text = doc  # sin "C.C." porque ya viene en la plantilla
    doc_font = "Helvetica-Bold"
    doc_size = _fit_text(
        text=doc_text,
        font=doc_font,
        base_size=20,
        max_w_px=w * DOC_MAX_W,
    )
    c.setFont(doc_font, doc_size)
    # Centro + desplazamiento horizontal (mm)
    c.drawCentredString((w / 2.0) + DOC_X_SHIFT_PT, h * DOC_Y, doc_text)

    c.save()
    buf.seek(0)
    return buf.read()

def _render_certificate(name: str, doc: str) -> Optional[bytes]:
    """
    Mezcla la plantilla con el overlay y devuelve el PDF final en bytes.
    """
    if not _template_exists():
        return None

    reader = PdfReader(ASSETS_TEMPLATE)
    page = reader.pages[0]
    w = float(page.mediabox.width)
    h = float(page.mediabox.height)

    overlay_reader = PdfReader(io.BytesIO(_overlay_bytes(name, doc, w, h)))
    page.merge_page(overlay_reader.pages[0])

    writer = PdfWriter()
    writer.add_page(page)
    out = io.BytesIO()
    writer.write(out)
    out.seek(0)
    return out.read()

# -------------------------------------------------------------------
# UI: PÚBLICO (sin login)
# -------------------------------------------------------------------
def public_page():
    st.header("Certificados")
    if not _template_exists():
        st.error("No se encontró la plantilla del certificado en **assets/certificado_base.pdf**.")
        return

    df = _load_registry()
    if df is None or df.empty:
        st.warning("Aún no hay datos de asistencia cargados. Inténtelo más tarde.")
        return

    doc_in = st.text_input("Documento (solo números)")
    if st.button("Consultar y generar"):
        num = _only_digits(doc_in)
        if not num:
            st.warning("Ingrese un documento válido.")
            return

        row = df.loc[df["document"] == num]
        if row.empty:
            st.error("El documento no aparece en la base de datos. Si considera que es un error, escriba al correo desde el cual recibió el enlace.")
            return

        name = str(row.iloc[0]["names"]) or "(SIN NOMBRE)"
        pct = float(row.iloc[0]["percent"] or 0)

        if pct < 75:
            st.error(
                f"No es posible generar el certificado. Su porcentaje de asistencia es **{pct:.0f}%** "
                "y el mínimo requerido es **75%**. Para cualquier inquietud, comuníquese al correo "
                "desde el cual recibió el enlace."
            )
            return

        pdf = _render_certificate(name, num)
        if not pdf:
            st.error("No fue posible generar el PDF. Verifique la plantilla.")
            return

        st.success(f"¡Listo! Porcentaje de asistencia: **{pct:.0f}%**.")
        st.download_button(
            "Descargar certificado (PDF)",
            data=pdf,
            file_name=f"certificado_{num}.pdf",
            mime="application/pdf",
        )

    st.caption("Solo podrán descargar quienes tengan 75% o más de asistencia.")

# -------------------------------------------------------------------
# UI: ADMIN (con login, visible para ti)
# -------------------------------------------------------------------
def admin_page():
    st.header("Certificados · Configuración (Admin)")

    if not _template_exists():
        st.error("No se encontró la plantilla del certificado en **assets/certificado_base.pdf**.")
    else:
        st.success("Plantilla PDF encontrada ✅")

    st.subheader("1) Cargar Excel (Documento, Nombre, Asistencia)")
    up = st.file_uploader("Excel", type=["xlsx", "xls"])
    if up:
        try:
            raw = pd.read_excel(up)
            df = _normalize_registry(raw)
            st.write(df.head())
            _save_registry(df)
            st.success(f"Registro cargado y normalizado: **{len(df)}** filas. (Guardado en runtime)")
        except Exception as e:
            st.error(f"No fue posible leer el Excel: {e}")

    st.subheader("2) Probar generación")
    df = _load_registry()
    if df is None or df.empty:
        st.info("Primero cargue el Excel.")
        return

    test_doc = st.text_input("Documento de prueba")
    if st.button("Probar"):
        num = _only_digits(test_doc)
        row = df.loc[df["document"] == num]
        if row.empty:
            st.warning("Documento no encontrado en el registro.")
            return

        name = str(row.iloc[0]["names"])
        pct = float(row.iloc[0]["percent"] or 0)
        st.write(f"Nombre: **{name}**, Asistencia: **{pct:.0f}%**")

        if pct >= 75:
            pdf = _render_certificate(name, num)
            if pdf:
                st.download_button(
                    "Descargar certificado de prueba (PDF)",
                    data=pdf,
                    file_name=f"certificado_{num}.pdf",
                    mime="application/pdf",
                )
            else:
                st.error("No se pudo componer el PDF. Revise la plantilla.")
        else:
            st.warning("Este documento no alcanza el 75% mínimo.")
