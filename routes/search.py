
import streamlit as st
import pandas as pd
import io
from db import (
    search_people_with_slots, distinct_values,
    get_active_slot, mark_attendance_for_slot, clear_attendance_slot, log_action,
    delete_people_by_ids
)

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

ORDER = [
    "id","region","department","municipality","document","names","phone","email","position","entity",
    "registro_dia1_manana","registro_dia1_tarde","registro_dia2_manana","registro_dia2_tarde"
]

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

    # === Selección con checkboxes + acciones en lote ===
    st.session_state.setdefault("selected_people_ids", set())

    slot = get_active_slot()
    cols_actions = st.columns([1.2,2.4,2.8,2.4,2.2])
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
        # NUEVO: borrar personas completas (solo admin)
        if st.button("🧹 Eliminar personas seleccionadas (definitivo)", disabled=not st.session_state.get("is_admin", False)):
            if not st.session_state.get("is_admin", False):
                st.error("Solo administradores.")
            else:
                ids = list(st.session_state["selected_people_ids"])
                if not ids:
                    st.warning("No hay personas seleccionadas.")
                else:
                    deleted = delete_people_by_ids(ids)
                    st.success(f"Eliminadas {deleted} persona(s) del sistema.")
                    curuser = st.session_state.get('user') or {}
                    log_action(curuser.get('id'), curuser.get('username'), 'delete_people_bulk', details={'count': deleted, 'ids': ids[:50]})
                    st.session_state["selected_people_ids"] = set()
                    st.rerun()
    with cols_actions[4]:
        st.caption(f"Momento activo: **{slot.replace('_',' ').title()}**")

    # Mostrar tabla
    st.dataframe(df)

    # Zona de selección granular
    st.markdown("#### Seleccionar personas")
    ids_series = df.get("Número", pd.Series(dtype=int))
    docs_series = df.get("Documento", pd.Series(dtype=str))
    names_series = df.get("Nombre completo", pd.Series(dtype=str))

    current_ids = set(pd.to_numeric(ids_series, errors="coerce").dropna().astype(int).tolist())

    # Si marcan 'Todos', setea estados y recarga para que los checkboxes usen session_state
    if select_all:
        for pid in current_ids:
            st.session_state[f"selpid_{pid}"] = True
        st.session_state["_was_all"] = True
        st.rerun()
    else:
        if st.session_state.get("_was_all", False):
            # Si quieres desmarcar todo al quitar 'Todos', descomenta:
            # for pid in current_ids:
            #     st.session_state[f"selpid_{pid}"] = False
            st.session_state["_was_all"] = False

    # Reconstruir selección según estados reales de checkboxes
    selected = set()
    max_rows = 500
    rows_to_show = min(len(ids_series), max_rows)
    if len(ids_series) > max_rows:
        st.info(f"Mostrando {max_rows} primeras filas para selección (de {len(ids_series)}). Filtra más para ver menos.")

    for i in range(rows_to_show):
        try:
            pid = int(ids_series.iloc[i])
        except Exception:
            continue
        doc = str(docs_series.iloc[i]) if i < len(docs_series) else ""
        nm = str(names_series.iloc[i]) if i < len(names_series) else ""
        key = f"selpid_{pid}"
        st.session_state.setdefault(key, False)
        cols = st.columns([0.6,2.6,2.6])
        with cols[0]:
            cb = st.checkbox("", key=key)  # sin value=
        cols[1].markdown(f"**{nm}**")
        cols[2].markdown(f"`{doc}`")
        if st.session_state.get(key, False):
            selected.add(pid)

    st.session_state["selected_people_ids"] = selected
    st.caption(f"Seleccionados: **{len(selected)}**")

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
