import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from io import StringIO, BytesIO

# ----------------------------
# Configuración base
# ----------------------------
st.set_page_config(page_title="CRM político sencillo", page_icon="📇", layout="wide")

# Utilidades
HOY = date.today()

TIPOS_PENDIENTE = ["Principal", "Recomendación", "Planilla"]
ESTADOS = ["Pendiente", "Hecho"]
CANALES = ["Llamada", "Reunión", "Mensaje", "Otro"]
GENERO = ["Hombre", "Mujer", "Otro/ND"]

@st.cache_data
def _csv_bytes(df: pd.DataFrame, filename: str) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")

# ----------------------------
# Estado inicial (en memoria)
# ----------------------------
if "contacts" not in st.session_state:
    st.session_state.contacts = pd.DataFrame(
        columns=[
            "Nombre",            # clave textual
            "Género",            # Hombre/Mujer/Otro
            "Rol",               # planilla / contacto / familiar / etc.
            "Notas",             # notas libres de la persona
            "Relaciones",        # texto tipo: "Es compadre de X; Madre de Y"
            "Último contacto"    # fecha calculada
        ]
    )

if "interacciones" not in st.session_state:
    st.session_state.interacciones = pd.DataFrame(
        columns=[
            "Fecha",           # fecha de la interacción
            "Nombre",          # persona
            "Canal",           # llamada/reunión/mensaje
            "Resumen",         # qué se habló
            "Tipo",            # Principal / Recomendación / Planilla
            "Referencias",     # a quién recomendó (separado por coma)
            "Próxima acción",  # texto de la próxima acción
            "Próxima fecha",   # fecha próxima acción (opcional)
            "Estado"           # Pendiente/Hecho
        ]
    )

if "planilla" not in st.session_state:
    st.session_state.planilla = pd.DataFrame(
        columns=[
            "Nombre",
            "Género",
            "Estatus"  # Confirmado / Posible
        ]
    )

# ----------------------------
# Funciones de negocio
# ----------------------------

def normaliza_nombre(n: str) -> str:
    return (n or "").strip()


def actualizar_ultimo_contacto():
    """Actualiza la columna 'Último contacto' en contactos usando interacciones."""
    if st.session_state.interacciones.empty:
        return
    last = (
        st.session_state.interacciones
        .sort_values("Fecha")
        .groupby("Nombre")["Fecha"].last()
    )
    st.session_state.contacts.set_index("Nombre", inplace=True, drop=False)
    for nombre, f in last.items():
        if nombre in st.session_state.contacts.index:
            st.session_state.contacts.loc[nombre, "Último contacto"] = f
    st.session_state.contacts.reset_index(drop=True, inplace=True)


def get_pendientes_df():
    df = st.session_state.interacciones.copy()
    if df.empty:
        return df
    # Solo pendientes
    df = df[df["Estado"] == "Pendiente"].copy()
    # Orden por fecha próxima primero y después por fecha de creación
    df["Próxima fecha sort"] = pd.to_datetime(df["Próxima fecha"], errors="coerce")
    df["Fecha sort"] = pd.to_datetime(df["Fecha"], errors="coerce")
    df = df.sort_values(["Próxima fecha sort", "Fecha sort"], ascending=[True, False])
    df.drop(columns=["Próxima fecha sort", "Fecha sort"], inplace=True)
    return df


def kpi_semana(df_inter: pd.DataFrame):
    if df_inter.empty:
        return 0
    semana_inicio = HOY - timedelta(days=6)
    mask = pd.to_datetime(df_inter["Fecha"]).dt.date >= semana_inicio
    return int(mask.sum())


def asegurate_contacto_semanal(nombre: str) -> bool:
    """True si han pasado >7 días desde el último contacto."""
    df = st.session_state.interacciones
    if df.empty:
        return True
    sub = df[df["Nombre"] == nombre]
    if sub.empty:
        return True
    last = pd.to_datetime(sub["Fecha"]).max().date()
    return (HOY - last).days >= 7


# ----------------------------
# Sidebar (navegación)
# ----------------------------
st.sidebar.title("📇 CRM político sencillo")
page = st.sidebar.radio(
    "Navegación",
    ["Dashboard", "Registrar interacción", "Pendientes", "Planilla", "Contactos", "Importar/Exportar"],
)

