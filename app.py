import streamlit as st
import pandas as pd
from datetime import date, timedelta
import os

# Configuración inicial
DATA_FILE = "habits_franklin.csv"
HABITS = ["Camina", "Escribe", "Estira", "Lee", "Medita", "Respira", "Tapping"]
DAYS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

# Cargar datos
if os.path.exists(DATA_FILE):
    df = pd.read_csv(DATA_FILE)
else:
    df = pd.DataFrame(columns=["Semana", "Hábito"] + DAYS)

# Calcular inicio de semana actual
hoy = date.today()
inicio_semana = hoy - timedelta(days=hoy.weekday())
semana_str = inicio_semana.strftime("%Y-%m-%d")

# Configurar Streamlit
st.set_page_config(page_title="Habit Tracker Franklin", layout="centered")
st.title("📊 Habit Tracker Semanal (Estilo Benjamin Franklin)")
st.subheader(f"Semana que inicia: {semana_str}")

# Tabla de hábitos con casillas por día
st.markdown("### ❌ Marca cuando **fallaste** en un hábito (al estilo Franklin)")
records = []
for habit in HABITS:
    st.markdown(f"**{habit}**")
    cols = st.columns(len(DAYS))
    row = {"Semana": semana_str, "Hábito": habit}
    for i, day in enumerate(DAYS):
        fallo = cols[i].checkbox(day, key=f"{habit}_{day}")
        row[day] = 1 if fallo else 0
    records.append(row)

# Guardar datos
if st.button("💾 Guardar hábitos semanales"):
    df_new = pd.DataFrame(records)
    df = pd.concat([df, df_new], ignore_index=True)
    df.to_csv(DATA_FILE, index=False)
    st.success("✅ Registro de hábitos guardado correctamente.")

# Mostrar historial
if st.checkbox("📂 Ver historial de hábitos"):
    st.dataframe(df[df["Semana"] == semana_str])
