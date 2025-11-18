
import os
import streamlit as st

from db import (
    init_database,
    ensure_default_admin,
    ensure_audit_table,
    ensure_import_batch_tables,
)

from routes import assistance, search, create, users, import_people, audit

# ---- Inicialización segura de la base ----
def _safe_bootstrap():
    try:
        init_database()
        ensure_default_admin()
        ensure_audit_table()
        ensure_import_batch_tables()
    except Exception as e:
        st.info(f"No se pudo inicializar DB automáticamente: {e}")

_safe_bootstrap()

# ---- UI ----
st.set_page_config(page_title="Asistencia", layout="wide")

# Autenticación básica en session_state (asumimos que ya existe lógica en routes/users)
if "is_auth" not in st.session_state:
    st.session_state["is_auth"] = False

# Login mínimo (delegado a users.route si lo tienes; aquí placeholder)
if not st.session_state.get("is_auth"):
    users.login_page()
else:
    menu = st.sidebar.selectbox("Menú", ["Asistencia", "Buscar", "Nuevo", "Usuarios", "Importar", "Auditoría"])
    if menu == "Asistencia":
        assistance.page()
    elif menu == "Buscar":
        search.page()
    elif menu == "Nuevo":
        create.page()
    elif menu == "Usuarios":
        users.page()
    elif menu == "Importar":
        import_people.page()
    elif menu == "Auditoría":
        audit.page()
