
import streamlit as st
from db import init_database, ensure_default_admin, ensure_audit_table
from routes import assistance, search, create, users, import_people, audit
import bcrypt

st.set_page_config(page_title="Asistencia", layout="wide")

if "db_init" not in st.session_state:
    try:
        init_database()
        ensure_default_admin()
        ensure_audit_table(); ensure_import_batch_tables()
    except Exception as e:
        st.warning(f"No se pudo inicializar DB automáticamente: {e}")
    st.session_state["db_init"] = True

from db import get_user

def do_login(user, pwd):
    row = get_user(user)
    if not row:
        return False, None
    _id, username, password_hash, is_admin, is_active = row
    if not is_active:
        return False, None
    ok = bcrypt.checkpw(pwd.encode("utf-8"), password_hash.encode("utf-8"))
    if not ok:
        return False, None
    return True, {"id": _id, "username": username, "is_admin": is_admin}

if "user" not in st.session_state:
    st.session_state["user"] = None

if st.session_state["user"] is None:
    st.title("Ingreso")
    u = st.text_input("Usuario", value="")
    p = st.text_input("Contraseña", type="password", value="")
    if st.button("Entrar"):
        ok, info = do_login(u, p)
        if ok:
            st.session_state["user"] = info
            st.rerun()
        else:
            st.error("Usuario/contraseña inválidos o inactivo.")
    st.stop()

st.sidebar.write(f"👤 {st.session_state['user']['username']}")
if st.sidebar.button("Cerrar sesión"):
    st.session_state["user"] = None
    st.rerun()

menu = ["Asistencia", "Buscar", "Nuevo"]
if st.session_state["user"]["is_admin"]:
    menu.extend(["Usuarios", "Importar", "Auditoría"])

choice = st.sidebar.selectbox("Menú", menu)

st.session_state["is_admin"] = bool(st.session_state["user"]["is_admin"])

if choice == "Asistencia":
    assistance.page()
elif choice == "Buscar":
    search.page()
elif choice == "Nuevo":
    create.page()
elif choice == "Usuarios":
    users.page()
elif choice == "Importar":
    import_people.page()
elif choice == "Auditoría":
    audit.page()
