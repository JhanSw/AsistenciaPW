import streamlit as st
from db import init_database, ensure_default_admin, get_user_by_username, verify_password
import importlib

st.set_page_config(page_title="Asistencia", page_icon="✅", layout="wide")

# Init DB and admin
init_database()
ensure_default_admin()

# ------------- Login gate -------------
if "auth" not in st.session_state:
    st.session_state.auth = {"logged": False, "user": None, "is_admin": False}

def do_login(username, password):
    u = get_user_by_username(username.strip())
    if not u or not u["is_active"]:
        return False, "Usuario no existe o está inactivo."
    if not verify_password(password, u["password_hash"]):
        return False, "Contraseña incorrecta."
    st.session_state.auth = {"logged": True, "user": u["username"], "is_admin": u["is_admin"]}
    return True, ""

def do_logout():
    st.session_state.auth = {"logged": False, "user": None, "is_admin": False}
    st.rerun()

def login_form():
    st.title("Sistema de Asistencia")
    st.subheader("Iniciar Sesión")
    with st.form("login_form", clear_on_submit=False):
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        ok = st.form_submit_button("Entrar")
        if ok:
            okk, msg = do_login(u, p)
            if not okk:
                st.error(msg)
            else:
                st.success("Bienvenido.")
                st.rerun()
    st.caption("Usuario admin por defecto: **admin** / **Admin2025!** (cámbiala luego).")

if not st.session_state.auth["logged"]:
    login_form()
    st.stop()

# ------------- App -------------
st.sidebar.write(f"👤 {st.session_state.auth['user']}")
if st.sidebar.button("Cerrar sesión"):
    do_logout()

pages = {
    "Asistencia": importlib.import_module("routes.assistance"),
    "Buscar": importlib.import_module("routes.search"),
    "Nuevo": importlib.import_module("routes.create"),
}
if st.session_state.auth["is_admin"]:
    pages["Usuarios"] = importlib.import_module("routes.users")

st.title("Sistema de Asistencia")
choice = st.sidebar.radio("Módulos", list(pages.keys()))
pages[choice].render()
