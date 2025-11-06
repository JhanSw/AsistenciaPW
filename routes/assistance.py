import streamlit as st
from db import get_person_by_document, add_person, add_assistance

def render():
    st.subheader("Confirmación de Asistencia")
    doc = st.text_input("Documento de Identidad", key="doc_buscar")

    c1, c2 = st.columns([1,1])
    with c1:
        if st.button("Buscar", use_container_width=True):
            if not doc:
                st.warning("Ingresa un documento.")
                st.stop()
            person = get_person_by_document(doc)
            st.session_state['last_person'] = person
            st.session_state['last_doc'] = doc
    with c2:
        if st.button("Limpiar", use_container_width=True):
            st.session_state.pop('last_person', None)
            st.session_state.pop('last_doc', None)
            try:
                st.rerun()
            except Exception:
                st.experimental_rerun()

    person = st.session_state.get('last_person')
    last_doc = st.session_state.get('last_doc', doc)

    if person:
        st.success("Registro encontrado")
        st.write(f"**Departamento/Distrito:** {person.get('department','')}")
        st.write(f"**Nombres:** {person.get('names','')}")
        st.write(f"**Entidad:** {person.get('entity','')}")
        if st.button("Confirmar asistencia ✅"):
            add_assistance(person['id'])
            st.success("Asistencia Confirmada")
    elif last_doc:
        st.info("No existe. Crear nuevo registro y confirmar:")
        with st.form("nuevo_reg"):
            department = st.text_input("Departamento/Distrito")
            municipality = st.text_input("Municipio")
            names = st.text_input("Nombres Completos")
            phone = st.text_input("Teléfono")
            email = st.text_input("Correo electrónico")
            position = st.text_input("Cargo")
            entity = st.text_input("Entidad")
            submitted = st.form_submit_button("Guardar y Confirmar")
            if submitted:
                if not names:
                    st.warning("Los Nombres son obligatorios")
                else:
                    pid = add_person("", department, municipality, last_doc, names, phone, email, position, entity)
                    add_assistance(pid)
                    st.success("Creado y asistencia confirmada")