# ----------------------------
# Dashboard
# ----------------------------
if page == "Dashboard":
    st.title("📊 Dashboard")

    inter = st.session_state.interacciones
    contactos = st.session_state.contacts

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        total_personas = contactos["Nombre"].nunique()
        st.metric("Personas registradas", total_personas)
    with col2:
        total_inter = len(inter)
        st.metric("Interacciones totales", total_inter)
    with col3:
        semana = kpi_semana(inter)
        st.metric("Interacciones últimos 7 días", semana)
    with col4:
        pend = len(get_pendientes_df())
        st.metric("Pendientes abiertos", pend)

    st.subheader("Pendientes por fecha (prioridad)")
    dfp = get_pendientes_df()
    if dfp.empty:
        st.info("No hay pendientes registrados.")
    else:
        # Señal visual para atrasados / hoy
        def _flag(row):
            if not row["Próxima fecha"]:
                return "—"
            try:
                d = pd.to_datetime(row["Próxima fecha"]).date()
            except Exception:
                return "—"
            if d < HOY:
                return "⚠️ Atrasado"
            if d == HOY:
                return "🔔 Hoy"
            return "" 
        dfp = dfp.copy()
        dfp["Alerta"] = dfp.apply(_flag, axis=1)
        st.dataframe(dfp[["Nombre", "Tipo", "Resumen", "Próxima acción", "Próxima fecha", "Alerta"]], use_container_width=True)

    st.divider()
    st.subheader("Personas que requieren contacto semanal (≥7 días sin contacto)")
    if contactos.empty:
        st.info("Aún no hay contactos.")
    else:
        alerta = []
        for n in sorted(contactos["Nombre"].dropna().unique()):
            if asegurate_contacto_semanal(n):
                alerta.append(n)
        if alerta:
            st.write(", ".join(alerta))
        else:
            st.success("Todos con contacto en los últimos 7 días.")

# ----------------------------
# Registrar interacción
# ----------------------------
elif page == "Registrar interacción":
    st.title("✍️ Registrar interacción")
    contactos = st.session_state.contacts

    with st.form("frm_interaccion"):
        colA, colB = st.columns([2,1])
        with colA:
            nombre = st.text_input("Nombre (nuevo o existente)")
        with colB:
            canal = st.selectbox("Canal", CANALES, index=0)
        resumen = st.text_area("Resumen de lo hablado / acordado")
        tipo = st.selectbox("Tipo de pendiente", TIPOS_PENDIENTE, index=0)
        refs = st.text_input("Referencias / a quién recomendó (separar por coma)")
        prox_accion = st.text_input("Próxima acción")
        prox_fecha = st.date_input("Próxima fecha (opcional)", value=None)
        estado = st.selectbox("Estado", ESTADOS, index=0)
        submitted = st.form_submit_button("Guardar interacción")

    if submitted:
        nombre = normaliza_nombre(nombre)
        if not nombre:
            st.error("El nombre es obligatorio.")
        else:
            # Alta rápida de contacto si no existe
            if nombre not in st.session_state.contacts["Nombre"].values:
                st.session_state.contacts.loc[len(st.session_state.contacts)] = [nombre, "Otro/ND", "", "", "", None]
            # Guardar interacción
            nueva = {
                "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Nombre": nombre,
                "Canal": canal,
                "Resumen": resumen,
                "Tipo": tipo,
                "Referencias": refs,
                "Próxima acción": prox_accion,
                "Próxima fecha": prox_fecha.strftime("%Y-%m-%d") if prox_fecha else "",
                "Estado": estado,
            }
            st.session_state.interacciones.loc[len(st.session_state.interacciones)] = nueva

            # Alta de referencias como contactos (sin duplicar)
            if refs:
                for r in [normaliza_nombre(x) for x in refs.split(",") if x.strip()]:
                    if r and r not in st.session_state.contacts["Nombre"].values:
                        st.session_state.contacts.loc[len(st.session_state.contacts)] = [r, "Otro/ND", "", "", "", None]
            actualizar_ultimo_contacto()
            st.success("Interacción guardada.")

    st.divider()
    st.subheader("Atajo: Alta / edición rápida de persona")
    with st.form("frm_persona"):
        col1, col2, col3 = st.columns(3)
        with col1:
            p_nombre = st.text_input("Nombre")
        with col2:
            p_genero = st.selectbox("Género", GENERO, index=2)
        with col3:
            p_rol = st.text_input("Rol / Etiqueta (p.ej. planilla, contacto, familiar)")
        p_notas = st.text_area("Notas")
        p_rel = st.text_input("Relaciones (ej. 'Compadre de Doña Rafa; Madre de Gaby')")
        btnp = st.form_submit_button("Guardar persona")
    if btnp:
        p_nombre = normaliza_nombre(p_nombre)
        if not p_nombre:
            st.error("El nombre es obligatorio.")
        else:
            dfc = st.session_state.contacts
            if p_nombre in dfc["Nombre"].values:
                idx = dfc.index[dfc["Nombre"] == p_nombre][0]
                dfc.loc[idx, ["Género", "Rol", "Notas", "Relaciones"]] = [p_genero, p_rol, p_notas, p_rel]
                st.success("Persona actualizada.")
            else:
                st.session_state.contacts.loc[len(st.session_state.contacts)] = [p_nombre, p_genero, p_rol, p_notas, p_rel, None]
                st.success("Persona creada.")

