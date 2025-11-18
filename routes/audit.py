
import streamlit as st
import pandas as pd
import io
from db import get_connection

ACTIONS = [
    "create_person",
    "confirm_attendance",
    "clear_attendance",
    "create_user",
    "update_user",
    "delete_user",
    "import_people",
]

def load_audit(filters):
    conn = get_connection()
    sql = "SELECT timestamp_utc, user_id, username, action, person_id, slot, details FROM audit_log WHERE 1=1"
    params = []
    if filters.get("action"):
        sql += " AND action = %s"; params.append(filters["action"])
    if filters.get("username"):
        sql += " AND username ILIKE %s"; params.append(f"%{filters['username']}%")
    sql += " ORDER BY timestamp_utc DESC LIMIT 2000"
    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
    return pd.DataFrame(rows, columns=cols)

def page():
    if not st.session_state.get("is_admin"):
        st.error("Solo administradores.")
        return

    st.title("Auditoría")

    c1, c2 = st.columns(2)
    with c1:
        action = st.selectbox("Acción", options=[""] + ACTIONS, index=0)
    with c2:
        username = st.text_input("Usuario (contiene)")

    df = load_audit({"action": action or None, "username": username.strip() or None})

    st.write(f"Se encontraron **{len(df)}** eventos (máx. 2000).")
    st.dataframe(df)

    if not df.empty:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="xlsxwriter") as w:
            df.to_excel(w, index=False, sheet_name="auditoria")
        st.download_button("Descargar Excel", buf.getvalue(), file_name="auditoria.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
