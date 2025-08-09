# streamlit_app.py
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from io import BytesIO
import os

# =========================
# CONFIGURACIÓN BÁSICA
# =========================
st.set_page_config(page_title="Seguimiento de Llamadas · Campaña", layout="centered")

DB_PATH = "data/seguimiento.db"
os.makedirs("data", exist_ok=True)

# ⚠️ EDITA ESTOS VALORES
ALLOWED_PROMOTERS = [
    "Tania","Olga","Emilio","Sergio","Juan","Elvia","Claudia",
    "María","Pedro","Luis","Ana","Carmen","Hugo","Martha","Carlos",
]
ALLOWED_PROMOTERS = sorted(list(set([n.strip() for n in ALLOWED_PROMOTERS if n.strip()])))

ADMIN_PIN = "2468"  # <— cámbialo

CALL_STATES = ["Pendiente","Contestó","No contestó","Rechazó","Confirmó asistencia"]

# =========================
# DB: FUNCIONES
# =========================
def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    with get_conn() as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            promoter TEXT NOT NULL,
            name TEXT NOT NULL,
            phone TEXT,
            neighborhood TEXT,
            notes TEXT,
            status TEXT DEFAULT 'Pendiente',
            last_call_ts TEXT,
            created_at TEXT NOT NULL
        );
        """)
        con.commit()

def add_contact(promoter, name, phone, neighborhood, notes):
    with get_conn() as con:
        con.execute("""
        INSERT INTO contacts (promoter, name, phone, neighborhood, notes, status, created_at)
        VALUES (?,?,?,?,?,'Pendiente',?)
        """, (promoter, name.strip(), phone.strip(), neighborhood.strip(), notes.strip(), datetime.now().isoformat()))
        con.commit()

def fetch_contacts(promoter=None, status=None, search=None):
    q = "SELECT id, promoter, name, phone, neighborhood, notes, status, last_call_ts, created_at FROM contacts WHERE 1=1"
    params = []
    if promoter:
        q += " AND promoter=?"
        params.append(promoter)
    if status and status != "Todos":
        q += " AND status=?"
        params.append(status)
    if search:
        q += " AND (LOWER(name) LIKE ? OR LOWER(phone) LIKE ? OR LOWER(neighborhood) LIKE ? OR LOWER(notes) LIKE ?)"
        s = f"%{search.lower()}%"
        params += [s,s,s,s]
    q += " ORDER BY id DESC"
    with get_conn() as con:
        df = pd.read_sql_query(q, con, params=params)
    return df

def update_rows_status(updates: pd.DataFrame):
    if updates.empty:
        return 0
    changed = 0
    with get_conn() as con:
        for _, r in updates.iterrows():
            # si cambió estado, actualizar timestamp
            if r.get("_status_changed", False):
                con.execute("""
                    UPDATE contacts
                    SET status=?, notes=?, last_call_ts=?
                    WHERE id=?
                """, (r["status"], r["notes"], datetime.now().isoformat(), int(r["id"])))
            else:
                con.execute("""
                    UPDATE contacts
                    SET status=?, notes=?
                    WHERE id=?
                """, (r["status"], r["notes"], int(r["id"])))
            changed += 1
        con.commit()
    return changed

def reassign_contacts(ids, new_promoter):
    if not ids:
        return 0
    with get_conn() as con:
        con.executemany("UPDATE contacts SET promoter=? WHERE id=?", [(new_promoter, int(i)) for i in ids])
        con.commit()
    return len(ids)

def delete_contacts(ids):
    if not ids:
        return 0
    with get_conn() as con:
        con.executemany("DELETE FROM contacts WHERE id=?", [(int(i),) for i in ids])
        con.commit()
    return len(ids)

# =========================
# UTILS
# =========================
def df_for_editor(df: pd.DataFrame, allow_promoter=False):
    if df.empty:
        return df
    df = df.copy()
    # columnas orden
    cols = ["id","name","phone","neighborhood","status","notes","last_call_ts","promoter","created_at"]
    cols = [c for c in cols if c in df.columns]
    df = df[cols]
    if not allow_promoter and "promoter" in df.columns:
        # el promotor no debe editarse en panel promotor
        pass
    return df

def excel_download(df: pd.DataFrame, filename="reporte.xlsx"):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Llamadas", index=False)
    buffer.seek(0)
    st.download_button("📥 Descargar Excel", buffer, file_name=filename, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

def wa_link(phone, text="Hola, ¿podemos platicar un minuto?"):
    phone = str(phone or "").replace(" ", "").replace("-", "")
    if not phone:
        return ""
    return f"https://wa.me/{phone}?text={text}"

def tel_link(phone):
    phone = str(phone or "").strip()
    return f"tel:{phone}" if phone else ""

# =========================
# UI
# =========================
init_db()
st.title("📞 Seguimiento de llamadas · Invitar a votar")

# Login simple en sesión
if "role" not in st.session_state:
    st.session_state.role = None
if "promoter" not in st.session_state:
    st.session_state.promoter = None
if "admin_ok" not in st.session_state:
    st.session_state.admin_ok = False

with st.sidebar:
    st.header("Acceso")
    role = st.radio("Entrar como:", ["Promotor","Administrador"], index=0)
    if role == "Promotor":
        promoter = st.text_input("Tu nombre (exacto)", placeholder="Ej. Tania")
        if st.button("Entrar", type="primary", use_container_width=True):
            if promoter.strip() in ALLOWED_PROMOTERS:
                st.session_state.role = "Promotor"
                st.session_state.promoter = promoter.strip()
            else:
                st.error("Nombre no autorizado. Pide alta al administrador.")
        st.caption("Sólo ves tus contactos.")
    else:
        pin = st.text_input("PIN de administrador", type="password")
        if st.button("Entrar", type="primary", use_container_width=True):
            if pin == ADMIN_PIN:
                st.session_state.role = "Administrador"
                st.session_state.admin_ok = True
            else:
                st.error("PIN incorrecto.")
        st.caption("Vista global, asignaciones, importación/exportación.")

# =========================
# PROMOTOR
# =========================
def promoter_view():
    st.subheader(f"👤 Promotor: {st.session_state.promoter}")

    with st.expander("➕ Agregar contacto rápido", expanded=False):
        c1, c2 = st.columns(2)
        name = c1.text_input("Nombre*", placeholder="Nombre de la persona")
        phone = c2.text_input("Teléfono", placeholder="10 dígitos")
        c3, c4 = st.columns(2)
        neighborhood = c3.text_input("Colonia / Zona", placeholder="Opcional")
        notes = c4.text_input("Notas", placeholder="Observaciones")
        if st.button("Guardar contacto", type="primary"):
            if not name.strip():
                st.warning("Nombre es obligatorio.")
            else:
                add_contact(st.session_state.promoter, name, phone, neighborhood, notes)
                st.success("Contacto agregado.")

    st.divider()

    # Filtros
    fc1, fc2 = st.columns([2,1])
    search = fc1.text_input("Buscar (nombre / teléfono / colonia / notas)", placeholder="Escribe para filtrar…")
    status_f = fc2.selectbox("Estado", ["Todos"] + CALL_STATES, index=0)

    df = fetch_contacts(promoter=st.session_state.promoter, status=status_f, search=search)
    st.caption(f"Total: {len(df)}")

    if df.empty:
        st.info("Sin contactos. Agrega desde el formulario.")
        return

    # Enlaces de acción
    df_display = df.copy()
    df_display["Llamar"] = df_display["phone"].apply(lambda p: f"[📲 Llamar]({tel_link(p)})" if p else "")
    df_display["WhatsApp"] = df_display["phone"].apply(lambda p: f"[💬 WhatsApp]({wa_link(p)})" if p else "")
    df_display = df_display.rename(columns={
        "name":"Nombre","phone":"Teléfono","neighborhood":"Colonia","notes":"Notas","status":"Estado","last_call_ts":"Última llamada","created_at":"Creado","promoter":"Promotor"
    })

    # Editor: permitir editar Estado y Notas
    edit_cols = ["id","Nombre","Teléfono","Colonia","Estado","Notas","Última llamada","Llamar","WhatsApp"]
    edit_cols = [c for c in edit_cols if c in df_display.columns]
    edited = st.data_editor(
        df_display[edit_cols],
        hide_index=True,
        column_config={
            "Estado": st.column_config.SelectboxColumn("Estado", options=CALL_STATES),
            "Llamar": st.column_config.LinkColumn("Llamar"),
            "WhatsApp": st.column_config.LinkColumn("WhatsApp")
        },
        disabled=["id","Nombre","Teléfono","Colonia","Última llamada","Llamar","WhatsApp"],
        use_container_width=True,
        key="editor_promoter"
    )

    # Detectar cambios de estado vs original
    merged = edited.merge(df, left_on="id", right_on="id", how="left", suffixes=("_e",""))
    updates = []
    for _, r in merged.iterrows():
        status_changed = (r["Estado"] != r["status"])
        if status_changed or (str(r["Notas"]) != str(r["notes"])):
            updates.append({
                "id": r["id"],
                "status": r["Estado"],
                "notes": r["Notas"],
                "_status_changed": bool(status_changed)
            })
    if updates and st.button("💾 Guardar cambios", type="primary"):
        n = update_rows_status(pd.DataFrame(updates))
        st.success(f"Cambios guardados: {n}")

    # Reintentos rápidos
    st.markdown("#### 🔁 Reintentos")
    if st.button("Filtrar 'No contestó'"):
        st.session_state["editor_promoter_filtered"] = True
        # Forzar filtro de estado
        st.rerun()

    # Resumen por estado
    st.markdown("#### 📊 Resumen")
    resumen = df.groupby("status").size().reindex(CALL_STATES, fill_value=0).reset_index()
    resumen.columns = ["Estado","Total"]
    st.table(resumen)

    # Exportar del promotor
    excel_download(df_display, filename=f"reporte_{st.session_state.promoter}.xlsx")

# =========================
# ADMIN
# =========================
def admin_view():
    st.subheader("🛠️ Panel administrador")
    tabs = st.tabs(["📋 Contactos","📈 Estadísticas","📥 Importar","🔁 Reasignar / Borrar","⚙️ Configuración"])

    # --- TAB CONTACTOS
    with tabs[0]:
        c1,c2,c3 = st.columns([1,1,2])
        promoter_f = c1.selectbox("Promotor", ["Todos"] + ALLOWED_PROMOTERS, index=0)
        status_f = c2.selectbox("Estado", ["Todos"] + CALL_STATES, index=0)
        search = c3.text_input("Buscar (nombre/tel/colonia/notas)")

        promoter_q = None if promoter_f == "Todos" else promoter_f
        df = fetch_contacts(promoter=promoter_q, status=status_f, search=search)
        st.caption(f"Total: {len(df)}")

        if df.empty:
            st.info("Sin registros.")
        else:
            df_display = df.copy()
            df_display["Llamar"] = df_display["phone"].apply(lambda p: f"[📲 Llamar]({tel_link(p)})" if p else "")
            df_display["WhatsApp"] = df_display["phone"].apply(lambda p: f"[💬 WhatsApp]({wa_link(p)})" if p else "")
            df_display = df_display.rename(columns={
                "name":"Nombre","phone":"Teléfono","neighborhood":"Colonia","notes":"Notas",
                "status":"Estado","last_call_ts":"Última llamada","promoter":"Promotor","created_at":"Creado"
            })
            edit_cols = ["id","Promotor","Nombre","Teléfono","Colonia","Estado","Notas","Última llamada","Llamar","WhatsApp","Creado"]
            edited = st.data_editor(
                df_display[edit_cols],
                hide_index=True,
                column_config={
                    "Estado": st.column_config.SelectboxColumn("Estado", options=CALL_STATES),
                    "Llamar": st.column_config.LinkColumn("Llamar"),
                    "WhatsApp": st.column_config.LinkColumn("WhatsApp"),
                    "Promotor": st.column_config.SelectboxColumn("Promotor", options=ALLOWED_PROMOTERS),
                },
                disabled=["id","Última llamada","Llamar","WhatsApp","Creado"],
                use_container_width=True,
                key="editor_admin"
            )
            # Detectar cambios
            merged = edited.merge(df, on="id", how="left", suffixes=("_e",""))
            updates = []
            reassign = []
            for _, r in merged.iterrows():
                status_changed = (r["Estado"] != r["status"])
                notes_changed = (str(r["Notas"]) != str(r["notes"]))
                promoter_changed = (r["Promotor"] != r["promoter"])
                if status_changed or notes_changed:
                    updates.append({
                        "id": r["id"],
                        "status": r["Estado"],
                        "notes": r["Notas"],
                        "_status_changed": bool(status_changed)
                    })
                if promoter_changed:
                    reassign.append((r["id"], r["Promotor"]))
            c1, c2 = st.columns(2)
            if updates and c1.button("💾 Guardar ediciones", type="primary"):
                n = update_rows_status(pd.DataFrame(updates))
                st.success(f"Actualizados: {n}")
            if reassign and c2.button("🔁 Guardar reasignaciones"):
                n = 0
                with get_conn() as con:
                    for rid, newp in reassign:
                        con.execute("UPDATE contacts SET promoter=? WHERE id=?", (newp, int(rid)))
                        n += 1
                    con.commit()
                st.success(f"Reasignados: {n}")

            excel_download(df_display, filename="reporte_global.xlsx")

    # --- TAB ESTADÍSTICAS
    with tabs[1]:
        df_all = fetch_contacts()
        if df_all.empty:
            st.info("Sin datos.")
        else:
            # Por promotor y estado
            pivot = df_all.pivot_table(index="promoter", columns="status", values="id", aggfunc="count", fill_value=0)
            pivot = pivot.reindex(columns=CALL_STATES, fill_value=0)
            pivot["Total"] = pivot.sum(axis=1)
            st.markdown("#### Por promotor y estado")
            st.dataframe(pivot, use_container_width=True)
            # Totales
            totales = df_all["status"].value_counts().reindex(CALL_STATES, fill_value=0).rename_axis("Estado").reset_index(name="Total")
            st.markdown("#### Totales por estado")
            st.table(totales)

    # --- TAB IMPORTAR
    with tabs[2]:
        st.markdown("Sube CSV o Excel con columnas: **name, phone, neighborhood, notes, promoter** (promoter debe estar en la lista permitida).")
        up = st.file_uploader("Archivo .csv / .xlsx", type=["csv","xlsx"])
        if up:
            try:
                if up.name.lower().endswith(".csv"):
                    df_imp = pd.read_csv(up)
                else:
                    df_imp = pd.read_excel(up)
                req = {"name","phone","neighborhood","notes","promoter"}
                missing = req - set([c.lower() for c in df_imp.columns])
                if missing:
                    st.error(f"Faltan columnas: {', '.join(missing)}")
                else:
                    # normalizar nombres de columnas
                    mapper = {c.lower(): c for c in df_imp.columns}
                    df_imp = df_imp.rename(columns=mapper)
                    ok_rows = 0
                    for _, r in df_imp.iterrows():
                        prom = str(r["promoter"]).strip()
                        if prom not in ALLOWED_PROMOTERS:
                            continue
                        add_contact(
                            prom,
                            str(r["name"] or "").strip(),
                            str(r.get("phone","") or ""),
                            str(r.get("neighborhood","") or ""),
                            str(r.get("notes","") or "")
                        )
                        ok_rows += 1
                    st.success(f"Importados: {ok_rows}")
            except Exception as e:
                st.error(f"Error al importar: {e}")

    # --- TAB REASIGNAR / BORRAR
    with tabs[3]:
        df = fetch_contacts()
        if df.empty:
            st.info("Sin registros.")
        else:
            st.caption("Selecciona por filtros y actúa sobre los IDs marcados.")
            c1,c2,c3 = st.columns([1,1,2])
            promoter_f = c1.selectbox("Filtrar promotor", ["Todos"] + ALLOWED_PROMOTERS, index=0, key="re_pf")
            status_f = c2.selectbox("Filtrar estado", ["Todos"] + CALL_STATES, index=0, key="re_sf")
            search = c3.text_input("Buscar", key="re_search")
            promoter_q = None if promoter_f == "Todos" else promoter_f
            df = fetch_contacts(promoter=promoter_q, status=status_f, search=search)
            if df.empty:
                st.info("Sin coincidencias.")
            else:
                df_show = df[["id","promoter","name","phone","neighborhood","status","notes"]].copy()
                st.dataframe(df_show, use_container_width=True, height=400)
                ids = st.text_input("IDs separados por coma (ej. 12,15,18)")
                ids_list = [s.strip() for s in ids.split(",") if s.strip().isdigit()] if ids else []
                colA, colB, colC = st.columns(3)
                newp = colA.selectbox("Nuevo promotor", ALLOWED_PROMOTERS)
                if colB.button("🔁 Reasignar seleccionados"):
                    n = reassign_contacts(ids_list, newp)
                    st.success(f"Reasignados: {n}")
                if colC.button("🗑️ Borrar seleccionados"):
                    n = delete_contacts(ids_list)
                    st.success(f"Borrados: {n}")

    # --- TAB CONFIGURACIÓN
    with tabs[4]:
        st.markdown("**Promotores permitidos:**")
        st.code(", ".join(ALLOWED_PROMOTERS))
        st.info("Para agregar o quitar promotores, edita la lista ALLOWED_PROMOTERS en el código.")
        st.markdown(f"**PIN actual:** `{ADMIN_PIN}` (edítalo en el código).")
        st.caption("La base se guarda en data/seguimiento.db (SQLite).")

# =========================
# ROUTING
# =========================
if st.session_state.role == "Promotor" and st.session_state.promoter:
    promoter_view()
elif st.session_state.role == "Administrador" and st.session_state.admin_ok:
    admin_view()
else:
    st.info("Inicia sesión desde la barra lateral.")
