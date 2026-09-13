import sqlite3
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st

# 1. IMPOSTAZIONI PAGINA
st.set_page_config(
    page_title="Gestionale Transitorio & Estivo",
    layout="wide",
    page_icon="🏖️",
)

# STILE CSS PERSONALE (Incluso supporto al gradiente bicolore per i cambi ospite)
st.markdown(
    """
    <style>
    .stApp { background-color: #f8f9fa; }
    div[data-testid="column"] { padding: 0px 2px !important; }
    
    .sticky-header-container {
        position: -webkit-sticky;
        position: sticky;
        top: 2.8rem;
        background-color: #ffffff;
        z-index: 999;
        padding: 10px 5px;
        border-bottom: 2px solid #cbd5e1;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        border-radius: 6px;
        margin-bottom: 10px;
    }

    /* Quadratini compattezza calendario */
    .cal-grid {
        display: grid;
        grid-template-columns: repeat(7, 1fr);
        gap: 3px;
        margin-bottom: 15px;
    }
    .cal-day {
        aspect-ratio: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 11px;
        font-weight: bold;
        border-radius: 4px;
        border: 1px solid #cbd5e1;
        background-color: #ffffff;
        color: #475569;
    }
    .cal-day-empty {
        aspect-ratio: 1;
        border: none;
        background: transparent;
    }
    .month-title {
        text-align: center;
        font-weight: bold;
        font-size: 14px;
        background-color: #e2e8f0;
        padding: 4px;
        border-radius: 4px;
        margin-bottom: 5px;
        color: #1e293b;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# 2. DATABASE LOCALE
conn = sqlite3.connect("gestionale_estivo.db", check_same_thread=False)
c = conn.cursor()

c.execute(
    """
    CREATE TABLE IF NOT EXISTS immobili (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT UNIQUE,
        indirizzo TEXT,
        periodo_invernale TEXT,
        canone_concordato REAL DEFAULT 0.0,
        note TEXT
    )
"""
)

c.execute(
    """
    CREATE TABLE IF NOT EXISTS pagamenti_inverno (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        immobile_id INTEGER,
        anno INTEGER,
        mese INTEGER,
        stato TEXT,
        importo REAL,
        spesa_luce REAL DEFAULT 0.0,
        stato_luce TEXT DEFAULT 'Rosso',
        spesa_gas REAL DEFAULT 0.0,
        stato_gas TEXT DEFAULT 'Rosso',
        UNIQUE(immobile_id, anno, mese)
    )
"""
)

c.execute(
    """
    CREATE TABLE IF NOT EXISTS prenotazioni (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        immobile_id INTEGER,
        ospite_nome TEXT,
        telefono TEXT,
        num_persone INTEGER,
        data_checkin TEXT,
        data_checkout TEXT,
        importo_totale REAL,
        caparra REAL,
        colore TEXT,
        note TEXT
    )
"""
)

c.execute(
    """
    CREATE TABLE IF NOT EXISTS uscite (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        immobile_id INTEGER,
        data_spesa TEXT,
        categoria TEXT,
        descrizione TEXT,
        importo REAL,
        inserito_da TEXT
    )
"""
)

conn.commit()

MESI_NOMI = [
    "Gen",
    "Feb",
    "Mar",
    "Apr",
    "Mag",
    "Giu",
    "Lug",
    "Ago",
    "Set",
    "Ott",
    "Nov",
    "Dic",
]

COLOR_MAP = {
    "🔵 Blu": {"bg": "#3b82f6", "text": "#ffffff"},
    "🟢 Verde": {"bg": "#22c55e", "text": "#ffffff"},
    "🟡 Giallo": {"bg": "#eab308", "text": "#000000"},
    "🟣 Viola": {"bg": "#a855f7", "text": "#ffffff"},
    "🟠 Arancione": {"bg": "#f97316", "text": "#ffffff"},
    "🔴 Rosso": {"bg": "#ef4444", "text": "#ffffff"},
    "🟤 Marrone": {"bg": "#854d0e", "text": "#ffffff"},
}


# FUNZIONE DI CONTROLLO SOVRAPPOSIZIONE DATES
def verifica_sovrapposizione(
    immobile_id, checkin_str, checkout_str, pren_id_esclusa=None
):
    """
    Controlla se ci sono sovrapposizioni di date.
    Una prenotazione A [in_A, out_A] e B [in_B, out_B] si sovrappongono se:
    in_A < out_B AND out_A > in_B
    """
    if pren_id_esclusa:
        c.execute(
            """
            SELECT id, ospite_nome, data_checkin, data_checkout 
            FROM prenotazioni 
            WHERE immobile_id=? AND id != ? AND data_checkin < ? AND data_checkout > ?
        """,
            (immobile_id, pren_id_esclusa, checkout_str, checkin_str),
        )
    else:
        c.execute(
            """
            SELECT id, ospite_nome, data_checkin, data_checkout 
            FROM prenotazioni 
            WHERE immobile_id=? AND data_checkin < ? AND data_checkout > ?
        """,
            (immobile_id, checkout_str, checkin_str),
        )

    return c.fetchall()


# POP-UP MODIFICA/CANCELLA PRENOTAZIONE ESTIVA
@st.dialog("✏️ Gestisci Prenotazione Estiva")
def popup_gestione_prenotazione(pren_id):
    c.execute(
        "SELECT immobile_id, ospite_nome, telefono, num_persone, data_checkin, data_checkout, importo_totale, caparra, colore FROM prenotazioni WHERE id=?",
        (pren_id,),
    )
    p = c.fetchone()
    if not p:
        st.error("Prenotazione non trovata.")
        return

    st.write(f"Modifica prenotazione di **{p[1]}**")

    e_ospite = st.text_input("Ospite Nome/Cognome", value=p[1])
    e_tel = st.text_input("Telefono", value=p[2] or "")
    e_num = st.number_input("Ospiti", min_value=1, value=int(p[3] or 1))

    col_d1, col_d2 = st.columns(2)
    with col_d1:
        e_in = st.date_input(
            "Check-in", value=datetime.strptime(p[4], "%Y-%m-%d").date()
        )
    with col_d2:
        e_out = st.date_input(
            "Check-out", value=datetime.strptime(p[5], "%Y-%m-%d").date()
        )

    col_i1, col_i2 = st.columns(2)
    with col_i1:
        e_tot = st.number_input(
            "Totale Soggiorno (€)", min_value=0.0, value=float(p[6] or 0.0)
        )
    with col_i2:
        e_cap = st.number_input(
            "Caparra Ricevuta (€)", min_value=0.0, value=float(p[7] or 0.0)
        )

    list_col = list(COLOR_MAP.keys())
    idx_col = list_col.index(p[8]) if p[8] in list_col else 0
    e_colore = st.selectbox("Colore Calendario", list_col, index=idx_col)

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("💾 Aggiorna Prenotazione", type="primary"):
            if e_in >= e_out:
                st.error("⚠️ La data di Check-out deve essere successiva al Check-in!")
            else:
                conflitti = verifica_sovrapposizione(
                    p[0], str(e_in), str(e_out), pren_id_esclusa=pren_id
                )
                if conflitti:
                    nomi_conf = ", ".join([c[1] for c in conflitti])
                    st.error(
                        f"🚨 **ERRORE OVERBOOKING!** Date occupate da: **{nomi_conf}**"
                    )
                else:
                    c.execute(
                        """
                        UPDATE prenotazioni 
                        SET ospite_nome=?, telefono=?, num_persone=?, data_checkin=?, data_checkout=?, importo_totale=?, caparra=?, colore=?
                        WHERE id=?
                    """,
                        (
                            e_ospite,
                            e_tel,
                            e_num,
                            str(e_in),
                            str(e_out),
                            e_tot,
                            e_cap,
                            e_colore,
                            pren_id,
                        ),
                    )
                    conn.commit()
                    st.success("Modificata con successo!")
                    st.rerun()

    with col_btn2:
        if st.button("🗑️ Elimina Prenotazione"):
            c.execute("DELETE FROM prenotazioni WHERE id=?", (pren_id,))
            conn.commit()
            st.success("Prenotazione eliminata!")
            st.rerun()


# POP-UP NUOVA PRENOTAZIONE PER LA CASA SELEZIONATA
@st.dialog("➕ Nuova Prenotazione Estiva")
def popup_nuova_prenotazione(imm_id, imm_nome, default_year):
    st.write(f"Nuova prenotazione per: **{imm_nome}**")

    with st.form("form_nuova_pren", clear_on_submit=False):
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            ospite = st.text_input("Nome e Cognome Ospite")
            telefono = st.text_input("Telefono Ospite")
            num_pers = st.number_input("Numero Ospiti", min_value=1, value=2)

        with col_p2:
            default_in = datetime(default_year, 7, 1).date()
            default_out = datetime(default_year, 7, 7).date()

            d_in = st.date_input(
                "Check-in", value=default_in, format="DD/MM/YYYY"
            )
            d_out = st.date_input(
                "Check-out", value=default_out, format="DD/MM/YYYY"
            )

            imp_tot = st.number_input(
                "Totale Soggiorno (€)", min_value=0.0, step=50.0
            )
            caparra = st.number_input(
                "Caparra Ricevuta (€)", min_value=0.0, step=20.0
            )
            colore = st.selectbox(
                "Colore Evidenziatore Calendario:", list(COLOR_MAP.keys())
            )

        submit = st.form_submit_button("💾 Salva Prenotazione", type="primary")
        if submit:
            if not ospite:
                st.error("⚠️ Inserisci il nome dell'ospite.")
            elif d_in >= d_out:
                st.error("⚠️ La data di Check-out deve essere successiva al Check-in!")
            else:
                conflitti = verifica_sovrapposizione(imm_id, str(d_in), str(d_out))
                if conflitti:
                    nomi_conf = ", ".join([c[1] for c in conflitti])
                    st.error(
                        f"🚨 **CAMPANELLO D'ALLARME - OVERBOOKING!** Date già prenotate da: **{nomi_conf}**"
                    )
                else:
                    c.execute(
                        """
                        INSERT INTO prenotazioni (immobile_id, ospite_nome, telefono, num_persone, data_checkin, data_checkout, importo_totale, caparra, colore)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            imm_id,
                            ospite,
                            telefono,
                            num_pers,
                            str(d_in),
                            str(d_out),
                            imp_tot,
                            caparra,
                            colore,
                        ),
                    )
                    conn.commit()
                    st.success("Prenotazione salvata con successo!")
                    st.rerun()


