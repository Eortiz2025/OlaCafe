import streamlit as st
import pandas as pd
import unicodedata
from datetime import datetime

# =========================
# Configuración básica
# =========================
st.set_page_config(page_title="Toma de lista", page_icon="🗳️", layout="centered")
st.title("🗳️ Toma de lista")

# =========================
# Utilidades
# =========================
def _norm(x: str) -> str:
    """Quita acentos y pasa a minúsculas para comparar."""
    x = "" if x is None else str(x)
    x = unicodedata.normalize("NFD", x)
    return "".join(c for c in x if unicodedata.category(c) != "Mn").lower()

def _title_keep_caps(s: str) -> str:
    """
    Pone título amigable: 'ANA MARIA' -> 'Ana Maria'.
    Mantiene siglas sencillas como 'XX' en mayúscula.
    """
    parts = s.strip().split()
    out = []
    for p in parts:
        if p.upper() in {"XX"}:
            out.append(p.upper())
        else:
            out.append(p.capitalize())
    return " ".join(out)

def parse_line_to_fields(line: str):
    """
    Recibe una línea con: Nombres ...  Apellido1  Apellido2
    - Últimos 2 tokens -> Apellido1, Apellido2
    - Resto -> Nombre (puede tener varios tokens)
    - Si solo hay 2 tokens, Apellido2 = ""
    - Si hay <2 tokens, se descarta
    """
    raw = line.strip()
    if not raw:
        return None
    # Separar por espacios/tabulaciones múltiples
    tokens = [t for t in raw.replace("\t", " ").split(" ") if t != ""]
    if len(tokens) < 2:
        return None  # no parseable
    if len(tokens) == 2:
        nombre = tokens[0]
        ap1 = tokens[1]
        ap2 = ""
    else:
        ap2 = tokens[-1]
        ap1 = tokens[-2]
        nombre = " ".join(tokens[:-2])

    # Normalizar visual (sin afectar búsqueda)
    nombre = _title_keep_caps(nombre)
    ap1 = _title_keep_caps(ap1)
    ap2 = _title_keep_caps(ap2)
    return nombre, ap1, ap2

def asignar_padrinos_round_robin(n, padrinos):
    """Devuelve lista de padrinos para n filas, RR sobre lista padrinos."""
    out = []
    m = len(padrinos)
    for i in range(n):
        out.append(padrinos[i % m])
    return out

# =========================
# Estado
# =========================
if "padron" not in st.session_state:
    st.session_state.padron = pd.DataFrame()  # vacío hasta cargar
if "padrinos_lista" not in st.session_state:
    st.session_state.padrinos_lista = ["Alberto", "Alma", "Edgar"]

# =========================
# Carga de padrón (pegando texto)
# =========================
with st.expander("Cargar/actualizar padrón (pegar texto)", expanded=st.session_state.padron.empty):
    st.markdown(
        "Pega **una persona por línea** con formato: `NOMBRES  APELLIDO1  APELLIDO2` "
        "(pueden ser varios nombres; separa por espacio o tabulación)."
    )
    raw_text = st.text_area(
        "Pega aquí tu lista completa",
        height=260,
        placeholder="Ejemplo:\nAARON    MIRANDA    DOMINGUEZ\nABEL     ROBLES     ESCOBOZA\nABEL EDUARDO    SANDOVAL    ZAVALA\n...",
    )

    colA, colB = st.columns([2, 1])
    with colA:
        padrinos_input = st.text_input(
            "Padrinos (separados por coma) para asignación simulada:",
            value=", ".join(st.session_state.padrinos_lista),
            help="Se asignarán en round-robin: P1, P2, P3, P1, P2, ...",
        )
    with colB:
        if st.button("Cargar lista"):
            # Actualizar padrinos
            pl = [p.strip() for p in padrinos_input.split(",") if p.strip()]
            if not pl:
                pl = ["Alberto", "Alma", "Edgar"]
            st.session_state.padrinos_lista = pl

            # Parsear líneas
            rows = []
            for ln in raw_text.splitlines():
                parsed = parse_line_to_fields(ln)
                if parsed is None:
                    continue
                nombre, ap1, ap2 = parsed
                rows.append([nombre, ap1, ap2])

            if not rows:
                st.error("No se detectaron filas válidas. Revisa el formato.")
            else:
                df = pd.DataFrame(rows, columns=["Nombre", "Apellido1", "Apellido2"])
                df.insert(0, "ID", range(1, len(df) + 1))
                df["Padrino"] = asignar_padrinos_round_robin(len(df), st.session_state.padrinos_lista)
                df["Presente"] = False
                df["Hora"] = ""
                st.session_state.padron = df.set_index("ID")
                st.success(f"Padrón cargado: {len(df)} personas.")

    # Botón para borrar padrón (reiniciar)
    if not st.session_state.padron.empty and st.button("Borrar padrón (reiniciar)"):
        st.session_state.padron = pd.DataFrame()
        st.success("Padrón eliminado. Vuelve a pegar y cargar.")
        st.stop()

# =========================
# Buscador solo por nombre
# =========================
if st.session_state.padron.empty:
    st.warning("Aún no hay padrón. Pega tu lista en el panel de arriba y pulsa **Cargar lista**.")
    st.stop()

q_nom = st.text_input("Buscar por nombre")

# =========================
# Filtrado (lista oculta si no hay búsqueda)
# =========================
padron = st.session_state.padron.copy()
if q_nom:
    padron = padron[padron["Nombre"].apply(_norm).str.contains(_norm(q_nom))]

if q_nom and not padron.empty:
    st.caption(f"Resultados: {len(padron)}")
    for id_, row in padron.iterrows():
        etiqueta = f"{row['Nombre']} {row['Apellido1']} {row['Apellido2']}".strip()
        etiqueta = etiqueta if not row['Padrino'] else f"{etiqueta} — [{row['Padrino']}]"
        chk = st.checkbox(etiqueta, value=bool(row["Presente"]), key=f"p_{id_}")
        if chk != row["Presente"]:
            st.session_state.padron.at[id_, "Presente"] = chk
            st.session_state.padron.at[id_, "Hora"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if chk else ""
            st.rerun()
elif q_nom and padron.empty:
    st.info("Sin coincidencias.")
else:
    st.info("Escribe un **nombre** para buscar.")
