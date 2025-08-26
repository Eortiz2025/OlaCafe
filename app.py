import streamlit as st
import pandas as pd
import unicodedata

st.set_page_config(page_title="Toma de lista", page_icon="🗳️", layout="centered")
st.title("🗳️ Toma de lista")

def _norm(x):
    x = "" if x is None else str(x)
    x = unicodedata.normalize("NFD", x)
    return "".join(c for c in x if unicodedata.category(c) != "Mn").lower()

# ----------------------------
# Padrón precargado (20 nombres)
# ----------------------------
data = [
    ["Juan", "Pérez", "López"],
    ["María", "Gómez", "Hernández"],
    ["Luis", "Ramírez", "Castro"],
    ["Ana", "Torres", "Martínez"],
    ["Carlos", "Fernández", "Ruiz"],
    ["Sofía", "Rodríguez", "García"],
    ["Miguel", "Hernández", "Santos"],
    ["Lucía", "Vargas", "Morales"],
    ["José", "Díaz", "Ramos"],
    ["Carmen", "Ortiz", "Delgado"],
    ["Pedro", "Navarro", "Aguilar"],
    ["Elena", "Mendoza", "Romero"],
    ["Jorge", "Flores", "Reyes"],
    ["Patricia", "Serrano", "Acosta"],
    ["Andrés", "Guerrero", "Silva"],
    ["Isabel", "Cruz", "Salazar"],
    ["Hugo", "Molina", "Paredes"],
    ["Adriana", "Campos", "Rangel"],
    ["Fernando", "Suárez", "Valdez"],
    ["Gabriela", "Luna", "Méndez"],
]

if "padron" not in st.session_state:
    df = pd.DataFrame(data, columns=["Nombre", "Apellido1", "Apellido2"])
    df["Presente"] = False
    st.session_state.padron = df

# ----------------------------
# Buscador
# ----------------------------
c1, c2, c3 = st.columns(3)
q_nom = c1.text_input("Buscar nombre")
q_ap1 = c2.text_input("Buscar primer apellido")
q_ap2 = c3.text_input("Buscar segundo apellido")

padron = st.session_state.padron.copy()
if q_nom:
    padron = padron[padron["Nombre"].apply(_norm).str.contains(_norm(q_nom))]
if q_ap1:
    padron = padron[padron["Apellido1"].apply(_norm).str.contains(_norm(q_ap1))]
if q_ap2:
    padron = padron[padron["Apellido2"].apply(_norm).str.contains(_norm(q_ap2))]

st.write(f"Resultados: {len(padron)}")

# ----------------------------
# Lista con checkboxes (con reload)
# ----------------------------
for i, row in padron.iterrows():
    label = f"{row['Nombre']} {row['Apellido1']} {row['Apellido2']}"
    chk = st.checkbox(label, value=bool(row["Presente"]), key=f"p_{i}")
    if chk != row["Presente"]:
        st.session_state.padron.at[i, "Presente"] = chk
        st.rerun()   # 🔄 Recarga la app para mostrar todo otra vez

# ----------------------------
# Exportar lista
# ----------------------------
st.download_button(
    "💾 Descargar lista",
    st.session_state.padron.to_csv(index=False).encode("utf-8"),
    file_name="toma_lista.csv",
    mime="text/csv",
)
