import streamlit as st
from db import list_users, create_user, set_user_active, set_user_password

def render():
    st.subheader("Administración de Usuarios")
    st.caption("Crear usuarios y gestionar estados.")

    with st.expander("➕ Crear usuario nuevo", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            username = st.text_input("Usuario")
            pwd = st.text_input("Contraseña", type="password")
        with c2:
            pwd2 = st.text_input("Repetir Contraseña", type="password")
            is_admin = st.checkbox("Es administrador", value=False)
        if st.button("Crear usuario", type="primary"):
            if not username or not pwd:
                st.warning("Usuario y Contraseña son obligatorios.")
            elif pwd != pwd2:
                st.error("Las contraseñas no coinciden.")
            else:
                ok = create_user(username, pwd, is_admin=is_admin)
                if ok:
                    st.success("Usuario creado.")
                else:
                    st.error("No se pudo crear (¿ya existe?).")

    st.divider()
    st.markdown("### Usuarios actuales")
    users = list_users()
    if not users:
        st.info("No hay usuarios.")
        return

    for u in users:
        col1, col2, col3, col4 = st.columns([2,1,1,2])
        with col1:
            st.write(f"**{u['username']}** {'👑' if u['is_admin'] else ''}")
        with col2:
            st.write("Activo" if u['is_active'] else "Inactivo")
        with col3:
            if st.button("🔁 Toggle", key=f"tg{u['id']}"):
                set_user_active(u['id'], not u['is_active'])
                st.rerun()
        with col4:
            with st.popover("Cambiar contraseña", use_container_width=True):
                np1 = st.text_input(f"Nueva contraseña ({u['username']})", type="password", key=f"np1{u['id']}")
                np2 = st.text_input("Repetir nueva contraseña", type="password", key=f"np2{u['id']}")
                if st.button("Guardar", key=f"save{u['id']}"):
                    if np1 and np1 == np2:
                        set_user_password(u['id'], np1)
                        st.success("Contraseña actualizada.")
                    else:
                        st.error("Las contraseñas no coinciden.")
