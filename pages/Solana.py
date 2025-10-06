from Toolchain.solana_module.anchor_module.dapp_automatic_insertion_manager import upload_trace_file
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
from  solana_module.solana_utils import load_keypair_from_file, create_client, solana_base_path
import  solana_module.anchor_module.dapp_automatic_insertion_manager as trace_manager
from Toolchain.solana_module.anchor_module.interactive_data_insertion_dapp import (
    fetch_programs,
    load_idl_for_program,
    fetch_instructions_for_program,
    fetch_program_context,
    check_if_array,
    check_type,
)

# --------------------------------------------------
#  for Interactive section
# --------------------------------------------------
def _render_account_block(acc: str, wallet_files: list[str]):
    with st.expander(f"Account: {acc}", expanded=False):
        method = st.selectbox(
            f"Metodo per {acc}",
            ["Wallet", "PDA Manuale", "PDA Seeds", "PDA Random"],
            key=f"method_{acc}"
        )
        data = {"name": acc, "method": method}

        if method == "Wallet":
            data['wallet'] = st.selectbox(
                f"Wallet file per {acc}", ["--"] + wallet_files, key=f"wallet_{acc}"
            )
            st.caption("Usa direttamente la public key del wallet scelto.")

        elif method == "PDA Manuale":
            data['pda_manual'] = st.text_input(
                f"PDA (44 caratteri Base58)", key=f"pda_manual_{acc}", placeholder="Es: 44 chars"
            )
            st.caption("Inserisci una PDA già calcolata.")

        elif method == "PDA Seeds":
            st.write("Generazione PDA da seeds deterministici")
            seeds_count = st.number_input(
                f"Numero seeds", min_value=1, max_value=10, value=1, key=f"seeds_count_{acc}"
            )
            seeds = []
            for i in range(seeds_count):
                col1, col2 = st.columns([1,3])
                with col1:
                    smode = st.selectbox(
                        f"Tipo {i+1}", ["Wallet", "Manual", "Random"], key=f"seed_mode_{acc}_{i}"
                    )
                seed_entry = {"mode": smode}
                with col2:
                    if smode == 'Wallet':
                        seed_entry['wallet'] = st.selectbox(
                            f"Wallet seed {i+1}", ["--"] + wallet_files, key=f"seed_wallet_{acc}_{i}"
                        )
                    elif smode == 'Manual':
                        seed_entry['manual'] = st.text_input(
                            f"Seed manuale {i+1}", key=f"seed_manual_{acc}_{i}", placeholder="stringa"
                        )
                    else:
                        st.caption("Generato random alla submit")
                seeds.append(seed_entry)
            data['seeds'] = seeds
            data['seeds_count'] = seeds_count

        else:  # PDA Random
            st.info("PDA casuale generata alla submit (32 bytes → base58 → Pubkey)")

        # Debug opzionale (attivabile impostando ?debug=1 nell'URL) usando nuova API st.query_params
        qp = st.query_params
        if qp.get('debug', ['0'])[0] == '1':
            st.code({k: v for k, v in data.items() if k != 'seeds'})
        return data


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
    ("Gestione Wallet", "Compile & Deploy", "Interactive Data Insertion", "Automatic Data Insertion", "Chiudi Programma", "Altro")
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

    st.markdown("----")
    upload_trace_file()
