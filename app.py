import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="OlaCafe - Control de Inventario", layout="centered")

PRODUCTOS = ["Pan Hogaza", "Jamón Serrano", "Jamón de Pavo"]
RECETAS = {
    "Sándwich de Serrano": {"Pan Hogaza": 2, "Jamón Serrano": 1},
    "Sándwich de Pavo": {"Pan Hogaza": 2, "Jamón de Pavo": 1},
    "Toast": {"Pan Hogaza": 1},
}

# Inicializar estado
if "inventario" not in st.session_state:
    st.session_state.inventario = {p: 0 for p in PRODUCTOS}
    st.session_state.inicial = {p: 0 for p in PRODUCTOS}
    st.session_state.movimientos = []

st.title("🥪 OlaCafe | Control de Inventario Diario")

# Formulario: Inventario inicial
with st.expander("📥 Inventario inicial del día", expanded=False):
    with st.form("inventario_inicial_form"):
        st.subheader("Registrar inventario inicial")
        iniciales = {}
        for producto in PRODUCTOS:
            cantidad = st.number_input(f"{producto}", min_value=0, key=f"inicial_{producto}")
            iniciales[producto] = cantidad
        submitted = st.form_submit_button("Guardar Inventario Inicial")
        if submitted:
            for producto, cantidad in iniciales.items():
                st.session_state.inventario[producto] = cantidad
                st.session_state.inicial[producto] = cantidad
                st.session_state.movimientos.append((producto, "Inicial", cantidad))
            st.success("Inventario inicial registrado correctamente.")

# Botón: Entradas
if st.button("➕ Registrar Entradas"):
    st.subheader("Entradas del Día")
    for producto in PRODUCTOS:
        cantidad = st.number_input(f"Entraron de {producto}", min_value=0, key=f"entrada_{producto}")
        if cantidad > 0:
            st.session_state.inventario[producto] += cantidad
            st.session_state.movimientos.append((producto, "Entrada", cantidad))

# Botón: Salidas
if st.button("➖ Registrar Salidas"):
    st.subheader("Salidas por Ventas")
    for nombre, receta in RECETAS.items():
        cantidad = st.number_input(f"Vendidos: {nombre}", min_value=0, key=f"salida_{nombre}")
        if cantidad > 0:
            for producto, mult in receta.items():
                total = cantidad * mult
                st.session_state.inventario[producto] -= total
                st.session_state.movimientos.append((producto, f"Salida ({nombre})", total))

# Botón: Ver inventario actual
if st.button("📊 Dame el inventario actual"):
    st.write("### Inventario Actual")
    df_inv = pd.DataFrame(list(st.session_state.inventario.items()), columns=["Producto", "Cantidad Actual"])
    st.table(df_inv)

# Mostrar resumen final del día
st.subheader("📋 Resumen del Día")
df = pd.DataFrame(columns=["Producto", "Inicial", "Entradas", "Salidas", "Final"])
for producto in PRODUCTOS:
    inicial = st.session_state.inicial.get(producto, 0)
    entradas = sum(m[2] for m in st.session_state.movimientos if m[0] == producto and m[1] == "Entrada")
    salidas = sum(m[2] for m in st.session_state.movimientos if m[0] == producto and m[1].startswith("Salida"))
    final = st.session_state.inventario[producto]
    df.loc[len(df)] = [producto, inicial, entradas, salidas, final]

st.dataframe(df, use_container_width=True)

# Descargar CSV
if st.download_button("📥 Descargar reporte CSV", data=df.to_csv(index=False), file_name="reporte_inventario.csv"):
    st.success("Reporte generado con éxito.")
