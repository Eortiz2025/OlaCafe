import streamlit as st
import pandas as pd
import datetime

# -------------------------------
# Configuración inicial
st.set_page_config(page_title="Control de Promotores", layout="centered")
st.title("📋 Registro de Votantes por Promotor")

# -------------------------------
# Base de datos en memoria (o en archivo si lo deseas guardar)
if "usuarios" not in st.session_state:
    st.session_state.usuarios = {}

if "datos" not in st.session_state:
    st.session_state.datos = pd.DataFrame(columns=["Promotor", "Votante", "Teléfono", "¿Llamó?", "Fecha"])

# -------------------------------
# Función para validar usuarios
def autenticar(usuario, contraseña):
    if usuario in st.session_state.usuarios:
        return st.session_state.usuarios[usuario] == contraseña
    return False

# -------------------------------
# Registro o inicio de sesión
modo = st.sidebar.radio("Acceso", ["🔐 Iniciar sesión", "🆕 Registrarse"])

if modo == "🆕 Registrarse":
    st.sidebar.subheader("🆕 Registro")
    nuevo_usuario = st.sidebar.text_input("Nombre de promotor")
    nueva_contraseña = st.sidebar.text_input("Contraseña", type="password")
    if st.sidebar.button("Crear cuenta"):
        if nuevo_usuario in st.session_state.usuarios:
            st.sidebar.warning("⚠️ Este usuario ya existe.")
        elif nuevo_usuario.strip() == "":
            st.sidebar.warning("⚠️ Nombre inválido.")
        else:
            st.session_state.usuarios[nuevo_usuario] = nueva_contraseña
            st.sidebar.success("✅ Usuario registrado. Ahora inicia sesión.")

else:
    st.sidebar.subheader("🔐 Inicio de sesión")
    usuario = st.sidebar.text_input("Usuario")
    contraseña = st.sidebar.text_input("Contraseña", type="password")
    if st.sidebar.button("Entrar"):
        if autenticar(usuario, contraseña):
            st.session_state.usuario_activo = usuario
            st.sidebar.success(f"Bienvenido {usuario}")
        else:
            st.sidebar.error("Acceso denegado.")

# -------------------------------
# App principal si hay sesión iniciada
if "usuario_activo" in st.session_state:

    usuario = st.session_state.usuario_activo

    st.subheader(f"Bienvenido: {usuario}")

    if usuario == "admin":
        st.success("🔒 Vista de administrador")
        st.dataframe(st.session_state.datos)
        if st.download_button("📥 Exportar a Excel", st.session_state.datos.to_csv(index=False).encode(), file_name="votantes.csv"):
            st.success("Archivo exportado.")
    else:
        st.subheader("📌 Captura de votantes")

        with st.form("formulario"):
            nombre_votante = st.text_input("Nombre del votante")
            telefono = st.text_input("Teléfono (opcional)")
            llamado = st.checkbox("¿Ya le llamaste?")
            enviar = st.form_submit_button("Guardar")

            if enviar:
                nueva_fila = {
                    "Promotor": usuario,
                    "Votante": nombre_votante,
                    "Teléfono": telefono,
                    "¿Llamó?": "✅ Sí" if llamado else "❌ No",
                    "Fecha": datetime.date.today().isoformat()
                }
                st.session_state.datos = pd.concat(
                    [st.session_state.datos, pd.DataFrame([nueva_fila])],
                    ignore_index=True
                )
                st.success("✅ Registro guardado.")

        st.subheader("📋 Tus registros")
        registros = st.session_state.datos
        st.dataframe(registros[registros["Promotor"] == usuario])
