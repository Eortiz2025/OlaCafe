import pandas as pd
import streamlit as st
import io
from datetime import datetime

st.set_page_config(page_title="Agente de Compras", page_icon="💼")
st.title("💼 Agente de Compras")

# Subida del archivo
archivo = st.file_uploader("🗂️ Sube el archivo exportado desde Erply (.xls)", type=["xls"])

# Preguntar número de días
dias_input = st.text_input("⏰ ¿Cuántos días deseas calcular para VtaProm? (Escribe un número)")

# Validar que sea un número entero positivo
if not dias_input.strip().isdigit() or int(dias_input) <= 0:
    st.warning("⚠️ Por favor escribe un número válido de días (mayor que 0) para continuar.")
    st.stop()

dias_usuario = int(dias_input)

# Calcular días transcurridos desde el 1 de enero
dias_transcurridos_2025 = (datetime.today() - datetime.today().replace(month=1, day=1)).days + 1
st.info(f"📅 Días transcurridos en 2025 hasta hoy: {dias_transcurridos_2025}")

if archivo:
    try:
        # Leer archivo Excel con encabezados a partir de la fila 4
        tabla = pd.read_excel(archivo, skiprows=3)

        if tabla.columns[0] in ("", "Unnamed: 0", "No", "Moneda"):
            tabla = tabla.iloc[:, 1:]

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

        tabla = tabla.drop(columns=[
            "Ventas netas totales ($)", "Stock (apartado)", "Stock (disponible)",
            "Ventas netas totales ($) (2)"
        ])

        tabla = tabla.rename(columns={
            "Stock (total)": "Stock",
            "Cantidad vendida": "V365",  # representa ventas 2025 acumuladas
            "Cantidad vendida (2)": "V30D"
        })

        # Filtrar productos con proveedor válido
        tabla = tabla[tabla["Proveedor"].notna()]
        tabla = tabla[tabla["Proveedor"].astype(str).str.strip() != ""]

        # Filtro opcional por proveedor
        if st.checkbox("¿Deseas calcular sólo un proveedor?", value=False):
            proveedor = st.selectbox("Selecciona el proveedor a calcular:", sorted(tabla["Proveedor"].unique()))
            tabla = tabla[tabla["Proveedor"] == proveedor]

        # Convertir columnas a numérico
        for col in ["V365", "V30D", "Stock"]:
            tabla[col] = pd.to_numeric(tabla[col], errors="coerce").fillna(0).round()

        # Cálculos clave
        tabla["VtaDiaria"] = (tabla["V365"] / dias_transcurridos_2025).round(2)
        tabla["VtaProm"] = (tabla["VtaDiaria"] * dias_usuario).round()

        max_calculado = []
        for _, row in tabla.iterrows():
            if row["V30D"] == 0:
                max_val = 0.5 * row["VtaProm"]
            else:
                intermedio = max(0.6 * row["V30D"] + 0.4 * row["VtaProm"], row["V30D"])
                max_val = min(intermedio, row["V30D"] * 1.5)
            max_calculado.append(round(max_val))

        tabla["Max"] = max_calculado
        tabla["Compra"] = (tabla["Max"] - tabla["Stock"]).clip(lower=0).round()

        # Limpiar temporal
        tabla = tabla.drop(columns=["VtaDiaria"])

        # Filtrar productos a comprar
        tabla = tabla[tabla["Compra"] > 0].sort_values("Nombre")

        # Mostrar o no proveedor
        if st.checkbox("¿Mostrar Proveedor?", value=False):
            columnas_finales = ["Código", "Código EAN", "Nombre", "Proveedor", "Stock", "V365", "VtaProm", "V30D", "Max", "Compra"]
        else:
            tabla = tabla.drop(columns=["Proveedor"])
            columnas_finales = ["Código", "Código EAN", "Nombre", "Stock", "V365", "VtaProm", "V30D", "Max", "Compra"]

        tabla = tabla[columnas_finales]

        st.success("✅ Archivo procesado correctamente")
        st.dataframe(tabla)

        # Exportar a Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            tabla.to_excel(writer, index=False, sheet_name='Compra del día')
            worksheet = writer.sheets['Compra del día']
            worksheet.freeze_panes = worksheet['A2']

        st.download_button(
            label="📄 Descargar Excel",
            data=output.getvalue(),
            file_name="Compra del día.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # Productos calientes
        st.subheader("🔥 Top 10 Productos donde V30D supera a VtaProm (Orden alfabético)")
        calientes = tabla[tabla["V30D"] > tabla["VtaProm"]]
        if not calientes.empty:
            st.dataframe(calientes[["Código", "Nombre", "V365", "VtaProm", "V30D"]].head(10))
        else:
            st.info("✅ No hay productos con V30D mayores que VtaProm en este momento.")

    except Exception as e:
        st.error(f"❌ Error al procesar el archivo: {e}")
