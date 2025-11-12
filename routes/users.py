
import streamlit as st
from db import create_user, update_user, delete_user

def page():
    if not st.session_state.get("is_admin"):
        st.error("Solo administradores.")
        return
    st.title("Usuarios")

    st.subheader("Crear usuario")
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

    st.subheader("Editar usuario existente")
    with st.form("edit_user"):
        uid = st.number_input("ID de usuario", min_value=1, step=1)
        new_u = st.text_input("Nuevo usuario (opcional)")
        new_p = st.text_input("Nueva contraseña (opcional)", type="password")
        adm = st.selectbox("Admin", options=["","Sí","No"], index=0)
        act = st.selectbox("Activo", options=["","Sí","No"], index=0)
        sb2 = st.form_submit_button("Actualizar")
    if sb2:
        kwargs = {}
        if new_u.strip(): kwargs["username"] = new_u.strip()
        if new_p.strip(): kwargs["password"] = new_p.strip()
        if adm != "": kwargs["is_admin"] = (adm == "Sí")
        if act != "": kwargs["is_active"] = (act == "Sí")
        try:
            update_user(uid, **kwargs)
            st.success("Actualizado.")
        except Exception as e:
            st.error(f"Error: {e}")

    st.subheader("Eliminar usuario")
    with st.form("del_user"):
        uid2 = st.number_input("ID a eliminar", min_value=1, step=1, key="delid")
        sb3 = st.form_submit_button("Eliminar")
    if sb3:
        try:
            delete_user(uid2)
            st.success("Eliminado.")
        except Exception as e:
            st.error(f"Error: {e}")
