import streamlit as st
import os
import sys
import requests
import json

st.set_page_config(
    page_title="Solana DApp",  
    page_icon="🌞"              
)

toolchain_path = os.path.join(os.path.dirname(__file__), "..", "Toolchain")
sys.path.append(toolchain_path)

# ==============================
# Import moduli Solana
# ==============================
import solana_module.anchor_module.compiler_and_deployer_adpp as toolchain
from solana_module.solana_utils import load_keypair_from_file, create_client

st.set_page_config(page_title="Solana DApp", layout="wide")
st.title("🌞 Toolchain Solana")

# ==============================
# Sidebar
# ==============================
st.sidebar.header("Menu")
selected_action = st.sidebar.radio(
    "Scegli un'azione:",
    ("Gestione Wallet", "Compile & Deploy", "Chiudi Programma", "Altro")
)

WALLETS_PATH = os.path.join(toolchain_path, "solana_module", "solana_wallets")
ANCHOR_PROGRAMS_PATH = os.path.join(toolchain_path, "solana_module", "anchor_module", "anchor_programs")

# ==============================
# Sezione principale
# ==============================
st.header(f"{selected_action}")

if selected_action == "Gestione Wallet":
    wallet_files = [f for f in os.listdir(WALLETS_PATH) if f.endswith(".json")]
    selected_wallet_file = st.selectbox("Seleziona wallet", ["--"] + wallet_files)
    
    if selected_wallet_file != "--" and st.button("Mostra saldo e PubKey"):
        try:
            res = requests.post(
                "http://127.0.0.1:5000/wallet_balance",
                json={"wallet_file": selected_wallet_file}
            )
            if res.status_code == 200:
                data = res.json()
                st.success(f"Saldo SOL: {data['balance']} SOL")
                st.info(f"Public Key: {data['pubkey']}")
            else:
                st.error(res.json().get("error", "Errore sconosciuto"))
        except requests.exceptions.RequestException as e:
            st.error(f"Errore di connessione al backend: {e}")

elif selected_action == "Compile & Deploy":
    st.subheader("Compila e deploya un programma Solana")
    
    wallet_files = [f for f in os.listdir(WALLETS_PATH) if f.endswith(".json")]
    selected_wallet_file = st.selectbox("Seleziona wallet per deploy", ["--"] + wallet_files)

    program_files = [f for f in os.listdir(ANCHOR_PROGRAMS_PATH) if f.endswith(".rs")]
    selected_program_file = st.selectbox("Seleziona programma", ["--"] + program_files)

    deploy_flag = st.checkbox("Esegui deploy dopo compilazione", value=True)

    if selected_wallet_file != "--" and selected_program_file != "--" and st.button("Compile & Deploy"):
        st.info("⚡ Avvio compilazione e deploy... potrebbe richiedere qualche minuto ⏳")
        
        progress_bar = st.empty()
        status_placeholder = st.empty()

        # STEP 1: Compilazione
        progress_bar.progress(30)
        status_placeholder.info(f"📦 Compilazione del programma `{selected_program_file}` in corso...")

        compile_res = toolchain.compile_and_deploy_programs(
            wallet_name=selected_wallet_file,
            cluster="devnet",
            deploy=False
        )
    
        if compile_res["success"]:
            status_placeholder.success(f"✅ Compilazione completata per `{selected_program_file}`!")
        else:
            status_placeholder.error(f"❌ Errore durante la compilazione: {compile_res.get('error', 'Errore sconosciuto')}")
            print("Dettagli JSON compilation:", compile_res)
            st.stop()
        
        progress_bar.progress(50)
        status_placeholder.empty()

        # STEP 2: Deploy (se richiesto)
        if deploy_flag:
            progress_bar.progress(70)
            status_placeholder.info(f"🚀 Deploy del programma `{selected_program_file}` in corso...")
            deploy_res = toolchain.compile_and_deploy_programs(
                wallet_name=selected_wallet_file,
                cluster="devnet",
                deploy=True
            )

            if deploy_res["success"]:
                status_placeholder.success(
                    f"🎉 Deploy completato! Program ID: {deploy_res['programs'][0]['program_id']}"
                )
            else:
                status_placeholder.error(
                    f"❌ Deploy fallito: {deploy_res['programs'][0].get('errors')}"
                )
            
            print("Dettagli JSON compile & deploy:", json.dumps(deploy_res, indent=2))

        progress_bar.progress(100)
        status_placeholder.empty()
        progress_bar.empty()
        st.success("✅ Operazione completata con successo!")

elif selected_action == "Chiudi Programma":
    st.subheader("Chiudi un programma")

else:
    st.subheader("Altre funzionalità")
    st.write("Sezione placeholder per altre funzioni future della DApp.")

# ==============================
# Footer
# ==============================
st.markdown("---")
st.write("© 2025 - Solana")
