import streamlit as st
import pandas as pd
import unicodedata

st.set_page_config(page_title="Toma de lista", page_icon="🗳️", layout="centered")
st.title("🗳️ Toma de lista")

def _norm(x):
    x = "" if x is None else str(x)
    x = unicodedata.normalize("NFD", x)
    return "".join(c for c in x if unicodedata.category(c) != "Mn").lower()

if "padron" not in st.session_state:
    st.session_state.padron = pd.DataFrame()

archivo = st.file_uploader("CSV (columnas: Nombre, Apellido)", type=["csv"])
if archivo:
    df = pd.read_csv(archivo, dtype=str).fillna("")
    if not {"Nombre", "Apellido"}.issubset(df.columns):
        st.error("El CSV debe tener columnas: Nombre y Apellido.")
        st.stop()
    if "Presente" not in df.columns:
        df["Presente"] = False
    st.session_state.padron = df

if st.session_state.padron.empty:
    st.info("Sube el CSV para comenzar.")
    st.stop()

c1, c2 = st.columns(2)
q_nom = c1.text_input("Buscar nombre")
q_ape = c2.text_input("Buscar apellido")

padron = st.session_state.padron.copy()
if q_nom:
    padron = padron[padron["Nombre"].apply(_norm).str.contains(_norm(q_nom))]
if q_ape:
    padron = padron[padron["Apellido"].apply(_norm).str.contains(_norm(q_ape))]

st.write(f"Resultados: {len(padron)}")
for i, row in padron.iterrows():
    chk = st.checkbox(f"{row['Nombre']} {row['Apellido']}", value=bool(row["Presente"]), key=f"p_{i}")
    st.session_state.padron.at[i, "Presente"] = chk

st.download_button("💾 Descargar lista", st.session_state.padron.to_csv(index=False).encode("utf-8"),
                   file_name="toma_lista.csv", mime="text/csv")

