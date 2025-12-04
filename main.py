# main.py
import streamlit as st

st.set_page_config(page_title="Asistencia / Certificados", page_icon="✅", layout="wide")

# ------------------------
# Importar rutas
# ------------------------
from routes import certificates

# Intentar cargar módulos admin; si alguno falta no rompemos
try:
    from routes import assistance
except Exception:
    assistance = None

try:
    from routes import search
except Exception:
    search = None

try:
    from routes import create
except Exception:
    create = None

try:
    from routes import users
except Exception:
    users = None

try:
    from routes import import_people
except Exception:
    import_people = None

try:
    from routes import audit
except Exception:
    audit = None

# ------------------------
# Estado de sesión
# ------------------------
if "user" not in st.session_state:
    # Que tu users.login_page() deje algo como {"username": "...", "is_admin": True}
    st.session_state.user = None

def is_authenticated() -> bool:
    """Devuelve True si el módulo de login dejó un usuario válido en sesión."""
    u = st.session_state.get("user")
    return bool(u)

# ------------------------
# Sidebar: menú según login
# ------------------------
if is_authenticated():
    menu = st.sidebar.selectbox(
        "Menú",
        ["Certificados", "Asistencia", "Buscar", "Nuevo", "Usuarios", "Importar", "Auditoría"],
        index=0
    )
else:
    menu = st.sidebar.selectbox("Menú", ["Certificados"], index=0)

# ------------------------
# Expander de ingreso admin (opcional)
# ------------------------
with st.sidebar.expander("Ingreso administrador (opcional)", expanded=False):
    if users and hasattr(users, "login_page"):
        # Debe encargarse de establecer st.session_state.user si el login es correcto
        users.login_page()
    else:
        st.caption("El componente de ingreso no está disponible en esta build.")

# ------------------------
# Router
# ------------------------
def _safe_page(mod, title=None):
    """Llama mod.page() de forma segura si existe."""
    if not mod:
        st.error("Este módulo no está disponible en el despliegue.")
        return
    if title:
        st.title(title)
    if hasattr(mod, "page") and callable(getattr(mod, "page")):
        try:
            mod.page()
        except Exception as e:
            st.error(f"Ocurrió un error al cargar la página: {e}")
    else:
        st.error("El módulo no define una función page().")

# ---- Certificados (público / admin) ----
if menu == "Certificados":
    # Si hay sesión y existe admin_page() -> panel de configuración/descarga admin
    if is_authenticated() and hasattr(certificates, "admin_page"):
        try:
            certificates.admin_page()
        except Exception as e:
            st.error(f"Error en certificados (admin): {e}")
    else:
        # Público: sólo documento y descarga (no requiere login)
        if hasattr(certificates, "public_page"):
            try:
                certificates.public_page()
            except Exception as e:
                st.error(f"Error en certificados (público): {e}")
        else:
            # Compatibilidad con implementaciones antiguas que solo tenían certificates.page()
            _safe_page(certificates)

# ---- Resto del menú: requiere login ----
if is_authenticated():
    if menu == "Asistencia":
        _safe_page(assistance, title="Asistencia")
    elif menu == "Buscar":
        _safe_page(search, title="Buscar")
    elif menu == "Nuevo":
        _safe_page(create, title="Nuevo")
    elif menu == "Usuarios":
        _safe_page(users, title="Usuarios")
    elif menu == "Importar":
        _safe_page(import_people, title="Importar")
    elif menu == "Auditoría":
        _safe_page(audit, title="Auditoría")

# Pie de página
st.markdown(
    "<div style='margin-top:2rem;color:#8c8c8c;font-size:0.85rem;'>"
    "© Sistema de Asistencia & Certificados</div>",
    unsafe_allow_html=True,
)