# POP-UP MODIFICA LOCALE
@st.dialog("✏️ Modifica Dati Locale")
def popup_modifica_locale(
    imm_id, nome_att, ind_att, per_att, canone_att, note_att
):
    m_nome = st.text_input("Nome Immobile / Casa Vacanze", value=nome_att)
    m_ind = st.text_input("Indirizzo Completo", value=ind_att or "")
    m_periodo = st.text_input(
        "Periodo Affitto Transitorio Invernale", value=per_att or ""
    )
    m_canone = st.number_input(
        "Canone Mensile Concordato (€)",
        min_value=0.0,
        value=float(canone_att or 0.0),
    )
    m_note = st.text_area("Note", value=note_att or "")

    if st.button("💾 Salva Modifiche", type="primary"):
        c.execute(
            "UPDATE immobili SET nome=?, indirizzo=?, periodo_invernale=?, canone_concordato=?, note=? WHERE id=?",
            (m_nome, m_ind, m_periodo, m_canone, m_note, imm_id),
        )
        conn.commit()
        st.rerun()


# POP-UP AFFITTI INVERNALI
@st.dialog("⚙️ Gestione Mese / Affitto & Utenze")
def popup_modifica_inverno(
    imm_id, imm_nome, anno, mese_num, imp_att, st_att, canone_base
):
    st.write(f"Immobile: **{imm_nome}** - Periodo: **{MESI_NOMI[mese_num-1]} {anno}**")
    c.execute(
        "SELECT spesa_luce, stato_luce, spesa_gas, stato_gas FROM pagamenti_inverno WHERE immobile_id=? AND anno=? AND mese=?",
        (imm_id, anno, mese_num),
    )
    r_spese = c.fetchone()
    l_imp = r_spese[0] if r_spese else 0.0
    l_st = r_spese[1] if r_spese else "Rosso"
    g_imp = r_spese[2] if r_spese else 0.0
    g_st = r_spese[3] if r_spese else "Rosso"

    imp_default = imp_att if imp_att > 0 else canone_base

    st.markdown("### 💶 Canone Affitto")
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        imp_canone = st.number_input(
            "Importo Canone (€)", min_value=0.0, value=float(imp_default)
        )
    with col_c2:
        st_canone = st.selectbox(
            "Stato Canone:",
            ["🔴 Da Incassare", "🟢 Incassato"],
            index=1 if st_att in ["Verde", "Arancione"] else 0,
        )

    st.markdown("---")
    st.markdown("### 💡 Recupero Spese Utenze")
    col_l1, col_l2 = st.columns(2)
    with col_l1:
        v_luce = st.number_input(
            "Importo Luce (€)", min_value=0.0, value=float(l_imp), key="v_luce"
        )
        st_luce = st.checkbox(
            "Luce Incassata 🟢", value=(l_st == "Verde"), key="st_luce"
        )
    with col_l2:
        v_gas = st.number_input(
            "Importo Gas (€)", min_value=0.0, value=float(g_imp), key="v_gas"
        )
        st_gas = st.checkbox(
            "Gas Incassato 🟢", value=(g_st == "Verde"), key="st_gas"
        )

    if st.button("💾 Salva Dati Mese", type="primary"):
        st_c_clean = "Rosso" if "Da Incassare" in st_canone else "Verde"
        st_l_clean = "Verde" if st_luce else "Rosso"
        st_g_clean = "Verde" if st_gas else "Rosso"

        c.execute(
            """
            INSERT INTO pagamenti_inverno (immobile_id, anno, mese, stato, importo, spesa_luce, stato_luce, spesa_gas, stato_gas)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(immobile_id, anno, mese) DO UPDATE SET
            importo=excluded.importo, stato=excluded.stato,
            spesa_luce=excluded.spesa_luce, stato_luce=excluded.stato_luce,
            spesa_gas=excluded.spesa_gas, stato_gas=excluded.stato_gas
        """,
            (
                imm_id,
                anno,
                mese_num,
                st_c_clean,
                imp_canone,
                v_luce,
                st_l_clean,
                v_gas,
                st_g_clean,
            ),
        )
        conn.commit()
        st.rerun()


