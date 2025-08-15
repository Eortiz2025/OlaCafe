import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta

# ============================
# Configuración base
# ============================
st.set_page_config(page_title="CRM político (simple)", page_icon="📇", layout="wide")
HOY = date.today()

TIPOS = ["Principal", "Recomendación", "Planilla"]
ESTADOS = ["Pendiente", "Hecho"]
CANALES = ["Llamada", "Reunión", "Mensaje", "Otro"]

@st.cache_data
def csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")

# ============================
# Estado inicial (minimalista)
# ============================
if "contactos" not in st.session_state:
    st.session_state.contactos = pd.DataFrame(
        columns=["Nombre", "Notas", "Último contacto"]
    )

if "interacciones" not in st.session_state:
    st.session_state.interacciones = pd.DataFrame(
        columns=[
            "Fecha", "Nombre", "Canal", "Resumen", 
            "Tipo", "Próxima acción", "Próxima fecha", "Estado"
        ]
    )

if "planilla" not in st.session_state:
    st.session_state.planilla = pd.DataFrame(
        columns=["Nombre", "Género", "Estatus"]  # Género: Hombre/Mujer, Estatus: Confirmado/Posible
    )

# ============================
# Funciones simples
# ============================

def normaliza(s: str) -> str:
    return (s or "").strip()


def actualizar_ultimo_contacto():
    df = st.session_state.interacciones
    if df.empty:
        return
    last = (
        df.dropna(subset=["Nombre"])  # seguridad
          .sort_values("Fecha")
          .groupby("Nombre")["Fecha"].last()
    )
    c = st.session_state.contactos
    if c.empty:
        c = pd.DataFrame({"Nombre": last.index, "Notas": "", "Último contacto": last.values})
    else:
        c = c.set_index("Nombre")
        for n, f in last.items():
            if n in c.index:
                c.loc[n, "Último contacto"] = f
        # añade faltantes
        faltan = [n for n in last.index if n not in c.index]
        if faltan:
            extra = pd.DataFrame(index=faltan, data={"Notas": "", "Último contacto": last.loc[faltan].values})
            c = pd.concat([c, extra])
        c = c.reset_index()
    st.session_state.contactos = c


def pendientes_df():
    df = st.session_state.interacciones
    if df.empty:
        return df
    df = df[df["Estado"] == "Pendiente"].copy()
    df["Próxima fecha sort"] = pd.to_datetime(df["Próxima fecha"], errors="coerce")
    df = df.sort_values(["Próxima fecha sort", "Fecha"], ascending=[True, False])
    return df.drop(columns=["Próxima fecha sort"]) 


def kpi_semana():
    df = st.session_state.interacciones
    if df.empty:
        return 0
    semana_inicio = HOY - timedelta(days=6)
    mask = pd.to_datetime(df["Fecha"]).dt.date >= semana_inicio
    return int(mask.sum())


def requiere_contacto(nombre: str) -> bool:
    df = st.session_state.interacciones
    if df.empty:
        return True
    sub = df[df["Nombre"] == nombre]
    if sub.empty:
        return True
    last = pd.to_datetime(sub["Fecha"]).max().date()
    return (HOY - last).days >= 7

# ============================
# Navegación (5 secciones)
# ============================
st.sidebar.title("📇 CRM político (simple)")
seccion = st.sidebar.radio(
    "Navegación",
    ["Dashboard", "Interacciones", "Pendientes", "Planilla", "Datos"],
)

# ============================
# Dashboard
# ============================
if seccion == "Dashboard":
    st.title("📊 Dashboard")
    inter = st.session_state.interacciones
    cont = st.session_state.contactos

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Personas", cont["Nombre"].nunique())
    with c2:
        st.metric("Interacciones", len(inter))
    with c3:
        st.metric("Últimos 7 días", kpi_semana())
    with c4:
        st.metric("Pendientes", len(pendientes_df()))

    st.subheader("Pendientes (prioridad por fecha)")
    dfp = pendientes_df()
    if dfp.empty:
        st.info("Sin pendientes.")
    else:
        def alerta(row):
            if not row["Próxima fecha"]:
                return "—"
            try:
                d = pd.to_datetime(row["Próxima fecha"]).date()
            except Exception:
                return "—"
            if d < HOY: return "⚠️ Atrasado"
            if d == HOY: return "🔔 Hoy"
            return ""
        dfp = dfp.copy()
        dfp["Alerta"] = dfp.apply(alerta, axis=1)
        st.dataframe(
            dfp[["Nombre", "Tipo", "Resumen", "Próxima acción", "Próxima fecha", "Alerta"]],
            use_container_width=True,
        )

    st.divider()
    st.subheader("Requeridos contacto semanal (≥7 días sin contacto)")
    if cont.empty:
        st.info("Aún no hay contactos.")
    else:
        nombres = sorted(cont["Nombre"].dropna().unique())
        faltan = [n for n in nombres if requiere_contacto(n)]
        if faltan:
            st.write(", ".join(faltan))
        else:
            st.success("Todos en los últimos 7 días.")

