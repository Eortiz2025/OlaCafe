import streamlit as st
import pandas as pd
from datetime import datetime, date
import time
import os

CSV_FILE = "historial_meditacion.csv"

# ---------- Utilidades de historial ----------
def cargar_historial():
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE, parse_dates=["fecha_hora"])
        df["fecha"] = df["fecha_hora"].dt.date
        return df
    else:
        return pd.DataFrame(columns=["fecha_hora", "duracion_min", "notas", "fecha"])

def guardar_sesion(duracion_min, notas=""):
    df = cargar_historial()
    ahora = datetime.now()
    nueva = pd.DataFrame(
        {
            "fecha_hora": [ahora],
            "duracion_min": [duracion_min],
            "notas": [notas],
            "fecha": [ahora.date()],
        }
    )
    df = pd.concat([df, nueva], ignore_index=True)
    df.to_csv(CSV_FILE, index=False)

# ---------- App ----------
st.set_page_config(page_title="Meditación", page_icon="🧘", layout="centered")
st.title("🧘 Temporizador de Meditación")
st.caption("Temporizador + historial de días y número de sesiones.")

historial = cargar_historial()

st.subheader("1️⃣ Configura tu sesión")
duracion_min = st.number_input(
    "Duración (minutos)", min_value=1, max_value=120, value=10, step=1
)
notas = st.text_input("Notas (opcional)", placeholder="Meditación de la mañana, etc.")

col1, col2 = st.columns(2)

with col1:
    iniciar = st.button("▶ Iniciar meditación")

with col2:
    registrar_manual = st.button("✅ Registrar sesión sin temporizador")

# ---------- Registrar sin temporizador ----------
if registrar_manual:
    guardar_sesion(duracion_min, notas)
    st.success(f"Sesión de {duracion_min} min registrada manualmente.")

# ---------- Temporizador ----------
if "en_curso" not in st.session_state:
    st.session_state.en_curso = False

if iniciar:
    st.session_state.en_curso = True

if st.session_state.en_curso:
    st.subheader("⏳ Temporizador en curso")
    placeholder = st.empty()

    total_segundos = int(duracion_min * 60)

    for restante in range(total_segundos, -1, -1):
        minutos = restante // 60
        segundos = restante % 60
        placeholder.markdown(
            f"## ⏰ {minutos:02d}:{segundos:02d} restantes",
            unsafe_allow_html=True,
        )
        time.sleep(1)
    st.session_state.en_curso = False
    guardar_sesion(duracion_min, notas)
    st.success(f"Sesión completada y guardada ({duracion_min} min). 🙏")

# ---------- Historial ----------
st.subheader("2️⃣ Historial de meditaciones")

if historial.empty:
    st.info("Todavía no hay sesiones registradas.")
else:
    # Resumen por día
    resumen = (
        historial.groupby("fecha")
        .agg(
            sesiones=("duracion_min", "count"),
            minutos_totales=("duracion_min", "sum"),
        )
        .reset_index()
        .sort_values("fecha", ascending=False)
    )

    st.markdown("**Resumen por día**")
    st.dataframe(resumen, use_container_width=True)

    with st.expander("Ver historial detallado"):
        st.dataframe(
            historial.sort_values("fecha_hora", ascending=False),
            use_container_width=True,
        )
