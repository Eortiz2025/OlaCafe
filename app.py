import streamlit as st
import pandas as pd
import unicodedata
from datetime import datetime
from pathlib import Path

st.set_page_config(page_title="Toma de lista", page_icon="🗳️", layout="centered")
st.title("🗳️ Toma de lista")

# ----------------------------
# Utilidad para normalizar texto
# ----------------------------
def _norm(x: str) -> str:
    x = "" if x is None else str(x)
    x = unicodedata.normalize("NFD", x)
    return "".join(c for c in x if unicodedata.category(c) != "Mn").lower()

# ----------------------------
# Cargar nombres desde archivo externo
# ----------------------------
ARCHIVO = Path("nombres.txt")

if not ARCHIVO.exists():
    st.error("⚠️ No encontré el archivo 'nombres.txt'. Crea uno en la misma carpeta de la app con un nombre por línea.")
    st.stop()

with ARCHIVO.open("r", encoding="utf-8") as f:
    nombres_raw = [line.strip() for line in f if line.strip()]

# Ordenar alfabéticamente
nombres = sorted(nombres_raw)

# ----------------------------
# Estado inicial
# ----------------------------
if "padron" not in st.session_state:
    df = pd.DataFrame(nombres, columns=["NombreCompleto"])
    df.insert(0, "ID", range(1, len(df) + 1))
    df["Presente"] = False
    df["Hora"] = ""
    st.session_state.padron = df.set_index("ID")

# ----------------------------
# Buscador
# ----------------------------
q = st.text_input("Buscar nombre o apellido")

padron = st.session_state.padron.copy()
if q:
    padron = padron[padron["NombreCompleto"].apply(_norm).str.contains(_norm(q))]

# ----------------------------
# Mostrar resultados
# ----------------------------
if q and not padron.empty:
    st.caption(f"Resultados: {len(padron)}")
    for id_, row in padron.iterrows():
        chk = st.checkbox(row["NombreCompleto"], value=bool(row["Presente"]), key=f"p_{id_}")
        if chk != row["Presente"]:
            st.session_state.padron.at[id_, "Presente"] = chk
            st.session_state.padron.at[id_, "Hora"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if chk else ""
            st.rerun()
elif q:
    st.info("Sin coincidencias.")
else:
    st.info("Escribe un nombre o apellido para buscar.")
