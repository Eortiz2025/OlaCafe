import streamlit as st
import pandas as pd
from datetime import datetime
import unicodedata
from io import StringIO

# ----------------------------
# Configuración básica
# ----------------------------
st.set_page_config(page_title="Toma de lista – Mesa de votación", page_icon="🗳️", layout="wide")
st.title("🗳️ Toma de lista – Mesa de votación")

# ----------------------------
# Utilidades
# ----------------------------
def _now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

@st.cache_data
def _template_csv() -> bytes:
    df = pd.DataFrame({
        "ID": [1, 2, 3],
        "Nombre": ["Juan", "María", "Luis"],
        "Apellido": ["Pérez", "Gómez", "Ramírez"],
        "Sección": [101, 101, 102],
        "Folio": ["A001", "A002", "A003"],
        "Voto": [False, False, False],
        "Hora": ["", "", ""],
        "Mesa": ["", "", ""],
        "Operador": ["", "", ""],
    })
    return df.to_csv(index=False).encode("utf-8")

def _normalize(s: str) -> str:
    """Quita acentos y pasa a minúsculas para comparar."""
    if s is None:
        return ""
    s = str(s)
    s = unicodedata.normalize('NFD', s)
    s = ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn')
    return s.lower()

def _ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    # Columnas requeridas mínimas
    cols_req = ["ID", "Nombre", "Apellido"]
    for c in cols_req:
        if c not in df.columns:
            raise ValueError(f"Falta la columna obligatoria: {c}")
    # Columnas opcionales con default
    if "Sección" not in df.columns: df["Sección"] = ""
    if "Folio" not in df.columns: df["Folio"] = ""
    if "Voto" not in df.columns: df["Voto"] = False
    if "Hora" not in df.columns: df["Hora"] = ""
    if "Mesa" not in df.columns: df["Mesa"] = ""
    if "Operador" not in df.columns: df["Operador"] = ""
    # Tipos básicos
    df["Voto"] = df["Voto"].astype(bool)
    return df

# ----------------------------
# Estado
# ----------------------------
if "padron" not in st.session_state:
    st.session_state.padron = pd.DataFrame()
if "padron_path" not in st.session_state:
    st.session_state.padron_path = None

# ----------------------------
# Barra lateral: controles globales
# ----------------------------
with st.sidebar:
    st.header("⚙️ Configuración")
    mesa = st.text_input("Mesa/Urna", value=st.session_state.get("mesa", "Mesa 1"))
    operador = st.text_input("Operador", value=st.session_state.get("operador", ""))
    permitir_desmarcar = st.toggle("Permitir corrección (desmarcar)", value=False, help="Si se desactiva, una vez marcado no se puede desmarcar.")
    st.session_state.mesa = mesa
    st.session_state.operador = operador

    st.divider()
    st.caption("Plantilla CSV (encabezados requeridos: ID, Nombre, Apellido)")
    st.download_button("⬇️ Descargar plantilla CSV", data=_template_csv(), file_name="plantilla_padron.csv", mime="text/csv")

# ----------------------------
# Carga de padrón
# ----------------------------
archivo = st.file_uploader("📎 Sube padrón en CSV (UTF-8)", type=["csv"]) 
if archivo:
    try:
        df = pd.read_csv(archivo, dtype=str).fillna("")
        # Tipos: ID puede ser numérico o string, lo conservamos como string para claves
        if "ID" in df.columns:
            df["ID"] = df["ID"].astype(str)
        df = _ensure_columns(df)
        # Índice por ID para escritura rápida
        if df["ID"].duplicated().any():
            st.error("Hay IDs duplicados. Corrige el archivo para continuar.")
        else:
            df = df.set_index("ID", drop=False)
            st.session_state.padron = df
            st.success(f"Padrón cargado: {len(df)} registros.")
    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")

# ----------------------------
# Buscador
# ----------------------------
if st.session_state.padron.empty:
    st.info("Carga un padrón para iniciar.")
    st.stop()

