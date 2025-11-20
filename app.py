import streamlit as st
import pandas as pd
from datetime import datetime, date
import time
import os
import calendar

CSV_FILE = "historial_meditacion.csv"

# ---------- Utilidades de historial ----------
def cargar_historial():
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE, parse_dates=["fecha_hora"])
        df["fecha"] = df["fecha_hora"].dt.date
        # Compatibilidad por si no existiera columna notas
        if "notas" not in df.columns:
            df["notas"] = ""
        return df
    else:
        return pd.DataFrame(columns=["fecha_hora", "duracion_min", "notas", "fecha"])

def guardar_sesion(duracion_min):
    df = cargar_historial()
    ahora = datetime.now()
    nueva = pd.DataFrame(
        {
            "fecha_hora": [ahora],
            "duracion_min": [duracion_min],
            "notas": [""],
            "fecha": [ahora.date()],
        }
    )
    df = pd.concat([df, nueva], ignore_index=True)
    df.to_csv(CSV_FILE, index=False)

# ---------- App ----------
st.set_page_config(page_title="Meditación", page_icon="🧘", layout="centered")
st.title("🧘 Temporizador de Meditación")
st.caption("Temporizador + historial mensual con días meditados en verde.")

historial = cargar_historial()

st.subheader("1️⃣ Configura tu sesión")
duracion_min = st.number_input(
    "Duración (minutos)", min_value=1, max_value=120, value=15, step=1
)

col1, col2 = st.columns(2)

with col1:
    iniciar = st.button("▶ Iniciar meditación")

with col2:
    registrar_manual = st.button("✅ Registrar sesión sin temporizador")

# ---------- Registrar sin temporizador ----------
if registrar_manual:
    guardar_sesion(duracion_min)
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
    guardar_sesion(duracion_min)
    st.success(f"Sesión completada y guardada ({duracion_min} min). 🙏")

# ---------- Historial ----------
st.subheader("2️⃣ Historial de meditaciones")

if historial.empty:
    st.info("Todavía no hay sesiones registradas.")
else:
    # ---- Calendario mensual actual ----
    hoy = date.today()
    year = hoy.year
    month = hoy.month

    # Fechas en las que se meditó (set de date)
    fechas_meditadas = set(historial["fecha"].unique())

    cal_mes = calendar.monthcalendar(year, month)
    dias_semana = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

    tabla_html = "<table style='border-collapse: collapse; width: 100%; text-align: center;'>"

    # Encabezado
    tabla_html += "<tr>"
    for d in dias_semana:
        tabla_html += f"<th style='border:1px solid #ddd; padding:4px;'>{d}</th>"
    tabla_html += "</tr>"

    # Filas de semanas
    for semana in cal_mes:
        tabla_html += "<tr>"
        for dia in semana:
            if dia == 0:
                tabla_html += "<td style='border:1px solid #ddd; padding:4px;'>&nbsp;</td>"
            else:
                fecha_dia = date(year, month, dia)
                if fecha_dia in fechas_meditadas:
                    bg = "#b6fcb6"  # verde suave
                else:
                    bg = "#f5f5f5"  # gris claro

                tabla_html += (
                    f"<td style='border:1px solid #ddd; padding:4px; "
                    f"background-color:{bg};'>{dia}</td>"
                )
        tabla_html += "</tr>"

    tabla_html += "</table>"

    st.markdown("**Calendario del mes actual** (verde = hubo meditación)")
    st.markdown(tabla_html, unsafe_allow_html=True)

    # ---- Resumen por día ----
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
