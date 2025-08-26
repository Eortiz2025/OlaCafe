import streamlit as st
import pandas as pd
import unicodedata
from datetime import datetime

# ----------------------------
# Configuración
# ----------------------------
st.set_page_config(page_title="Toma de lista", page_icon="🗳️", layout="centered")
st.title("🗳️ Toma de lista")

# ----------------------------
# Utilidades
# ----------------------------
def _norm(x: str) -> str:
    """Quita acentos y pasa a minúsculas para comparar."""
    x = "" if x is None else str(x)
    x = unicodedata.normalize("NFD", x)
    return "".join(c for c in x if unicodedata.category(c) != "Mn").lower()

def _clear_search():
    # Callback para limpiar campos sin chocar con el ciclo de ejecución
    st.session_state["q_nom"] = ""
    st.session_state["q_ap1"] = ""
    st.session_state["q_ap2"] = ""

# ----------------------------
# Datos precargados (20)
# ID, Nombre, Apellido1, Apellido2, Padrino
# ----------------------------
DATA20 = [
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
]

# ----------------------------
# Estado inicial (persistencia en sesión)
# ----------------------------
if "padron" not in st.session_state:
    df = pd.DataFrame(DATA20, columns=["ID", "Nombre", "Apellido1", "Apellido2", "Padrino"])
    df["Presente"] = False
    df["Hora"] = ""
    st.session_state.padron = df.set_index("ID")  # índice estable por ID

# ----------------------------
# Buscador (en vivo)
# ----------------------------
c1, c2, c3, c4 = st.columns([2,2,2,1])
q_nom = c1.text_input("Nombre", key="q_nom")
q_ap1 = c2.text_input("Primer apellido", key="q_ap1")
q_ap2 = c3.text_input("Segundo apellido", key="q_ap2")
c4.button("Limpiar", on_click=_clear_search)

# ----------------------------
# Filtrado (base oculta hasta que haya búsqueda)
# ----------------------------
padron_full = st.session_state.padron.copy()
padron = padron_full.copy()

if q_nom:
    padron = padron[padron["Nombre"].apply(_norm).str.contains(_norm(q_nom))]
if q_ap1:
    padron = padron[padron["Apellido1"].apply(_norm).str.contains(_norm(q_ap1))]
if q_ap2:
    padron = padron[padron["Apellido2"].apply(_norm).str.contains(_norm(q_ap2))]

min_chars = 1
hay_busqueda_valida = any(len(q) >= min_chars for q in [q_nom, q_ap1, q_ap2])

if hay_busqueda_valida:
    st.caption(f"Resultados: {len(padron)}")
    # Render de checkboxes (con reload y persistencia)
    for id_, row in padron.iterrows():
        etiqueta = f"{row['Nombre']} {row['Apellido1']} {row['Apellido2']} — [{row['Padrino']}]"
        chk = st.checkbox(etiqueta, value=bool(row["Presente"]), key=f"p_{id_}")
        if chk != row["Presente"]:
            st.session_state.padron.at[id_, "Presente"] = chk
            st.session_state.padron.at[id_, "Hora"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if chk else ""
            st.rerun()
else:
    st.info(f"Escribe al menos {min_chars} letra en Nombre o Apellidos para buscar.")

# ----------------------------
# Exportar CSV
# ----------------------------
st.download_button(
    "💾 Descargar lista",
    st.session_state.padron.reset_index().to_csv(index=False).encode("utf-8"),
    file_name="toma_lista.csv",
    mime="text/csv",
)
