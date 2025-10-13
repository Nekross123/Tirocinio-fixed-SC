
import streamlit as st
import os
import sys
import requests
import json
import asyncio

toolchain_path = os.path.join(os.path.dirname(__file__), "..", "Toolchain")
sys.path.append(toolchain_path)
# ==============================
# Import Solana modules
# ==============================
from solana_module.anchor_module.dapp_automatic_insertion_manager import  fetch_initialized_programs , build_table
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
            f"Method for {acc}",
            ["Wallet", "Manual PDA", "PDA Seeds", "Random PDA"],
            key=f"method_{acc}"
        )
        data = {"name": acc, "method": method}

        if method == "Wallet":
            data['wallet'] = st.selectbox(
                f"Wallet file for {acc}", ["--"] + wallet_files, key=f"wallet_{acc}"
            )
            st.caption("Use the public key of the selected wallet directly.")

        elif method == "Manual PDA":
            data['pda_manual'] = st.text_input(
                f"PDA (44 Base58 characters)", key=f"pda_manual_{acc}", placeholder="E.g: 44 chars"
            )
            st.caption("Enter a pre-calculated PDA.")

        elif method == "PDA Seeds":
            st.write("Generate PDA from deterministic seeds")
            seeds_count = st.number_input(
                f"Number of seeds", min_value=1, max_value=10, value=1, key=f"seeds_count_{acc}"
            )
            seeds = []
            for i in range(seeds_count):
                col1, col2 = st.columns([1,3])
                with col1:
                    smode = st.selectbox(
                        f"Type {i+1}", ["Wallet", "Manual", "Random"], key=f"seed_mode_{acc}_{i}"
                    )
                seed_entry = {"mode": smode}
                with col2:
                    if smode == 'Wallet':
                        seed_entry['wallet'] = st.selectbox(
                            f"Wallet seed {i+1}", ["--"] + wallet_files, key=f"seed_wallet_{acc}_{i}"
                        )
                    elif smode == 'Manual':
                        seed_entry['manual'] = st.text_input(
                            f"Manual seed {i+1}", key=f"seed_manual_{acc}_{i}", placeholder="string"
                        )
                    else:
                        st.caption("Generated randomly on submit")
                seeds.append(seed_entry)
            data['seeds'] = seeds
            data['seeds_count'] = seeds_count

        else:  # Random PDA
            st.info("Random PDA generated on submit (32 bytes → base58 → Pubkey)")

        # Optional debug (activate by setting ?debug=1 in URL) using new st.query_params API
        qp = st.query_params
        if qp.get('debug', ['0'])[0] == '1':
            st.code({k: v for k, v in data.items() if k != 'seeds'})
        return data


st.set_page_config(
    page_title="Solana DApp",  
    page_icon="🌞"              
)


st.set_page_config(page_title="Solana DApp", layout="wide")
st.title("🌞 Solana Toolchain")

# ==============================
# Sidebar
# ==============================
st.sidebar.header("Menu")
selected_action = st.sidebar.radio(
    "Choose an action:",
    ("Manage Wallets","Upload new program", "Compile & Deploy", "Interactive Data Insertion", "Close programs","Execution Traces")
)

WALLETS_PATH = os.path.join(toolchain_path, "solana_module", "solana_wallets")
ANCHOR_PROGRAMS_PATH = os.path.join(toolchain_path, "solana_module", "anchor_module", "anchor_programs")
TRACES_PATH = os.path.join(toolchain_path, "solana_module", "anchor_module", "execution_traces")

# ==============================
# Main section
# ==============================
st.header(f"{selected_action}")

if selected_action == "Manage Wallets":
    wallet_files = [f for f in os.listdir(WALLETS_PATH) if f.endswith(".json")]
    selected_wallet_file = st.selectbox("Select wallet", ["--"] + wallet_files)
    
    if selected_wallet_file != "--" and st.button("Show balance and PubKey"):
        try:
            res = requests.post(
                "http://127.0.0.1:5000/wallet_balance",
                json={"wallet_file": selected_wallet_file}
            )
            if res.status_code == 200:
                data = res.json()
                st.success(f"SOL Balance: {data['balance']} SOL")
                st.info(f"Public Key: {data['pubkey']}")
            else:
                st.error(res.json().get("error", "Unknown error"))
        except requests.exceptions.RequestException as e:
            st.error(f"Backend connection error: {e}")

