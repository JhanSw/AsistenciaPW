
import streamlit as st
from db import ensure_default_admin, authenticate_user, authenticate_user_ci

def login_page():
    """Pantalla de ingreso (case-insensitive) con compatibilidad hacia atrás."""
    st.title("Ingreso")

    # Garantiza admin por defecto si hace falta
    try:
        ensure_default_admin()
    except Exception:
        pass

    username = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")

    if st.button("Entrar"):
        uname_norm = (username or "").strip().lower()
        pwd = (password or "").strip()

        user_obj = None

        # 1) Intento insensible a mayúsculas
        try:
            user_obj = authenticate_user_ci(uname_norm, pwd)
        except Exception:
            user_obj = None

        # 2) Fallback: authenticate_user con usuario normalizado
        if not user_obj:
            try:
                res = authenticate_user(uname_norm, pwd)
                if isinstance(res, tuple) and len(res) == 2:
                    ok, user = res
                    user_obj = user if ok else None
                else:
                    user_obj = res
            except Exception:
                user_obj = None

        # 3) Fallback: authenticate_user con nombre tal cual
        if not user_obj and username:
            try:
                res = authenticate_user((username or "").strip(), pwd)
                if isinstance(res, tuple) and len(res) == 2:
                    ok, user = res
                    user_obj = user if ok else None
                else:
                    user_obj = res
            except Exception:
                user_obj = None

        if user_obj and user_obj.get("is_active", True):
            st.session_state["is_auth"] = True
            st.session_state["user"] = {
                "id": user_obj.get("id"),
                "username": user_obj.get("username") or uname_norm,
                "is_admin": bool(user_obj.get("is_admin", False)),
            }
            st.session_state["is_admin"] = bool(user_obj.get("is_admin", False))
            st.rerun()
        else:
            st.error("Usuario/contraseña inválidos o inactivo.")

# ---- A continuación permanece el resto de tu módulo (CRUD de usuarios, etc.) ----
