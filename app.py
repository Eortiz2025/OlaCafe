# streamlit_app.py
import streamlit as st
import pandas as pd
import sqlite3, os, hashlib, json
from datetime import datetime, timedelta
from io import BytesIO

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Seguimiento de Llamadas · Campaña", layout="centered")
DB_PATH = "data/seguimiento.db"
os.makedirs("data", exist_ok=True)

# EDITA:
ALLOWED_PROMOTERS = sorted(list(set([n.strip() for n in [
    "Tania","Olga","Emilio","Sergio","Juan","Elvia","Claudia","María","Pedro","Luis","Ana","Carmen","Hugo","Martha","Carlos"
] if n.strip()])))
ADMIN_PIN = "2468"

CALL_STATES = ["Pendiente","Contactado - Neutral","Convencido","Indeciso","Rechazó","No contestó","Número incorrecto","DNC"]  # DNC = Do Not Contact
REASONS = ["Interesado en propuesta económica","Inseguro por seguridad","Molestia por política","No vive en la zona","Número repetido","Otros"]
SEGMENTS = ["Prioritario","Simpatizante","Neutro","Opositor","Desconocido"]
ISSUES   = ["Economía","Seguridad","Servicios","Valores","Corrupción","Otros"]

# Guiones A/B por segmento/tema (muy breve). Se asignan automáticamente por aleatoriedad.
SCRIPTS = {
    "A": {
        "base": "Hola {nombre}, te hablo como ciudadano. Este {fecha} buscamos tu voto para {candidato}. ¿Puedo contarte en 20s por qué es distinto?",
        "Economía": "La propuesta central: bajar gasto inútil y apoyar a quien trabaja. ¿Te interesa recibir un resumen por WhatsApp?",
        "Seguridad": "Plan claro: policía local profesional y justicia rápida al delincuente. ¿Te mando el plan en 1 página?",
        "Servicios": "Arreglar lo básico primero: agua, baches, alumbrado. ¿Te envío la ruta de mejoras de tu colonia?",
        "Valores": "Orden, familia y trabajo. Sin improvisaciones. ¿Te mando el compromiso firmado?",
        "Corrupción": "Auditorías trimestrales y compras abiertas. ¿Te comparto cómo lo vamos a hacer?"
    },
    "B": {
        "base": "Hola {nombre}, soy {promotor}. Hacemos una consulta breve: ¿qué te importa más hoy, economía o seguridad?",
        "Economía": "Tenemos un plan para que alcance más: disciplina fiscal + impulso a negocios. ¿Te envío el resumen?",
        "Seguridad": "Tolerancia cero al delito y apoyo a policías. ¿Te comparto las 3 acciones inmediatas?",
        "Servicios": "Primero tu calle: agenda pública de obras. ¿Quieres el link?",
        "Valores": "Cuidar lo que funciona y corregir excesos. ¿Te mando el compromiso?",
        "Corrupción": "Candados reales anti-corrupción, medibles. ¿Gustas verlo por WhatsApp?"
    }
}

WHATSAPP_TPL = {
    "Convencido": "Hola {nombre}, gracias por tu apoyo. Te envío el resumen: {link}",
    "Indeciso": "Hola {nombre}, aquí va la info de {issue}: {link}. ¿Lo revisas y te marco mañana?",
    "Contactado - Neutral": "Hola {nombre}, te comparto en 1 página: {link}",
}