# ============================
# Interacciones (única forma)
# ============================
elif seccion == "Interacciones":
    st.title("✍️ Interacciones")

    with st.form("frm_interaccion"):
        cA, cB = st.columns([2,1])
        with cA:
            nombre = st.text_input("Nombre (nuevo o existente)")
        with cB:
            canal = st.selectbox("Canal", CANALES)
        resumen = st.text_area("Resumen / acuerdos")
        tipo = st.selectbox("Tipo", TIPOS)
        prox_accion = st.text_input("Próxima acción")
        prox_fecha = st.date_input("Próxima fecha (opcional)", value=None)
        estado = st.selectbox("Estado", ESTADOS, index=0)
        ok = st.form_submit_button("Guardar")

    if ok:
        nombre = normaliza(nombre)
        if not nombre:
            st.error("El nombre es obligatorio.")
        else:
            # alta rápida de contacto si no existe
            c = st.session_state.contactos
            if nombre not in c["Nombre"].values:
                c.loc[len(c)] = [nombre, "", None]
                st.session_state.contactos = c
            # guardar
            nueva = {
                "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Nombre": nombre,
                "Canal": canal,
                "Resumen": resumen,
                "Tipo": tipo,
                "Próxima acción": prox_accion,
                "Próxima fecha": prox_fecha.strftime("%Y-%m-%d") if prox_fecha else "",
                "Estado": estado,
            }
            st.session_state.interacciones.loc[len(st.session_state.interacciones)] = nueva
            actualizar_ultimo_contacto()
            st.success("Interacción guardada.")

    st.divider()
    st.subheader("Historial")
    df = st.session_state.interacciones
    if df.empty:
        st.info("Sin interacciones todavía.")
    else:
        st.dataframe(df.sort_values("Fecha", ascending=False), use_container_width=True)

# ============================
# Pendientes (vista + actualización rápida)
# ============================
elif seccion == "Pendientes":
    st.title("✅ Pendientes")

    df = st.session_state.interacciones
    if df.empty:
        st.info("Sin interacciones.")
    else:
        colf1, colf2 = st.columns(2)
        with colf1:
            tipos = st.multiselect("Tipo", TIPOS, default=TIPOS)
        with colf2:
            estado_sel = st.selectbox("Estado", ["Pendiente", "Hecho", "Todos"], index=0)

        v = df.copy()
        if estado_sel != "Todos":
            v = v[v["Estado"] == estado_sel]
        v = v[v["Tipo"].isin(tipos)]
        v["_pf"] = pd.to_datetime(v["Próxima fecha"], errors="coerce")
        v = v.sort_values(["Estado", "_pf"], ascending=[True, True]).drop(columns=["_pf"])
        st.dataframe(v, use_container_width=True)

        st.subheader("Actualizar estado")
        with st.form("frm_upd"):
            n = st.text_input("Nombre")
            f = st.text_input("Fecha exacta (YYYY-MM-DD HH:MM:SS)")
            nuevo = st.selectbox("Nuevo estado", ESTADOS, index=1)
            pf = st.date_input("Nueva próxima fecha (opcional)", value=None)
            ok = st.form_submit_button("Actualizar")
        if ok:
            mask = (df["Nombre"] == n) & (df["Fecha"] == f)
            if mask.any():
                st.session_state.interacciones.loc[mask, "Estado"] = nuevo
                if pf:
                    st.session_state.interacciones.loc[mask, "Próxima fecha"] = pf.strftime("%Y-%m-%d")
                actualizar_ultimo_contacto()
                st.success("Actualizado.")
            else:
                st.error("No se encontró esa interacción.")

# ============================
# Planilla (opcional, conservando 8/8)
# ============================
elif seccion == "Planilla":
    st.title("🧾 Planilla (meta 8 y 8)")
    pl = st.session_state.planilla

    with st.form("frm_pl"):
        pn = st.text_input("Nombre")
        pg = st.selectbox("Género", ["Hombre", "Mujer"], index=0)
        pe = st.selectbox("Estatus", ["Confirmado", "Posible"], index=0)
        ok = st.form_submit_button("Guardar")
    if ok:
        pn = normaliza(pn)
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

    if pl.empty:
        st.info("Aún no hay registros.")
    else:
        conf_h = ((pl["Género"] == "Hombre") & (pl["Estatus"] == "Confirmado")).sum()
        conf_m = ((pl["Género"] == "Mujer") & (pl["Estatus"] == "Confirmado")).sum()
        c1, c2 = st.columns(2)
        c1.metric("Hombres confirmados", conf_h, delta=f"Meta 8 (faltan {max(0, 8-conf_h)})")
        c2.metric("Mujeres confirmadas", conf_m, delta=f"Meta 8 (faltan {max(0, 8-conf_m)})")
        st.dataframe(pl.sort_values(["Género", "Estatus", "Nombre"]), use_container_width=True)

# ============================
# Datos (importar/exportar)
# ============================
elif seccion == "Datos":
    st.title("⬇️⬆️ Datos")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button("contactos.csv", csv_bytes(st.session_state.contactos), file_name="contactos.csv")
    with c2:
        st.download_button("interacciones.csv", csv_bytes(st.session_state.interacciones), file_name="interacciones.csv")
    with c3:
        st.download_button("planilla.csv", csv_bytes(st.session_state.planilla), file_name="planilla.csv")

    st.divider()
    st.subheader("Importar CSV (reemplaza la tabla)")
    u1, u2, u3 = st.columns(3)
    with u1:
        up = st.file_uploader("contactos.csv", type=["csv"], key="up_c")
        if up is not None:
            st.session_state.contactos = pd.read_csv(up)
            st.success("Contactos importados.")
    with u2:
        up = st.file_uploader("interacciones.csv", type=["csv"], key="up_i")
        if up is not None:
            st.session_state.interacciones = pd.read_csv(up)
            st.success("Interacciones importadas.")
    with u3:
        up = st.file_uploader("planilla.csv", type=["csv"], key="up_p")
        if up is not None:
            st.session_state.planilla = pd.read_csv(up)
            st.success("Planilla importada.")

# post-proceso mínimo
actualizar_ultimo_contacto()