elif selected_action == "Upload new program":
    st.subheader("Upload Rust Program")
    
    uploaded_file = st.file_uploader(
        "Choose a Rust file (.rs)", 
        type="rs",
        help="Upload a .rs file containing your Anchor program code"
    )
    
    if uploaded_file is not None:
        program_content = uploaded_file.read().decode('utf-8')
        program_name = uploaded_file.name
        
        try:
            # Ensure anchor_programs directory exists
            os.makedirs(ANCHOR_PROGRAMS_PATH, exist_ok=True)
            
            # Save the program file
            program_path = os.path.join(ANCHOR_PROGRAMS_PATH, program_name)
            with open(program_path, 'w', encoding='utf-8') as f:
                f.write(program_content)
            
            st.success(f"✅ Program uploaded successfully!")
            st.info(f"📁 **File name**: {program_name}")
            st.info(f"📂 **Saved to**: `{program_path}`")
            st.info(f"🔧 You can now compile and deploy this program in the 'Compile & Deploy' section.")
            
        except Exception as e:
            st.error(f"❌ Error saving program: {e}")

elif selected_action == "Compile & Deploy":
    
    wallet_files = [f for f in os.listdir(WALLETS_PATH) if f.endswith(".json")]
    selected_wallet_file = st.selectbox("Select wallet for deployment", ["--"] + wallet_files)

    selected_cluster = st.selectbox("Select a cluster", ["--"] + ["Devnet", "Testnet", "Mainnet"])

    st.markdown("----")
    # Choose compilation mode
    compile_mode = st.radio(
        "Compilation mode:",
        ("All programs", "Single program"),
        help="Choose whether to compile all programs or just a specific one"
    )

    selected_program_file = None
    if compile_mode == "Single program":
        program_files = [f for f in os.listdir(ANCHOR_PROGRAMS_PATH) if f.endswith(".rs")]
        selected_program_file = st.selectbox("Select program", ["--"] + program_files)
    else:
        # Show list of all programs that will be compiled
        program_files = [f for f in os.listdir(ANCHOR_PROGRAMS_PATH) if f.endswith(".rs")]
        if program_files:
            st.info("📋 Programs that will be compiled and deployed:")
            for i, prog in enumerate(program_files, 1):
                st.write(f"{i}. `{prog}`")
        else:
            st.warning("❌ No .rs programs found in the anchor_programs folder")

    st.markdown("----")
    deploy_flag = st.checkbox("Also deploy after compilation", value=True)

    # Button conditions
    if compile_mode == "All programs":
        can_proceed = selected_wallet_file != "--" and selected_cluster != "--" and len(program_files) > 0
    else:
        can_proceed = selected_wallet_file != "--" and selected_program_file != "--" and selected_cluster != "--"

    if can_proceed and st.button("Compile & Deploy"):
        if compile_mode == "Single program":
            st.info(f"⚡ Starting compilation and deployment of `{selected_program_file}`... ⏳")
        else:
            st.info(f"⚡ Starting compilation and deployment of {len(program_files)} programs... ⏳")
        
        progress_bar = st.empty()
        status_placeholder = st.empty()

        # STEP 1: Compilation
        progress_bar.progress(30)
        if compile_mode == "Single program":
            status_placeholder.info(f"📦 Compiling program `{selected_program_file}`...")
        else:
            status_placeholder.info(f"📦 Compiling {len(program_files)} programs...")

        try:
            compile_payload = {
                "wallet_file": selected_wallet_file,
                "cluster": selected_cluster,
                "deploy": False
            }
            # Add single_program parameter if in single program mode
            if compile_mode == "Single program":
                compile_payload["single_program"] = selected_program_file
                
            compile_res = requests.post(
                "http://127.0.0.1:5000/compile_deploy",
                json=compile_payload
            )
            compile_res = compile_res.json()
        except requests.exceptions.RequestException as e:
            st.error(f"Backend connection error: {e}")
            st.stop()
    
        if compile_res["success"]:

            st.empty()
            if compile_mode == "Single program":
                status_placeholder.success(f"✅ Compilation completed for `{selected_program_file}`!")
            else:
                compiled_count = len([p for p in compile_res["programs"] if p["compiled"]])
                status_placeholder.success(f"✅ Compilation completed: {compiled_count}/{len(compile_res['programs'])} programs!")
        else:
            st.empty()
            status_placeholder.error(f"❌ Error during compilation: {compile_res.get('error', 'Unknown error')}")
            print("Compilation JSON details:", compile_res)
            st.stop()
        
        progress_bar.progress(50)
        status_placeholder.empty()

        # STEP 2: Deploy (if requested)
        if deploy_flag:
            progress_bar.progress(70)
            if compile_mode == "Single program":
                status_placeholder.info(f"🚀 Deploying program `{selected_program_file}`...")
            else:
                status_placeholder.info(f"🚀 Deploying {len(program_files)} programs...")
            
            try:
                deploy_payload = {
                    "wallet_file": selected_wallet_file,
                    "cluster": selected_cluster,
                    "deploy": True
                }
                # Add single_program parameter if in single program mode
                if compile_mode == "Single program":
                    deploy_payload["single_program"] = selected_program_file
                    
                deploy_res = requests.post(
                    "http://127.0.0.1:5000/compile_deploy",
                    json=deploy_payload
                )
                deploy_res = deploy_res.json()
            except requests.exceptions.RequestException as e:
                st.error(f"Backend connection error: {e}")
                st.stop()

            # Check if all operations were successful
            all_successful = True
            has_errors = False
            
            if compile_mode == "Single program":
                if deploy_res['programs']:
                    prog = deploy_res['programs'][0]
                    all_successful = prog.get('anchorpy_initialized', False) and prog.get('compiled', False) and prog.get('deployed', False)
                    if prog.get('errors'):
                        has_errors = True
                        st.subheader("❌ Errors encountered:")
                        for error in prog['errors']:
                            st.error(f"🔴 {error.strip()}")
                    
                    if deploy_res["success"] and prog.get('deployed', False):
                        program_id = prog.get('program_id', 'N/A')
                        status_placeholder.success(f"🎉 Deployment completed! Program ID: {program_id}")
                    elif deploy_res["success"] and prog.get('compiled', False) and not prog.get('deployed', False):
                        status_placeholder.warning(f"⚠️ Compilation succeeded but deployment failed")
                    elif not deploy_res["success"]:
                        status_placeholder.error(f"❌ Operation failed")
                else:
                    all_successful = False
                    status_placeholder.error("❌ No program data returned")
            else:
                # Multiple programs mode
                successful_programs = []
                failed_programs = []
                
                for prog in deploy_res.get("programs", []):
                    prog_all_success = prog.get('anchorpy_initialized', False) and prog.get('compiled', False) and prog.get('deployed', False)
                    
                    if prog.get('errors'):
                        has_errors = True
                        failed_programs.append(prog)
                    
                    if prog_all_success:
                        successful_programs.append(prog)
                    else:
                        failed_programs.append(prog)
                        all_successful = False
                
                # Show errors if any
                if has_errors:
                    st.subheader("❌ Errors encountered:")
                    for prog in failed_programs:
                        if prog.get('errors'):
                            st.error(f"🔴 **{prog['program']}**: {'; '.join(prog['errors'])}")
                
                # Show deployment results
                if deploy_res["success"]:
                    deployed_count = len([p for p in deploy_res["programs"] if p.get("deployed", False)])
                    total_count = len(deploy_res["programs"])
                    
                    if deployed_count == total_count:
                        status_placeholder.success(f"🎉 All programs deployed successfully: {deployed_count}/{total_count}")
                    elif deployed_count > 0:
                        status_placeholder.warning(f"⚠️ Partial success: {deployed_count}/{total_count} programs deployed")
                    else:
                        status_placeholder.error(f"❌ No programs deployed successfully")
                    
                    # Show Program IDs of all deployed programs
                    if deployed_count > 0:
                        st.subheader("📋 Successfully deployed programs:")
                        for prog in deploy_res["programs"]:
                            if prog.get("deployed", False) and prog.get("program_id"):
                                st.success(f"✅ `{prog['program']}`: {prog['program_id']}")
                else:
                    all_successful = False
                    status_placeholder.error(f"❌ Operation failed")
            
            print("Compile & deploy JSON details:", json.dumps(deploy_res, indent=2))

        progress_bar.progress(100)
        status_placeholder.empty()
        progress_bar.empty()
        
        # Only show success if all operations completed successfully and no errors
        if deploy_flag:
            if all_successful and not has_errors:
                st.success("✅ Operation completed successfully!")
            elif has_errors:
                st.error("❌ Operation completed with errors")
            else:
                st.warning("⚠️ Operation completed with some failures")
        else:
            # Only compilation was requested
            compile_successful = True
            compile_has_errors = False
            
            if compile_mode == "Single program":
                if compile_res.get('programs'):
                    prog = compile_res['programs'][0]
                    compile_successful = prog.get('compiled', False)
                    if prog.get('errors'):
                        compile_has_errors = True
            else:
                for prog in compile_res.get("programs", []):
                    if not prog.get('compiled', False) or prog.get('errors'):
                        compile_successful = False
                    if prog.get('errors'):
                        compile_has_errors = True
            
            if compile_successful and not compile_has_errors:
                st.success("✅ Compilation completed successfully!")
            elif compile_has_errors:
                st.error("❌ Compilation completed with errors")
            else:
                st.warning("⚠️ Compilation completed with some failures")


