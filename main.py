import streamlit as st
from db import init_database, populate_sample_data
import importlib

st.set_page_config(page_title='Asistencia', page_icon='✅', layout='wide')

init_database()
try:
    populate_sample_data()
except Exception:
    pass

st.title('Sistema de Asistencia')

pages = {}
for name in ('assistance','create','search'):
    try:
        pages[name] = importlib.import_module(f'routes.{name}')
    except Exception:
        pass

if pages:
    choice = st.sidebar.radio('Módulos', list(pages.keys()))
    pages[choice].render()
else:
    st.info('Agrega módulos en routes/*.py con una función render().')
