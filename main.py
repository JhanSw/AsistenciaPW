import streamlit as st
from db import init_database
import importlib

st.set_page_config(page_title="Asistencia", page_icon="✅", layout="wide")
init_database()

st.title("Sistema de Asistencia")

pages = {
    "asistencia": importlib.import_module("routes.assistance"),
    "buscar": importlib.import_module("routes.search"),
    "nuevo": importlib.import_module("routes.create"),
}

choice = st.sidebar.radio("Módulos", list(pages.keys()))
pages[choice].render()
