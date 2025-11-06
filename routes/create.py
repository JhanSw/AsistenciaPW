import streamlit as st
from db import add_person

def render():
    st.subheader("Nuevo registro")
    with st.form("create_person"):
        region = st.text_input("Región")
        department = st.text_input("Departamento/Distrito")
        municipality = st.text_input("Municipio")
        document = st.text_input("Documento de Identidad")
        names = st.text_input("Nombres Completos")
        phone = st.text_input("Teléfono")
        email = st.text_input("Correo electrónico")
        position = st.text_input("Cargo")
        entity = st.text_input("Entidad")
        ok = st.form_submit_button("Guardar")
        if ok:
            if not document or not names:
                st.warning("Documento y Nombres son obligatorios.")
            else:
                pid = add_person(region, department, municipality, document, names, phone, email, position, entity)
                if pid:
                    st.success("Guardado correctamente.")
                else:
                    st.warning("El documento ya existe; no se creó un nuevo registro.")
