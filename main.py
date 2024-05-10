import pandas as pd
import streamlit as st

st.title("Introduccion a StreamLit")

@st.cache_data
def load_data(path: str):
    data = pd.read_csv(path)
    return data

uploaded_file = st.file_uploader("Choose a file")
df = load_data(uploaded_file)
st.dataframe(df)