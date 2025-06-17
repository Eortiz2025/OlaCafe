import pandas as pd
import streamlit as st
import io
from datetime import datetime

st.set_page_config(page_title="Agente de Compras 2025", page_icon="💼")
st.title("💼 Agente de Compras 2025")

# Subida del archivo
archivo = st.file_uploader("🗂️ Sube el archivo exportado desde Erply (.xls)", type=["xls"])

# Preguntar número de días
dias = st.text_input("⏰ ¿Cuántos días deseas calcular para VtaProm? (Escribe un número)")

# Validar que sea un número entero positivo
if not dias.strip().isdigit() or int(dias) <= 0:
    st.warning("⚠️ Por favor escribe un número válido de días (mayor que 0) para continuar.")
    st.stop()

dias = int(dias)

if archivo:
    try:
        # ✅ Lectura robusta desde HTML embebido en .xls
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

        # Renombrar columnas clave
        tabla = tabla.rename(columns={
            "Stock (total)": "Stock",
            "Cantidad vendida": "V365",
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

        # ✅ Calcular días reales (ajustando 10 días no trabajados)
        dias_transcurridos_2025 = (datetime.today() - datetime(datetime.today().year, 1, 1)).days + 1 - 10
        st.info(f"📅 Días considerados para VtaDiaria: {dias_transcurridos_2025} (ajustado por 10 no laborados)")

        tabla["VtaDiaria"] = (tabla["V365"] / dias_transcurridos_2025).round(2)
        tabla["VtaProm"] = (tabla["VtaDiaria"] * dias).round()

        # Calcular Max sugerido
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

        # Eliminar temporal
        tabla = tabla.drop(columns=["VtaDiaria"])
        tabla = tabla[tabla["Compra"] > 0].sort_values("Nombre")

        # Mostrar proveedor si se desea
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
            worksheet = writer.sheets['Compra del día']
            worksheet.freeze_panes = worksheet['A2']

        st.download_button(
            label="📄 Descargar Excel",
            data=output.getvalue(),
            file_name="Compra del día.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # 🔥 Top productos con V30D > VtaProm
        st.subheader("🔥 Top 10 Productos donde V30D supera a VtaProm (Orden alfabético)")
        productos_calientes = tabla[tabla["V30D"] > tabla["VtaProm"]]
        if not productos_calientes.empty:
            st.dataframe(productos_calientes[["Código", "Nombre", "V365", "VtaProm", "V30D"]].head(10))
        else:
            st.info("✅ No hay productos con V30D mayores que VtaProm en este momento.")

    except Exception as e:
        st.error(f"❌ Error al procesar el archivo: {e}")
