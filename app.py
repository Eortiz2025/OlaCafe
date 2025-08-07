import streamlit as st
import pandas as pd
import datetime

st.set_page_config(page_title="Captura de Votantes", layout="centered")
st.title("🗳️ Registros promovidos")

# Lista fija de nombres permitidos
usuarios_validos = ["Tania", "Olga", "Emilio", "Sergio", "Juan", "Elvia", "Claudia", "admin"]

# Base de datos inicial
if "datos" not in st.session_state:
    st.session_state.datos = pd.DataFrame(columns=["Promotor", "Votante", "Teléfono", "¿Llamó?", "Fecha"])

# Ingreso simple por nombre
nombre = st.text_input("Escribe tu nombre para acceder (ej. Tania)").strip()

if nombre:
    if nombre in usuarios_validos:
        st.success(f"Bienvenido, {nombre}")

        if nombre == "admin":
            st.subheader("📊 Vista de administrador")
            st.dataframe(st.session_state.datos)
            st.download_button("📥 Descargar Excel", st.session_state.datos.to_csv(index=False).encode(), file_name="votantes.csv")
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
                    st.session_state.datos = pd.concat(
                        [st.session_state.datos, pd.DataFrame([nueva_fila])],
                        ignore_index=True
                    )
                    st.success("✔️ Registro guardado")

            st.subheader("📄 Tus registros")
            filtro = st.session_state.datos[st.session_state.datos["Promotor"] == nombre]
            st.dataframe(filtro)

    else:
        st.error("⚠️ Este nombre no está autorizado. Pide acceso al administrador.")
