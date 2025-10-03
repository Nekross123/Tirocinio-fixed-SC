import streamlit as st
import os
import sys
import requests
import json
import asyncio

toolchain_path = os.path.join(os.path.dirname(__file__), "..", "Toolchain")
sys.path.append(toolchain_path)
# ==============================
# Import moduli Solana
# ==============================

import solana_module.anchor_module.compiler_and_deployer_adpp as toolchain
from  solana_module.solana_utils import load_keypair_from_file, create_client
import  solana_module.anchor_module.dapp_automatic_insertion_manager as trace_manager


st.set_page_config(
    page_title="Solana DApp",  
    page_icon="🌞"              
)


st.set_page_config(page_title="Solana DApp", layout="wide")
st.title("🌞 Toolchain Solana")

# ==============================
# Sidebar
# ==============================
st.sidebar.header("Menu")
selected_action = st.sidebar.radio(
    "Scegli un'azione:",
    ("Gestione Wallet", "Compile & Deploy", "Automatic Data Insertion", "Chiudi Programma", "Altro")
)

WALLETS_PATH = os.path.join(toolchain_path, "solana_module", "solana_wallets")
ANCHOR_PROGRAMS_PATH = os.path.join(toolchain_path, "solana_module", "anchor_module", "anchor_programs")
TRACES_PATH = os.path.join(toolchain_path, "solana_module", "anchor_module", "execution_traces")

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
    st.subheader("Compila e deploya programmi Solana")
    
    wallet_files = [f for f in os.listdir(WALLETS_PATH) if f.endswith(".json")]
    selected_wallet_file = st.selectbox("Seleziona wallet per deploy", ["--"] + wallet_files)

    selected_cluster = st.selectbox("Seleziona un cluster", ["--"] + ["Devnet", "Testnet", "Mainnet"])

    st.markdown("----")
    # Scegli modalità di compilazione
    compile_mode = st.radio(
        "Modalità di compilazione:",
        ("Tutti i programmi", "Programma singolo"),
        help="Scegli se compilare tutti i programmi o solo uno specifico"
    )

    selected_program_file = None
    if compile_mode == "Programma singolo":
        program_files = [f for f in os.listdir(ANCHOR_PROGRAMS_PATH) if f.endswith(".rs")]
        selected_program_file = st.selectbox("Seleziona programma", ["--"] + program_files)
    else:
        # Mostra lista di tutti i programmi che verranno compilati
        program_files = [f for f in os.listdir(ANCHOR_PROGRAMS_PATH) if f.endswith(".rs")]
        if program_files:
            st.info("📋 Programmi che verranno compilati e deployati:")
            for i, prog in enumerate(program_files, 1):
                st.write(f"{i}. `{prog}`")
        else:
            st.warning("❌ Nessun programma .rs trovato nella cartella anchor_programs")

    st.markdown("----")
    deploy_flag = st.checkbox("Esegui anche il deploy dopo la compilazione", value=True)

    # Condizioni per il pulsante
    if compile_mode == "Tutti i programmi":
        can_proceed = selected_wallet_file != "--" and selected_cluster != "--" and len(program_files) > 0
    else:
        can_proceed = selected_wallet_file != "--" and selected_program_file != "--" and selected_cluster != "--"

    if can_proceed and st.button("Compile & Deploy"):
        if compile_mode == "Programma singolo":
            st.info(f"⚡ Avvio compilazione e deploy di `{selected_program_file}`... ⏳")
        else:
            st.info(f"⚡ Avvio compilazione e deploy di {len(program_files)} programmi... ⏳")
        
        progress_bar = st.empty()
        status_placeholder = st.empty()

        # STEP 1: Compilazione
        progress_bar.progress(30)
        if compile_mode == "Programma singolo":
            status_placeholder.info(f"📦 Compilazione del programma `{selected_program_file}` in corso...")
        else:
            status_placeholder.info(f"📦 Compilazione di {len(program_files)} programmi in corso...")

        try:
            compile_payload = {
                "wallet_file": selected_wallet_file,
                "cluster": selected_cluster,
                "deploy": False
            }
            # Aggiungi il parametro single_program se in modalità singolo programma
            if compile_mode == "Programma singolo":
                compile_payload["single_program"] = selected_program_file
                
            compile_res = requests.post(
                "http://127.0.0.1:5000/compile_deploy",
                json=compile_payload
            )
            compile_res = compile_res.json()
        except requests.exceptions.RequestException as e:
            st.error(f"Errore di connessione al backend: {e}")
            st.stop()
    
        if compile_res["success"]:
            if compile_mode == "Programma singolo":
                status_placeholder.success(f"✅ Compilazione completata per `{selected_program_file}`!")
            else:
                compiled_count = len([p for p in compile_res["programs"] if p["compiled"]])
                status_placeholder.success(f"✅ Compilazione completata: {compiled_count}/{len(compile_res['programs'])} programmi!")
        else:
            status_placeholder.error(f"❌ Errore durante la compilazione: {compile_res.get('error', 'Errore sconosciuto')}")
            print("Dettagli JSON compilation:", compile_res)
            st.stop()
        
        progress_bar.progress(50)
        status_placeholder.empty()

        # STEP 2: Deploy (se richiesto)
        if deploy_flag:
            progress_bar.progress(70)
            if compile_mode == "Programma singolo":
                status_placeholder.info(f"🚀 Deploy del programma `{selected_program_file}` in corso...")
            else:
                status_placeholder.info(f"🚀 Deploy di {len(program_files)} programmi in corso...")
            
            try:
                deploy_payload = {
                    "wallet_file": selected_wallet_file,
                    "cluster": selected_cluster,
                    "deploy": True
                }
                # Aggiungi il parametro single_program se in modalità singolo programma
                if compile_mode == "Programma singolo":
                    deploy_payload["single_program"] = selected_program_file
                    
                deploy_res = requests.post(
                    "http://127.0.0.1:5000/compile_deploy",
                    json=deploy_payload
                )
                deploy_res = deploy_res.json()
            except requests.exceptions.RequestException as e:
                st.error(f"Errore di connessione al backend: {e}")
                st.stop()

            if deploy_res["success"]:
                if compile_mode == "Programma singolo":
                    program_id = deploy_res['programs'][0]['program_id'] if deploy_res['programs'] else "N/A"
                    status_placeholder.success(f"🎉 Deploy completato! Program ID: {program_id}")
                else:
                    deployed_count = len([p for p in deploy_res["programs"] if p["deployed"]])
                    status_placeholder.success(f"🎉 Deploy completato: {deployed_count}/{len(deploy_res['programs'])} programmi!")
                    
                    # Mostra i Program ID di tutti i programmi deployati
                    if deployed_count > 0:
                        st.subheader("📋 Programmi deployati:")
                        for prog in deploy_res["programs"]:
                            if prog["deployed"] and prog["program_id"]:
                                st.success(f"✅ `{prog['program']}`: {prog['program_id']}")
            else:
                if compile_mode == "Programma singolo":
                    errors = deploy_res['programs'][0].get('errors', []) if deploy_res['programs'] else ["Errore sconosciuto"]
                    status_placeholder.error(f"❌ Deploy fallito: {'; '.join(errors)}")
                else:
                    failed_programs = [p for p in deploy_res["programs"] if not p["deployed"]]
                    status_placeholder.error(f"❌ Deploy fallito per {len(failed_programs)} programmi")
                    for prog in failed_programs:
                        st.error(f"❌ `{prog['program']}`: {'; '.join(prog.get('errors', ['Errore sconosciuto']))}")
            
            print("Dettagli JSON compile & deploy:", json.dumps(deploy_res, indent=2))

        progress_bar.progress(100)
        status_placeholder.empty()
        progress_bar.empty()
        st.success("✅ Operazione completata con successo!")
elif selected_action == "Automatic Data Insertion":

    traces_files = [f for f in os.listdir(TRACES_PATH) if f.endswith(".json")]
    selected_trace_file = st.selectbox("Select trace", ["--"] + traces_files)

    if selected_trace_file != "--" and st.button("Load and execute trace"):

        asyncio.run(trace_manager.run_execution_trace(selected_trace_file))

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
