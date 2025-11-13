import streamlit as st
import pandas as pd
import io
from db import search_people_with_slots, distinct_values

LABELS = {
    "id": "Número",
    "region": "Provincia",
    "department": "Departamento",
    "municipality": "Municipio",
    "document": "Documento",
    "names": "Nombre completo",
    "phone": "Celular",
    "email": "Correo electrónico",
    "position": "Cargo",
    "entity": "Entidad",
    "registro_dia1_manana": "Registro mañana día 1.",
    "registro_dia1_tarde": "Registro tarde día 1.",
    "registro_dia2_manana": "Registro mañana día 2.",
    "registro_dia2_tarde": "Registro tarde día 2.",
}

ORDER = ["id","region","department","municipality","document","names","phone","email","position","entity",
         "registro_dia1_manana","registro_dia1_tarde","registro_dia2_manana","registro_dia2_tarde"]

def page():
    st.title("Buscar")

    # Text search still allowed (by nombre/documento)
    q_text = st.text_input("Buscar por nombre o documento", value="")

    # Dropdown options from DB
    regiones = distinct_values("region")
    municipios = distinct_values("municipality")
    entidades = distinct_values("entity")

    c1, c2, c3 = st.columns(3)
    with c1:
        sel_region = st.multiselect("Provincia (region)", opciones:=regiones)
    with c2:
        sel_muni = st.multiselect("Municipio", opciones:=municipios)
    with c3:
        sel_ent = st.multiselect("Entidad", opciones:=entidades)

    # Query
    df = search_people_with_slots(
        q=q_text.strip(),
        regions=sel_region,
        municipalities=sel_muni,
        entities=sel_ent,
        limit=1000
    )

    # Reorder and relabel
    for col in ORDER:
        if col not in df.columns:
            df[col] = None
    df = df[ORDER]

    df = df.rename(columns=LABELS)

    st.write(f"Se encontraron **{len(df)}** registros.")
    st.dataframe(df)

    if not df.empty:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="personas")
        st.download_button(
            label="Descargar Excel",
            data=buffer.getvalue(),
            file_name="personas.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
