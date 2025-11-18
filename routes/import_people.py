
import streamlit as st
import pandas as pd
import re
from db import upsert_people_bulk, log_action

TARGET = ["region","department","municipality","document","names","phone","email","position","entity"]

def _norm_text(x):
    if pd.isna(x): return ""
    s = str(x).strip().replace("\u00a0"," ")
    s = re.sub(r"\s+", " ", s)
    return s

def _only_digits(x):
    return re.sub(r"\D", "", str(x or ""))

def _clean_email(val: str) -> str:
    s = str(val or "").upper().replace("ANONYMOUS", "").strip()
    m = re.search(r"([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})", s)
    return m.group(1) if m else ""

def guess(col):
    key = col.strip().lower()
    if any(k in key for k in ["document","cedul","dni","cc","identidad"]): return "document"
    if any(k in key for k in ["nombre","apell"]): return "names"
    if any(k in key for k in ["telefono","celular","whatsapp","móvil","movil"]): return "phone"
    if any(k in key for k in ["correo","email","e-mail"]): return "email"
    if any(k in key for k in ["cargo","rol","puesto","ocupacion","ocupación"]): return "position"
    if any(k in key for k in ["entidad","empresa","instituci","organiza"]): return "entity"
    if any(k in key for k in ["municipio","ciudad","localidad"]): return "municipality"
    if any(k in key for k in ["departamento","distrito","estado"]): return "department"
    if any(k in key for k in ["provincia","región","region"]): return "region"
    return ""

def _to_upper(s: str) -> str:
    return str(s or "").upper()

def page():
    if not st.session_state.get("is_admin"):
        st.error("Solo administradores.")
        return

    st.title("Importar personas (con normalización automática)")
    up = st.file_uploader("Archivo Excel (.xlsx) o CSV", type=["xlsx","csv"])
    if not up:
        st.info("Sube un archivo para continuar.")
        return

    # Leer archivo
    if up.name.lower().endswith(".csv"):
        df = pd.read_csv(up)
        sheet = None
    else:
        xls = pd.ExcelFile(up, engine="openpyxl")
        sheet = st.selectbox("Hoja", xls.sheet_names, index=0)
        df = pd.read_excel(up, sheet_name=sheet, engine="openpyxl")

    st.subheader("Mapeo sugerido")
    map_dest = {}
    for c in df.columns:
        opts = [""] + TARGET
        gi_guess = guess(c)
        gi = opts.index(gi_guess) if gi_guess in opts else 0
        map_dest[c] = st.selectbox(f"Destino para: **{c}**", options=opts, index=gi, key=f"map_{c}")

    # Unir columnas hacia la plantilla destino
    tmp = {}
    for dest in TARGET:
        cols = [src for src, d in map_dest.items() if d == dest]
        if not cols:
            tmp[dest] = ""
        else:
            tmp[dest] = df[cols].astype(str).apply(lambda r: " ".join([x for x in r if str(x).strip() and str(x).lower()!='nan']).strip(), axis=1)

    people = pd.DataFrame({k: (tmp[k] if not isinstance(tmp[k], str) else pd.Series([""]*len(df))) for k in TARGET})

    # Normalizaciones solicitadas
    people["document"] = people["document"].apply(_only_digits)
    people["phone"] = people["phone"].apply(_only_digits)

    for col in ["region","department","municipality","names","email","position","entity"]:
        people[col] = people[col].apply(_norm_text).apply(_to_upper)

    people["names"] = people["names"].str.replace(r"\bNAN\b", "", regex=True).str.replace(r"\s+", " ", regex=True).str.strip()
    people["email"] = people["email"].apply(_clean_email)

    # Validaciones mínimas
    errors = []
    missing_doc = people["document"].eq("") | people["document"].isna()
    missing_names = people["names"].eq("") | people["names"].isna()
    if missing_doc.any():
        errors.append(f"{int(missing_doc.sum())} fila(s) sin DOCUMENTO.")
    if missing_names.any():
        errors.append(f"{int(missing_names.sum())} fila(s) sin NOMBRES.")

    dup_infile = people["document"].duplicated(keep="first")
    if int(dup_infile.sum()) > 0:
        errors.append(f"{int(dup_infile.sum())} duplicado(s) de DOCUMENTO en el archivo; se conservará la primera aparición.")

    st.subheader("Previsualización (ya normalizado)")
    st.dataframe(people.head(50))

    if errors:
        st.warning("Validaciones:")
        for e in errors:
            st.write(f"- {e}")

    can_import = not missing_doc.any() and not missing_names.any()
    if st.button("Importar a la base de datos", disabled=not can_import):
        try:
            people = people[~dup_infile].copy()
            rows = list(people[TARGET].itertuples(index=False, name=None))
            count = upsert_people_bulk(rows)
            st.success(f"Importación completada. Registros procesados: {len(rows)} (upsert={count}).")
            curuser = st.session_state.get('user') or {}
            log_action(curuser.get('id'), curuser.get('username'), 'import_people', details={'rows': len(rows), 'sheet': sheet, 'normalized': True})
        except Exception as ex:
            st.error(f"Error durante la importación: {ex}")
