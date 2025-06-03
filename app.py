import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
import os

# ---------- Configuracion Inicial ----------
DATA_FILE = "planner_hybrid.csv"
ROLES = ["Yo mismo", "Familia", "Profesional", "Aprendizaje"]
SLOTS = [f"{hour}:00" for hour in range(6, 22)]  # Horario de 6am a 9pm
DAYS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

# ---------- Cargar datos ----------
if os.path.exists(DATA_FILE):
    df = pd.read_csv(DATA_FILE)
else:
    df = pd.DataFrame(columns=["Semana", "Fecha", "Rol", "Meta", "Dia", "Hora", "Tarea", "Prioridad", "Estado"])

st.set_page_config(page_title="Planner Híbrido", layout="wide")
st.title("🧭 Planner Semanal - FranklinCovey + GTD")

# ---------- Seleccion de semana ----------
hoy = date.today()
inicio_semana = hoy - timedelta(days=hoy.weekday())
semana_str = inicio_semana.strftime("%Y-%m-%d")
st.subheader(f"Planificación de la semana: {semana_str}")

# ---------- Roles y metas ----------
st.markdown("### 🎯 Roles y metas semanales")
seccion_metas = []
for rol in ROLES:
    meta = st.text_input(f"Meta para el rol: {rol}", key=f"meta_{rol}")
    if meta:
        seccion_metas.append({"Semana": semana_str, "Fecha": semana_str, "Rol": rol, "Meta": meta})

# ---------- Tareas diarias con prioridad ----------
st.markdown("### ✅ Tareas por día con prioridad (A: Alta, B: Media, C: Baja)")
tareas = []
for dia in DAYS:
    with st.expander(dia):
        for i in range(3):
            tarea = st.text_input(f"Tarea {i+1} para {dia}", key=f"{dia}_tarea_{i}")
            prioridad = st.selectbox(f"Prioridad", ["", "A", "B", "C"], key=f"{dia}_prio_{i}")
            if tarea and prioridad:
                tareas.append({"Semana": semana_str, "Fecha": semana_str, "Dia": dia, "Tarea": tarea, "Prioridad": prioridad, "Hora": "", "Estado": "Pendiente", "Rol": "", "Meta": ""})

# ---------- Agenda horaria (simplificada) ----------
st.markdown("### 🕒 Agenda horaria semanal")
agenda = []
for dia in DAYS:
    with st.expander(f"Agenda para {dia}"):
        for hora in SLOTS:
            evento = st.text_input(f"{hora}", key=f"{dia}_{hora}")
            if evento:
                agenda.append({"Semana": semana_str, "Fecha": semana_str, "Dia": dia, "Hora": hora, "Tarea": evento, "Prioridad": "", "Estado": "Pendiente", "Rol": "", "Meta": ""})

# ---------- Seccion "Sharpen the Saw" ----------
st.markdown("### 🧘 Sharpen the Saw")
areas = ["Física", "Mental", "Espiritual", "Social"]
saw = []
for area in areas:
    actividad = st.text_input(f"Actividad para {area}", key=f"saw_{area}")
    if actividad:
        saw.append({"Semana": semana_str, "Fecha": semana_str, "Dia": "", "Hora": "", "Tarea": actividad, "Prioridad": "B", "Estado": "Pendiente", "Rol": "Renovación", "Meta": area})

# ---------- Guardar datos ----------
if st.button("💾 Guardar planificación semanal"):
    # Consolidar todo
    metas_df = pd.DataFrame(seccion_metas)
    tareas_df = pd.DataFrame(tareas)
    agenda_df = pd.DataFrame(agenda)
    saw_df = pd.DataFrame(saw)
    
    full_df = pd.concat([df, metas_df, tareas_df, agenda_df, saw_df], ignore_index=True)
    full_df.to_csv(DATA_FILE, index=False)
    st.success("✅ Planificación guardada correctamente")

# ---------- Visualizar datos ----------
if st.checkbox("📂 Mostrar planificación guardada"):
    st.dataframe(full_df.tail(100))
