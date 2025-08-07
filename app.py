import streamlit as st
import pandas as pd
import datetime
import os

st.set_page_config(page_title="Registro de mi red", layout="centered")
st.title("🗳️ Registro de mi red")

ARCHIVO_DATOS = "votantes.csv"
usuarios_validos = ["Tania", "Olga", "Emilio", "Sergio", "Juan", "Elvia", "Claudia", "admin"]

# Cargar base de datos o crear nueva
if os.path.exists(ARCHIVO_DATOS):
    df = pd.read_csv(ARCHIVO_DATOS)
else:
    df = pd.DataFrame(columns=["Promotor", "Votante", "¿Ya le llamaste?", "Fecha"])

# Entrada de usuario
nombre = st.text_input("Escribe tu nombre para acceder (ej. Tania)").strip()

if nombre:
    if nombre in usuarios_validos:
        st.success(f"Hola, {nombre}")

        if nombre == "admin":
            st.subheader("📊 Vista de administrador")
            st.dataframe(df)
            st.download_button("📥 Descargar Excel", df.to_csv(index=False).encode(), file_name="votantes.csv")

        else:
            st.subheader("✍️ Captura contacto")

            with st.form("formulario"):
                votante = st.text_input("Nombre del contacto")
                llamo = st.checkbox("¿Ya le llamaste?")
                enviar = st.form_submit_button("Guardar")

                if enviar and votante.strip():
                    nueva_fila = {
                        "Promotor": nombre,
                        "Votante": votante.strip(),
                        "¿Ya le llamaste?": "✅ Sí" if llamo else "❌ No",
                        "Fecha": datetime.date.today().isoformat()
                    }
                    df = pd.concat([df, pd.DataFrame([nueva_fila])], ignore_index=True)
                    df.to_csv(ARCHIVO_DATOS, index=False)
                    st.success("✔️ Registro guardado")

            st.subheader("📄 Tus registros")

            # Mostrar registros propios
            registros = df[df["Promotor"] == nombre].reset_index(drop=True)

            for i, fila in registros.iterrows():
                col1, col2 = st.columns([3, 1])
                col1.markdown(f"**{fila['Votante']}** — {fila['¿Ya le llamaste?']} — {fila['Fecha']}")
                if fila["¿Ya le llamaste?"] == "❌ No":
                    if col2.button("Marcar como llamado", key=f"llamar_{i}"):
                        idx_real = df[(df["Promotor"] == nombre) & (df["Votante"] == fila["Votante"]) & (df["Fecha"] == fila["Fecha"])].index[0]
                        df.at[idx_real, "¿Ya le llamaste?"] = "✅ Sí"
                        df.to_csv(ARCHIVO_DATOS, index=False)
                        st.experimental_rerun()
                else:
                    col2.markdown("✅ Ya llamado")

    else:
        st.error("⚠️ Este nombre no está autorizado.")
