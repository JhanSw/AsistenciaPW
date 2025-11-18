
import streamlit as st
from db import list_users, create_user, update_user, delete_user, log_action, ensure_default_admin, authenticate_user_ci

def page():
    if not st.session_state.get("is_admin"):
        st.error("Solo administradores.")
        return

    st.title("Usuarios")

    st.session_state.setdefault("editing_user", None)
    st.session_state.setdefault("editing_snapshot", None)
    st.session_state.setdefault("selected_users", set())

    with st.expander("➕ Crear usuario"):
        with st.form("crear_user"):
            u = st.text_input("Usuario *")
            p = st.text_input("Contraseña *", type="password")
            is_admin = st.checkbox("Admin", value=False)
            active = st.checkbox("Activo", value=True)
            sb = st.form_submit_button("Crear")
        if sb:
            if not u.strip() or not p.strip():
                st.error("Usuario y contraseña obligatorios.")
            else:
                try:
                    uid = create_user(u.strip(), p.strip(), is_admin, active)
                    st.success(f"Usuario creado ID {uid}")
                    curuser = st.session_state.get('user') or {}
                    log_action(curuser.get('id'), curuser.get('username'), 'create_user', details={'created_id': uid, 'username': u.strip(), 'is_admin': is_admin, 'active': active})
                except Exception as e:
                    st.error(f"Error: {e}")

    st.subheader("Listado")

    data = list_users()
    if not data:
        st.info("No hay usuarios.")
        return

    # Barra superior con acciones en lote
    cols_top = st.columns([1,2,2,2,3])
    with cols_top[0]:
        select_all = st.checkbox("Todos", key="select_all_users", value=False)
    with cols_top[-1]:
        if st.button("🗑️ Eliminar seleccionados", type="secondary"):
            to_delete = list(st.session_state["selected_users"])
            if not to_delete:
                st.warning("No hay usuarios seleccionados.")
            else:
                deleted = 0
                errs = []
                for uid, username in [(u[0], u[1]) for u in data if u[0] in to_delete]:
                    if username == "admin":
                        errs.append("No se puede eliminar el usuario 'admin'.")
                        continue
                    try:
                        delete_user(uid)
                        deleted += 1
                    except Exception as e:
                        errs.append(str(e))
                st.session_state["selected_users"] = set()
                if deleted:
                    st.success(f"Eliminados {deleted} usuario(s).")
                    curuser = st.session_state.get('user') or {}
                    log_action(curuser.get('id'), curuser.get('username'), 'delete_user', details={'bulk': True, 'count': deleted})
                    st.rerun()
                if errs:
                    st.warning(" | ".join(errs))

    # 'Seleccionar todo' o limpiar selección si la lista cambió
    current_ids = {uid for (uid, *_rest) in data}
    selected = set(st.session_state["selected_users"]) & current_ids
    if select_all:
        selected = set(current_ids)
        # pero sin 'admin'
        selected -= {uid for (uid, username, *_r) in data if username == "admin"}
    st.session_state["selected_users"] = selected

    # Editor en línea (individual)
    if st.session_state["editing_user"] is not None and st.session_state["editing_snapshot"] is not None:
        uid, username, is_admin, is_active = st.session_state["editing_snapshot"]
        st.markdown(f"### Editar usuario #{uid}")
        with st.form("edit_inline"):
            new_u = st.text_input("Usuario", value=username)
            new_p = st.text_input("Nueva contraseña (opcional)", type="password")
            adm = st.checkbox("Es administrador", value=bool(is_admin))
            act = st.checkbox("Activo", value=bool(is_active))
            c1, c2, c3 = st.columns(3)
            save = c1.form_submit_button("Guardar cambios")
            cancel = c2.form_submit_button("Cancelar")
            delete = c3.form_submit_button("Eliminar usuario", disabled=(username == "admin"))
        if save:
            try:
                update_user(uid,
                            username=new_u.strip() if new_u.strip() else username,
                            is_admin=adm,
                            is_active=act,
                            password=new_p.strip() if new_p.strip() else None)
                st.success("Actualizado.")
                curuser = st.session_state.get('user') or {}
                log_action(curuser.get('id'), curuser.get('username'), 'update_user', details={'user_id': uid})
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
        elif cancel:
            st.session_state["editing_user"] = None
            st.session_state["editing_snapshot"] = None
            st.rerun()
        elif delete:
            try:
                delete_user(uid)
                st.success("Eliminado.")
                curuser = st.session_state.get('user') or {}
                log_action(curuser.get('id'), curuser.get('username'), 'delete_user', details={'user_id': uid})
                st.session_state["editing_user"] = None
                st.session_state["editing_snapshot"] = None
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

        st.markdown("---")

    # Tabla con checkboxes + datos + editar
    for (uid, username, is_admin, is_active, created_at) in data:
        row = st.columns([0.7,2.8,1.4,1.4,2,1.2])
        disabled = (username == "admin")
        checked = uid in st.session_state["selected_users"]
        with row[0]:
            cb = st.checkbox("", key=f"sel_{uid}", value=checked, disabled=disabled)
            # Sync selección
            if cb and not disabled:
                st.session_state["selected_users"].add(uid)
            else:
                st.session_state["selected_users"].discard(uid)
        row[1].markdown(f"**{uid} – {username}**")
        row[2].write("Admin ✅" if is_admin else "Admin ❌")
        row[3].write("Activo ✅" if is_active else "Activo ❌")
        row[4].write(str(created_at) if created_at else "-")
        if row[5].button("Editar", key=f"edit_{uid}"):
            st.session_state["editing_user"] = uid
            st.session_state["editing_snapshot"] = (uid, username, is_admin, is_active)
            st.rerun()


