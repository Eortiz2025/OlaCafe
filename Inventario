import streamlit as st
import pandas as pd
from datetime import datetime
import re

st.set_page_config(page_title="Control de Inventario Diario", layout="centered")

# Productos iniciales y configuración base
PRODUCTOS = ["Pan Hogaza", "Jamón Serrano", "Jamón de Pavo"]
CONVERSION_SANDWICH = {
    "sandwich de serrano": {"Pan Hogaza": 2, "Jamón Serrano": 1},
    "sandwich de pavo": {"Pan Hogaza": 2, "Jamón de Pavo": 1},
}

# Inicializar estado si no existe
if "inventario" not in st.session_state:
    st.session_state.inventario = {
        "Pan Hogaza": 1,
        "Jamón Serrano": 35,
        "Jamón de Pavo": 46,
    }
    st.session_state.movimientos = []
    st.session_state.inicial = st.session_state.inventario.copy()

st.title("📦 Control Conversacional de Inventario")

entrada = st.text_input("Escribe lo que pasó hoy (entradas, ventas, etc.)")

if st.button("Registrar") and entrada:
    texto = entrada.lower()
    movimientos = []

    # Detectar entradas usando "entraron" o "compra"
    for producto in PRODUCTOS:
        patrones = [
            f"entraron (\\d+) (?:de )?{producto.lower()}",
            f"compra (?:de )?(\\d+) (?:de )?{producto.lower()}"
        ]
        for patron in patrones:
            match = re.search(patron, texto)
            if match:
                cantidad = int(match.group(1))
                st.session_state.inventario[producto] += cantidad
                movimientos.append((producto, "Entrada", cantidad))

    # Detectar ventas por combos
    for tipo, receta in CONVERSION_SANDWICH.items():
        patron = f"vend(?:imos|ieron)? (\\d+) {tipo}"
        match = re.search(patron, texto)
        if match:
            cantidad = int(match.group(1))
            for prod, cant in receta.items():
                total = cantidad * cant
                st.session_state.inventario[prod] -= total
                movimientos.append((prod, "Salida", total))

    # Detectar ventas de toast (cada palabra "toast" cuenta como 1)
    toast_count = len(re.findall(r"\\btoast\\b", texto))
    if toast_count > 0:
        st.session_state.inventario["Pan Hogaza"] -= toast_count
        movimientos.append(("Pan Hogaza", "Salida", toast_count))

    st.session_state.movimientos.extend(movimientos)
    st.success("Movimiento registrado")

# Mostrar resumen diario
st.subheader("📋 Resumen del Día")
df = pd.DataFrame(columns=["Producto", "Inicial", "Entradas", "Salidas", "Final"])
for producto in PRODUCTOS:
    inicial = st.session_state.inicial.get(producto, 0)
    entradas = sum(m[2] for m in st.session_state.movimientos if m[0] == producto and m[1] == "Entrada")
    salidas = sum(m[2] for m in st.session_state.movimientos if m[0] == producto and m[1] == "Salida")
    final = st.session_state.inventario[producto]
    df.loc[len(df)] = [producto, inicial, entradas, salidas, final]

st.dataframe(df, use_container_width=True)

# Guardar como CSV (opcional)
if st.download_button("📥 Descargar reporte CSV", data=df.to_csv(index=False), file_name="reporte_inventario.csv"):
    st.success("Reporte generado con éxito.")

# Mostrar inventario actual
if st.button("📊 Dame el inventario actual"):
    inventario_df = pd.DataFrame(list(st.session_state.inventario.items()), columns=["Producto", "Cantidad Actual"])
    st.write("### Inventario Actual")
    st.table(inventario_df)
