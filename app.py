import pandas as pd

# Archivo (ajusta si cambia el nombre/ruta)
PATH = r"/mnt/data/Ventas  03-01-2026-03-01-2026.xls"

def leer_ventas_erply_html_xls(path: str) -> pd.DataFrame:
    # Muchos "xls" de Erply realmente son HTML con tabla
    tables = pd.read_html(path)
    if not tables:
        raise ValueError("No se encontraron tablas en el archivo.")

    df = tables[0].copy()

    # Aplanar encabezados multinivel (tomar el último nivel útil)
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

    # Quitar fila de totales (Erply suele poner "total ($)" al final)
    for c in ["Fecha", "Moneda", "Factura de ventas", "Creador de factura"]:
        if c in df.columns:
            df = df[df[c].astype(str).str.lower() != "total ($)"]

    # Normalizar numéricos
    num_cols = [
        "Ventas totales con IVA ($)",
        "Ventas netas totales ($)",
        "IVA 16% ($)",
        "Cantidad vendida",
    ]
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    return df

def resumen_por_vendedor(df: pd.DataFrame) -> pd.DataFrame:
    vendedor_col = "Creador de factura"
    importe_col = "Ventas totales con IVA ($)"
    ticket_col = "Factura de ventas"

    missing = [c for c in [vendedor_col, importe_col, ticket_col] if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas necesarias: {missing}. Columnas encontradas: {list(df.columns)}")

    out = (
        df.groupby(vendedor_col, dropna=False)
          .agg(
              importe_con_iva=(importe_col, "sum"),
              tickets=(ticket_col, lambda s: s.nunique()),
          )
          .reset_index()
          .rename(columns={vendedor_col: "vendedor"})
          .sort_values("importe_con_iva", ascending=False)
    )

    return out

if __name__ == "__main__":
    df = leer_ventas_erply_html_xls(PATH)
    tabla = resumen_por_vendedor(df)

    # Mostrar
    print(tabla.to_string(index=False))

    # Guardar (opcional)
    tabla.to_excel("/mnt/data/resumen_vendedores_03-01-2026.xlsx", index=False)
    tabla.to_csv("/mnt/data/resumen_vendedores_03-01-2026.csv", index=False, encoding="utf-8-sig")
