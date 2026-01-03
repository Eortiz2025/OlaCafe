# app.py
import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Ventas por vendedor", layout="wide")

def leer_ventas_erply(file_bytes: bytes) -> pd.DataFrame:
    # Erply .xls suele ser HTML -> read_html
    tables = pd.read_html(BytesIO(file_bytes))
    if not tables:
        raise ValueError("No se encontraron tablas en el archivo.")
    df = tables[0].copy()

    # Aplanar encabezados multinivel
    if isinstance(df.columns, pd.MultiIndex):
        flat_cols = []
        for col in df.columns:
            name = None
            for part in reversed(col):
                part = "" if part is None else str(part)
                if part and not part.startswith("Unnamed"):
                    name = part
                    break
            flat_cols.append(name or str(col[-1]))
        df.columns = flat_cols

    # Quitar fila total si existe
    for c in ["Fecha", "Moneda", "Factura de ventas", "Creador de factura"]:
        if c in df.columns:
            df = df[df[c].astype(str).str.lower() != "total ($)"]

    # Normalizar numéricos
    for c in ["Ventas totales con IVA ($)", "Ventas netas totales ($)", "IVA 16% ($)", "Cantidad vendida"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    return df

def resumen_por_vendedor(df: pd.DataFrame) -> pd.DataFrame:
    vendedor_col = "Creador de factura"
    importe_col = "Ventas totales con IVA ($)"
    ticket_col = "Factura de ventas"

    faltan = [c for c in [vendedor_col, importe_col, ticket_col] if c not in df.columns]
    if faltan:
        raise ValueError(
            f"El archivo no trae las columnas esperadas: {faltan}\n"
            f"Columnas encontradas: {list(df.columns)}"
        )

    out = (
        df.groupby(vendedor_col, dropna=False)
          .agg(
              importe_con_iva=(importe_col, "sum"),
              tickets=(ticket_col, "nunique"),
          )
          .reset_index()
          .rename(columns={vendedor_col: "vendedor"})
          .sort_values("importe_con_iva", ascending=False)
    )

    out["importe_con_iva"] = out["importe_con_iva"].fillna(0).round(2)
    out["tickets"] = out["tickets"].fillna(0).astype(int)
    return out

# ---------------- UI ----------------
st.title("Ventas por vendedor (Importe con IVA + Tickets)")

c1, c2, c3 = st.columns([2, 1, 1])
with c1:
    up = st.file_uploader("Sube el archivo de ventas (.xls de Erply)", type=["xls", "html"])
with c2:
    if st.button("Actualizar"):
        st.rerun()
with c3:
    if st.button("Reset (limpiar todo)"):
        st.session_state.clear()
        st.rerun()

if up is None:
    st.info("Sube el archivo para ver el resumen.")
    st.stop()

# Leer SIEMPRE desde bytes (esto evita el “no se refresca”)
file_bytes = up.getvalue()

df = leer_ventas_erply(file_bytes)
tabla = resumen_por_vendedor(df)

st.subheader("Resumen")
st.dataframe(tabla, use_container_width=True)

# Descargas
csv_data = tabla.to_csv(index=False).encode("utf-8-sig")
xlsx_buffer = BytesIO()
with pd.ExcelWriter(xlsx_buffer, engine="openpyxl") as writer:
    tabla.to_excel(writer, index=False, sheet_name="Resumen")
xlsx_data = xlsx_buffer.getvalue()

d1, d2 = st.columns(2)
with d1:
    st.download_button("Descargar CSV", data=csv_data, file_name="resumen_vendedores.csv", mime="text/csv")
with d2:
    st.download_button(
        "Descargar Excel",
        data=xlsx_data,
        file_name="resumen_vendedores.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
