import streamlit as st

# Rutas
from routes import certificates

# Intenta importar módulos admin si existen (no rompe si faltan)
try:
    from routes import assistance, search, create, users, import_people, audit
except Exception:
    assistance = search = create = users = import_people = audit = None

st.set_page_config(page_title="Asistencia / Certificados", page_icon="✅", layout="wide")

menu = st.selectbox("Menú", ["Certificados","Asistencia","Buscar","Nuevo","Usuarios","Importar","Auditoría"], index=0)

# ---- Módulo público ----
if menu == "Certificados":
    certificates.page()

# ---- Área admin: en expander (opcional) ----
with st.expander("Ingreso administrador (opcional)"):
    if users and hasattr(users, "login_page"):
        users.login_page()
    else:
        st.caption("El componente de ingreso no está disponible en esta build.")

# ---- el resto solo se muestra si el usuario ya está autenticado
#     (tu lógica de sesión original puede ir aquí). Para no romper, 
#     mostramos páginas si los módulos existen.
if menu == "Asistencia" and assistance and hasattr(assistance, "page"):
    assistance.page()
elif menu == "Buscar" and search and hasattr(search, "page"):
    search.page()
elif menu == "Nuevo" and create and hasattr(create, "page"):
    create.page()
elif menu == "Usuarios" and users and hasattr(users, "page"):
    users.page()
elif menu == "Importar" and import_people and hasattr(import_people, "page"):
    import_people.page()
elif menu == "Auditoría" and audit and hasattr(audit, "page"):
    audit.page()
