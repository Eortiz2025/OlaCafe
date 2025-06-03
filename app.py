import streamlit as st
import pandas as pd
from datetime import date, timedelta
import os

# Configuración inicial
DATA_FILE = "planner_hybrid.csv"
ROLES = ["Yo mismo", "Familia", "Profesional", "Aprendizaje"]
AREAS_SAW = ["Físico", "Mental", "Espiritual", "Social"]

# Cargar datos
if os.path.exists(DATA_FILE):
    df = pd.read_csv(DATA_FILE)
else:
    df = pd.DataFrame(columns=["Semana", "Fecha", "Rol", "Meta", "Area", "Actividad"])

# Calcular inicio de semana actual
hoy = date.today()
inicio_semana = hoy - timedelta(days=hoy.weekday())
semana_str = inicio_semana.strftime("%Y-%m-%d")

# Configurar Streamlit
st.set_page_config(page_title="Planner Semanal", layout="centered")
st.title("🧭 Planificación Semanal (FranklinCovey + GTD)")
st.subheader(f"Semana que inicia: {semana_str}")

# ------------------------
# 🧱 Sección: Metas por rol
# ------------------------
st.markdown("### 🎯 Metas por Rol")
metas = []
cols = st.columns(2)
for i, rol in enumerate(ROLES):
    with cols[i % 2]:
        meta = st.text_input(f"Meta para el rol: {rol}", key=f"meta_{rol}")
        if meta:
            metas.append({"Semana": semana_str, "Fecha": semana_str, "Rol": rol, "Meta": meta, "Area": "", "Actividad": ""})

# ------------------------
# 🧘 Sección: Sharpen the Saw
# ------------------------
st.markdown("### 🧘 Renovación Personal (Sharpen the Saw)")
saw = []
cols = st.columns(2)
for i, area in enumerate(AREAS_SAW):
    with cols[i % 2]:
        act = st.text_input(f"Actividad para {area}", key=f"saw_{area}")
        if act:
            saw.append({"Semana": semana_str, "Fecha": semana_str, "Rol": "Renovación", "Meta": area, "Area": area, "Actividad": act})

# ------------------------
# Guardar datos
# ------------------------
if st.button("💾 Guardar planificación semanal"):
    metas_df = pd.DataFrame(metas)
    saw_df = pd.DataFrame(saw)
    df = pd.concat([df, metas_df, saw_df], ignore_index=True)
    df.to_csv(DATA_FILE, index=False)
    st.success("✅ Planificación guardada correctamente.")

# ------------------------
# Ver últimos registros
# ------------------------
if st.checkbox("📂 Ver últimas metas y actividades"):
    st.dataframe(df[df["Semana"] == semana_str])
