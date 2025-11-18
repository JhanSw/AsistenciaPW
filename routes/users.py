
import streamlit as st
from db import ensure_default_admin, authenticate_user_ci
# authenticate_user puede no existir en algunas versiones: import opcional
try:
    from db import authenticate_user  # type: ignore
except Exception:
    authenticate_user = None  # type: ignore

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

        # 2) Fallback: authenticate_user con usuario normalizado (si existe)
        if not user_obj and authenticate_user:
            try:
                res = authenticate_user(uname_norm, pwd)  # type: ignore
                if isinstance(res, tuple) and len(res) == 2:
                    ok, user = res
                    user_obj = user if ok else None
                else:
                    user_obj = res
            except Exception:
                user_obj = None

        # 3) Fallback: authenticate_user con nombre tal cual (si existe)
        if not user_obj and authenticate_user and username:
            try:
                res = authenticate_user((username or "").strip(), pwd)  # type: ignore
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


# =====================
#   Admin Users Page
# =====================
import bcrypt
from db import get_connection

def _fetch_users():
    conn = get_connection()
    with conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, username, is_admin, is_active, created_at FROM users ORDER BY id ASC")
            rows = cur.fetchall()
    return rows

def _set_password(username: str, new_password: str):
    pwd_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode()
    conn = get_connection()
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET password_hash=%s WHERE LOWER(username)=LOWER(%s)",
                (pwd_hash, username.strip(),),
            )

def _upsert_user(username: str, password: str, is_admin: bool, is_active: bool = True):
    username = username.strip().lower()
    pwd_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode()
    conn = get_connection()
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (username, password_hash, is_admin, is_active)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (username) DO UPDATE
                  SET password_hash = EXCLUDED.password_hash,
                      is_admin = EXCLUDED.is_admin,
                      is_active = EXCLUDED.is_active
                """,
                (username, pwd_hash, is_admin, is_active),
            )

def _update_flags(username: str, is_admin: bool, is_active: bool):
    username = username.strip().lower()
    conn = get_connection()
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET is_admin=%s, is_active=%s WHERE LOWER(username)=LOWER(%s)",
                (is_admin, is_active, username),
            )

def _delete_user(username: str):
    username = username.strip().lower()
    if username == "admin":
        raise ValueError("No se puede eliminar el usuario 'admin'.")
    conn = get_connection()
    with conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE LOWER(username)=LOWER(%s)", (username,))

def page():
    # Solo admin
    if not st.session_state.get("is_admin"):
        st.error("Necesitas permisos de administrador para ver esta sección.")
        return

    st.title("Usuarios")

    # Crear usuario
    with st.expander("➕ Crear/actualizar usuario"):
        cu1, cu2 = st.columns([2,1])
        new_user = cu1.text_input("Usuario (se guardará en minúsculas)", key="new_user_name").strip()
        new_pass = cu1.text_input("Contraseña", type="password", key="new_user_pwd")
        new_is_admin = cu2.checkbox("Admin", value=False, key="new_user_admin")
        new_is_active = cu2.checkbox("Activo", value=True, key="new_user_active")
        if st.button("Guardar usuario (crea o actualiza)", type="primary", key="btn_create_user"):
            if not new_user or not new_pass:
                st.warning("Usuario y contraseña son obligatorios.")
            else:
                try:
                    _upsert_user(new_user, new_pass, new_is_admin, new_is_active)
                    st.success(f"Usuario '{new_user.lower()}' guardado correctamente.")
                except Exception as e:
                    st.error(f"Error al guardar: {e}")

    # Lista y edición
    st.subheader("Listado")
    rows = _fetch_users()
    if rows:
        # Mostrar tabla
        import pandas as pd
        df = pd.DataFrame(rows, columns=["id", "username", "is_admin", "is_active", "created_at"])
        df_display = df.rename(columns={
            "id":"ID", "username":"Usuario", "is_admin":"Admin", "is_active":"Activo", "created_at":"Creado"
        })
        st.dataframe(df_display, use_container_width=True, hide_index=True)

        st.subheader("Editar / cambiar contraseña / eliminar")
        usernames = df["username"].tolist()
        sel = st.selectbox("Selecciona usuario", usernames, key="sel_user_edit")
        if sel:
            col1, col2 = st.columns([2,1])
            # Flags actuales
            current = df[df["username"]==sel].iloc[0]
            e_admin = col2.checkbox("Admin", value=bool(current["is_admin"]), key="edit_admin")
            e_active = col2.checkbox("Activo", value=bool(current["is_active"]), key="edit_active")

            if col2.button("Guardar cambios", key="btn_save_flags"):
                try:
                    _update_flags(sel, e_admin, e_active)
                    st.success("Actualizado.")
                except Exception as e:
                    st.error(f"Error: {e}")

            # Cambio de contraseña
            st.markdown("**Cambiar contraseña**")
            np1, np2 = st.columns(2)
            p1 = np1.text_input("Nueva contraseña", type="password", key="pwd1")
            p2 = np2.text_input("Confirmar contraseña", type="password", key="pwd2")
            if st.button("Actualizar contraseña", key="btn_set_pwd"):
                if not p1 or p1 != p2:
                    st.warning("Las contraseñas no coinciden.")
                else:
                    try:
                        _set_password(sel, p1)
                        st.success("Contraseña actualizada.")
                    except Exception as e:
                        st.error(f"Error: {e}")

            # Eliminar
            st.markdown("**Eliminar usuario**")
            if st.button("Eliminar usuario seleccionado", key="btn_delete_user"):
                try:
                    _delete_user(sel)
                    st.success("Usuario eliminado.")
                except Exception as e:
                    st.error(f"Error: {e}")
    else:
        st.info("No hay usuarios registrados.")
