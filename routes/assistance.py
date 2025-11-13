import streamlit as st
from db import get_active_slot, set_active_slot, mark_attendance_for_slot, find_person_by_document, create_person, get_attendance_status, clear_attendance_slot, log_action

def _labels(person_row):
    # row: id, region, department, municipality, document, names, phone, email, position, entity
    keys = ["id","region","department","municipality","document","names","phone","email","position","entity"]
    return dict(zip(keys, person_row))

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

    st.subheader("Buscar y confirmar por documento")

    c1, c2 = st.columns([2,1])
    with c1:
        doc = st.text_input("Documento", key="doc_input")
    with c2:
        do_search = st.button("Buscar", use_container_width=True)

    # Estado para detalle encontrado
    if "found_person" not in st.session_state:
        st.session_state["found_person"] = None

    if do_search:
        if not doc.strip():
            st.error("Ingrese un documento para buscar.")
        else:
            doc_norm = doc.replace(".","").replace(" ","")
            row = find_person_by_document(doc_norm)
            if row:
                st.session_state["found_person"] = _labels(row)
            else:
                st.session_state["found_person"] = None
                st.info("No existe en base. Puedes crearlo abajo y confirmar.")

    # Si existe, mostrar detalle bonito y botón Confirmar
    if st.session_state.get("found_person"):
        p = st.session_state["found_person"]
        st.markdown("### Datos del registro")
        st.write(f"**Provincia:** {p.get('region','-')}")
        st.write(f"**Municipio:** {p.get('municipality','-')}")
        st.write(f"**Documento:** {p.get('document','-')}")
        st.write(f"**Nombre completo:** {p.get('names','-')}")
        st.write(f"**Correo electrónico:** {p.get('email','-')}")
        st.write(f"**Entidad:** {p.get('entity','-')}")
        st.write(f"**Cargo:** {p.get('position','-')}")

        if st.button("Confirmar asistencia"):
            slot = get_active_slot()
            mark_attendance_for_slot(p["id"], slot)
            st.success(f"Asistencia registrada en **{slot.replace('_',' ').title()}** para documento {p['document']}.")
            user = st.session_state.get('user') or {}
            log_action(user.get('id'), user.get('username'), 'confirm_attendance', person_id=p['id'], slot=slot)

        st.markdown("---")
        st.markdown("#### Estado de registros")
        status = get_attendance_status(p["id"])  # dict por slot -> timestamp
        pretty = {
            "registro_dia1_manana": "Registro mañana día 1.",
            "registro_dia1_tarde":  "Registro tarde día 1.",
            "registro_dia2_manana": "Registro mañana día 2.",
            "registro_dia2_tarde":  "Registro tarde día 2.",
        }
        cols = st.columns(4)
        for i, key in enumerate(["registro_dia1_manana","registro_dia1_tarde","registro_dia2_manana","registro_dia2_tarde"]):
            with cols[i]:
                st.caption(pretty[key])
                st.write(str(status.get(key)) if status.get(key) else "—")
                if st.session_state.get("is_admin") and status.get(key):
                    if st.button(f"Borrar {i+1}", key=f"del_{key}"):
                        clear_attendance_slot(p["id"], key)
                        user = st.session_state.get('user') or {}
                        log_action(user.get('id'), user.get('username'), 'clear_attendance', person_id=p['id'], slot=key)
                        st.success("Registro borrado.")
                        st.rerun()

    st.markdown("---")
    st.subheader("Crear nuevo y confirmar")
    with st.form("crear_minimo"):
        region       = st.text_input("Provincia (region)")
        department   = st.text_input("Departamento")
        municipality = st.text_input("Municipio")
        doc_new      = st.text_input("Documento *")
        names        = st.text_input("Nombre completo *")
        email        = st.text_input("Correo electrónico")
        entity       = st.text_input("Entidad")
        position     = st.text_input("Cargo")
        phone        = st.text_input("Celular")

        submitted   = st.form_submit_button("Crear y Marcar Asistencia")
    if submitted:
        if not doc_new.strip() or not names.strip():
            st.error("Documento y Nombres son obligatorios.")
        else:
            pid = create_person(
                region=region.strip(),
                department=department.strip(),
                municipality=municipality.strip(),
                document=doc_new.replace(".","").replace(" ",""),
                names=names.strip(),
                phone=phone.strip(),
                email=email.strip(),
                position=position.strip(),
                entity=entity.strip(),
            )
            slot = get_active_slot()
            mark_attendance_for_slot(pid, slot)
            st.success(f"Creado y marcado en **{slot.replace('_',' ').title()}**")
            user = st.session_state.get('user') or {}
            log_action(user.get('id'), user.get('username'), 'create_person', person_id=pid)
            log_action(user.get('id'), user.get('username'), 'confirm_attendance', person_id=pid, slot=slot)