elif selected_action == "Execution Traces":

    fetched_programs = fetch_initialized_programs()
    if not fetched_programs:
        st.warning("No programs initialized yet, please compile and deploy a program first")
    else:


        traces_files = [f for f in os.listdir(TRACES_PATH) if f.endswith(".json")]
        selected_trace_file = st.selectbox("Select trace", ["--"] + traces_files)

        if selected_trace_file != "--" and st.button("Load and execute trace"):
            try:
                trace_res = requests.post(
                    "http://127.0.0.1:5000/automatic_data_insertion",
                    json={"trace_file": selected_trace_file}
                )

                if trace_res.status_code == 200:
                    st.info("Trace loaded successfully.")
                    
                    build_table(trace_res.json().get("result"))
                else:
                    st.error(trace_res.json().get("error", "Unknown error"))
            except requests.exceptions.RequestException as e:
                st.error(f"Backend connection error: {e}")
                st.stop()


        

   
    
elif selected_action == "Interactive Data Insertion":
    st.caption("Fill everything out and submit in one go.")

    programs = fetch_programs()
    if not programs:
        st.warning("No programs initialized yet, please compile and deploy a program first")
    else:

        program = st.selectbox("Program", ["--"] + programs)

        idl = None
        instructions = []
        if program != "--":
            try:
                idl = load_idl_for_program(program)
                instructions = fetch_instructions_for_program(program)
            except FileNotFoundError as e:
                st.error(str(e))

        instruction = st.selectbox("Instruction", ["--"] + instructions) if program != "--" else "--"

        if program == "--":
            st.info("Select a program.")
        elif instruction == "--":
            st.info("Select an instruction.")
        else:
            ctx = fetch_program_context(program, instruction)
            req_accounts = ctx['required_accounts']
            signer_accounts = ctx['signer_accounts']
            args_spec = ctx['args_spec']
            wallets_dir = os.path.join(solana_base_path, 'solana_wallets')
            wallet_files = [f for f in os.listdir(wallets_dir) if f.endswith('.json')]

            st.markdown("---")
            st.markdown("### Parameters")

            st.markdown("#### Accounts")
            account_inputs = []
            for acc in req_accounts:
                data = _render_account_block(acc, wallet_files)
                account_inputs.append(data)

            # Form only for payees/args/provider + submit
            with st.form("interactive_tx_form"):

                # Payees
                payees = []
                if instruction == 'initialize':
                    st.markdown("#### Payees")
                    num_payees = st.number_input("Number of payees", min_value=0, max_value=50, value=0, key="num_payees2")
                    for i in range(num_payees):
                        wallet_sel = st.selectbox(f"Payee {i+1}", ["--"] + wallet_files, key=f"payee2_{i}")
                        payees.append(wallet_sel)

                # Args
                st.markdown("#### Arguments")
                arg_values = {}
                for a in args_spec:
                    name = a['name']
                    array_type, array_length = check_if_array(a)
                    if array_type is not None:
                        if array_length is not None:
                            arg_values[name] = st.text_input(f"{name} (array {array_type}[{array_length}])", key=f"arg2_{name}")
                        else:
                            arg_values[name] = st.text_input(f"{name} (vector {array_type}, empty = [] )", key=f"arg2_{name}")
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
                            st.warning(f"Unsupported type: {a['type']}")

                # Provider
                st.markdown("#### Provider")
                provider_wallet = st.selectbox("Provider wallet", ["--"] + wallet_files, key="prov2")
                send_now = st.checkbox("Send now || Calculate transaction", value=True, key="send_now2")

                submitted = st.form_submit_button("Build & (Send)", type="primary")

            # Local result variables 
            if submitted:
                result_placeholder = st.empty()
                try:
                    result_placeholder.info("Building transaction...")

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
                        result_placeholder.error(f"Error: {error_data.get('error', 'Unknown error')}")
                    else:
                        response_data = response.json()
                        if not response_data.get("success"):
                            result_placeholder.error(f"Error: {response_data.get('error', 'Unknown error')}")
                        else:
                            result = response_data["result"]

                            # Display
                            st.markdown("---")
                            st.subheader("Result")
                            st.write(f"**Size:** {result['size']} bytes")
                            st.write(f"**Fee:** {result['fees']} lamports")
                            st.write(f"**Cluster:** {result['cluster']}")

                            if result['sent']:
                                tx_hash = result['hash']
                                result_placeholder.success(f"✅ Transaction sent successfully!")
                                st.code(tx_hash, language=None)

                                # Show saved file info
                                if result.get('saved_file'):
                                    st.success(f"📁 Result saved in: `execution_traces_results/{result['saved_file']}`")
                                elif result.get('save_error'):
                                    st.warning(f"⚠️ Transaction sent but save failed: {result['save_error']}")
                            else:
                                if not result['is_deployed']:
                                    result_placeholder.warning("⚠️ Program not deployed: transaction not sent")
                                else:
                                    result_placeholder.success("✅ Transaction built (not sent)")

                except requests.exceptions.RequestException as e:
                    result_placeholder.error(f"Backend connection error: {e}")
                except Exception as e:
                    result_placeholder.error(f"Error: {e}")



elif selected_action == "Close programs":
    

    fetched_programs = fetch_initialized_programs()

    if not fetched_programs:
        st.warning("No programs initialized yet, please compile and deploy a program first")
    else:
        selected_program = st.selectbox("Select a program", ["--"] + fetched_programs)


        if selected_program != "--" and st.button("Close program"):
            try:
                res = requests.post(
                    "http://127.0.0.1:5000/close_program",
                    json={"program": selected_program}
                )

                if res.status_code == 200 and res.json().get("success"):
                    print(res.json().get("success"))
                    st.info("Program closed successfully.")

                else:
                    st.error(res.json().get("error", "Unknown error"))
                    st.warning("Check if the program is deplyed on the selected cluster and if the wallet has enough funds.")
                    st.warning("You can delete the program manually from the .anchor_files folder if the problem persists.")

            except requests.exceptions.RequestException as e:
                st.error(f"Backend connection error: {e}")
                st.stop()



# ==============================
# Footer
# ==============================
st.markdown("---")
st.write("© 2025 - Solana")