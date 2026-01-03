import streamlit as st
import pandas as pd

st.set_page_config(page_title="Ventas por vendedor", layout="wide")

def leer_ventas_erply_html_xls_from_bytes(file_bytes: bytes) -> pd.DataFrame:
    # read_html acepta objeto tipo archivo (BytesIO)
    from io import BytesIO
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

    missing = [c for c in [vendedor_col, importe_col, ticket_col] if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas: {missing}. Encontradas: {list(df.columns)}")

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
    return out

st.title("Ventas por vendedor (importe con IVA + tickets)")

col1, col2 = st.columns([2, 1])
with col1:
    up = st.file_uploader("Sube el archivo de ventas (.xls de Erply)", type=["xls", "html"])

with col2:
    if st.button("Actualizar ahora"):
        st.rerun()

if up is None:
    st.info("Sube el archivo para ver la tabla.")
    st.stop()

# Clave anti-caché: el contenido del archivo
file_bytes = up.getvalue()

# NO caches aquí (o cachea usando hash de bytes)
df = leer_ventas_erply_html_xls_from_bytes(file_bytes)
tabla = resumen_por_vendedor(df)

st.subheader("Resumen")
st.dataframe(tabla, use_container_width=True)

st.download_button(
    "Descargar CSV",
    data=tabla.to_csv(index=False).encode("utf-8-sig"),
    file_name="resumen_vendedores.csv",
    mime="text/csv",
)