# ----------------------------
# Pendientes
# ----------------------------
elif page == "Pendientes":
    st.title("✅ Pendientes")

    tipo_filtro = st.multiselect("Filtrar por tipo", TIPOS_PENDIENTE, default=TIPOS_PENDIENTE)
    estado_filtro = st.selectbox("Estado", ["Pendiente", "Hecho", "Todos"], index=0)

    df = st.session_state.interacciones.copy()
    if df.empty:
        st.info("Aún no hay interacciones.")
    else:
        if estado_filtro != "Todos":
            df = df[df["Estado"] == estado_filtro]
        df = df[df["Tipo"].isin(tipo_filtro)]
        # Orden sugerido
        df["_pf"] = pd.to_datetime(df["Próxima fecha"], errors="coerce")
        df = df.sort_values(["Estado", "_pf"], ascending=[True, True])
        df.drop(columns=["_pf"], inplace=True)
        st.dataframe(df, use_container_width=True)

    st.divider()
    st.subheader("Actualizar estado rápido")
    with st.form("frm_estado"):
        nombre_u = st.text_input("Nombre")
        fecha_u = st.text_input("Fecha exacta de la interacción a actualizar (YYYY-MM-DD HH:MM:SS)")
        nuevo_estado = st.selectbox("Nuevo estado", ESTADOS, index=1)
        nueva_fecha = st.date_input("Nueva próxima fecha (opcional)", value=None)
        btnu = st.form_submit_button("Actualizar")
    if btnu:
        df = st.session_state.interacciones
        mask = (df["Nombre"] == nombre_u) & (df["Fecha"] == fecha_u)
        if mask.any():
            st.session_state.interacciones.loc[mask, "Estado"] = nuevo_estado
            if nueva_fecha:
                st.session_state.interacciones.loc[mask, "Próxima fecha"] = nueva_fecha.strftime("%Y-%m-%d")
            actualizar_ultimo_contacto()
            st.success("Actualizado.")
        else:
            st.error("No se encontró esa interacción (verifica nombre y fecha exacta).")

