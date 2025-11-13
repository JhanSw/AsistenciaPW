import streamlit as st
from db import list_users, create_user, update_user, delete_user, log_action

def page():
    if not st.session_state.get("is_admin"):
        st.error("Solo administradores.")
        return

    st.title("Usuarios")

    # Estado para editor inline
    st.session_state.setdefault("editing_user", None)
    st.session_state.setdefault("editing_snapshot", None)

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

    # Si hay un usuario en edición, mostrar editor arriba
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
                st.session_state["editing_user"] = None
                st.session_state["editing_snapshot"] = None
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

    # Render filas con botón Editar (abre editor inline)
    for (uid, username, is_admin, is_active, created_at) in data:
        cols = st.columns([3,2,2,2,2])
        cols[0].markdown(f"**{uid} – {username}**")
        cols[1].write("Admin ✅" if is_admin else "Admin ❌")
        cols[2].write("Activo ✅" if is_active else "Activo ❌")
        cols[3].write(str(created_at) if created_at else "-")
        if cols[4].button("Editar", key=f"edit_{uid}"):
            st.session_state["editing_user"] = uid
            st.session_state["editing_snapshot"] = (uid, username, is_admin, is_active)
            st.rerun()
