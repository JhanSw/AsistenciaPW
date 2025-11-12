
import streamlit as st
from db import create_person

def page():
    st.title("Nuevo registro")
    with st.form("nuevo_reg"):
        region = st.text_input("Región")
        department = st.text_input("Provincia/Departamento")
        municipality = st.text_input("Municipio")
        document = st.text_input("Documento *")
        names = st.text_input("Nombres y Apellidos *")
        phone = st.text_input("Teléfono")
        email = st.text_input("Email")
        position = st.text_input("Cargo")
        entity = st.text_input("Entidad")

        sb = st.form_submit_button("Crear")
    if sb:
        if not document.strip() or not names.strip():
            st.error("Documento y Nombres son obligatorios.")
            return
        pid = create_person(
            region=region.strip(),
            department=department.strip(),
            municipality=municipality.strip(),
            document=document.replace(".","").replace(" ",""),
            names=names.strip(),
            phone=phone.strip(),
            email=email.strip(),
            position=position.strip(),
            entity=entity.strip(),
        )
        st.success(f"Creado ID {pid}")
