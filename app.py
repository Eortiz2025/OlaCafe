import streamlit as st
import pandas as pd
import os
from datetime import datetime

st.set_page_config(page_title="OlaCafe - Control de Inventario", layout="centered")

# Estilo visual
st.markdown("""
    <style>
    .main { background-color: #fdf6f0; color: #2e2e2e; }
    .stButton > button {
        background-color: #f77f00;
        color: white;
        font-weight: bold;
        border-radius: 8px;
        padding: 0.5em 1em;
    }
    .stDownloadButton > button {
        background-color: #007f5f;
        color: white;
        font-weight: bold;
        border-radius: 8px;
    }
    .title-cafe h1 { color: #6f4e37 !important; }
    .title-azul h3 { color: #002c4c !important; }
    </style>
""", unsafe_allow_html=True)

PRODUCTOS = ["Pan Hogaza", "Jamón Serrano", "Jamón de Pavo"]
RECETAS = {
    "Sándwich de Serrano": {"Pan Hogaza": 2, "Jamón Serrano": 2},
    "Sándwich de Pavo": {"Pan Hogaza": 2, "Jamón de Pavo": 2},
    "Toast": {"Pan Hogaza": 1},
}

CSV_FILE = "inventario_actual.csv"
MOVIMIENTOS_FILE = "movimientos.csv"
KARDEX_FILE = "kardex.csv"
HOY = datetime.today().strftime("%Y-%m-%d")
HOY_MOSTRAR = datetime.today().strftime("%d %b %Y")
ARCHIVO_INICIAL = f"inicial_{HOY}.csv"

inventario_prev = {p: 0 for p in PRODUCTOS}
inventario_inicial_registrado = False

if os.path.exists(CSV_FILE):
    df_prev = pd.read_csv(CSV_FILE)
    if not df_prev.empty and "Cantidad Actual" in df_prev.columns:
        inventario_prev = dict(zip(df_prev.Producto, df_prev["Cantidad Actual"]))
    elif os.path.exists(ARCHIVO_INICIAL):
        df_inicial = pd.read_csv(ARCHIVO_INICIAL)
        inventario_prev = dict(zip(df_inicial.Producto, df_inicial.Cantidad))

if os.path.exists(MOVIMIENTOS_FILE):
    df_movimientos = pd.read_csv(MOVIMIENTOS_FILE)
    movimientos_prev = [tuple(x) for x in df_movimientos[df_movimientos["Fecha"] == HOY][["Producto", "Movimiento", "Cantidad"]].values]
    inventario_inicial_registrado = not df_movimientos[
        (df_movimientos["Fecha"] == HOY) &
        (df_movimientos["Movimiento"] == "Inicial")
    ].empty
else:
    movimientos_prev = []

if "inventario" not in st.session_state:
    st.session_state.inventario = inventario_prev.copy()
    st.session_state.inicial = inventario_prev.copy()
    st.session_state.movimientos = movimientos_prev.copy()
    st.session_state.show_inicial = True
    st.session_state.show_entradas = True
    st.session_state.show_salidas = True

st.markdown(f"<div class='title-cafe'><h1>☕ OlaCafe | Control Diario</h1></div>", unsafe_allow_html=True)

def registrar_movimiento(producto, tipo, cantidad):
    st.session_state.movimientos.append((producto, tipo, cantidad))
    fila = pd.DataFrame([[HOY, producto, tipo, cantidad]], columns=["Fecha", "Producto", "Movimiento", "Cantidad"])
    if os.path.exists(MOVIMIENTOS_FILE):
        fila.to_csv(MOVIMIENTOS_FILE, mode="a", header=False, index=False)
    else:
        fila.to_csv(MOVIMIENTOS_FILE, index=False)

def registrar_kardex(producto, movimiento, detalle, cantidad, existencia):
    nuevo = pd.DataFrame([[HOY, producto, movimiento, detalle, cantidad, existencia]],
                         columns=["Fecha", "Producto", "Movimiento", "Detalle", "Cantidad", "Existencia"])
    if os.path.exists(KARDEX_FILE):
        nuevo.to_csv(KARDEX_FILE, mode="a", header=False, index=False)
    else:
        nuevo.to_csv(KARDEX_FILE, index=False)

if st.session_state.show_inicial:
    with st.expander("📥 Inventario inicial del día", expanded=False):
        with st.form("inventario_inicial_form"):
            st.subheader("Registrar inventario inicial")
            if inventario_inicial_registrado:
                st.info("✅ El inventario inicial ya fue registrado hoy. No es posible modificarlo nuevamente.")
            iniciales = {}
            for producto in PRODUCTOS:
                cantidad = st.number_input(f"{producto}", min_value=0, key=f"inicial_{producto}")
                iniciales[producto] = cantidad
            submitted = st.form_submit_button("✅ Guardar Inventario Inicial", disabled=inventario_inicial_registrado)
            if submitted:
                df_inicial = []
                for producto, cantidad in iniciales.items():
                    st.session_state.inventario[producto] = cantidad
                    st.session_state.inicial[producto] = cantidad
                    registrar_movimiento(producto, "Inicial", cantidad)
                    registrar_kardex(producto, "Inicial", "Inventario del día", cantidad, cantidad)
                    df_inicial.append([producto, cantidad])
                pd.DataFrame(df_inicial, columns=["Producto", "Cantidad"]).to_csv(ARCHIVO_INICIAL, index=False)
                st.success("Inventario inicial registrado correctamente.")
                st.session_state.show_inicial = False

# Resto del código de entradas, salidas, resumen, descarga y borrado queda igual (sin cambios)
