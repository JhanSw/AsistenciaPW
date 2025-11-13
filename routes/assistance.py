import streamlit as st
from db import get_active_slot, set_active_slot, mark_attendance_for_slot, find_person_by_document, create_person

def page():
    st.title("Asistencia")

    cols = st.columns([3,2])
    with cols[1]:
        if st.session_state.get("is_admin"):
            current = get_active_slot()
            labels = {
                "registro_dia1_manana": "Día 1 - Mañana",
                "registro_dia1_tarde":  "Día 1 - Tarde",
                "registro_dia2_manana": "Día 2 - Mañana",
                "registro_dia2_tarde":  "Día 2 - Tarde",
            }
            reverse = {v: k for k, v in labels.items()}
            keys = list(labels.keys())
            idx = keys.index(current) if current in keys else 0
            choice = st.selectbox("Momento activo (global)", list(labels.values()), index=idx, key="active_slot_selector")
            new_slot = reverse[choice]
            if new_slot != current:
                set_active_slot(new_slot)
                st.success(f"Momento activo cambiado a: {choice}")

    st.subheader("Confirmar asistencia por documento")
    doc = st.text_input("Documento")
    if st.button("Confirmar asistencia"):
        if not doc.strip():
            st.error("Ingrese un documento.")
            return
        doc_norm = doc.replace(".","").replace(" ","")
        row = find_person_by_document(doc_norm)
        if not row:
            st.info("No existe, crea registro mínimo para confirmar.")
            with st.form("crear_minimo"):
                department  = st.text_input("Provincia/Departamento")
                municipality= st.text_input("Municipio")
                names       = st.text_input("Nombres y Apellidos *")
                phone       = st.text_input("Teléfono")
                email       = st.text_input("Email")
                position    = st.text_input("Cargo")
                entity      = st.text_input("Entidad")
                submitted   = st.form_submit_button("Crear y Marcar Asistencia")
            if submitted:
                if not names.strip():
                    st.error("Nombres es obligatorio.")
                    return
                pid = create_person(
                    region="",
                    department=department.strip(),
                    municipality=municipality.strip(),
                    document=doc_norm,
                    names=names.strip(),
                    phone=phone.strip(),
                    email=email.strip(),
                    position=position.strip(),
                    entity=entity.strip(),
                )
                slot = get_active_slot()
                mark_attendance_for_slot(pid, slot)
                st.success(f"Creado y marcado en **{slot.replace('_',' ').title()}**")
        else:
            person_id = row[0]
            slot = get_active_slot()
            mark_attendance_for_slot(person_id, slot)
            st.success(f"Asistencia registrada en **{slot.replace('_',' ').title()}** para documento {doc_norm}.")
