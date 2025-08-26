import streamlit as st
import pandas as pd
import unicodedata
from datetime import datetime

st.set_page_config(page_title="Toma de lista", page_icon="🗳️", layout="centered")
st.title("🗳️ Toma de lista")

# ----------------------------
# Utilidades
# ----------------------------
def _norm(x: str) -> str:
    x = "" if x is None else str(x)
    x = unicodedata.normalize("NFD", x)
    return "".join(c for c in x if unicodedata.category(c) != "Mn").lower()

# ----------------------------
# Datos (20 originales + 18 nuevos con Padrino simulado)
# ----------------------------
DATA = [
    [1,  "Juan",      "Pérez",     "López",     "Alberto"],
    [2,  "María",     "Gómez",     "Hernández", "Alma"],
    [3,  "Luis",      "Ramírez",   "Castro",    "Edgar"],
    [4,  "Ana",       "Torres",    "Martínez",  "Alberto"],
    [5,  "Carlos",    "Fernández", "Ruiz",      "Alma"],
    [6,  "Sofía",     "Rodríguez", "García",    "Edgar"],
    [7,  "Miguel",    "Hernández", "Santos",    "Alberto"],
    [8,  "Lucía",     "Vargas",    "Morales",   "Alma"],
    [9,  "José",      "Díaz",      "Ramos",     "Edgar"],
    [10, "Carmen",    "Ortiz",     "Delgado",   "Alberto"],
    [11, "Pedro",     "Navarro",   "Aguilar",   "Alma"],
    [12, "Elena",     "Mendoza",   "Romero",    "Edgar"],
    [13, "Jorge",     "Flores",    "Reyes",     "Alberto"],
    [14, "Patricia",  "Serrano",   "Acosta",    "Alma"],
    [15, "Andrés",    "Guerrero",  "Silva",     "Edgar"],
    [16, "Isabel",    "Cruz",      "Salazar",   "Alberto"],
    [17, "Hugo",      "Molina",    "Paredes",   "Alma"],
    [18, "Adriana",   "Campos",    "Rangel",    "Edgar"],
    [19, "Fernando",  "Suárez",    "Valdez",    "Alberto"],
    [20, "Gabriela",  "Luna",      "Méndez",    "Alma"],
    [21, "Alberto",   "Contreras", "", "Alberto"],
    [22, "Edgar",     "Sanchez",   "", "Alma"],
    [23, "Emilio",    "Urrecha",   "", "Edgar"],
    [24, "Javier",    "Osorio",    "", "Alberto"],
    [25, "Juan",      "Gonzalez",  "", "Alma"],
    [26, "Miguel",    "Ontiveros", "", "Edgar"],
    [27, "Noe",       "Silvas",    "", "Alberto"],
    [28, "Raul",      "Valdez",    "", "Alma"],
    [29, "Sergio",    "Galvan",    "", "Edgar"],
    [30, "Alma",      "Morgan",    "", "Alberto"],
    [31, "Cata",      "Frank",     "", "Alma"],
    [32, "Claudia",   "Sing",      "", "Edgar"],
    [33, "Minerva",   "Salomon",   "", "Alberto"],
    [34, "Karen",     "Garcia",    "", "Alma"],
    [35, "Laura",     "Contreras", "", "Edgar"],
    [36, "Marcela",   "Landel",    "", "Alberto"],
    [37, "Olga",      "Escamilla", "", "Alma"],
    [38, "Vanessa",   "Sanchez",   "", "Edgar"],
]

# ----------------------------
# Estado inicial
# ----------------------------
if "padron" not in st.session_state:
    df = pd.DataFrame(DATA, columns=["ID", "Nombre", "Apellido1", "Apellido2", "Padrino"])
    df["Presente"] = False
    df["Hora"] = ""
    st.session_state.padron = df.set_index("ID")

# ----------------------------
# Buscador solo por nombre
# ----------------------------
q_nom = st.text_input("Buscar por nombre", key="q_nom")

# ----------------------------
# Filtrado
# ----------------------------
padron = st.session_state.padron.copy()
if q_nom:
    padron = padron[padron["Nombre"].apply(_norm).str.contains(_norm(q_nom))]

# ----------------------------
# Mostrar resultados
# ----------------------------
if not padron.empty and q_nom:
    st.caption(f"Resultados: {len(padron)}")
    for id_, row in padron.iterrows():
        etiqueta = f"{row['Nombre']} {row['Apellido1']} {row['Apellido2']}".strip()
        etiqueta = etiqueta if row["Padrino"] == "" else f"{etiqueta} — [{row['Padrino']}]"
        chk = st.checkbox(etiqueta, value=bool(row["Presente"]), key=f"p_{id_}")
        if chk != row["Presente"]:
            st.session_state.padron.at[id_, "Presente"] = chk
            st.session_state.padron.at[id_, "Hora"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if chk else ""
            st.rerun()
