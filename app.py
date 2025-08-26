import streamlit as st
import pandas as pd
import unicodedata

st.set_page_config(page_title="Toma de lista", page_icon="🗳️", layout="centered")
st.title("🗳️ Toma de lista – Mesa de votación")

# ----------------------------
# Utilidades
# ----------------------------
def _normalize(s: str) -> str:
    """Quita acentos y pasa a minúsculas para comparar."""
    if s is None:
        return ""
    s = str(s)
    s = unicodedata.normalize('NFD', s)
    s = ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn')
    return s.lower()

# ----------------------------
# Estado
# ----------------------------
if "padron" not in st.session_state:
    st.session_state.padron = pd.DataFrame()

# ----------------------------
# Carga de padrón
# ----------------------------
archivo = st.file_uploader("📎 Sube padrón en CSV (UTF-8, columnas: Nombre, Apellido)", type=["csv"]) 
if archivo:
    try:
        df = pd.read_csv(archivo, dtype=str).fillna("")
        if "Nombre" not in df.columns or "Apellido" not in df.columns:
            st.error("El CSV debe tener al menos las columnas: Nombre y Apellido.")
        else:
            df["Presente"] = False
            st.session_state.padron = df
            st.success(f"Padrón cargado: {len(df)} registros.")
    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")

# ----------------------------
# Buscador
# ----------------------------
if st.session_state.padron.empty:
    st.stop()

col1, col2 = st.columns([2,2])
with col1:
    q_nombre = st.text_input("Buscar por nombre")
with col2:
    q_apellido = st.text_input("Buscar por apellido")

padron = st.session_state.padron.copy()
if q_nombre:
    mask = padron["Nombre"].apply(_normalize).str.contains(_normalize(q_nombre))
    padron = padron[mask]
if q_apellido:
    mask = padron["Apellido"].apply(_normalize).str.contains(_normalize(q_apellido))
    padron = padron[mask]

st.write(f"Resultados: {len(padron)}")

# ----------------------------
# Lista con checkboxes
# ----------------------------
for idx, row in padron.iterrows():
    checked = st.checkbox(f"{row['Nombre']} {row['Apellido']}", value=row["Presente"], key=f"chk_{idx}")
    st.session_state.padron.at[idx, "Presente"] = checked

# ----------------------------
# Exportar lista actualizada
# ----------------------------
csv_bytes = st.session_state.padron.to_csv(index=False).encode("utf-8")
st.download_button("💾 Descargar lista", data=csv_bytes, file_name="toma_lista.csv", mime="text/csv")
