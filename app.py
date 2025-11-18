# archivo: moviliza_7.py

import streamlit as st
import pandas as pd
import numpy as np
from io import StringIO

st.set_page_config(page_title="Moviliza 7", page_icon="✅", layout="wide")
st.title("✅ Moviliza 7")
st.caption("Red de movilización por distritos 11 al 17, con span de control máximo 7.")

# --------- Configuración básica ---------
DISTRICTOS = [11, 12, 13, 14, 15, 16, 17]
ROLES = ["General", "Coordinador distrito", "Jefe", "Movilizable"]
NIVELES_APOYO = ["No contactado", "A favor", "Indeciso", "En contra"]
SI_NO_ND = ["ND", "Sí", "No"]

COLUMNAS = [
    "id",
    "nombre",
    "telefono",
    "distrito",
    "rol",
    "responsable",
    "nivel_apoyo",
    "confirma_voto",
    "ya_voto",
    "requiere_transporte",
    "notas",
]

TIPOS_DEFECTO = {
    "id": "Int64",
    "nombre": "string",
    "telefono": "string",
    "distrito": "Int64",
    "rol": "string",
    "responsable": "string",
    "nivel_apoyo": "string",
    "confirma_voto": "string",
    "ya_voto": "string",
    "requiere_transporte": "string",
    "notas": "string",
}


def crear_df_vacio():
    df = pd.DataFrame(columns=COLUMNAS)
    for col, t in TIPOS_DEFECTO.items():
        df[col] = df[col].astype(t)
    return df


def asegurar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    # Añadir columnas faltantes
    for col in COLUMNAS:
        if col not in df.columns:
            df[col] = pd.Series(pd.NA, index=df.index)
    df = df[COLUMNAS]
    # Tipos
    for col, t in TIPOS_DEFECTO.items():
        try:
            df[col] = df[col].astype(t)
        except Exception:
            pass
    return df


if "df" not in st.session_state:
    st.session_state.df = crear_df_vacio()

df = st.session_state.df

# --------- Sidebar: carga / filtros / exportación ---------
st.sidebar.header("Datos")

uploaded = st.sidebar.file_uploader(
    "Cargar CSV existente", type=["csv"], help="Base con estructura similar (columnas compatibles)."
)
if uploaded is not None:
    try:
        df_subido = pd.read_csv(uploaded)
        df_subido = asegurar_columnas(df_subido)
        st.session_state.df = df_subido
        df = st.session_state.df
        st.sidebar.success("Archivo cargado correctamente.")
    except Exception as e:
        st.sidebar.error(f"Error al leer el CSV: {e}")

st.sidebar.markdown("---")

st.sidebar.subheader("Filtros rápidos")

f_distrito = st.sidebar.multiselect(
    "Distritos", DISTRICTOS, default=DISTRICTOS
)
f_rol = st.sidebar.multiselect(
    "Roles", ROLES, default=ROLES
)

# responsables dinámicos
responsables_opts = sorted(list(df["responsable"].dropna().unique()))
f_responsable = st.sidebar.multiselect(
    "Responsable directo", responsables_opts, default=[]
)

st.sidebar.markdown("---")

csv_export = df.to_csv(index=False).encode("utf-8")
st.sidebar.download_button(
    "⬇️ Descargar CSV completo",
    data=csv_export,
    file_name="moviliza7_base.csv",
    mime="text/csv",
)

# --------- Filtro global aplicado ---------
mascara = df["distrito"].isin(f_distrito) & df["rol"].isin(f_rol)
if f_responsable:
    mascara = mascara & df["responsable"].isin(f_responsable)

df_filtrado = df[mascara].copy()

# --------- Tabs ---------
tab_tablero, tab_personas, tab_captura, tab_diaD, tab_estructura = st.tabs(
    ["Tablero", "Personas", "Captura rápida", "Día D", "Estructura"]
)

# ========= TABLERO =========
with tab_tablero:
    st.subheader("Resumen general")

    total_registros = len(df)
    total_movilizables = (df["rol"] == "Movilizable").sum()
    total_contactados = (df["nivel_apoyo"] != "No contactado").sum()
    total_a_favor = (df["nivel_apoyo"] == "A favor").sum()
    total_indecisos = (df["nivel_apoyo"] == "Indeciso").sum()
    total_ya_voto = (df["ya_voto"] == "Sí").sum()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Personas en base", total_registros)
    c2.metric("Movilizables (rol)", total_movilizables)
    c3.metric("Contactados", total_contactados)
    c4.metric("Ya votaron (marcados)", total_ya_voto)

    st.markdown("### Resumen por distrito (solo movilizables)")

    df_m = df[df["rol"] == "Movilizable"].copy()
    if not df_m.empty:
        resumen = (
            df_m.groupby("distrito")
            .agg(
                total=("id", "count"),
                a_favor=("nivel_apoyo", lambda s: (s == "A favor").sum()),
                indecisos=("nivel_apoyo", lambda s: (s == "Indeciso").sum()),
                confirma=("confirma_voto", lambda s: (s == "Sí").sum()),
                ya_voto=("ya_voto", lambda s: (s == "Sí").sum()),
            )
            .reset_index()
        )
        st.dataframe(resumen, use_container_width=True)
    else:
        st.info("Aún no hay movilizables registrados.")

