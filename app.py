import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="Gestionale Affitti",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- GESTIONE LOGIN & SICUREZZA ---
def check_password():
    """Ritorna True se l'utente ha inserito la password corretta."""
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
        return True

    # Interfaccia di Login
    st.markdown("<br><br><h2 style='text-align: center;'>🔒 Accesso Riservato - Gestionale Immobili</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("login_form"):
            password_input = st.text_input("Inserisci Password:", type="password")
            submit_login = st.form_submit_button("Accedi", use_container_width=True)
            
            if submit_login:
                master_password = st.secrets.get("PASSWORD_GESTIONALE", "admin123")
                if password_input == master_password:
                    st.session_state["password_correct"] = True
                    st.rerun()
                else:
                    st.error("❌ Password errata.")
    return False

if not check_password():
    st.stop()

# --- DATABASE INIZIALIZZAZIONE ---
def get_db():
    conn = sqlite3.connect("gestionale_estivo.db", check_same_thread=False)
    return conn

conn = get_db()
c = conn.cursor()

# Tabella Locali
c.execute('''CREATE TABLE IF NOT EXISTS locali
             (id INTEGER PRIMARY KEY AUTOINCREMENT, 
              nome TEXT UNIQUE, 
              indirizzo TEXT, 
              periodo TEXT, 
              canone REAL)''')

# Tabella Utenze / Affitti Invernali
c.execute('''CREATE TABLE IF NOT EXISTS utenze
             (id INTEGER PRIMARY KEY AUTOINCREMENT, 
              locale_id INTEGER, 
              mese TEXT, 
              luce REAL DEFAULT 0, 
              gas REAL DEFAULT 0, 
              acqua REAL DEFAULT 0, 
              spese_condominio REAL DEFAULT 0, 
              affitto_versato REAL DEFAULT 0, 
              note TEXT, 
              pagato TEXT)''')

# Tabella Prenotazioni Estive
c.execute('''CREATE TABLE IF NOT EXISTS prenotazioni
             (id INTEGER PRIMARY KEY AUTOINCREMENT, 
              locale_id INTEGER, 
              ospite TEXT, 
              telefono TEXT, 
              checkin TEXT, 
              checkout TEXT, 
              totale REAL, 
              acconto REAL, 
              saldo REAL, 
              stato TEXT, 
              note TEXT)''')

# Tabella Uscite / Spese
c.execute('''CREATE TABLE IF NOT EXISTS uscite
             (id INTEGER PRIMARY KEY AUTOINCREMENT, 
              data_spesa TEXT, 
              categoria TEXT, 
              descrizione TEXT, 
              importo REAL, 
              inserito_da TEXT)''')
conn.commit()

# --- SIDEBAR & BARRA DI NAVIGAZIONE ---
st.sidebar.title("🏡 Gestionale Immobili")
st.sidebar.markdown("---")

menu = st.sidebar.radio(
    "Navigazione Menu:",
    [
        "🏠 Anagrafica Locali",
        "❄️ Affitti Invernali & Utenze",
        "☀️ Prenotazioni Estive",
        "💸 Registro Uscite / Spese"
    ]
)

st.sidebar.markdown("---")
if st.sidebar.button("🚪 Esci (Logout)"):
    st.session_state["password_correct"] = False
    st.rerun()

# ---------------------------------------------------------
# 1. ANAGRAFICA LOCALI
# ---------------------------------------------------------
if menu == "🏠 Anagrafica Locali":
    st.title("🏠 Anagrafica Locali e Immobili")
    st.caption("Gestisci le schede dei tuoi immobili registrati")
    
    with st.expander("➕ Aggiungi / Modifica Un Nuovo Locale", expanded=False):
        with st.form("form_locale", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            nome_loc = col_a.text_input("Nome Identificativo (es. CUPOLE GIÙ)*")
            indirizzo_loc = col_b.text_input("Indirizzo Completo")
            periodo_loc = col_a.text_input("Tipologia / Periodo (es. Settembre - Maggio)")
            canone_loc = col_b.number_input("Canone Mensile di Riferimento (€)", min_value=0.0, step=50.0)
            
            btn_salva = st.form_submit_button("💾 Salva Locale")
            if btn_salva:
                if nome_loc.strip():
                    try:
                        c.execute("INSERT INTO locali (nome, indirizzo, periodo, canone) VALUES (?, ?, ?, ?)",
                                  (nome_loc.strip().upper(), indirizzo_loc, periodo_loc, canone_loc))
                        conn.commit()
                        st.success(f"Locale '{nome_loc.upper()}' salvato con successo!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Un locale con questo nome esiste già!")
                else:
                    st.warning("Inserisci almeno il nome del locale.")

    # Visualizzazione Locali
    locali_df = pd.read_sql_query("SELECT * FROM locali ORDER BY nome ASC", conn)
    if not locali_df.empty:
        st.subheader("Elenco Immobili Registrati")
        cols = st.columns(2)
        for idx, row in locali_df.iterrows():
            with cols[idx % 2]:
                with st.container(border=True):
                    st.markdown(f"### 🏠 {row['nome']}")
                    st.write(f"📍 **Indirizzo:** {row['indirizzo'] if row['indirizzo'] else 'Non specificato'}")
                    st.write(f"📅 **Periodo:** {row['periodo'] if row['periodo'] else 'Non specificato'}")
                    st.write(f"💶 **Canone Mensile:** {row['canone']:.2f} €")
                    
                    if st.button(f"🗑️ Elimina {row['nome']}", key=f"del_loc_{row['id']}"):
                        c.execute("DELETE FROM locali WHERE id=?", (row['id'],))
                        conn.commit()
                        st.success("Locale eliminato!")
                        st.rerun()
    else:
        st.info("Nessun locale presente in archivio. Aggiungi il primo dal riquadro sopra.")

# ---------------------------------------------------------
# 2. AFFITTI INVERNALI & UTENZE
# ---------------------------------------------------------
elif menu == "❄️ Affitti Invernali & Utenze":
    st.title("❄️ Gestione Affitti Invernali & Utenze Mese per Mese")
    
    locali_df = pd.read_sql_query("SELECT * FROM locali ORDER BY nome ASC", conn)
    if locali_df.empty:
        st.warning("⚠️ Prima di proseguire, inserisci almeno un locale nell'Anagrafica!")
    else:
        locale_sel = st.selectbox("Seleziona Locale:", locali_df["nome"].tolist())
        locale_id = locali_df[locali_df["nome"] == locale_sel]["id"].values[0]
        
        with st.expander("➕ Registra Mese / Utenze per questo Locale"):
            with st.form("form_utenza", clear_on_submit=True):
                col1, col2, col3 = st.columns(3)
                mese_ref = col1.text_input("Mese di Riferimento (es. Ottobre 2026)*")
                affitto_v = col2.number_input("Canone Affitto Versato (€)", min_value=0.0, step=50.0)
                stato_pag = col3.selectbox("Stato Pagamento:", ["🔴 Da Saldare", "🟢 In Regola", "🟠 Parziale"])
                
                c_a, c_b, c_c, c_d = st.columns(4)
                luce_val = c_a.number_input("Luce (€)", min_value=0.0, step=10.0)
                gas_val = c_b.number_input("Gas (€)", min_value=0.0, step=10.0)
                acqua_val = c_c.number_input("Acqua (€)", min_value=0.0, step=10.0)
                cond_val = c_d.number_input("Condominio (€)", min_value=0.0, step=10.0)
                
                note_u = st.text_input("Note generali")
                btn_u = st.form_submit_button("💾 Salva Registrazione Mese")
                
                if btn_u and mese_ref.strip():
                    c.execute("""INSERT INTO utenze 
                                 (locale_id, mese, luce, gas, acqua, spese_condominio, affitto_versato, note, pagato)
                                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                              (locale_id, mese_ref.strip(), luce_val, gas_val, acqua_val, cond_val, affitto_v, note_u, stato_pag))
                    conn.commit()
                    st.success("Mese registrato con successo!")
                    st.rerun()

        st.subheader(f"Storico Utenze e Registri: {locale_sel}")
        utenze_df = pd.read_sql_query(
            "SELECT id, mese AS 'Mese', affitto_versato AS 'Affitto (€)', luce AS 'Luce (€)', gas AS 'Gas (€)', acqua AS 'Acqua (€)', spese_condominio AS 'Condominio (€)', pagato AS 'Stato', note AS 'Note' FROM utenze WHERE locale_id=? ORDER BY id DESC",
            conn, params=(locale_id,)
        )
        if not utenze_df.empty:
            st.dataframe(utenze_df, use_container_width=True)
        else:
            st.caption("Nessuna registrazione presente per questo locale.")

# ---------------------------------------------------------
# 3. PRENOTAZIONI ESTIVE
# ---------------------------------------------------------
elif menu == "☀️ Prenotazioni Estive":
    st.title("☀️ Calendario & Prenotazioni Estive")
    
    locali_df = pd.read_sql_query("SELECT * FROM locali ORDER BY nome ASC", conn)
    if locali_df.empty:
        st.warning("⚠️ Prima di proseguire, inserisci almeno un locale nell'Anagrafica!")
    else:
        locale_sel = st.selectbox("Seleziona Locale da Gestire:", locali_df["nome"].tolist())
        locale_id = locali_df[locali_df["nome"] == locale_sel]["id"].values[0]
        
        with st.expander("➕ Nuova Prenotazione Estiva"):
            with st.form("form_prenotazione", clear_on_submit=True):
                col1, col2 = st.columns(2)
                nome_ospite = col1.text_input("Nome e Cognome Ospite*")
                tel_ospite = col2.text_input("Telefono / Contatto")
                
                col3, col4 = st.columns(2)
                checkin_d = col3.date_input("Data Check-in")
                checkout_d = col4.date_input("Data Check-out")
                
                col5, col6 = st.columns(2)
                totale_p = col5.number_input("Prezzo Totale Soggiorno (€)", min_value=0.0, step=50.0)
                acconto_p = col6.number_input("Caparra / Acconto Versato (€)", min_value=0.0, step=50.0)
                
                saldo_p = totale_p - acconto_p
                st.info(f"💰 Saldo Da Incassare al Check-in: **{saldo_p:.2f} €**")
                
                stato_p = st.selectbox("Stato Prenotazione:", ["🟠 Caparra Ricevuta", "🟢 Saldato Completamente", "🔴 In Attesa Caparra", "⚫ Annullata"])
                note_p = st.text_area("Note / Richieste particolari")
                
                btn_p = st.form_submit_button("💾 Conferma e Salva Prenotazione")
                if btn_p and nome_ospite.strip():
                    c.execute("""INSERT INTO prenotazioni 
                                 (locale_id, ospite, telefono, checkin, checkout, totale, acconto, saldo, stato, note)
                                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                              (locale_id, nome_ospite.strip(), tel_ospite, str(checkin_d), str(checkout_d), totale_p, acconto_p, saldo_p, stato_p, note_p))
                    conn.commit()
                    st.success("Prenotazione salvata!")
                    st.rerun()

        st.subheader(f"Prenotazioni Registrate per {locale_sel}")
        preno_df = pd.read_sql_query(
            "SELECT id, ospite AS 'Ospite', telefono AS 'Telefono', checkin AS 'Check-in', checkout AS 'Check-out', totale AS 'Totale (€)', acconto AS 'Acconto (€)', saldo AS 'Saldo (€)', stato AS 'Stato', note AS 'Note' FROM prenotazioni WHERE locale_id=? ORDER BY checkin ASC",
            conn, params=(locale_id,)
        )
        if not preno_df.empty:
            st.dataframe(preno_df, use_container_width=True)
        else:
            st.caption("Nessuna prenotazione presente per questo immobile.")

# ---------------------------------------------------------
# 4. REGISTRO USCITE / SPESE
# ---------------------------------------------------------
elif menu == "💸 Registro Uscite / Spese":
    st.title("💸 Registro Spese e Manutenzioni")
    
    with st.expander("➕ Registra Nuova Uscita / Spesa"):
        with st.form("form_spesa", clear_on_submit=True):
            col1, col2 = st.columns(2)
            d_spesa = col1.date_input("Data della Spesa")
            cat_spesa = col2.selectbox("Categoria:", ["Manutenzione Ordinaria", "Lavori / Ristrutturazione", "Pulizie / Lavanderia", "Tasse / Bollette", "Acquisti Arredamento", "Altro"])
            
            col3, col4 = st.columns(2)
            desc_spesa = col3.text_input("Descrizione / Dettaglio Spesa*")
            imp_spesa = col4.number_input("Importo (€)", min_value=0.0, step=10.0)
            
            chi_registra = st.text_input("Inserito da (es. Nome Utente)")
            
            btn_s = st.form_submit_button("💾 Registra Spesa")
            if btn_s and desc_spesa.strip():
                c.execute("INSERT INTO uscite (data_spesa, categoria, descrizione, importo, inserito_da) VALUES (?, ?, ?, ?, ?)",
                          (str(d_spesa), cat_spesa, desc_spesa.strip(), imp_spesa, chi_registra))
                conn.commit()
                st.success("Spesa registrata!")
                st.rerun()

    spese_df = pd.read_sql_query("SELECT id, data_spesa AS 'Data', categoria AS 'Categoria', descrizione AS 'Descrizione', importo AS 'Importo (€)', inserito_da AS 'Registrato Da' FROM uscite ORDER BY data_spesa DESC", conn)
    if not spese_df.empty:
        st.dataframe(spese_df, use_container_width=True)
        totale_spese = spese_df["Importo (€)"].sum()
        st.metric(label="Totale Uscite Registrate", value=f"{totale_spese:.2f} €")
    else:
        st.info("Nessuna spesa o uscita registrata finora.")