elif selected_action == "Interactive Data Insertion":
    st.caption("Compila tutto e invia in una sola volta.")

    programs = fetch_programs()
    program = st.selectbox("Programma", ["--"] + programs)

    idl = None
    instructions = []
    if program != "--":
        try:
            idl = load_idl_for_program(program)
            instructions = fetch_instructions_for_program(program)
        except FileNotFoundError as e:
            st.error(str(e))

    instruction = st.selectbox("Istruzione", ["--"] + instructions) if program != "--" else "--"

    if program == "--":
        st.info("Seleziona un programma.")
    elif instruction == "--":
        st.info("Seleziona un'istruzione.")
    else:
        ctx = fetch_program_context(program, instruction)
        req_accounts = ctx['required_accounts']
        signer_accounts = ctx['signer_accounts']
        args_spec = ctx['args_spec']
        wallets_dir = os.path.join(solana_base_path, 'solana_wallets')
        wallet_files = [f for f in os.listdir(wallets_dir) if f.endswith('.json')]

        st.markdown("---")
        st.markdown("### Parametri")

        st.markdown("#### Accounts")
        account_inputs = []
        for acc in req_accounts:
            data = _render_account_block(acc, wallet_files)
            account_inputs.append(data)

        # Form solo per payees/args/provider + submit
        with st.form("interactive_tx_form"):

            # Payees
            payees = []
            if instruction == 'initialize':
                st.markdown("#### Payees")
                num_payees = st.number_input("Numero payees", min_value=0, max_value=50, value=0, key="num_payees2")
                for i in range(num_payees):
                    wallet_sel = st.selectbox(f"Payee {i+1}", ["--"] + wallet_files, key=f"payee2_{i}")
                    payees.append(wallet_sel)

            # Args
            st.markdown("#### Argomenti")
            arg_values = {}
            for a in args_spec:
                name = a['name']
                array_type, array_length = check_if_array(a)
                if array_type is not None:
                    if array_length is not None:
                        arg_values[name] = st.text_input(f"{name} (array {array_type}[{array_length}])", key=f"arg2_{name}")
                    else:
                        arg_values[name] = st.text_input(f"{name} (vector {array_type}, vuoto = [] )", key=f"arg2_{name}")
                else:
                    kind = check_type(a['type'])
                    if kind == 'integer':
                        arg_values[name] = st.text_input(f"{name} (integer)", key=f"arg2_{name}")
                    elif kind == 'boolean':
                        arg_values[name] = st.selectbox(f"{name} (boolean)", ["--","true","false"], key=f"arg2_{name}")
                    elif kind == 'floating point number':
                        arg_values[name] = st.text_input(f"{name} (float)", key=f"arg2_{name}")
                    elif kind == 'string':
                        arg_values[name] = st.text_input(f"{name} (string)", key=f"arg2_{name}")
                    else:
                        st.warning(f"Tipo non supportato: {a['type']}")

            # Provider
            st.markdown("#### Provider")
            provider_wallet = st.selectbox("Provider wallet", ["--"] + wallet_files, key="prov2")
            send_now = st.checkbox("Invia subito || Calcola transazione", value=True, key="send_now2")

            submitted = st.form_submit_button("Build & (Send)", type="primary")

        # Local result variables 
        if submitted:
            result_placeholder = st.empty()
            try:
                result_placeholder.info("Costruzione transazione...")
                
                # Prepare payload for Flask backend
                payload = {
                    "program": program,
                    "instruction": instruction,
                    "account_inputs": account_inputs,
                    "signer_accounts": signer_accounts,
                    "payees": payees,
                    "arg_values": arg_values,
                    "provider_wallet": provider_wallet,
                    "send_now": send_now
                }
                
                # Call Flask backend
                response = requests.post(
                    "http://127.0.0.1:5000/interactive_transaction",
                    json=payload
                )
                
                if response.status_code != 200:
                    error_data = response.json()
                    result_placeholder.error(f"Errore: {error_data.get('error', 'Errore sconosciuto')}")
                else:
                    response_data = response.json()
                    if not response_data.get("success"):
                        result_placeholder.error(f"Errore: {response_data.get('error', 'Errore sconosciuto')}")
                    else:
                        result = response_data["result"]
                        
                        # Display
                        st.markdown("---")
                        st.subheader("Risultato")
                        st.write(f"**Dimensione:** {result['size']} bytes")
                        st.write(f"**Fee:** {result['fees']} lamports")
                        st.write(f"**Cluster:** {result['cluster']}")
                        
                        if result['sent']:
                            tx_hash = result['hash']
                            result_placeholder.success(f"✅ Transazione inviata con successo!")
                            st.code(tx_hash, language=None)
                            
                            # Show saved file info
                            if result.get('saved_file'):
                                st.success(f"📁 Risultato salvato in: `execution_traces_results/{result['saved_file']}`")
                            elif result.get('save_error'):
                                st.warning(f"⚠️ Transazione inviata ma salvataggio fallito: {result['save_error']}")
                        else:
                            if not result['is_deployed']:
                                result_placeholder.warning("⚠️ Programma non deployato: transazione non inviata")
                            else:
                                result_placeholder.success("✅ Transazione costruita (non inviata)")
                        
            except requests.exceptions.RequestException as e:
                result_placeholder.error(f"Errore di connessione al backend: {e}")
            except Exception as e:
                result_placeholder.error(f"Errore: {e}")



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
