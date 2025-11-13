import streamlit as st
import pandas as pd
from db import upsert_people_bulk

TARGET = ["region","department","municipality","document","names","phone","email","position","entity"]

def _norm_text(x):
    if pd.isna(x): return ""
    x = str(x).strip().replace("\u00a0"," ")
    return x

def _norm_document(x):
    x = _norm_text(x)
    return x.replace(".","").replace(" ","")

def _valid_email(x):
    if not x: return True
    return "@" in x and "." in x.split("@")[-1]

def guess(col):
    key = col.strip().lower()
    if any(k in key for k in ["document","cedula","dni","cc","identidad"]): return "document"
    if any(k in key for k in ["nombre","apell"]): return "names"
    if any(k in key for k in ["telefono","celular","whatsapp","movil"]): return "phone"
    if any(k in key for k in ["correo","email","e-mail"]): return "email"
    if any(k in key for k in ["cargo","rol","puesto"]): return "position"
    if any(k in key for k in ["entidad","empresa","institucion","organizacion"]): return "entity"
    if any(k in key for k in ["municipio","ciudad","localidad"]): return "municipality"
    if any(k in key for k in ["departamento","distrito","provincia","estado"]): return "department"
    if "region" in key: return "region"
    return ""

def page():
    if not st.session_state.get("is_admin"):
        st.error("Solo administradores.")
        return

    st.title("Importar personas")
    up = st.file_uploader("Archivo Excel (.xlsx)", type=["xlsx"])
    if not up:
        st.info("Sube un archivo para continuar.")
        return

    xls = pd.ExcelFile(up)
    sheet = st.selectbox("Hoja", xls.sheet_names, index=0)
    df = pd.read_excel(up, sheet_name=sheet)

    st.subheader("Mapeo de columnas")
    map_dest = {}
    for c in df.columns:
        opts = [""] + TARGET
        gi = opts.index(guess(c)) if guess(c) in opts else 0
        map_dest[c] = st.selectbox(f"Destino para: **{c}**", options=opts, index=gi, key=f"map_{c}")

    tmp = {}
    for dest in TARGET:
        cols = [src for src, d in map_dest.items() if d == dest]
        if not cols:
            tmp[dest] = ""
        else:
            tmp[dest] = df[cols].astype(str).apply(lambda r: " ".join([x for x in r if str(x).strip() and str(x)!='nan']).strip(), axis=1)

    people = pd.DataFrame(tmp)
    people["document"] = people["document"].apply(_norm_document)
    for col in ["region","department","municipality","names","phone","email","position","entity"]:
        people[col] = people[col].apply(_norm_text)

    errors = []
    if people.empty:
        st.error("No hay filas para procesar.")
        return

    missing_doc = people["document"].eq("") | people["document"].isna()
    missing_names = people["names"].eq("") | people["names"].isna()
    if missing_doc.any():
        errors.append(f"{missing_doc.sum()} fila(s) sin DOCUMENTO.")
    if missing_names.any():
        errors.append(f"{missing_names.sum()} fila(s) sin NOMBRES.")

    bad_email = ~people["email"].apply(_valid_email)
    if bad_email.any():
        errors.append(f"{bad_email.sum()} email(s) con formato inválido.")

    dup_infile = people["document"].duplicated(keep="first")
    if int(dup_infile.sum()) > 0:
        errors.append(f"{int(dup_infile.sum())} duplicado(s) de DOCUMENTO en el archivo; se conservará la primera aparición.")

    st.subheader("Previsualización (transformado → people)")
    st.dataframe(people.head(50))

    if errors:
        st.warning("Validaciones:")
        for e in errors:
            st.write(f"- {e}")

    can_import = not missing_doc.any() and not missing_names.any()
    if st.button("Importar a la base de datos", disabled=not can_import):
        people = people[~dup_infile].copy()
        rows = list(people[TARGET].itertuples(index=False, name=None))
        try:
            count = upsert_people_bulk(rows)
            st.success(f"Importación completada. Registros procesados: {len(rows)} (upsert={count}).")
        except Exception as ex:
            st.error(f"Error durante la importación: {ex}")