c1, c2, c3 = st.columns([2,2,1])
with c1:
    q_nombre = st.text_input("Buscar por nombre", placeholder="Ej. Juan / Maria")
with c2:
    q_apellido = st.text_input("Buscar por apellido", placeholder="Ej. Pérez / Gómez")
with c3:
    limit = st.number_input("Máx. resultados", value=25, min_value=5, max_value=200, step=5)

# Filtro tolerante a acentos y mayúsculas
padron = st.session_state.padron.copy()
if q_nombre:
    mask = padron["Nombre"].apply(_normalize).str.contains(_normalize(q_nombre))
    padron = padron[mask]
if q_apellido:
    mask = padron["Apellido"].apply(_normalize).str.contains(_normalize(q_apellido))
    padron = padron[mask]

st.caption(f"Resultados: {len(padron)}")

# ----------------------------
# Marcar asistencia / voto
# ----------------------------

# Mostrar resumen arriba
total = len(st.session_state.padron)
marcados = int(st.session_state.padron["Voto"].sum())
pendientes = total - marcados
st.metric("Marcados", marcados)
st.metric("Pendientes", pendientes)

st.divider()

# Renderizado de filas con casillas
subset = padron.head(int(limit))
for _idx, row in subset.iterrows():
    col1, col2, col3, col4, col5 = st.columns([3,3,2,2,2])
    with col1:
        st.write(f"**{row['Nombre']} {row['Apellido']}**")
        st.caption(f"ID: {row['ID']}  •  Sección: {row['Sección']}  •  Folio: {row['Folio']}")
    with col2:
        st.write(f"Hora: {row['Hora'] if row['Hora'] else '—'}")
        st.write(f"Mesa: {row['Mesa'] if row['Mesa'] else '—'}")
    with col3:
        key_chk = f"chk_{row['ID']}"
        checked = st.checkbox("Votó", value=bool(row["Voto"]), key=key_chk)
    with col4:
        st.write("")
    with col5:
        if st.button("Marcar ahora" if not row["Voto"] else "Desmarcar", key=f"btn_{row['ID']}"):
            df = st.session_state.padron
            if not row["Voto"]:
                # Marcar
                df.at[row['ID'], "Voto"] = True
                df.at[row['ID'], "Hora"] = _now_str()
                df.at[row['ID'], "Mesa"] = st.session_state.mesa
                df.at[row['ID'], "Operador"] = st.session_state.operador
                st.toast(f"Marcado: {row['Nombre']} {row['Apellido']}")
                st.rerun()
            else:
                # Desmarcar sólo si está permitido
                if permitir_desmarcar:
                    df.at[row['ID'], "Voto"] = False
                    df.at[row['ID'], "Hora"] = ""
                    df.at[row['ID'], "Mesa"] = ""
                    # Conservamos Operador para trazabilidad
                    st.toast(f"Desmarcado: {row['Nombre']} {row['Apellido']}")
                    st.rerun()
                else:
                    st.warning("La corrección está deshabilitada en Configuración.")

# ----------------------------
# Exportación y respaldo
# ----------------------------
st.divider()
colA, colB, colC = st.columns([2,2,2])
with colA:
    csv_bytes = st.session_state.padron.to_csv(index=False).encode("utf-8")
    st.download_button("💾 Exportar CSV actual", data=csv_bytes, file_name=f"padron_actual_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", mime="text/csv")
with colB:
    only_marked = st.session_state.padron[st.session_state.padron["Voto"]]
    st.download_button("⬇️ Descargar SOLO marcados", data=only_marked.to_csv(index=False).encode("utf-8"), file_name="marcados.csv", mime="text/csv")
with colC:
    st.write("")
    st.caption("Consejo: realiza exportaciones periódicas como respaldo.")

# ----------------------------
# Vista rápida de tabla (sólo lectura)
# ----------------------------
with st.expander("Ver padrón completo (lectura)"):
    st.dataframe(st.session_state.padron, use_container_width=True, hide_index=True)
