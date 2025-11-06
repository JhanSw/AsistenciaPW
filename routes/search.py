import streamlit as st
from db import get_all_people, update_person
import pandas as pd

def render():
    st.subheader("Buscar Personas")
    data = get_all_people()
    if not data:
        st.info("Sin registros todavía.")
        return
    df = pd.DataFrame(data)

    # Filtros
    q = st.text_input("Buscar por nombre o documento")
    muni_list = sorted(list({(x.get('municipality') or '') for x in data}))
    muni = st.selectbox("Filtrar por municipio", ["(Todos)"] + muni_list)

    df_f = df.copy()
    if q:
        df_f = df_f[df_f['names'].str.contains(q, case=False, na=False) | df_f['document'].str.contains(q, na=False)]
    if muni != "(Todos)":
        df_f = df_f[df_f['municipality'].fillna('') == muni]

    # Resultado y contador
    st.caption(f"Se encontraron **{len(df_f)}** registros.")
    if df_f.empty:
        return

    # Tabla principal
    st.dataframe(df_f[['id','document','names','department','municipality','entity','last_assistance_utc']], use_container_width=True)

    st.markdown("### Edición rápida")
    st.caption("Selecciona un ID y edita campos puntuales (ej. Municipio).")
    with st.form("edit_person"):
        col = st.columns([1,2,2,2,2])
        with col[0]:
            person_id = st.number_input("ID", min_value=1, step=1)
        with col[1]:
            new_department = st.text_input("Departamento/Distrito (opcional)")
        with col[2]:
            new_muni = st.text_input("Municipio (opcional)")
        with col[3]:
            new_entity = st.text_input("Entidad (opcional)")
        with col[4]:
            new_names = st.text_input("Nombres (opcional)")
        submitted = st.form_submit_button("Guardar cambios")
        if submitted:
            fields = {}
            if new_department: fields['department'] = new_department
            if new_muni: fields['municipality'] = new_muni
            if new_entity: fields['entity'] = new_entity
            if new_names: fields['names'] = new_names
            if not fields:
                st.warning("No hay cambios para guardar.")
            else:
                ok = update_person(int(person_id), **fields)
                if ok:
                    st.success("Actualizado correctamente.")
                    try:
                        st.rerun()
                    except Exception:
                        st.experimental_rerun()
                else:
                    st.error("No se pudo actualizar (verifica el ID).")
