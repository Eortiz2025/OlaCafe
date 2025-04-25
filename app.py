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

# Cargar inventario actual
inventario_actual = {p: 0 for p in PRODUCTOS}
if os.path.exists(CSV_FILE):
    df_actual = pd.read_csv(CSV_FILE)
    if not df_actual.empty and "Cantidad Actual" in df_actual.columns:
        inventario_actual = dict(zip(df_actual.Producto, df_actual["Cantidad Actual"]))

# Cargar inventario inicial
inventario_inicial = {p: 0 for p in PRODUCTOS}
if os.path.exists(ARCHIVO_INICIAL):
    df_inicial = pd.read_csv(ARCHIVO_INICIAL)
    if not df_inicial.empty:
        inventario_inicial = dict(zip(df_inicial.Producto, df_inicial.Cantidad))

# Cargar movimientos previos del día
if os.path.exists(MOVIMIENTOS_FILE):
    df_movimientos = pd.read_csv(MOVIMIENTOS_FILE)
    movimientos_prev = [tuple(x) for x in df_movimientos[df_movimientos["Fecha"] == HOY][["Producto", "Movimiento", "Cantidad"]].values]
else:
    movimientos_prev = []

# Inicializar sesión
if "inventario" not in st.session_state:
    st.session_state.inventario = inventario_actual.copy()
if "inicial" not in st.session_state:
    st.session_state.inicial = inventario_inicial.copy()
if "movimientos" not in st.session_state:
    st.session_state.movimientos = movimientos_prev.copy()
if "movimientos_aplicados" not in st.session_state:
    for producto, tipo, cantidad in movimientos_prev:
        cantidad = int(cantidad)
        if tipo == "Entrada":
            st.session_state.inventario[producto] += cantidad
        elif tipo.startswith("Salida"):
            st.session_state.inventario[producto] -= cantidad
        elif tipo == "Inicial":
            st.session_state.inventario[producto] = cantidad
    st.session_state.movimientos_aplicados = True
if "show_inicial" not in st.session_state:
    st.session_state.show_inicial = True
if "show_entradas" not in st.session_state:
    st.session_state.show_entradas = True
if "show_salidas" not in st.session_state:
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

def guardar_inventario_actual_si_cambios():
    actual_df = pd.DataFrame(list(st.session_state.inventario.items()), columns=["Producto", "Cantidad Actual"])
    if not os.path.exists(CSV_FILE):
        actual_df.to_csv(CSV_FILE, index=False)
        return
    previo_df = pd.read_csv(CSV_FILE)
    if not actual_df.equals(previo_df):
        actual_df.to_csv(CSV_FILE, index=False)

# Inventario inicial
if st.session_state.show_inicial:
    with st.expander("📥 Inventario inicial del día", expanded=False):
        with st.form("inventario_inicial_form"):
            st.subheader("Registrar inventario inicial")
            iniciales = {}
            inventario_existente = os.path.exists(ARCHIVO_INICIAL)

            for producto in PRODUCTOS:
                cantidad = st.number_input(f"{producto}", min_value=0, key=f"inicial_{producto}", disabled=inventario_existente)
                iniciales[producto] = cantidad

            submitted = st.form_submit_button("✅ Guardar Inventario Inicial", disabled=inventario_existente)

            if inventario_existente:
                st.info("✅ El inventario inicial del día ya fue capturado.")
            elif submitted:
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

# Entradas
if st.session_state.show_entradas:
    with st.expander("➕ Registrar Entradas", expanded=False):
        with st.form("entradas_form"):
            st.subheader("Entradas del Día")
            entradas = {}
            for producto in PRODUCTOS:
                cantidad = st.number_input(f"Entraron de {producto}", min_value=0, key=f"entrada_{producto}")
                entradas[producto] = cantidad
            submitted = st.form_submit_button("✅ Guardar Entradas")
            if submitted:
                for producto, cantidad in entradas.items():
                    if cantidad > 0:
                        st.session_state.inventario[producto] += cantidad
                        registrar_movimiento(producto, "Entrada", cantidad)
                        registrar_kardex(producto, "Entrada", "Reposición", cantidad, st.session_state.inventario[producto])
                guardar_inventario_actual_si_cambios()
                st.success("Entradas registradas correctamente.")
                st.session_state.show_entradas = False

