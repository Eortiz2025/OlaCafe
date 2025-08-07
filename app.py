import streamlit as st
import pandas as pd
import datetime

st.set_page_config(page_title="Seguimiento de Promotores", layout="centered")

# Base temporal de datos
if "datos" not in st.session_state:
    st.session_state.datos = pd.DataFrame(columns=["Promotor", "Votante", "Teléfono", "¿Llamó?", "Fecha"])

# Usuarios registrados (puedes agregar más)
usuarios = {
    "admin": "adminpass"
    # Puedes agregar usuarios fijos aquí si no quieres permitir autoregistro
}

st.title("📋 Registro de Votantes")

# Registro o ingreso
st.subheader("🔐 Iniciar sesión")
usuario = st.text_input("Usuario")
clave = st.text_input("Contraseña", type="password")
entrar = st.button("Entrar")

if entrar:
    if usuario in usuarios and usuarios[usuario] == clave:
        st.session_state.usuario = usuario
    elif usuario not in usuarios:
        # Registro automático
        usuarios[usuario] = clave
        st.session_state.usuario = usuario
        st.success("🆕 Usuario registrado correctamente")
    else:
        st.error("❌ Contraseña incorrecta")

# Si está logueado
if "usuario" in st.session_state:
    usuario = st.session_state.usuario
    st.success(f"Bienvenido, {usuario}")

    with st.form("captura"):
        st.subheader("✍️ Captura de votante")
        votante = st.text_input("Nombre del votante")
        tel = st.text_input("Teléfono (opcional)")
        llamo = st.checkbox("¿Ya le llamaste?")
        guardar = st.form_submit_button("Guardar")

        if guardar:
            nueva_fila = {
                "Promotor": usuario,
                "Votante": votante,
                "Teléfono": tel,
                "¿Llamó?": "✅ Sí" if llamo else "❌ No",
                "Fecha": datetime.date.today().isoformat()
            }
            st.session_state.datos = pd.concat(
                [st.session_state.datos, pd.DataFrame([nueva_fila])],
                ignore_index=True
            )
            st.success("✔️ Guardado correctamente")

    st.subheader("📄 Tus registros")

    if usuario == "admin":
        st.dataframe(st.session_state.datos)
        st.download_button("📥 Descargar Excel", st.session_state.datos.to_csv(index=False).encode(), file_name="votantes.csv")
    else:
        filtro = st.session_state.datos[st.session_state.datos["Promotor"] == usuario]
        st.dataframe(filtro)
