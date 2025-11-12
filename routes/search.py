
import streamlit as st
import pandas as pd
import io
from db import search_people_with_slots

def page():
    st.title("Buscar")

    col1, col2, col3, col4 = st.columns([2,2,2,2])
    with col1:
        q_text = st.text_input("Nombre o Documento", value="")
    with col2:
        f_municipio = st.text_input("Municipio", value="")
    with col3:
        f_departamento = st.text_input("Provincia/Departamento", value="")
    with col4:
        f_entidad = st.text_input("Entidad", value="")

    df = search_people_with_slots(
        q=q_text.strip(),
        municipality=f_municipio.strip(),
        department=f_departamento.strip(),
        entity=f_entidad.strip(),
        limit=1000
    )

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