# 3. MENU NAVIGAZIONE
st.sidebar.image(
    "https://img.icons8.com/isometric/100/beach-house.png", width=70
)
st.sidebar.title("🏝️ Gestionale Immobili")
pagina = st.sidebar.radio(
    "Navigazione:",
    [
        "1. Anagrafica Locali",
        "2. Affitti Invernali (Mesi & Utenze)",
        "3. Calendario Prenotazioni Estive",
        "4. Registro Uscite & Spese",
    ],
)

# ==========================================
# PAGINA 1: ANAGRAFICA LOCALI
# ==========================================
if pagina == "1. Anagrafica Locali":
    st.title("🏡 Anagrafica Locali")

    with st.expander("➕ **Aggiungi Nuovo Locale**"):
        with st.form("form_locale", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                nome = st.text_input("Nome Immobile / Casa Vacanze")
                indirizzo = st.text_input("Indirizzo Completo")
                periodo_invernale = st.text_input(
                    "Periodo Transitorio (es. Set - Mag)"
                )
            with col2:
                canone = st.number_input(
                    "Canone Invernale Concordato (€)", min_value=0.0, value=400.0
                )
                note = st.text_area("Note (es. Keybox, WiFi)")

            if st.form_submit_button("💾 Salva Locale"):
                if nome:
                    try:
                        c.execute(
                            "INSERT INTO immobili (nome, indirizzo, periodo_invernale, canone_concordato, note) VALUES (?, ?, ?, ?, ?)",
                            (nome, indirizzo, periodo_invernale, canone, note),
                        )
                        conn.commit()
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Esiste già un locale con questo nome.")

    st.markdown("---")
    c.execute(
        "SELECT id, nome, indirizzo, periodo_invernale, canone_concordato, note FROM immobili"
    )
    immobili = c.fetchall()

    if immobili:
        cols = st.columns(3)
        for idx, imm in enumerate(immobili):
            imm_id, imm_nome, imm_ind, imm_per, imm_canone, imm_note = imm
            with cols[idx % 3]:
                st.info(
                    f"🏠 **{imm_nome}**\n\n📍 {imm_ind or 'N/D'}\n\n🗓️ {imm_per or 'Non spec.'}\n\n💶 {imm_canone:.0f} €/mese"
                )
                c_b1, c_b2 = st.columns(2)
                with c_b1:
                    if st.button(f"✏️ Modifica", key=f"ed_{imm_id}"):
                        popup_modifica_locale(
                            imm_id,
                            imm_nome,
                            imm_ind,
                            imm_per,
                            imm_canone,
                            imm_note,
                        )
                with c_b2:
                    if st.button(f"🗑️ Elimina", key=f"del_{imm_id}"):
                        c.execute("DELETE FROM immobili WHERE id=?", (imm_id,))
                        conn.commit()
                        st.rerun()

# ==========================================
# PAGINA 2: AFFITTI INVERNALI
# ==========================================
elif pagina == "2. Affitti Invernali (Mesi & Utenze)":
    st.title("📅 Quadro Affitti Invernali")

    c.execute("SELECT id, nome, canone_concordato FROM immobili")
    immobili = c.fetchall()

    if not immobili:
        st.warning("Inserisci prima i locali nella Pagina 1.")
    else:
        anno_sel = st.selectbox(
            "🗓️ Seleziona Anno:", list(range(2023, 2031)), index=4
        )  # Default 2027
        st.caption(
            "🔴 **Rosso:** Canone non incassato | 🟠 **Arancione:** Canone incassato ma utenze da incassare | 🟢 **Verde:** Tutto Incassato"
        )

        st.markdown(
            """
            <div class="sticky-header-container">
                <div style="display: flex; text-align: center; font-weight: bold; font-size: 13px;">
                    <div style="flex: 2.5; text-align: left;">Immobile</div>
                    <div style="flex: 1;">Gen</div><div style="flex: 1;">Feb</div><div style="flex: 1;">Mar</div>
                    <div style="flex: 1;">Apr</div><div style="flex: 1;">Mag</div><div style="flex: 1;">Giu</div>
                    <div style="flex: 1;">Lug</div><div style="flex: 1;">Ago</div><div style="flex: 1;">Set</div>
                    <div style="flex: 1;">Ott</div><div style="flex: 1;">Nov</div><div style="flex: 1;">Dic</div>
                    <div style="flex: 1.8; text-align: right; color:#2563eb;">Totale</div>
                </div>
            </div>
        """,
            unsafe_allow_html=True,
        )

        for imm_id, imm_nome, canone_base in immobili:
            row_cols = st.columns([2.5] + [1] * 12 + [1.8])
            row_cols[0].markdown(f"**{imm_nome}**")
            tot_incassato = 0.0

            for m_num in range(1, 13):
                c.execute(
                    "SELECT stato, importo, spesa_luce, stato_luce, spesa_gas, stato_gas FROM pagamenti_inverno WHERE immobile_id=? AND anno=? AND mese=?",
                    (imm_id, anno_sel, m_num),
                )
                res = c.fetchone()
                st_val = res[0] if res else "Sfitto"
                imp = res[1] if res else 0.0
                sp_luce = res[2] if res else 0.0
                st_luce = res[3] if res else "Rosso"
                sp_gas = res[4] if res else 0.0
                st_gas = res[5] if res else "Rosso"

                if st_val == "Verde":
                    tot_incassato += imp
                if st_luce == "Verde":
                    tot_incassato += sp_luce
                if st_gas == "Verde":
                    tot_incassato += sp_gas

                has_pending = (sp_luce > 0 and st_luce == "Rosso") or (
                    sp_gas > 0 and st_gas == "Rosso"
                )

                if st_val == "Rosso":
                    lbl = f"🔴{imp:.0f}€"
                elif st_val == "Verde" and has_pending:
                    lbl = f"🟠{imp:.0f}€"
                elif st_val == "Verde" and not has_pending:
                    lbl = f"🟢{imp:.0f}€"
                else:
                    lbl = "⚫"

                if row_cols[m_num].button(
                    lbl, key=f"inv_{imm_id}_{anno_sel}_{m_num}"
                ):
                    popup_modifica_inverno(
                        imm_id,
                        imm_nome,
                        anno_sel,
                        m_num,
                        imp,
                        st_val,
                        canone_base,
                    )

            row_cols[13].markdown(
                f"<div style='text-align: right; font-weight: bold; color: #16a34a;'>💰 {tot_incassato:.0f} €</div>",
                unsafe_allow_html=True,
            )

# ==========================================
# PAGINA 3: CALENDARIO PRENOTAZIONI ESTIVE
# ==========================================
elif pagina == "3. Calendario Prenotazioni Estive":
    st.title("☀️ Calendario Estivo (Maggio - Settembre)")

    c.execute("SELECT id, nome FROM immobili")
    immobili = c.fetchall()

    if not immobili:
        st.warning("Aggiungi prima i locali nella Pagina 1.")
    else:
        # 1. SELEZIONE CASA A GRIGLIETTA IN ALTO
        st.write("### 🏠 Scegli la Casa da Visualizzare:")

        if "casa_attiva_id" not in st.session_state:
            st.session_state.casa_attiva_id = immobili[0][0]

        grid_cols = st.columns(min(len(immobili), 6))
        for idx, (imm_id, imm_nome) in enumerate(immobili):
            btn_type = (
                "primary"
                if st.session_state.casa_attiva_id == imm_id
                else "secondary"
            )
            if grid_cols[idx % 6].button(
                f"🏠 {imm_nome}", key=f"btn_casa_{imm_id}", type=btn_type
            ):
                st.session_state.casa_attiva_id = imm_id
                st.rerun()

        casa_attuale_id = st.session_state.casa_attiva_id
        casa_attuale_nome = next(
            i[1] for i in immobili if i[0] == casa_attuale_id
        )

        st.markdown("---")

        col_tit, col_btn_add, col_ann = st.columns([2.5, 1.5, 1])
        with col_tit:
            st.subheader(f"📅 Vista Calendario: **{casa_attuale_nome}**")
        with col_btn_add:
            if st.button(
                f"➕ Aggiungi Prenotazione", type="primary", use_container_width=True
            ):
                popup_nuova_prenotazione(
                    casa_attuale_id,
                    casa_attuale_nome,
                    st.session_state.get("anno_est", 2027),
                )
        with col_ann:
            anno_cal = st.selectbox(
                "Anno:", [2025, 2026, 2027, 2028], index=2, key="anno_est"
            )

        # RECUPERO PRENOTAZIONI CASA SELEZIONATA
        c.execute(
            "SELECT id, ospite_nome, data_checkin, data_checkout, colore FROM prenotazioni WHERE immobile_id=?",
            (casa_attuale_id,),
        )
        pren_casa = c.fetchall()

        # 2. CALENDARIO IN UN'UNICA SCHERMATA (MAGGIO - SETTEMBRE) CON GESTIONE DOPPIO COLORE PER CAMBIO OSPITE
        mesi_estivi = [
            ("Maggio", 5),
            ("Giugno", 6),
            ("Luglio", 7),
            ("Agosto", 8),
            ("Settembre", 9),
        ]
        cal_cols = st.columns(5)

        for idx, (m_nome, m_num) in enumerate(mesi_estivi):
            with cal_cols[idx]:
                st.markdown(
                    f"<div class='month-title'>{m_nome}</div>",
                    unsafe_allow_html=True,
                )

                first_date = datetime(anno_cal, m_num, 1)
                start_day = first_date.weekday()  # 0 = Lunedì
                num_days = 31 if m_num in [5, 7, 8] else 30

                grid_html = '<div class="cal-grid">'

                # Spazi vuoti inizio mese
                for _ in range(start_day):
                    grid_html += '<div class="cal-day-empty"></div>'

                # Giorni del mese
                for day in range(1, num_days + 1):
                    curr_date_str = (
                        datetime(anno_cal, m_num, day).date().isoformat()
                    )

                    out_color = None
                    in_color = None
                    out_guest = ""
                    in_guest = ""

                    for p in pren_casa:
                        p_id, p_nome, p_in, p_out, p_col = p
                        col_hex = COLOR_MAP.get(
                            p_col, {"bg": "#3b82f6", "text": "#ffffff"}
                        )["bg"]

                        # Check-out in questo giorno
                        if curr_date_str == p_out:
                            out_color = col_hex
                            out_guest = f"Out: {p_nome}"

                        # Soggiorno in corso o Check-in in questo giorno
                        if p_in <= curr_date_str < p_out:
                            in_color = col_hex
                            in_guest = f"In: {p_nome}"

                    # DEFINIZIONE STILE BICOLORE O MONOCOLORE
                    style_attr = ""
                    txt_color = "#475569"
                    tooltip_list = []

                    if out_color and in_color:
                        # CAMBIO OSPITE STESSO GIORNO -> SPLIT BICOLORE IN DIAGONALE
                        style_attr = f"background: linear-gradient(135deg, {out_color} 50%, {in_color} 50%); color: #ffffff;"
                        tooltip_list = [out_guest, in_guest]
                    elif in_color:
                        # GIORNO INTERAMENTE PRENOTATO
                        style_attr = (
                            f"background-color: {in_color}; color: #ffffff;"
                        )
                        tooltip_list = [in_guest]
                    elif out_color:
                        # SOLO CHECK-OUT (MATTINA OCCUPATA)
                        style_attr = f"background: linear-gradient(135deg, {out_color} 50%, #ffffff 50%); color: #000000;"
                        tooltip_list = [out_guest]
                    else:
                        # LIBERO
                        style_attr = (
                            "background-color: #ffffff; color: #475569;"
                        )

                    tooltip = " | ".join(tooltip_list)
                    grid_html += f'<div class="cal-day" title="{tooltip}" style="{style_attr}">{day}</div>'

                grid_html += "</div>"
                st.markdown(grid_html, unsafe_allow_html=True)

        st.markdown("---")
        # 3. ELENCO PRENOTAZIONI CON TASTO MODIFICA/CANCELLA
        st.subheader(f"📋 Elenco Prenotazioni per {casa_attuale_nome}")

        c.execute(
            """
            SELECT id, ospite_nome, telefono, num_persone, data_checkin, data_checkout, importo_totale, caparra, colore
            FROM prenotazioni
            WHERE immobile_id=?
            ORDER BY data_checkin ASC
        """,
            (casa_attuale_id,),
        )
        pren_list = c.fetchall()

        if pren_list:
            for p in pren_list:
                (
                    p_id,
                    p_ospite,
                    p_tel,
                    p_num,
                    p_in,
                    p_out,
                    p_tot,
                    p_cap,
                    p_col,
                ) = p
                c_card1, c_card2 = st.columns([4, 1])
                with c_card1:
                    st.write(
                        f"👤 **{p_ospite}** | 🗓️ Dal **{p_in}** al **{p_out}** | 💶 Totale: **{p_tot:.0f} €** (Caparra: {p_cap:.0f} €) | Colore: {p_col}"
                    )
                with c_card2:
                    if st.button(f"✏️ / 🗑️ Gestisci", key=f"btn_mod_p_{p_id}"):
                        popup_gestione_prenotazione(p_id)
        else:
            st.info("Nessuna prenotazione inserita per questa casa.")

# ==========================================
# PAGINA 4: REGISTRO USCITE & SPESE
# ==========================================
elif pagina == "4. Registro Uscite & Spese":
    st.title("🛒 Registro Uscite & Spese Collaboratrice")

    c.execute("SELECT id, nome FROM immobili")
    immobili = c.fetchall()

    with st.expander("➕ **Registra Nuova Spesa / Uscita**"):
        with st.form("form_uscita", clear_on_submit=True):
            col_u1, col_u2 = st.columns(2)
            with col_u1:
                imm_u_nome = st.selectbox(
                    "Locale Associato", ["Generale / Tutti"] + [i[1] for i in immobili]
                )
                cat_spesa = st.selectbox(
                    "Categoria Spesa",
                    [
                        "Detersivi & Pulizie",
                        "Lenzuola & Lavanderia",
                        "Accessori Casa / Utensili",
                        "Manutenzione & Riparazioni",
                        "Altro",
                    ],
                )
                imp_u = st.number_input("Importo Spesa (€)", min_value=0.0, value=15.0)

            with col_u2:
                d_spesa = st.date_input("Data Spesa", format="DD/MM/YYYY")
                chi_registra = st.text_input(
                    "Registrato da", value="Collaboratrice"
                )
                desc_u = st.text_input("Dettaglio / Note")

            if st.form_submit_button("💾 Salva Spesa"):
                imm_u_id = (
                    next((i[0] for i in immobili if i[1] == imm_u_nome), 0)
                    if imm_u_nome != "Generale / Tutti"
                    else 0
                )
                c.execute(
                    "INSERT INTO uscite (immobile_id, data_spesa, categoria, descrizione, importo, inserito_da) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        imm_u_id,
                        str(d_spesa),
                        cat_spesa,
                        desc_u,
                        imp_u,
                        chi_registra,
                    ),
                )
                conn.commit()
                st.rerun()

    st.markdown("---")
    c.execute(
        "SELECT id, data_spesa, categoria, descrizione, importo, inserito_da FROM uscite ORDER BY data_spesa DESC"
    )
    lista_uscite = c.fetchall()

    if lista_uscite:
        df_u = pd.DataFrame(
            lista_uscite,
            columns=[
                "ID",
                "Data",
                "Categoria",
                "Descrizione",
                "Importo (€)",
                "Inserito Da",
            ],
        )
        st.dataframe(df_u, use_container_width=True)
        st.markdown(
            f"### 🔴 Totale Uscite Registrate: **{sum(x[4] for x in lista_uscite):.2f} €**"
        )
    else:
        st.caption("Nessuna spesa inserita.")