
import streamlit as st
import pandas as pd
import io
from db import search_people_with_slots, distinct_values, get_active_slot, mark_attendance_for_slot, clear_attendance_slot, log_action

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

    q_text = st.text_input("Buscar por nombre o documento", value="")

    regiones = distinct_values("region")
    municipios = distinct_values("municipality")
    entidades = distinct_values("entity")

    c1, c2, c3 = st.columns(3)
    with c1:
        sel_region = st.multiselect("Provincia (region)", regiones)
    with c2:
        sel_muni = st.multiselect("Municipio", municipios)
    with c3:
        sel_ent = st.multiselect("Entidad", entidades)

    df = search_people_with_slots(
        q=q_text.strip(),
        regions=sel_region,
        municipalities=sel_muni,
        entities=sel_ent,
        limit=2000
    )

    for col in ORDER:
        if col not in df.columns:
            df[col] = None
    df = df[ORDER]
    df = df.rename(columns=LABELS)

    st.write(f"Se encontraron **{len(df)}** registros.")

    # === NUEVO: selección con checkboxes + acciones en lote ===
    st.session_state.setdefault("selected_people_ids", set())

    # Barra de acciones
    slot = get_active_slot()
    cols_actions = st.columns([1,2,2,2])
    with cols_actions[0]:
        select_all = st.checkbox("Todos", key="select_all_people", value=False)
    with cols_actions[1]:
        if st.button("✅ Confirmar seleccionados (momento activo)"):
            ids = list(st.session_state["selected_people_ids"])
            if not ids:
                st.warning("No hay personas seleccionadas.")
            else:
                for pid in ids:
                    try:
                        mark_attendance_for_slot(pid, slot)
                        curuser = st.session_state.get('user') or {}
                        log_action(curuser.get('id'), curuser.get('username'), 'confirm_attendance', person_id=pid, slot=slot)
                    except Exception as e:
                        st.warning(f"PID {pid}: {e}")
                st.success(f"Confirmado para {len(ids)} persona(s) en **{slot.replace('_',' ').title()}**.")
                st.session_state["selected_people_ids"] = set()
                st.rerun()
    with cols_actions[2]:
        disable_clear = not st.session_state.get("is_admin", False)
        if st.button("🗑️ Borrar seleccionados (momento activo)", disabled=disable_clear):
            ids = list(st.session_state["selected_people_ids"])
            if not ids:
                st.warning("No hay personas seleccionadas.")
            else:
                if not st.session_state.get("is_admin", False):
                    st.error("Solo administradores.")
                else:
                    cleared = 0
                    for pid in ids:
                        try:
                            n = clear_attendance_slot(pid, slot)
                            if n: cleared += 1
                            curuser = st.session_state.get('user') or {}
                            log_action(curuser.get('id'), curuser.get('username'), 'clear_attendance', person_id=pid, slot=slot)
                        except Exception as e:
                            st.warning(f"PID {pid}: {e}")
                    st.success(f"Borrado para {cleared} persona(s) en **{slot.replace('_',' ').title()}**.")
                    st.session_state["selected_people_ids"] = set()
                    st.rerun()
    with cols_actions[3]:
        st.caption(f"Momento activo: **{slot.replace('_',' ').title()}**")

    # Listado con checkboxes por fila
    # Mostramos la tabla primero (por claridad)
    st.dataframe(df)

    # Zona de selección granular
    st.markdown("#### Seleccionar personas")
    # Construir lista (id, nombre, documento)
    ids_series = df["Número"] if "Número" in df.columns else pd.Series(dtype=int)
    docs_series = df["Documento"] if "Documento" in df.columns else pd.Series(dtype=str)
    names_series = df["Nombre completo"] if "Nombre completo" in df.columns else pd.Series(dtype=str)

    # Sincronizar selección con 'Todos'
    current_ids = set(ids_series.dropna().astype(int).tolist())
    selected = set(st.session_state["selected_people_ids"]) & current_ids
    if select_all:
        selected = set(current_ids)
    st.session_state["selected_people_ids"] = selected

    # Render checkboxes por fila (limit prudente si hay demasiados)
    max_rows = 500
    rows_to_show = min(len(ids_series), max_rows)
    if len(ids_series) > max_rows:
        st.info(f"Mostrando {max_rows} primeras filas para selección (de {len(ids_series)}). Filtra más para ver menos.")

    for i in range(rows_to_show):
        pid = int(ids_series.iloc[i])
        doc = str(docs_series.iloc[i])
        nm = str(names_series.iloc[i])
        cols = st.columns([0.6,2.6,2.6])
        with cols[0]:
            val = pid in st.session_state["selected_people_ids"]
            cb = st.checkbox("", key=f"selpid_{pid}", value=val)
            if cb:
                st.session_state["selected_people_ids"].add(pid)
            else:
                st.session_state["selected_people_ids"].discard(pid)
        cols[1].markdown(f"**{nm}**")
        cols[2].markdown(f"`{doc}`")

    # Exportar Excel (igual que antes)
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