# Salidas
if st.session_state.show_salidas:
    with st.expander("➖ Registrar Salidas", expanded=False):
        with st.form("salidas_form"):
            st.subheader("Salidas por Ventas")
            salidas = {}
            for nombre, receta in RECETAS.items():
                cantidad = st.number_input(f"Vendidos: {nombre}", min_value=0, key=f"salida_{nombre}")
                salidas[nombre] = cantidad
            submitted = st.form_submit_button("✅ Guardar Salidas")
            if submitted:
                for nombre, cantidad in salidas.items():
                    if cantidad > 0:
                        puede_salir = True
                        for producto, mult in RECETAS[nombre].items():
                            total = cantidad * mult
                            if st.session_state.inventario[producto] < total:
                                st.warning(f"No hay suficiente {producto} para {nombre}.")
                                puede_salir = False
                                break
                        if puede_salir:
                            for producto, mult in RECETAS[nombre].items():
                                total = cantidad * mult
                                st.session_state.inventario[producto] -= total
                                registrar_movimiento(producto, f"Salida - {nombre}", total)
                                registrar_kardex(producto, "Salida", nombre, total, st.session_state.inventario[producto])
                guardar_inventario_actual_si_cambios()
                st.success("Salidas registradas correctamente.")
                st.session_state.show_salidas = False

# Resumen
st.markdown(f"<div class='title-azul'><h3>📋 Resumen del Día - {HOY_MOSTRAR}</h3></div>", unsafe_allow_html=True)
df = pd.DataFrame(columns=["Producto", "Inicial", "Entradas", "Salidas", "Final"])
for producto in PRODUCTOS:
    inicial = st.session_state.inicial.get(producto, 0)
    entradas = sum(int(m[2]) for m in st.session_state.movimientos if m[0] == producto and m[1] == "Entrada")
    salidas = sum(int(m[2]) for m in st.session_state.movimientos if m[0] == producto and m[1].startswith("Salida"))
    final = inicial + entradas - salidas
    df.loc[len(df)] = [producto, inicial, entradas, salidas, final]

st.dataframe(df, use_container_width=True)

df_mov = pd.DataFrame(st.session_state.movimientos, columns=["Producto", "Movimiento", "Cantidad"])
with st.expander("🧾 Ver todos los movimientos registrados"):
    st.dataframe(df_mov, use_container_width=True)

if st.download_button("📥 Descargar reporte CSV", data=df.to_csv(index=False), file_name="reporte_inventario.csv"):
    st.success("Reporte generado con éxito.")

# Borrado protegido
with st.expander("🗑️ Borrar datos del día"):
    clave = st.text_input("Ingrese clave de administrador para continuar:", type="password")
    if clave == "1001":
        borrar = st.date_input("Seleccionar fecha a borrar", value=datetime.today())
        fecha_str = borrar.strftime("%Y-%m-%d")
        if st.button("🚨 Borrar inventario inicial, entradas, salidas y movimientos de ese día"):
            if os.path.exists(MOVIMIENTOS_FILE):
                df_mov = pd.read_csv(MOVIMIENTOS_FILE)
                df_mov = df_mov[df_mov["Fecha"] != fecha_str]
                df_mov.to_csv(MOVIMIENTOS_FILE, index=False)
            if os.path.exists(KARDEX_FILE):
                df_kardex = pd.read_csv(KARDEX_FILE)
                df_kardex = df_kardex[df_kardex["Fecha"] != fecha_str]
                df_kardex.to_csv(KARDEX_FILE, index=False)
            archivo_inicial = f"inicial_{fecha_str}.csv"
            if os.path.exists(archivo_inicial):
                os.remove(archivo_inicial)
            if fecha_str == HOY:
                for key in ["inventario", "inicial", "movimientos"]:
                    st.session_state[key] = {p: 0 for p in PRODUCTOS} if key != "movimientos" else []
                pd.DataFrame(PRODUCTOS, columns=["Producto"]).assign(**{"Cantidad Actual": 0}).to_csv(CSV_FILE, index=False)
            st.success(f"Datos del día {fecha_str} borrados correctamente.")
    elif clave != "":
        st.error("Clave incorrecta. No tienes permiso para borrar datos.")
