import streamlit as st
import pandas as pd
import datetime
import os

st.set_page_config(page_title="Captura de Votantes", layout="centered")
st.title("🗳️ Registro de Votantes por Promotor")

# Archivo CSV donde se guarda todo
ARCHIVO_DATOS = "votantes.csv"

# Lista fija de usuarios válidos
usuarios_validos = ["Tania", "Olga", "Emilio", "Sergio", "Juan", "Elvia", "Claudia", "admin"]

# Cargar datos desde el archivo si existe
if os.path.exists(ARCHIVO_DATOS):
    df = pd.read_csv(ARCHIVO_DATOS)
else:
    df = pd.DataFrame(columns=["Promotor", "Votante", "Teléfono", "¿Llamó?", "Fecha"])

# Entrada del usuario
nombre = st.text_input("Escribe tu nombre para acceder (ej. Tania)").strip()

if nombre:
    if nombre in usuarios_validos:
        st.success(f"Bienvenido, {nombre}")

        if nombre == "admin":
            st.subheader("📊 Vista de administrador")
            st.dataframe(df)
            st.download_button("📥 Descargar Excel", df.to_csv(index=False).encode(), file_name="votantes.csv")
        else:
            st.subheader("✍️ Captura de votante")

            with st.form("captura"):
                votante = st.text_input("Nombre del votante")
                telefono = st.text_input("Teléfono (opcional)")
                llamo = st.checkbox("¿Ya lo llamaste?")
                enviar = st.form_submit_button("Guardar")

                if enviar and votante.strip():
                    nueva_fila = {
                        "Promotor": nombre,
                        "Votante": votante.strip(),
                        "Teléfono": telefono.strip(),
                        "¿Llamó?": "✅ Sí" if llamo else "❌ No",
                        "Fecha": datetime.date.today().isoformat()
                    }
                    df = pd.concat([df, pd.DataFrame([nueva_fila])], ignore_index=True)
                    df.to_csv(ARCHIVO_DATOS, index=False)
                    st.success("✔️ Registro guardado")

            st.subheader("📄 Tus registros")
            st.dataframe(df[df["Promotor"] == nombre])
    else:
        st.error("⚠️ Este nombre no está autorizado.")
