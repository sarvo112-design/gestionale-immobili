import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="Gestionale Immobili",
    page_icon="🏠",
    layout="wide"
)

# --- GESTIONE LOGIN & SICUREZZA ---
def check_password():
    """Ritorna True se l'utente ha inserito la password corretta."""
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
        return True

    # Interfaccia di Login
    st.markdown("<h2 style='text-align: center;'>🔒 Accesso Riservato</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        password_input = st.text_input("Inserisci la Password di accesso:", type="password")
        if st.button("Accedi", use_container_width=True):
            # Recupera la password dai Secrets di Streamlit (o fallback di sicurezza)
            master_password = st.secrets.get("PASSWORD_GESTIONALE", "admin123")
            
            if password_input == master_password:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("❌ Password errata. Riprova.")
    return False

# Se il login non è superato, interrompe l'esecuzione dell'app
if not check_password():
    st.stop()

# --- DA QUI IN POI INIZIA IL GESTIONALE ---

# Tasto Logout nella Sidebar
st.sidebar.markdown("# 🏖️")
st.sidebar.title("Gestionale Immobili")
if st.sidebar.button("🚪 Esci (Logout)"):
    st.session_state["password_correct"] = False
    st.rerun()

# --- DATABASE INIZIALIZZAZIONE ---
conn = sqlite3.connect("gestionale_estivo.db", check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS locali
             (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, indirizzo TEXT, periodo TEXT, canone REAL)''')
c.execute('''CREATE TABLE IF NOT EXISTS utenze
             (id INTEGER PRIMARY KEY AUTOINCREMENT, locale_id INTEGER, mese TEXT, luce REAL, gas REAL, pagato TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS prenotazioni
             (id INTEGER PRIMARY KEY AUTOINCREMENT, locale_id INTEGER, ospite TEXT, checkin TEXT, checkout TEXT, totale REAL, acconto REAL, saldo REAL, stato TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS spese
             (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, descrizione TEXT, importo REAL, categoria TEXT)''')
conn.commit()

# --- NAVIGAZIONE ---
menu = st.sidebar.radio("Navigazione:", [
    "1. Anagrafica Locali", 
    "2. Affitti Invernali (Mesi & Utenze)", 
    "3. Calendario Prenotazioni Estive", 
    "4. Registro Uscite & Spese"
])

# 1. ANAGRAFICA LOCALI
if menu == "1. Anagrafica Locali":
    st.header("🏠 Anagrafica Locali")
    
    with st.expander("➕ Aggiungi Nuovo Locale"):
        with st.form("form_locale", clear_on_submit=True):
            nome = st.text_input("Nome Locale (es. CUPOLE GIÙ)")
            indirizzo = st.text_input("Indirizzo")
            periodo = st.text_input("Periodo (es. SETTEMBRE - MAGGIO o Non specifico)")
            canone = st.number_input("Canone Mensile (€)", min_value=0.0, step=50.0)
            submit = st.form_submit_button("Salva Locale")
            
            if submit and nome:
                c.execute("INSERT INTO locali (nome, indirizzo, periodo, canone) VALUES (?, ?, ?, ?)",
                          (nome, indirizzo, periodo, canone))
                conn.commit()
                st.success(f"Locale '{nome}' aggiunto con successo!")
                st.rerun()

    locali = pd.read_sql_query("SELECT * FROM locali", conn)
    if not locali.empty:
        cols = st.columns(2)
        for idx, row in locali.iterrows():
            with cols[idx % 2]:
                with st.container(border=True):
                    st.subheader(f"🏠 {row['nome']}")
                    st.write(f"📍 **Indirizzo:** {row['indirizzo']}")
                    st.write(f"📅 **Periodo:** {row['periodo']}")
                    st.write(f"💶 **Canone:** {row['canone']} €/mese")
                    
                    c1, c2 = st.columns(2)
                    if c1.button("🗑️ Elimina", key=f"del_{row['id']}"):
                        c.execute("DELETE FROM locali WHERE id=?", (row['id'],))
                        conn.commit()
                        st.rerun()

# 2. AFFITTI INVERNALI
elif menu == "2. Affitti Invernali (Mesi & Utenze)":
    st.header("❄️ Affitti Invernali & Utenze")
    locali = pd.read_sql_query("SELECT * FROM locali", conn)
    
    if locali.empty:
        st.warning("Inserisci prima un locale nell'Anagrafica Locali.")
    else:
        locale_scelto = st.selectbox("Seleziona Locale:", locali["nome"].tolist())
        locale_id = locali[locali["nome"] == locale_scelto]["id"].values[0]
        
        with st.expander("➕ Aggiungi Registro Mese / Utenze"):
            with st.form("form_utenze", clear_on_submit=True):
                mese = st.text_input("Mese (es. Ottobre 2026)")
                luce = st.number_input("Spesa Luce (€)", min_value=0.0, step=10.0)
                gas = st.number_input("Spesa Gas (€)", min_value=0.0, step=10.0)
                pagato = st.selectbox("Stato Pagamento:", ["🔴 Da Pagare", "🟢 Pagato"])
                submit = st.form_submit_button("Salva Registro")
                
                if submit and mese:
                    c.execute("INSERT INTO utenze (locale_id, mese, luce, gas, pagato) VALUES (?, ?, ?, ?, ?)",
                              (locale_id, luce, gas, pagato))
                    conn.commit()
                    st.success("Mese registrato!")
                    st.rerun()

        df_utenze = pd.read_sql_query("SELECT id, mese, luce, gas, pagato FROM utenze WHERE locale_id=?", conn, params=(locale_id,))
        st.dataframe(df_utenze, use_container_width=True)

# 3. PRENOTAZIONI ESTIVE
elif menu == "3. Calendario Prenotazioni Estive":
    st.header("☀️ Calendario Prenotazioni Estive")
    locali = pd.read_sql_query("SELECT * FROM locali", conn)
    
    if locali.empty:
        st.warning("Inserisci prima un locale in Anagrafica.")
    else:
        locale_scelto = st.selectbox("Seleziona Locale per Prenotazione:", locali["nome"].tolist())
        locale_id = locali[locali["nome"] == locale_scelto]["id"].values[0]
        
        with st.expander("➕ Nuova Prenotazione Estiva"):
            with st.form("form_prenotazione", clear_on_submit=True):
                ospite = st.text_input("Nome Ospite")
                c1, c2 = st.columns(2)
                checkin = c1.date_input("Check-in")
                checkout = c2.date_input("Check-out")
                totale = st.number_input("Totale Prezzo (€)", min_value=0.0, step=50.0)
                acconto = st.number_input("Acconto Versato (€)", min_value=0.0, step=50.0)
                saldo = totale - acconto
                st.info(f"Saldo Rimanente: {saldo} €")
                
                stato_pago = st.selectbox("Stato Finanziario:", ["🔴 Acconto Mancante", "🟠 Solo Acconto", "🟢 Saldato Fully", "⚫ Annullata"])
                submit = st.form_submit_button("Conferma Prenotazione")
                
                if submit and ospite:
                    c.execute("""INSERT INTO prenotazioni (locale_id, ospite, checkin, checkout, totale, acconto, saldo, stato) 
                                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                              (locale_id, ospite, str(checkin), str(checkout), totale, acconto, saldo, stato_pago))
                    conn.commit()
                    st.success("Prenotazione salvata!")
                    st.rerun()

        df_preno = pd.read_sql_query("SELECT id, ospite, checkin, checkout, totale, acconto, saldo, stato FROM prenotazioni WHERE locale_id=?", conn, params=(locale_id,))
        st.dataframe(df_preno, use_container_width=True)

# 4. REGISTRO SPESE
elif menu == "4. Registro Uscite & Spese":
    st.header("💸 Registro Uscite e Spese")
    
    with st.expander("➕ Registra Nuova Spesa"):
        with st.form("form_spesa", clear_on_submit=True):
            data_spesa = st.date_input("Data")
            desc = st.text_input("Descrizione Spesa")
            cat = st.selectbox("Categoria:", ["Manutenzione", "Pulizie", "Tasse/Bollette", "Arredo/Attrezzatura", "Altro"])
            importo = st.number_input("Importo (€)", min_value=0.0, step=10.0)
            submit = st.form_submit_button("Salva Spesa")
            
            if submit and desc:
                c.execute("INSERT INTO spese (data, descrizione, importo, categoria) VALUES (?, ?, ?, ?)",
                          (str(data_spesa), desc, importo, cat))
                conn.commit()
                st.success("Spesa registrata!")
                st.rerun()

    df_spese = pd.read_sql_query("SELECT * FROM spese ORDER BY data DESC", conn)
    st.dataframe(df_spese, use_container_width=True)