# ---------- Login simple para main.py ----------
import streamlit as st
try:
    from db import authenticate_user, ensure_default_admin, authenticate_user_ci
except Exception:
    # Mantener compatibilidad si los nombres difieren
    from db import ensure_default_admin
    def authenticate_user(u, p):
        try:
            ok, user = _authenticate_user(u, p)  # type: ignore
            return user if ok else None
        except Exception:
            return None


def login_page():
    st.title("Ingreso")

    try:
        ensure_default_admin()
    except Exception:
        pass

    username = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")

    if st.button("Entrar"):
        user_obj = None
        uname_norm = (username or "").strip().lower()

        # 1) Try case-insensitive auth if available
        try:
            user_obj = authenticate_user_ci(uname_norm, (password or "").strip())
        except Exception:
            user_obj = None

        # 2) Fallbacks: original authenticate_user, with normalized username and original
        if not user_obj:
            try:
                res = authenticate_user(uname_norm, (password or "").strip())
                if isinstance(res, tuple) and len(res) == 2:
                    ok, user = res
                    user_obj = user if ok else None
                else:
                    user_obj = res
            except Exception:
                user_obj = None

        if not user_obj and username:
            try:
                res = authenticate_user(username.strip(), (password or "").strip())
                if isinstance(res, tuple) and len(res) == 2:
                    ok, user = res
                    user_obj = user if ok else None
                else:
                    user_obj = res
            except Exception:
                user_obj = None

        if user_obj and (user_obj.get("is_active", True)):
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

                user_obj = result
        except Exception:
            user_obj = None

        if user_obj and (user_obj.get("is_active", True)):
            st.session_state["is_auth"] = True
            st.session_state["user"] = {
                "id": user_obj.get("id"),
                "username": user_obj.get("username") or username.strip(),
                "is_admin": bool(user_obj.get("is_admin", False)),
            }
            st.session_state["is_admin"] = bool(user_obj.get("is_admin", False))
            st.rerun()
        else:
            st.error("Usuario/contraseña inválidos o inactivo.")