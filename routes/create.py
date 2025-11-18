
import streamlit as st
from db import upsert_people_bulk

def create_person(**kwargs):
    row = (kwargs.get("region",""), kwargs.get("department",""), kwargs.get("municipality",""),
           kwargs.get("document",""), kwargs.get("names",""), kwargs.get("phone",""),
           kwargs.get("email",""), kwargs.get("position",""), kwargs.get("entity",""))
    upsert_people_bulk([row])
    return True

def page():
    st.title("Nuevo registro")
    with st.form("nuevo_reg"):
        region = st.text_input("Región (Provincia)")
        department = st.text_input("Departamento")
        municipality = st.text_input("Municipio")
        document = st.text_input("Documento *")
        names = st.text_input("Nombre completo *")
        phone = st.text_input("Celular")
        email = st.text_input("Correo electrónico")
        position = st.text_input("Cargo")
        entity = st.text_input("Entidad")

        sb = st.form_submit_button("Crear")
    if sb:
        if not document.strip() or not names.strip():
            st.error("Documento y Nombres son obligatorios.")
            return
        ok = create_person(
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
        if ok:
            st.success("Creado.")
