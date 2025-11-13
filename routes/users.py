import streamlit as st
from db import list_users, create_user, update_user, delete_user

def page():
    if not st.session_state.get("is_admin"):
        st.error("Solo administradores.")
        return

    st.title("Usuarios")

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
                except Exception as e:
                    st.error(f"Error: {e}")

    st.subheader("Listado")
    data = list_users()
    if not data:
        st.info("No hay usuarios.")
        return

    for (uid, username, is_admin, is_active, created_at) in data:
        cols = st.columns([3,2,2,2,2])
        cols[0].markdown(f"**{uid} – {username}**")
        cols[1].write("Admin ✅" if is_admin else "Admin ❌")
        cols[2].write("Activo ✅" if is_active else "Activo ❌")
        cols[3].write(str(created_at) if created_at else "-")
        if cols[4].button("Editar", key=f"edit_{uid}"):
            with st.modal(f"Editar usuario #{uid}"):
                st.markdown(f"**ID:** {uid}")
                new_u = st.text_input("Usuario", value=username, key=f"u_{uid}")
                new_p = st.text_input("Nueva contraseña (opcional)", type="password", key=f"p_{uid}")
                adm = st.checkbox("Es administrador", value=bool(is_admin), key=f"a_{uid}")
                act = st.checkbox("Activo", value=bool(is_active), key=f"ac_{uid}")
                c1, c2, c3 = st.columns(3)
                save = c1.button("Guardar cambios", key=f"save_{uid}")
                if username != "admin":
                    del_ok = c2.button("Eliminar usuario", key=f"del_{uid}")
                else:
                    del_ok = False
                    c2.write("No se puede eliminar 'admin'")

                if save:
                    try:
                        update_user(uid,
                                    username=new_u.strip() if new_u.strip() else username,
                                    is_admin=adm,
                                    is_active=act,
                                    password=new_p.strip() if new_p.strip() else None)
                        st.success("Actualizado.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

                if del_ok:
                    try:
                        delete_user(uid)
                        st.success("Eliminado.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
