import pandas as pd
import streamlit as st
import io
from datetime import datetime

st.set_page_config(page_title="Agente de Compras", page_icon="💼")
st.title("💼 Agente de Compras")

# Subida del archivo
archivo = st.file_uploader("🗂️ Sube el archivo exportado desde Erply (.xls)", type=["xls"])

# Calcular días transcurridos desde el 1 de enero
dias = (datetime.today() - datetime(datetime.today().year, 1, 1)).days + 1
st.info(f"📅 Días transcurridos en 2025 hasta hoy: {dias}")

if archivo:
    try:
        # ✅ Lectura robusta
        tabla = pd.read_html(archivo, header=3)[0]
        if tabla.columns[0] in ("", "Unnamed: 0", "No", "Moneda"):
            tabla = tabla.iloc[:, 1:]

        # Encabezados esperados
        columnas_deseadas = [
            "Código", "Código EAN", "Nombre",
            "Stock (total)", "Stock (apartado)", "Stock (disponible)",
            "Proveedor", "Cantidad vendida", "Ventas netas totales ($)",
            "Cantidad vendida (2)", "Ventas netas totales ($) (2)"
        ]

        if len(tabla.columns) >= len(columnas_deseadas):
            tabla.columns = columnas_deseadas[:len(tabla.columns)]
        else:
            st.error("❌ El archivo no tiene suficientes columnas.")
            st.stop()

        # Eliminar columnas innecesarias
        columnas_a_eliminar = [
            "Ventas netas totales ($)", "Stock (apartado)", "Stock (disponible)",
            "Ventas netas totales ($) (2)"
        ]
        tabla = tabla.drop(columns=columnas_a_eliminar)

        # Renombrar columnas
        tabla = tabla.rename(columns={
            "Stock (total)": "Stock",
            "Cantidad vendida": "V365",     # Ahora representa venta acumulada de 2025
            "Cantidad vendida (2)": "V30D"
        })

        # Filtrar productos sin proveedor
        tabla = tabla[tabla["Proveedor"].notna()]
        tabla = tabla[tabla["Proveedor"].astype(str).str.strip() != ""]

        # 👉 Calcular solo un proveedor si se desea
        calcular_proveedor = st.checkbox("¿Deseas calcular sólo un proveedor?", value=False)

        if calcular_proveedor:
            lista_proveedores = tabla["Proveedor"].dropna().unique()
            proveedor_seleccionado = st.selectbox("Selecciona el proveedor a calcular:", sorted(lista_proveedores))
            tabla = tabla[tabla["Proveedor"] == proveedor_seleccionado]

        # Convertir y limpiar columnas numéricas
        tabla["V365"] = pd.to_numeric(tabla["V365"], errors="coerce").fillna(0).round()
        tabla["V30D"] = pd.to_numeric(tabla["V30D"], errors="coerce").fillna(0).round()
        tabla["Stock"] = pd.to_numeric(tabla["Stock"], errors="coerce").fillna(0).round()

        # ✅ Cálculo ajustado a días transcurridos
        tabla["VtaDiaria"] = (tabla["V365"] / dias).round(2)
        tabla["VtaProm"] = (tabla["VtaDiaria"] * dias).round()

        max_calculado = []
        for i, row in tabla.iterrows():
            if row["V30D"] == 0:
                max_val = 0.5 * row["VtaProm"]
            else:
                intermedio = max(0.6 * row["V30D"] + 0.4 * row["VtaProm"], row["V30D"])
                max_val = min(intermedio, row["V30D"] * 1.5)
            max_calculado.append(round(max_val))

        tabla["Max"] = max_calculado
        tabla["Compra"] = (tabla["Max"] - tabla["Stock"]).clip(lower=0).round()

        # Eliminar columna temporal
        tabla = tabla.drop(columns=["VtaDiaria"])

        # Filtrar productos a comprar
        tabla = tabla[tabla["Compra"] > 0].sort_values("Nombre")

        # Mostrar proveedor si se elige
        mostrar_proveedor = st.checkbox("¿Mostrar Proveedor?", value=False)

        if mostrar_proveedor:
            columnas_finales = [
                "Código", "Código EAN", "Nombre", "Proveedor", "Stock",
                "V365", "VtaProm", "V30D", "Max", "Compra"
            ]
        else:
            tabla = tabla.drop(columns=["Proveedor"])
            columnas_finales = [
                "Código", "Código EAN", "Nombre", "Stock",
                "V365", "VtaProm", "V30D", "Max", "Compra"
            ]

        tabla = tabla[columnas_finales]

        st.success("✅ Archivo procesado correctamente")
        st.dataframe(tabla)

        # Descargar Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            tabla.to_excel(writer, index=False, sheet_name='Compra del día')
            workbook = writer.book
            worksheet = writer.sheets['Compra del día']
            worksheet.freeze_panes = worksheet['A2']

        processed_data = output.getvalue()

        st.download_button(
            label="📄 Descargar Excel",
            data=processed_data,
            file_name="Compra del día.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # 🔥 Productos donde V30D supera VtaProm
        st.subheader("🔥 Top 10 Productos donde V30D supera a VtaProm (Orden alfabético)")

        productos_calientes = tabla[tabla["V30D"] > tabla["VtaProm"]]

        if not productos_calientes.empty:
            productos_calientes = productos_calientes.sort_values("Nombre", ascending=True)
            top_productos = productos_calientes.head(10)
            columnas_a_mostrar = ["Código", "Nombre", "V365", "VtaProm", "V30D"]
            st.dataframe(top_productos[columnas_a_mostrar])
        else:
            st.info("✅ No hay productos con V30D mayores que VtaProm en este momento.")

    except Exception as e:
        st.error(f"❌ Error al procesar el archivo: {e}")