# ----------------------------
# Planilla (8 y 8)
# ----------------------------
elif page == "Planilla":
    st.title("🧾 Planilla (meta 8 hombres y 8 mujeres)")

    pl = st.session_state.planilla

    colA, colB = st.columns(2)
    with colA:
        st.subheader("Agregar / actualizar integrante")
        with st.form("frm_planilla"):
            pn = st.text_input("Nombre")
            pg = st.selectbox("Género", ["Hombre", "Mujer"], index=0)
            pe = st.selectbox("Estatus", ["Confirmado", "Posible"], index=0)
            btnp = st.form_submit_button("Guardar")
        if btnp:
            pn = normaliza_nombre(pn)
            if not pn:
                st.error("Nombre obligatorio.")
            else:
                if pn in pl["Nombre"].values:
                    idx = pl.index[pl["Nombre"] == pn][0]
                    pl.loc[idx, ["Género", "Estatus"]] = [pg, pe]
                else:
                    pl.loc[len(pl)] = [pn, pg, pe]
                st.session_state.planilla = pl
                st.success("Planilla actualizada.")

    with colB:
        st.subheader("Estado actual vs meta")
        if pl.empty:
            st.info("Aún no hay registros de planilla.")
        else:
            conf_h = ((pl["Género"] == "Hombre") & (pl["Estatus"] == "Confirmado")).sum()
            conf_m = ((pl["Género"] == "Mujer") & (pl["Estatus"] == "Confirmado")).sum()
            st.metric("Hombres confirmados", conf_h, delta=f"Meta 8 (faltan {max(0, 8-conf_h)})")
            st.metric("Mujeres confirmadas", conf_m, delta=f"Meta 8 (faltan {max(0, 8-conf_m)})")
        st.write("\n")

    st.subheader("Tabla de planilla")
    st.dataframe(pl.sort_values(["Género", "Estatus", "Nombre"], ascending=[True, True, True]), use_container_width=True)

# ----------------------------
# Contactos
# ----------------------------
elif page == "Contactos":
    st.title("👥 Contactos")
    contactos = st.session_state.contacts

    st.subheader("Listado")
    if contactos.empty:
        st.info("Aún no hay contactos.")
    else:
        st.dataframe(contactos.sort_values("Nombre"), use_container_width=True)

    st.divider()
    st.subheader("Editar relaciones/nota rápida")
    with st.form("frm_rel"):
        n = st.text_input("Nombre")
        rel = st.text_input("Relaciones (ej. 'Compadre de Doña Rafa; Madre de Gaby')")
        notas = st.text_area("Notas")
        gen = st.selectbox("Género", GENERO, index=2)
        rol = st.text_input("Rol / Etiqueta")
        btn = st.form_submit_button("Guardar cambios")
    if btn:
        n = normaliza_nombre(n)
        if not n:
            st.error("Nombre obligatorio.")
        else:
            dfc = st.session_state.contacts
            if n in dfc["Nombre"].values:
                idx = dfc.index[dfc["Nombre"] == n][0]
                dfc.loc[idx, ["Relaciones", "Notas", "Género", "Rol"]] = [rel, notas, gen, rol]
                st.success("Contacto actualizado.")
            else:
                st.session_state.contacts.loc[len(st.session_state.contacts)] = [n, gen, rol, notas, rel, None]
                st.success("Contacto creado.")

# ----------------------------
# Importar / Exportar
# ----------------------------
elif page == "Importar/Exportar":
    st.title("⬇️⬆️ Importar / Exportar datos")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.download_button("Descargar contactos.csv", _csv_bytes(st.session_state.contacts, "contactos.csv"), file_name="contactos.csv")
    with col2:
        st.download_button("Descargar interacciones.csv", _csv_bytes(st.session_state.interacciones, "interacciones.csv"), file_name="interacciones.csv")
    with col3:
        st.download_button("Descargar planilla.csv", _csv_bytes(st.session_state.planilla, "planilla.csv"), file_name="planilla.csv")

    st.divider()
    st.subheader("Importar desde CSV (reemplaza la tabla actual)")

    c1, c2, c3 = st.columns(3)
    with c1:
        up1 = st.file_uploader("Subir contactos.csv", type=["csv"], key="upc")
        if up1 is not None:
            st.session_state.contacts = pd.read_csv(up1)
            st.success("Contactos importados.")
    with c2:
        up2 = st.file_uploader("Subir interacciones.csv", type=["csv"], key="upi")
        if up2 is not None:
            st.session_state.interacciones = pd.read_csv(up2)
            st.success("Interacciones importadas.")
    with c3:
        up3 = st.file_uploader("Subir planilla.csv", type=["csv"], key="upp")
        if up3 is not None:
            st.session_state.planilla = pd.read_csv(up3)
            st.success("Planilla importada.")

# Post-procesos
actualizar_ultimo_contacto()
