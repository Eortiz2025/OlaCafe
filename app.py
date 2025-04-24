import streamlit as st
import pandas as pd

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

# Inicializar control de formularios
if "show_inicial" not in st.session_state:
    st.session_state.show_inicial = True
if "show_entradas" not in st.session_state:
    st.session_state.show_entradas = True
if "show_salidas" not in st.session_state:
    st.session_state.show_salidas = True

st.title("🥪 OlaCafe | Control de Inventario Diario")

# Formulario: Inventario inicial
if st.session_state.show_inicial:
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
                st.session_state.show_inicial = False

# Formulario: Entradas
if st.session_state.show_entradas:
    with st.expander("➕ Registrar Entradas", expanded=False):
        with st.form("entradas_form"):
            st.subheader("Entradas del Día")
            entradas = {}
            for producto in PRODUCTOS:
                cantidad = st.number_input(f"Entraron de {producto}", min_value=0, key=f"entrada_{producto}")
                entradas[producto] = cantidad
            submitted = st.form_submit_button("Guardar Entradas")
            if submitted:
                for producto, cantidad in entradas.items():
                    if cantidad > 0:
                        st.session_state.inventario[producto] += cantidad
                        st.session_state.movimientos.append((producto, "Entrada", cantidad))
                st.success("Entradas registradas correctamente.")
                st.session_state.show_entradas = False

# Formulario: Salidas
if st.session_state.show_salidas:
    with st.expander("➖ Registrar Salidas", expanded=False):
        with st.form("salidas_form"):
            st.subheader("Salidas por Ventas")
            salidas = {}
            for nombre, receta in RECETAS.items():
                cantidad = st.number_input(f"Vendidos: {nombre}", min_value=0, key=f"salida_{nombre}")
                salidas[nombre] = cantidad
            submitted = st.form_submit_button("Guardar Salidas")
            if submitted:
                for nombre, cantidad in salidas.items():
                    if cantidad > 0:
                        for producto, mult in RECETAS[nombre].items():
                            total = cantidad * mult
                            st.session_state.inventario[producto] -= total
                            st.session_state.movimientos.append((producto, f"Salida ({nombre})", total))
                st.success("Salidas registradas correctamente.")
                st.session_state.show_salidas = False

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