# =========================
# DB
# =========================
def conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    with conn() as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS contacts(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            promoter TEXT NOT NULL,
            name TEXT NOT NULL,
            phone TEXT,
            neighborhood TEXT,
            notes TEXT,
            status TEXT DEFAULT 'Pendiente',
            reason TEXT,
            segment TEXT DEFAULT 'Desconocido',
            issue_tag TEXT DEFAULT 'Economía',
            attempts INTEGER DEFAULT 0,
            last_call_ts TEXT,
            next_action_ts TEXT,
            dnc INTEGER DEFAULT 0,
            consent_whatsapp INTEGER DEFAULT 0,
            script_arm TEXT,
            source TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT
        );
        """)
        con.execute("""
        CREATE TABLE IF NOT EXISTS audit(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_id INTEGER,
            promoter TEXT,
            action TEXT,
            from_status TEXT,
            to_status TEXT,
            ts TEXT,
            meta TEXT
        );
        """)
        # índices útiles
        con.execute("CREATE INDEX IF NOT EXISTS idx_contacts_promoter ON contacts(promoter);")
        con.execute("CREATE INDEX IF NOT EXISTS idx_contacts_status ON contacts(status);")
        con.execute("CREATE INDEX IF NOT EXISTS idx_contacts_phone ON contacts(phone);")
        con.commit()

def upsert_contact(**kwargs):
    with conn() as con:
        fields = ",".join(kwargs.keys())
        qmarks = ",".join(["?"]*len(kwargs))
        con.execute(f"INSERT INTO contacts ({fields}) VALUES ({qmarks})", tuple(kwargs.values()))
        con.commit()

def fetch_contacts(promoter=None, status=None, search=None, only_mine=False):
    q = "SELECT * FROM contacts WHERE 1=1"
    p = []
    if promoter and only_mine:
        q += " AND promoter=?"; p.append(promoter)
    if status and status!="Todos":
        q += " AND status=?"; p.append(status)
    if search:
        s = f"%{search.lower()}%"
        q += " AND (LOWER(name) LIKE ? OR LOWER(phone) LIKE ? OR LOWER(neighborhood) LIKE ? OR LOWER(notes) LIKE ? OR LOWER(source) LIKE ?)"
        p += [s,s,s,s,s]
    q += " ORDER BY id DESC"
    with conn() as con:
        return pd.read_sql_query(q, con, params=p)

def save_edits(ed, orig, promoter_name):
    # Detecta cambios de estado/notas/segment/issue/reason/next_action_ts/consent/dnc
    merged = ed.merge(orig, on="id", suffixes=("_e",""), how="left")
    n=0
    with conn() as con:
        for _, r in merged.iterrows():
            changed = False
            updates = {}
            audit_meta = {}
            # Campos editables
            for field_map in [
                ("status","status","Estado"),
                ("notes","notes","Notas"),
                ("segment","segment","Segmento"),
                ("issue_tag","issue_tag","Tema"),
                ("reason","reason","Motivo"),
                ("next_action_ts","next_action_ts","Próxima acción"),
                ("consent_whatsapp","consent_whatsapp","Consent WA"),
                ("dnc","dnc","DNC"),
            ]:
                key_db, key_orig, key_edlabel = field_map
                val_new = r[f"{key_edlabel}"] if key_edlabel in ed.columns else r[key_db]
                # normalizar booleanos
                if key_db in ["consent_whatsapp","dnc"]:
                    val_new = 1 if str(val_new) in ["1","True","true","Sí","Si","sí"] else 0
                if str(val_new) != str(r[key_orig]):
                    updates[key_db] = val_new
                    changed = True
                    audit_meta[key_db] = {"from": r[key_orig], "to": val_new}

            # Si status cambió, sube attempts y last_call_ts
            if "status" in updates or (r.get("Estado") != r.get("status")):
                updates["attempts"] = int(r["attempts"] or 0) + 1
                updates["last_call_ts"] = datetime.now().isoformat()

            if changed:
                set_clause = ", ".join([f"{k}=?" for k in updates.keys()])
                vals = list(updates.values()) + [int(r["id"])]
                con.execute(f"UPDATE contacts SET {set_clause}, updated_at=? WHERE id=?", (*updates.values(), datetime.now().isoformat(), int(r["id"])))
                con.execute("INSERT INTO audit(contact_id,promoter,action,from_status,to_status,ts,meta) VALUES (?,?,?,?,?,?,?)",
                            (int(r["id"]), promoter_name, "edit", r["status"], updates.get("status", r["status"]),
                             datetime.now().isoformat(), json.dumps(audit_meta)))
                n += 1
        con.commit()
    return n

def reassign(ids, new_promoter, who):
    if not ids: return 0
    with conn() as con:
        for cid in ids:
            con.execute("UPDATE contacts SET promoter=?, updated_at=? WHERE id=?", (new_promoter, datetime.now().isoformat(), int(cid)))
            con.execute("INSERT INTO audit(contact_id,promoter,action,from_status,to_status,ts,meta) VALUES (?,?,?,?,?,?,?)",
                        (int(cid), who, "reassign", None, None, datetime.now().isoformat(), json.dumps({"to":new_promoter})))
        con.commit()
    return len(ids)

def delete_ids(ids, who):
    if not ids: return 0
    with conn() as con:
        for cid in ids:
            con.execute("DELETE FROM contacts WHERE id=?", (int(cid),))
            con.execute("INSERT INTO audit(contact_id,promoter,action,from_status,to_status,ts,meta) VALUES (?,?,?,?,?,?,?)",
                        (int(cid), who, "delete", None, None, datetime.now().isoformat(), json.dumps({})))
        con.commit()
    return len(ids)

# =========================
# UTILS
# =========================
def hash_arm(name, phone):
    seed = (str(name)+str(phone)).encode("utf-8")
    h = int(hashlib.md5(seed).hexdigest(), 16)
    return "A" if (h % 2)==0 else "B"

def pick_script(arm, issue):
    base = SCRIPTS[arm]["base"]
    extra = SCRIPTS[arm].get(issue, SCRIPTS[arm]["Economía"])
    return base + " " + extra

def tel_link(p): return f"tel:{str(p).strip()}" if p else ""
def wa_link(p, text="Hola, ¿podemos platicar un minuto?"): 
    if not p: return ""
    phone = str(p).replace(" ","").replace("-","")
    return f"https://wa.me/{phone}?text={text}"

def download_xlsx(df, name="reporte.xlsx"):
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as w:
        df.to_excel(w, index=False, sheet_name="Datos")
    buf.seek(0)
    st.download_button("📥 Descargar Excel", buf, file_name=name, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# =========================
# INIT + SESSION
# =========================
init_db()
if "role" not in st.session_state: st.session_state.role = None
if "promoter" not in st.session_state: st.session_state.promoter = None
if "admin_ok" not in st.session_state: st.session_state.admin_ok = False

st.title("📞 Seguimiento de llamadas · Invitar a votar")

# =========================
# SIDEBAR LOGIN
# =========================
with st.sidebar:
    st.header("Acceso")
    role = st.radio("Entrar como:", ["Promotor","Administrador"], index=0)
    if role == "Promotor":
        who = st.text_input("Tu nombre (exacto)", placeholder="Ej. Tania")
        if st.button("Entrar", type="primary", use_container_width=True):
            if who.strip() in ALLOWED_PROMOTERS:
                st.session_state.role = "Promotor"
                st.session_state.promoter = who.strip()
            else:
                st.error("Nombre no autorizado.")
        st.caption("Solo verás tus contactos.")
    else:
        pin = st.text_input("PIN admin", type="password")
        if st.button("Entrar", type="primary", use_container_width=True):
            if pin == ADMIN_PIN:
                st.session_state.role = "Administrador"
                st.session_state.admin_ok = True
            else:
                st.error("PIN incorrecto.")
        st.caption("Vista global, importación, métricas.")

# =========================
# PROMOTOR VIEW
# =========================
def promoter_view():
    me = st.session_state.promoter
    st.subheader(f"👤 Promotor: {me}")

    with st.expander("➕ Agregar contacto", expanded=False):
        c1,c2 = st.columns(2)
        name = c1.text_input("Nombre*", "")
        phone = c2.text_input("Teléfono", "")
        c3,c4 = st.columns(2)
        neighborhood = c3.text_input("Colonia/Zona","")
        issue = c4.selectbox("Tema principal", ISSUES, index=0)
        c5,c6 = st.columns(2)
        segment = c5.selectbox("Segmento", SEGMENTS, index=4)
        source = c6.text_input("Fuente (lista, puerta, ref.)","")
        notes = st.text_input("Notas","")
        consent = st.checkbox("Tiene consentimiento para WhatsApp", value=False)
        if st.button("Guardar", type="primary"):
            if not name.strip():
                st.warning("Nombre es obligatorio.")
            else:
                arm = hash_arm(name, phone)
                upsert_contact(
                    promoter=me, name=name.strip(), phone=phone.strip(),
                    neighborhood=neighborhood.strip(), notes=notes.strip(),
                    status="Pendiente", reason=None, segment=segment, issue_tag=issue,
                    attempts=0, last_call_ts=None, next_action_ts=None, dnc=0,
                    consent_whatsapp=1 if consent else 0, script_arm=arm, source=source.strip(),
                    created_at=datetime.now().isoformat(), updated_at=None
                )
                st.success("Contacto agregado.")

    st.divider()

    # Filtros rápidos operativos
    f1,f2,f3,f4 = st.columns([2,1,1,1])
    search = f1.text_input("Buscar (nombre/tel/colonia/notas/fuente)")
    status = f2.selectbox("Estado", ["Todos"] + CALL_STATES, index=0)
    segment = f3.selectbox("Segmento", ["Todos"] + SEGMENTS, index=0)
    only_due = f4.toggle("Solo con acción pendiente", value=False)

    df = fetch_contacts(promoter=me, status=status, search=search, only_mine=True)
    if segment != "Todos": df = df[df["segment"]==segment]
    if only_due: 
        now = datetime.now().isoformat()
        df = df[(df["next_action_ts"].notna()) & (df["next_action_ts"] <= now)]
    st.caption(f"Total: {len(df)}")

    if df.empty:
        st.info("Sin contactos.")
        return

    # Script asignado A/B
    with st.expander("🗣️ Guion sugerido (A/B) por contacto", expanded=False):
        st.write("Selecciona un contacto para ver su guion.")
        sample = df.iloc[0]
        st.code(pick_script(sample["script_arm"], sample["issue_tag"]).format(
            nombre=sample["name"], promotor=me, fecha="{fecha}", candidato="{candidato}"
        ))

    # Acciones rápidas por fila
    show = df.copy()
    show["Llamar"] = show["phone"].apply(lambda p: f"[📲]({tel_link(p)})" if p else "")
    def wa_btn(row):
        if not row["phone"] or int(row["consent_whatsapp"] or 0)==0: return ""
        tpl = WHATSAPP_TPL.get("Contactado - Neutral","Hola {nombre}").format(
            nombre=row["name"], issue=row["issue_tag"], link="https://tudominio/plan.pdf"
        )
        return f"[💬]({wa_link(row['phone'], tpl)})"
    show["WhatsApp"] = show.apply(wa_btn, axis=1)

    # Columnas editables clave
    show = show.rename(columns={
        "name":"Nombre","phone":"Teléfono","neighborhood":"Colonia","notes":"Notas",
        "status":"Estado","reason":"Motivo","segment":"Segmento","issue_tag":"Tema",
        "attempts":"Intentos","last_call_ts":"Última llamada","next_action_ts":"Próxima acción",
        "consent_whatsapp":"Consent WA","dnc":"DNC","source":"Fuente","created_at":"Creado"
    })
    cols = ["id","Nombre","Teléfono","Colonia","Tema","Segmento","Estado","Motivo","Notas",
            "Intentos","Última llamada","Próxima acción","Consent WA","DNC","Llamar","WhatsApp","Fuente","Creado"]
    cols = [c for c in cols if c in show.columns]
    edited = st.data_editor(
        show[cols],
        hide_index=True,
        column_config={
            "Estado": st.column_config.SelectboxColumn(options=CALL_STATES),
            "Motivo": st.column_config.SelectboxColumn(options=REASONS),
            "Segmento": st.column_config.SelectboxColumn(options=SEGMENTS),
            "Tema": st.column_config.SelectboxColumn(options=ISSUES),
            "Consent WA": st.column_config.CheckboxColumn(),
            "DNC": st.column_config.CheckboxColumn(),
            "Próxima acción": st.column_config.DatetimeColumn(format="YYYY-MM-DD HH:mm"),
            "Llamar": st.column_config.LinkColumn(),
            "WhatsApp": st.column_config.LinkColumn(),
        },
        disabled=["id","Intentos","Última llamada","Llamar","WhatsApp","Creado","Fuente"],
        use_container_width=True,
        key="prom_editor"
    )

    # Botones de resultado rápido
    c1,c2,c3,c4 = st.columns(4)
    if c1.button("✅ Convencido (+ cita mañana)"):
        # set estado y próxima acción para seleccionados? Tomamos todos visibles
        now = datetime.now()
        edited["Estado"] = "Convencido"
        edited["Próxima acción"] = (now + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    if c2.button("🤝 Indeciso (reintento 24h)"):
        edited["Estado"] = "Indeciso"
        edited["Próxima acción"] = (datetime.now() + timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    if c3.button("📵 No contesta (reintento 4h)"):
        edited["Estado"] = "No contestó"
        edited["Próxima acción"] = (datetime.now() + timedelta(hours=4)).strftime("%Y-%m-%d %H:%M:%S")
    if c4.button("🚫 DNC"):
        edited["DNC"] = True
        edited["Estado"] = "DNC"

    # Guardar
    if st.button("💾 Guardar cambios", type="primary"):
        # Recuperar original para comparar
        orig = fetch_contacts(promoter=me, status="Todos", search=None, only_mine=True)
        n = save_edits(edited, orig, me)
        st.success(f"Cambios guardados: {n}")

    # Resumen
    st.markdown("#### 📊 Resumen")
    agg = df.groupby("status").size().reindex(CALL_STATES, fill_value=0).reset_index()
    agg.columns = ["Estado","Total"]
    st.table(agg)

    # Export personal
    download_xlsx(show, f"reporte_{me}.xlsx")

# =========================
# ADMIN VIEW
# =========================
def admin_view():
    st.subheader("🛠️ Panel administrador")
    tabs = st.tabs(["📋 Contactos","📈 Métricas","📥 Importar/Dedup","🔁 Reasignar/Borrar","🧾 Auditoría","⚙️ Config"])

    # CONTACTOS
    with tabs[0]:
        c1,c2,c3,c4 = st.columns([1,1,2,1])
        promoter_f = c1.selectbox("Promotor", ["Todos"]+ALLOWED_PROMOTERS, index=0)
        status_f = c2.selectbox("Estado", ["Todos"]+CALL_STATES, index=0)
        search = c3.text_input("Buscar")
        only_due = c4.toggle("Solo con acción pendiente", value=False)

        df = fetch_contacts(promoter=None if promoter_f=="Todos" else promoter_f, status=status_f, search=search, only_mine=False)
        if only_due:
            now = datetime.now().isoformat()
            df = df[(df["next_action_ts"].notna()) & (df["next_action_ts"] <= now)]
        st.caption(f"Total: {len(df)}")

        if df.empty:
            st.info("Sin registros.")
        else:
            view = df.copy()
            view["Llamar"] = view["phone"].apply(lambda p: f"[📲]({tel_link(p)})" if p else "")
            view["WhatsApp"] = view.apply(lambda r: f"[💬]({wa_link(r['phone'])})" if r["phone"] and int(r["consent_whatsapp"] or 0)==1 else "", axis=1)
            view = view.rename(columns={
                "name":"Nombre","phone":"Teléfono","neighborhood":"Colonia","notes":"Notas","status":"Estado",
                "reason":"Motivo","segment":"Segmento","issue_tag":"Tema","attempts":"Intentos",
                "last_call_ts":"Última llamada","next_action_ts":"Próxima acción","consent_whatsapp":"Consent WA",
                "dnc":"DNC","source":"Fuente","promoter":"Promotor","created_at":"Creado","script_arm":"Brazo"
            })
            cols = ["id","Promotor","Nombre","Teléfono","Colonia","Tema","Segmento","Estado","Motivo","Notas",
                    "Intentos","Última llamada","Próxima acción","Consent WA","DNC","Brazo","Llamar","WhatsApp","Fuente","Creado"]
            edited = st.data_editor(
                view[cols],
                hide_index=True,
                column_config={
                    "Estado": st.column_config.SelectboxColumn(options=CALL_STATES),
                    "Motivo": st.column_config.SelectboxColumn(options=REASONS),
                    "Segmento": st.column_config.SelectboxColumn(options=SEGMENTS),
                    "Tema": st.column_config.SelectboxColumn(options=ISSUES),
                    "Consent WA": st.column_config.CheckboxColumn(),
                    "DNC": st.column_config.CheckboxColumn(),
                    "Próxima acción": st.column_config.DatetimeColumn(format="YYYY-MM-DD HH:mm"),
                    "Llamar": st.column_config.LinkColumn(),
                    "WhatsApp": st.column_config.LinkColumn(),
                    "Promotor": st.column_config.SelectboxColumn(options=ALLOWED_PROMOTERS),
                },
                disabled=["id","Intentos","Última llamada","Brazo","Llamar","WhatsApp","Creado"],
                use_container_width=True,
                key="admin_editor"
            )
            if st.button("💾 Guardar ediciones", type="primary"):
                orig = fetch_contacts(promoter=None if promoter_f=="Todos" else promoter_f, status=status_f, search=search, only_mine=False)
                n = save_edits(edited, orig, "ADMIN")
                st.success(f"Actualizados: {n}")

            download_xlsx(view, "reporte_global.xlsx")

    # MÉTRICAS
    with tabs[1]:
        df = fetch_contacts()
        if df.empty:
            st.info("Sin datos.")
        else:
            # Eficacia por promotor (Convencido / Contactos)
            conv = (df["status"]=="Convencido").groupby(df["promoter"]).sum().rename("Convencidos")
            total = df.groupby("promoter")["id"].count().rename("Contactos")
            nc = (df["status"]=="No contestó").groupby(df["promoter"]).sum().rename("NoContestó")
            met = pd.concat([total, conv, nc], axis=1).fillna(0)
            met["Tasa Conversión %"] = (met["Convencidos"]/met["Contactos"]*100).round(1).fillna(0)
            st.markdown("#### 🏁 Eficacia por promotor")
            st.dataframe(met)

            st.markdown("#### 🔎 Distribución por estado")
            dist = df["status"].value_counts().reindex(CALL_STATES, fill_value=0).reset_index()
            dist.columns = ["Estado","Total"]
            st.table(dist)

            st.markdown("#### ⏰ Acciones pendientes (vencidas)")
            due = df[(df["next_action_ts"].notna()) & (df["next_action_ts"] <= datetime.now().isoformat())]
            st.dataframe(due[["id","promoter","name","phone","status","next_action_ts","notes"]], use_container_width=True)

    # IMPORTAR / DEDUP
    with tabs[2]:
        st.markdown("Sube CSV/XLSX con columnas: name, phone, neighborhood, notes, promoter, segment, issue_tag, source, consent_whatsapp (0/1)")
        up = st.file_uploader("Archivo", type=["csv","xlsx"])
        dedup_on_phone = st.checkbox("Eliminar duplicados por teléfono (mantener el primero)", value=True)
        if up:
            try:
                df = pd.read_csv(up) if up.name.lower().endswith(".csv") else pd.read_excel(up)
                df.columns = [c.strip().lower() for c in df.columns]
                if "name" not in df.columns: st.error("Falta columna 'name'"); st.stop()
                if "promoter" not in df.columns: df["promoter"] = "SIN_ASIGNAR"
                if dedup_on_phone and "phone" in df.columns:
                    df = df.drop_duplicates(subset=["phone"], keep="first")
                ok=0
                with conn() as con:
                    for _, r in df.iterrows():
                        prom = str(r.get("promoter","")).strip()
                        if prom and prom!="SIN_ASIGNAR" and prom not in ALLOWED_PROMOTERS: 
                            continue
                        name = str(r.get("name","")).strip()
                        if not name: continue
                        phone = str(r.get("phone","") or "")
                        arm = hash_arm(name, phone)
                        con.execute("""
                            INSERT INTO contacts(promoter,name,phone,neighborhood,notes,status,reason,segment,issue_tag,attempts,
                            last_call_ts,next_action_ts,dnc,consent_whatsapp,script_arm,source,created_at,updated_at)
                            VALUES (?,?,?,?,?,'Pendiente',?,?,?,?,?,?,?,?,?,?,?,?)
                        """, (
                            prom or "SIN_ASIGNAR", name, phone,
                            str(r.get("neighborhood","") or ""), str(r.get("notes","") or ""),
                            None, str(r.get("segment","Desconocido") or "Desconocido"),
                            str(r.get("issue_tag","Economía") or "Economía"),
                            0, None, None,
                            1 if int(r.get("dnc",0) or 0)==1 else 0,
                            1 if int(r.get("consent_whatsapp",0) or 0)==1 else 0,
                            arm, str(r.get("source","") or ""),
                            datetime.now().isoformat(), None
                        ))
                        ok+=1
                    con.commit()
                st.success(f"Importados: {ok}")
            except Exception as e:
                st.error(f"Error al importar: {e}")

    # REASIGNAR / BORRAR
    with tabs[3]:
        df = fetch_contacts()
        if df.empty:
            st.info("Sin registros.")
        else:
            st.caption("Filtra, revisa IDs y actúa.")
            c1,c2,c3 = st.columns([1,1,2])
            pf = c1.selectbox("Promotor", ["Todos"]+ALLOWED_PROMOTERS, index=0, key="re_pf")
            sf = c2.selectbox("Estado", ["Todos"]+CALL_STATES, index=0, key="re_sf")
            search = c3.text_input("Buscar", key="re_search")
            view = fetch_contacts(None if pf=="Todos" else pf, sf, search, only_mine=False)
            st.dataframe(view[["id","promoter","name","phone","status","segment","issue_tag","attempts","next_action_ts"]], use_container_width=True, height=380)
            ids = st.text_input("IDs separados por coma (ej. 12,15,18)")
            lst = [s.strip() for s in ids.split(",") if s.strip().isdigit()] if ids else []
            colA, colB, colC = st.columns(3)
            newp = colA.selectbox("Nuevo promotor", ALLOWED_PROMOTERS)
            if colB.button("🔁 Reasignar"):
                n = reassign(lst, newp, "ADMIN")
                st.success(f"Reasignados: {n}")
            if colC.button("🗑️ Borrar"):
                n = delete_ids(lst, "ADMIN")
                st.success(f"Borrados: {n}")

    # AUDITORÍA
    with tabs[4]:
        with conn() as con:
            ad = pd.read_sql_query("SELECT * FROM audit ORDER BY id DESC LIMIT 1000", con)
        if ad.empty:
            st.info("Sin auditoría.")
        else:
            st.dataframe(ad, use_container_width=True, height=420)
            download_xlsx(ad, "auditoria.xlsx")

    # CONFIG
    with tabs[5]:
        st.markdown("**Promotores permitidos:**")
        st.code(", ".join(ALLOWED_PROMOTERS))
        st.markdown(f"**PIN:** `{ADMIN_PIN}`")
        st.caption("Base: data/seguimiento.db · Puedes respaldarla descargando el contenedor o montando almacenamiento persistente.")

# =========================
# ROUTER
# =========================
if st.session_state.role == "Promotor" and st.session_state.promoter:
    promoter_view()
elif st.session_state.role == "Administrador" and st.session_state.admin_ok:
    admin_view()
else:
    st.info("Inicia sesión desde la barra lateral.")