# ========= PERSONAS =========
with tab_personas:
    st.subheader("Listado filtrado")

    st.caption(
        "Se muestran las personas según los filtros de la barra lateral. "
        "Si necesitas editar, hazlo en el CSV y vuelve a cargar."
    )

    st.dataframe(df_filtrado, use_container_width=True)

# ========= CAPTURA RÁPIDA =========
with tab_captura:
    st.subheader("Alta de persona en la red")

    with st.form("form_alta_persona"):
        c1, c2 = st.columns(2)
        with c1:
            nombre = st.text_input("Nombre")
            telefono = st.text_input("Teléfono / WhatsApp")
            distrito = st.selectbox("Distrito", DISTRICTOS)
            rol = st.selectbox("Rol", ROLES)
        with c2:
            responsable = st.text_input(
                "Responsable directo",
                help="Nombre de la persona de la que depende en la cadena de mando.",
            )
            nivel_apoyo = st.selectbox("Nivel de apoyo", NIVELES_APOYO, index=0)
            confirma_voto = st.selectbox("¿Confirma que votará?", SI_NO_ND, index=0)
            requiere_transporte = st.selectbox("¿Requiere transporte?", SI_NO_ND, index=0)

        notas = st.text_area("Notas", height=80)

        enviado = st.form_submit_button("Guardar")

    if enviado:
        if not nombre:
            st.error("Falta el nombre.")
        else:
            if df["id"].isna().all():
                nuevo_id = 1
            else:
                max_id = df["id"].max()
                nuevo_id = int(max_id) + 1 if pd.notna(max_id) else 1

            nueva_fila = {
                "id": nuevo_id,
                "nombre": nombre,
                "telefono": telefono,
                "distrito": distrito,
                "rol": rol,
                "responsable": responsable,
                "nivel_apoyo": nivel_apoyo,
                "confirma_voto": confirma_voto,
                "ya_voto": "No",
                "requiere_transporte": requiere_transporte,
                "notas": notas,
            }

            st.session_state.df = pd.concat(
                [df, pd.DataFrame([nueva_fila])], ignore_index=True
            )
            st.session_state.df = asegurar_columnas(st.session_state.df)
            df = st.session_state.df
            st.success(f"Persona registrada con ID {nuevo_id}.")

# ========= DÍA D =========
with tab_diaD:
    st.subheader("Operación Día D")

    st.caption("Aquí marcas quién ya votó y quién requiere transporte (movilizables).")

    # Solo movilizables filtrados
    df_mov = df_filtrado[df_filtrado["rol"] == "Movilizable"].copy()

    if df_mov.empty:
        st.info("No hay movilizables en el filtro actual.")
    else:
        st.markdown("#### Selección masiva")

        ids_disp = list(df_mov["id"])
        ids_label = [
            f"{int(row.id)} - {row.nombre} (Dist {row.distrito}, Resp: {row.responsable})"
            for _, row in df_mov.iterrows()
        ]
        opciones = {label: _id for label, _id in zip(ids_label, ids_disp)}

        selec_ya_voto = st.multiselect(
            "Marcar como 'Ya votó'",
            options=list(opciones.keys()),
        )
        selec_transporte = st.multiselect(
            "Marcar como 'Requiere transporte = Sí'",
            options=list(opciones.keys()),
        )

        if st.button("Aplicar cambios Día D"):
            ids_ya_voto = [opciones[x] for x in selec_ya_voto]
            ids_trans = [opciones[x] for x in selec_transporte]

            df.loc[df["id"].isin(ids_ya_voto), "ya_voto"] = "Sí"
            df.loc[df["id"].isin(ids_trans), "requiere_transporte"] = "Sí"

            st.session_state.df = df
            st.success("Actualización aplicada.")

        st.markdown("#### Tabla de movilizables (filtro actual)")
        st.dataframe(
            df_mov[
                [
                    "id",
                    "nombre",
                    "distrito",
                    "responsable",
                    "nivel_apoyo",
                    "confirma_voto",
                    "ya_voto",
                    "requiere_transporte",
                ]
            ],
            use_container_width=True,
        )

# ========= ESTRUCTURA =========
with tab_estructura:
    st.subheader("Estructura por distrito y rol")

    if df.empty:
        st.info("Aún no hay datos.")
    else:
        tabla_rol = (
            df.groupby(["distrito", "rol"])
            .agg(conteo=("id", "count"))
            .reset_index()
            .pivot(index="distrito", columns="rol", values="conteo")
            .fillna(0)
            .astype(int)
        )
        st.markdown("#### Número de personas por distrito y rol")
        st.dataframe(tabla_rol, use_container_width=True)

        st.markdown("#### Coordinadores y jefes por distrito")

        df_coord_jefes = df[df["rol"].isin(["Coordinador distrito", "Jefe"])][
            ["id", "nombre", "rol", "distrito", "responsable"]
        ].sort_values(["distrito", "rol", "nombre"])
        st.dataframe(df_coord_jefes, use_container_width=True)
