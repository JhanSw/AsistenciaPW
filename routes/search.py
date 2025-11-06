import streamlit as st
from db import get_all_people
import pandas as pd

def render():
    st.subheader("Buscar personas")
    data = get_all_people()
    if not data:
        st.info("Sin registros todavía.")
        return
    df = pd.DataFrame(data)
    q = st.text_input("Buscar por nombre o documento")
    muni_list = sorted(list({(x.get('municipality') or '') for x in data}))
    muni = st.selectbox("Filtrar por municipio", ["(Todos)"] + muni_list)

    if q:
        df = df[df['names'].str.contains(q, case=False, na=False) | df['document'].str.contains(q, na=False)]
    if muni != "(Todos)":
        df = df[df['municipality'].fillna('') == muni]

    st.dataframe(df[['document','names','department','municipality','entity','last_assistance_utc']], use_container_width=True)
