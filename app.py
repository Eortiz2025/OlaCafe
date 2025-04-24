import os
import pandas as pd
import streamlit as st
from datetime import datetime

HOY = datetime.today().strftime("%Y-%m-%d")
HOY_MOSTRAR = datetime.today().strftime("%d %b %Y")
CSV_FILE = "inventario_actual.csv"
MOVIMIENTOS_FILE = "movimientos.csv"
KARDEX_FILE = "kardex.csv"
ARCHIVO_INICIAL = f"inicial_{HOY}.csv"

class InventarioManager:
    def __init__(self, productos, recetas):
        self.productos = productos
        self.recetas = recetas
        self._init_estado()

    def _init_estado(self):
        inventario = {p: 0 for p in self.productos}
        if os.path.exists(CSV_FILE):
            df_prev = pd.read_csv(CSV_FILE)
            inventario = dict(zip(df_prev.Producto, df_prev["Cantidad Actual"]))
        movimientos = []
        if os.path.exists(MOVIMIENTOS_FILE):
            df_mov = pd.read_csv(MOVIMIENTOS_FILE)
            movimientos = [tuple(x) for x in df_mov[df_mov["Fecha"] == HOY][["Producto", "Movimiento", "Cantidad"]].values]

        st.session_state.setdefault("inventario", inventario.copy())
        st.session_state.setdefault("inicial", inventario.copy())
        st.session_state.setdefault("movimientos", movimientos.copy())
        st.session_state.setdefault("show_inicial", True)
        st.session_state.setdefault("show_entradas", True)
        st.session_state.setdefault("show_salidas", True)

    def cargar_inicial(self):
        if st.session_state.show_inicial:
            with st.expander("📥 Inventario inicial del día", expanded=False):
                with st.form("inventario_inicial_form"):
                    st.subheader("Registrar inventario inicial")
                    iniciales = {p: st.number_input(f"{p}", min_value=0, key=f"inicial_{p}") for p in self.productos}
                    if st.form_submit_button("✅ Guardar Inventario Inicial"):
                        for producto, cantidad in iniciales.items():
                            st.session_state.inventario[producto] = cantidad
                            st.session_state.inicial[producto] = cantidad
                            self._registrar_movimiento(producto, "Inicial", cantidad)
                            self._registrar_kardex(producto, "Inicial", "Inventario del día", cantidad, cantidad)
                        pd.DataFrame(iniciales.items(), columns=["Producto", "Cantidad"]).to_csv(ARCHIVO_INICIAL, index=False)
                        st.success("Inventario inicial registrado correctamente.")
                        st.session_state.show_inicial = False

    def registrar_entradas(self):
        if st.session_state.show_entradas:
            with st.expander("➕ Registrar Entradas", expanded=False):
                with st.form("entradas_form"):
                    st.subheader("Entradas del Día")
                    entradas = {p: st.number_input(f"Entraron de {p}", min_value=0, key=f"entrada_{p}") for p in self.productos}
                    if st.form_submit_button("✅ Guardar Entradas"):
                        for producto, cantidad in entradas.items():
                            if cantidad > 0:
                                st.session_state.inventario[producto] += cantidad
                                self._registrar_movimiento(producto, "Entrada", cantidad)
                                self._registrar_kardex(producto, "Entrada", "Reposición", cantidad, st.session_state.inventario[producto])
                        st.success("Entradas registradas correctamente.")
                        st.session_state.show_entradas = False

    def registrar_salidas(self):
        if st.session_state.show_salidas:
            with st.expander("➖ Registrar Salidas", expanded=False):
                with st.form("salidas_form"):
                    st.subheader("Salidas por Ventas")
                    salidas = {n: st.number_input(f"Vendidos: {n}", min_value=0, key=f"salida_{n}") for n in self.recetas}
                    if st.form_submit_button("✅ Guardar Salidas"):
                        for nombre, cantidad in salidas.items():
                            if cantidad > 0:
                                for producto, mult in self.recetas[nombre].items():
                                    total = cantidad * mult
                                    if st.session_state.inventario[producto] < total:
                                        st.warning(f"No hay suficiente {producto} para {nombre}. Salida omitida.")
                                        break
                                else:
                                    for producto, mult in self.recetas[nombre].items():
                                        total = cantidad * mult
                                        st.session_state.inventario[producto] -= total
                                        self._registrar_movimiento(producto, f"Salida - {nombre}", total)
                                        self._registrar_kardex(producto, "Salida", nombre, total, st.session_state.inventario[producto])
                        st.success("Salidas registradas correctamente.")
                        st.session_state.show_salidas = False

    def guardar_inventario(self):
        pd.DataFrame(list(st.session_state.inventario.items()), columns=["Producto", "Cantidad Actual"]).to_csv(CSV_FILE, index=False)

    def mostrar_resumen(self):
        st.markdown(f"<div class='title-azul'><h3>📋 Resumen del Día - {HOY_MOSTRAR}</h3></div>", unsafe_allow_html=True)
        df = pd.DataFrame(columns=["Producto", "Inicial", "Entradas", "Salidas", "Final"])
        for producto in self.productos:
            inicial = st.session_state.inicial.get(producto, 0)
            entradas = sum(int(m[2]) for m in st.session_state.movimientos if m[0] == producto and m[1] == "Entrada")
            salidas = sum(int(m[2]) for m in st.session_state.movimientos if m[0] == producto and m[1].startswith("Salida"))
            final = st.session_state.inventario[producto]
            df.loc[len(df)] = [producto, inicial, entradas, salidas, final]
        st.dataframe(df, use_container_width=True)
        st.session_state["resumen_df"] = df

    def mostrar_movimientos(self):
        df_mov = pd.DataFrame(st.session_state.movimientos, columns=["Producto", "Movimiento", "Cantidad"])
        with st.expander("🧾 Ver todos los movimientos registrados"):
            st.dataframe(df_mov, use_container_width=True)

    def descargar_reporte(self):
        df = st.session_state.get("resumen_df", None)
        if df is not None:
            if st.download_button("📥 Descargar reporte CSV", data=df.to_csv(index=False), file_name="reporte_inventario.csv"):
                st.success("Reporte generado con éxito.")

    def reiniciar_dia(self):
        for k in ["inventario", "inicial", "movimientos", "show_inicial", "show_entradas", "show_salidas"]:
            if k in st.session_state:
                del st.session_state[k]

    def _registrar_movimiento(self, producto, tipo, cantidad):
        st.session_state.movimientos.append((producto, tipo, cantidad))
        fila = pd.DataFrame([[HOY, producto, tipo, cantidad]], columns=["Fecha", "Producto", "Movimiento", "Cantidad"])
        if os.path.exists(MOVIMIENTOS_FILE):
            fila.to_csv(MOVIMIENTOS_FILE, mode="a", header=False, index=False)
        else:
            fila.to_csv(MOVIMIENTOS_FILE, index=False)

    def _registrar_kardex(self, producto, movimiento, detalle, cantidad, existencia):
        nuevo = pd.DataFrame([[HOY, producto, movimiento, detalle, cantidad, existencia]],
                             columns=["Fecha", "Producto", "Movimiento", "Detalle", "Cantidad", "Existencia"])
        if os.path.exists(KARDEX_FILE):
            nuevo.to_csv(KARDEX_FILE, mode="a", header=False, index=False)
        else:
            nuevo.to_csv(KARDEX_FILE, index=False)
