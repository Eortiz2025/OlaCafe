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
# Barra lateral
# ----------------------------
with st.sidebar:
    st.subheader("Ajustes")
    ocultar_base = st.toggle(
        "Ocultar base (mostrar solo al buscar)",
        value=True,
        help="No renderiza la lista completa; solo aparece cuando escribes nombre/apellidos."
    )
    supervisor = st.toggle(
        "Modo supervisor (ver todo)",
        value=False,
        help="Muestra toda la lista ignorando 'Ocultar base'."
    )

# ----------------------------
# Buscador (actualiza en tiempo real mientras tecleas)
# ----------------------------
c1, c2, c3 = st.columns(3)
q_nom = c1.text_input("Nombre", key="q_nom")
q_ap1 = c2.text_input("Primer apellido", key="q_ap1")
q_ap2 = c3.text_input("Segundo apellido", key="q_ap2")

colb1, colb2 = st.columns([1, 1])
if colb1.button("Limpiar búsqueda"):
    st.session_state["q_nom"] = ""
    st.session_state["q_ap1"] = ""
    st.session_state["q_ap2"] = ""
    st.rerun()

# ----------------------------
# Filtrado
# ----------------------------
padron_full = st.session_state.padron.copy()
padron = padron_full.copy()

if q_nom:
    padron = padron[padron["Nombre"].apply(_norm).str.contains(_norm(q_nom))]
if q_ap1:
    padron = padron[padron["Apellido1"].apply(_norm).str.contains(_norm(q_ap1))]
if q_ap2:
    padron = padron[padron["Apellido2"].apply(_norm).str.contains(_norm(q_ap2))]

# ----------------------------
# Lógica de visibilidad
# ----------------------------
min_chars = 1  # mínimo de letras para mostrar resultados en modo oculto
hay_busqueda_valida = any(len(q) >= min_chars for q in [q_nom, q_ap1, q_ap2])

if supervisor or not ocultar_base or hay_busqueda_valida:
    base_a_mostrar = padron if (hay_busqueda_valida or supervisor or not ocultar_base) else padron_full
    st.caption(f"Resultados: {len(base_a_mostrar)}")

    # Render de checkboxes (con reload y persistencia)
    for id_, row in base_a_mostrar.iterrows():
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
