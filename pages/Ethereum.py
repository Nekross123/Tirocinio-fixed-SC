import streamlit as st
import os
import sys
import requests
import json
import asyncio

toolchain_path = os.path.join(os.path.dirname(__file__), "..", "Toolchain")
sys.path.append(toolchain_path)

# ==============================
# Import Ethereum modules
# ==============================
try:
    from ethereum_module.hardhat_module.compiler_and_deployer import compile_and_deploy_contracts
    import ethereum_module.ethereum_utils as eth_utils
    from ethereum_module.hardhat_module.contract_utils import (
        fetch_deployed_contracts,
        load_abi_for_contract,
        fetch_functions_for_contract,
        fetch_contract_context,
    )
except ImportError as e:
    st.error(f"Ethereum modules not found. Please ensure the Toolchain is properly set up: {e}")
    st.stop()

# --------------------------------------------------
#  for Interactive section
# --------------------------------------------------
def _render_address_block(param_name: str, param_type: str, wallet_files: list[str]):
    """Render UI block for address/account parameter input"""
    with st.expander(f"Parameter: {param_name} ({param_type})", expanded=False):
        method = st.selectbox(
            f"Method for {param_name}",
            ["Wallet Address", "Manual Address", "Contract Address"],
            key=f"method_{param_name}"
        )
        data = {"name": param_name, "type": param_type, "method": method}

        if method == "Wallet Address":
            data['wallet'] = st.selectbox(
                f"Wallet file for {param_name}", ["--"] + wallet_files, key=f"wallet_{param_name}"
            )
            st.caption("Use the address of the selected wallet.")

        elif method == "Manual Address":
            data['address_manual'] = st.text_input(
                f"Address (0x...)", key=f"address_manual_{param_name}", 
                placeholder="0x742d35cc6532c49e390d93c9c7bb35b3b7a5c57e"
            )
            st.caption("Enter an Ethereum address manually.")

        elif method == "Contract Address":
            # List deployed contracts
            try:
                contracts = fetch_deployed_contracts()
                data['contract'] = st.selectbox(
                    f"Contract for {param_name}", ["--"] + contracts, key=f"contract_{param_name}"
                )
            except:
                st.warning("No deployed contracts found")
                data['contract'] = "--"

        return data

st.set_page_config(
    page_title="Ethereum DApp",  
    page_icon="⚡"              
)

st.title("⚡ Ethereum Toolchain")

# ==============================
# Sidebar
# ==============================
st.sidebar.header("Menu")
selected_action = st.sidebar.radio(
    "Choose an action:",
    ("Manage Wallets", "Upload new contract", "Compile & Deploy", "Interactive Contract Interaction", "Other")
)

WALLETS_PATH = os.path.join(toolchain_path, "ethereum_module", "ethereum_wallets")
CONTRACTS_PATH = os.path.join(toolchain_path, "ethereum_module", "hardhat_module", "contracts")
DEPLOYMENTS_PATH = os.path.join(toolchain_path, "ethereum_module", "hardhat_module", "deployments")

# ==============================
# Main section
# ==============================
st.header(f"{selected_action}")

if selected_action == "Manage Wallets":
    if not os.path.exists(WALLETS_PATH):
        st.warning("Wallets directory not found. Please create Ethereum wallets first.")
    else:
        wallet_files = [f for f in os.listdir(WALLETS_PATH) if f.endswith(".json")]
        selected_wallet_file = st.selectbox("Select wallet", ["--"] + wallet_files)
        
        if selected_wallet_file != "--" and st.button("Show balance and address"):
            try:
                res = requests.post(
                    "http://127.0.0.1:5000/eth_wallet_balance",
                    json={"wallet_file": selected_wallet_file}
                )
                if res.status_code == 200:
                    data = res.json()
                    st.success(f"ETH Balance: {data['balance']} ETH")
                    st.info(f"Address: {data['address']}")
                else:
                    st.error(res.json().get("error", "Unknown error"))
            except requests.exceptions.RequestException as e:
                st.error(f"Backend connection error: {e}")

elif selected_action == "Upload new contract":
    st.subheader("Upload Solidity Contract")
    
    uploaded_file = st.file_uploader(
        "Choose a Solidity file (.sol)", 
        type="sol",
        help="Upload a .sol file containing your smart contract code"
    )
    
    if uploaded_file is not None:
        contract_content = uploaded_file.read().decode('utf-8')
        contract_name = uploaded_file.name
        
        try:
            # Ensure contracts directory exists
            os.makedirs(CONTRACTS_PATH, exist_ok=True)
            
            # Save the contract file
            contract_path = os.path.join(CONTRACTS_PATH, contract_name)
            with open(contract_path, 'w', encoding='utf-8') as f:
                f.write(contract_content)
            
            st.success(f"✅ Contract uploaded successfully!")
            st.info(f"📁 **File name**: {contract_name}")
            st.info(f"📂 **Saved to**: `{contract_path}`")
            st.info(f"🔧 You can now compile and deploy this contract in the 'Compile & Deploy' section.")
            
        except Exception as e:
            st.error(f"❌ Error saving contract: {e}")

elif selected_action == "Compile & Deploy":
    if not os.path.exists(WALLETS_PATH):
        st.warning("No wallets found. Please create Ethereum wallets first.")
    elif not os.path.exists(CONTRACTS_PATH):
        st.warning("No contracts directory found. Please upload contracts first.")
    else:
        wallet_files = [f for f in os.listdir(WALLETS_PATH) if f.endswith(".json")]
        selected_wallet_file = st.selectbox("Select wallet for deployment", ["--"] + wallet_files)

        selected_network = st.selectbox(
            "Select a network", 
            ["--", "localhost", "sepolia", "goerli", "mainnet"]
        )

        st.markdown("----")
        # Choose compilation mode
        compile_mode = st.radio(
            "Compilation mode:",
            ("All contracts", "Single contract"),
            help="Choose whether to compile all contracts or just a specific one"
        )

        selected_contract_file = None
        if compile_mode == "Single contract":
            contract_files = [f for f in os.listdir(CONTRACTS_PATH) if f.endswith(".sol")]
            selected_contract_file = st.selectbox("Select contract", ["--"] + contract_files)
        else:
            # Show list of all contracts that will be compiled
            contract_files = [f for f in os.listdir(CONTRACTS_PATH) if f.endswith(".sol")]
            if contract_files:
                st.info("📋 Contracts that will be compiled and deployed:")
                for i, contract in enumerate(contract_files, 1):
                    st.write(f"{i}. `{contract}`")
            else:
                st.warning("❌ No .sol contracts found in the contracts folder")

        st.markdown("----")
        deploy_flag = st.checkbox("Also deploy after compilation", value=True)

        # Button conditions
        if compile_mode == "All contracts":
            can_proceed = selected_wallet_file != "--" and selected_network != "--" and len(contract_files) > 0
        else:
            can_proceed = selected_wallet_file != "--" and selected_contract_file != "--" and selected_network != "--"

        if can_proceed and st.button("Compile & Deploy"):
            if compile_mode == "Single contract":
                st.info(f"⚡ Starting compilation and deployment of `{selected_contract_file}`... ⏳")
            else:
                st.info(f"⚡ Starting compilation and deployment of {len(contract_files)} contracts... ⏳")
            
            progress_bar = st.empty()
            status_placeholder = st.empty()

            # STEP 1: Compilation
            progress_bar.progress(30)
            if compile_mode == "Single contract":
                status_placeholder.info(f"📦 Compiling contract `{selected_contract_file}`...")
            else:
                status_placeholder.info(f"📦 Compiling {len(contract_files)} contracts...")

            try:
                compile_payload = {
                    "wallet_file": selected_wallet_file,
                    "network": selected_network,
                    "deploy": False
                }
                # Add single_contract parameter if in single contract mode
                if compile_mode == "Single contract":
                    compile_payload["single_contract"] = selected_contract_file
                    
                compile_res = requests.post(
                    "http://127.0.0.1:5000/eth_compile_deploy",
                    json=compile_payload
                )
                compile_res = compile_res.json()
            except requests.exceptions.RequestException as e:
                st.error(f"Backend connection error: {e}")
                st.stop()
        
            if compile_res["success"]:
                st.empty()
                if compile_mode == "Single contract":
                    status_placeholder.success(f"✅ Compilation completed for `{selected_contract_file}`!")
                else:
                    compiled_count = len([c for c in compile_res["contracts"] if c["compiled"]])
                    status_placeholder.success(f"✅ Compilation completed: {compiled_count}/{len(compile_res['contracts'])} contracts!")
            else:
                st.empty()
                status_placeholder.error(f"❌ Error during compilation: {compile_res.get('error', 'Unknown error')}")
                st.stop()
            
            progress_bar.progress(50)
            status_placeholder.empty()

            # STEP 2: Deploy (if requested)
            if deploy_flag:
                progress_bar.progress(70)
                if compile_mode == "Single contract":
                    status_placeholder.info(f"🚀 Deploying contract `{selected_contract_file}`...")
                else:
                    status_placeholder.info(f"🚀 Deploying {len(contract_files)} contracts...")
                
                try:
                    deploy_payload = {
                        "wallet_file": selected_wallet_file,
                        "network": selected_network,
                        "deploy": True
                    }
                    # Add single_contract parameter if in single contract mode
                    if compile_mode == "Single contract":
                        deploy_payload["single_contract"] = selected_contract_file
                        
                    deploy_res = requests.post(
                        "http://127.0.0.1:5000/eth_compile_deploy",
                        json=deploy_payload
                    )
                    deploy_res = deploy_res.json()
                except requests.exceptions.RequestException as e:
                    st.error(f"Backend connection error: {e}")
                    st.stop()

                # Check if all operations were successful
                all_successful = True
                has_errors = False
                
                if compile_mode == "Single contract":
                    if deploy_res['contracts']:
                        contract = deploy_res['contracts'][0]
                        all_successful = contract.get('compiled', False) and contract.get('deployed', False)
                        if contract.get('errors'):
                            has_errors = True
                            st.subheader("❌ Errors encountered:")
                            for error in contract['errors']:
                                st.error(f"🔴 {error.strip()}")
                        
                        if deploy_res["success"] and contract.get('deployed', False):
                            contract_address = contract.get('address', 'N/A')
                            status_placeholder.success(f"🎉 Deployment completed! Contract Address: {contract_address}")
                        elif deploy_res["success"] and contract.get('compiled', False) and not contract.get('deployed', False):
                            status_placeholder.warning(f"⚠️ Compilation succeeded but deployment failed")
                        elif not deploy_res["success"]:
                            status_placeholder.error(f"❌ Operation failed")
                    else:
                        all_successful = False
                        status_placeholder.error("❌ No contract data returned")
                else:
                    # Multiple contracts mode
                    successful_contracts = []
                    failed_contracts = []
                    
                    for contract in deploy_res.get("contracts", []):
                        contract_all_success = contract.get('compiled', False) and contract.get('deployed', False)
                        
                        if contract.get('errors'):
                            has_errors = True
                            failed_contracts.append(contract)
                        
                        if contract_all_success:
                            successful_contracts.append(contract)
                        else:
                            failed_contracts.append(contract)
                            all_successful = False
                    
                    # Show errors if any
                    if has_errors:
                        st.subheader("❌ Errors encountered:")
                        for contract in failed_contracts:
                            if contract.get('errors'):
                                st.error(f"🔴 **{contract['contract']}**: {'; '.join(contract['errors'])}")
                    
                    # Show deployment results
                    if deploy_res["success"]:
                        deployed_count = len([c for c in deploy_res["contracts"] if c.get("deployed", False)])
                        total_count = len(deploy_res["contracts"])
                        
                        if deployed_count == total_count:
                            status_placeholder.success(f"🎉 All contracts deployed successfully: {deployed_count}/{total_count}")
                        elif deployed_count > 0:
                            status_placeholder.warning(f"⚠️ Partial success: {deployed_count}/{total_count} contracts deployed")
                        else:
                            status_placeholder.error(f"❌ No contracts deployed successfully")
                        
                        # Show Contract Addresses of all deployed contracts
                        if deployed_count > 0:
                            st.subheader("📋 Successfully deployed contracts:")
                            for contract in deploy_res["contracts"]:
                                if contract.get("deployed", False) and contract.get("address"):
                                    st.success(f"✅ `{contract['contract']}`: {contract['address']}")
                    else:
                        all_successful = False
                        status_placeholder.error(f"❌ Operation failed")

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
                
                if compile_mode == "Single contract":
                    if compile_res.get('contracts'):
                        contract = compile_res['contracts'][0]
                        compile_successful = contract.get('compiled', False)
                        if contract.get('errors'):
                            compile_has_errors = True
                else:
                    for contract in compile_res.get("contracts", []):
                        if not contract.get('compiled', False) or contract.get('errors'):
                            compile_successful = False
                        if contract.get('errors'):
                            compile_has_errors = True
                
                if compile_successful and not compile_has_errors:
                    st.success("✅ Compilation completed successfully!")
                elif compile_has_errors:
                    st.error("❌ Compilation completed with errors")
                else:
                    st.warning("⚠️ Compilation completed with some failures")

elif selected_action == "Interactive Contract Interaction":
    st.caption("Select a deployed contract and interact with its functions.")

    try:
        contracts = fetch_deployed_contracts()
        if not contracts:
            st.warning("No contracts deployed yet, please compile and deploy a contract first")
        else:
            contract = st.selectbox("Contract", ["--"] + contracts)

            abi = None
            functions = []
            if contract != "--":
                try:
                    abi = load_abi_for_contract(contract)
                    functions = fetch_functions_for_contract(contract)
                except FileNotFoundError as e:
                    st.error(str(e))

            function_name = st.selectbox("Function", ["--"] + functions) if contract != "--" else "--"

            if contract == "--":
                st.info("Select a contract.")
            elif function_name == "--":
                st.info("Select a function.")
            else:
                ctx = fetch_contract_context(contract, function_name)
                inputs = ctx['inputs']
                is_payable = ctx['is_payable']
                is_view = ctx['is_view']
                
                wallet_files = [f for f in os.listdir(WALLETS_PATH) if f.endswith('.json')]

                st.markdown("---")
                st.markdown("### Parameters")

                # Form for function parameters + submit
                with st.form("interact_contract_form"):
                    
                    # Function inputs
                    param_values = {}
                    address_inputs = []
                    
                    if inputs:
                        st.markdown("#### Function Parameters")
                        for inp in inputs:
                            param_name = inp['name']
                            param_type = inp['type']
                            
                            if param_type == 'address':
                                # Special handling for address parameters
                                data = _render_address_block(param_name, param_type, wallet_files)
                                address_inputs.append(data)
                            elif param_type.startswith('uint') or param_type.startswith('int'):
                                param_values[param_name] = st.text_input(
                                    f"{param_name} ({param_type})", 
                                    key=f"param_{param_name}",
                                    placeholder="Enter number"
                                )
                            elif param_type == 'bool':
                                param_values[param_name] = st.selectbox(
                                    f"{param_name} (bool)", 
                                    ["--", "true", "false"], 
                                    key=f"param_{param_name}"
                                )
                            elif param_type == 'string':
                                param_values[param_name] = st.text_input(
                                    f"{param_name} (string)", 
                                    key=f"param_{param_name}",
                                    placeholder="Enter string"
                                )
                            elif param_type == 'bytes' or param_type.startswith('bytes'):
                                param_values[param_name] = st.text_input(
                                    f"{param_name} ({param_type})", 
                                    key=f"param_{param_name}",
                                    placeholder="0x..."
                                )
                            else:
                                param_values[param_name] = st.text_input(
                                    f"{param_name} ({param_type})", 
                                    key=f"param_{param_name}",
                                    help=f"Custom type: {param_type}"
                                )
                    
                    # Value field for payable functions
                    value_eth = "0"
                    if is_payable:
                        st.markdown("#### Ether Value")
                        value_eth = st.text_input(
                            "Value (ETH)", 
                            value="0",
                            key="value_eth",
                            help="Amount of Ether to send with the transaction"
                        )
                    
                    # Caller wallet
                    st.markdown("#### Transaction Sender")
                    caller_wallet = st.selectbox(
                        "Caller wallet", 
                        ["--"] + wallet_files, 
                        key="caller_wallet"
                    )
                    
                    # Gas settings
                    st.markdown("#### Gas Settings")
                    col1, col2 = st.columns(2)
                    with col1:
                        gas_limit = st.text_input(
                            "Gas Limit", 
                            value="300000",
                            key="gas_limit"
                        )
                    with col2:
                        gas_price = st.text_input(
                            "Gas Price (Gwei)", 
                            value="20",
                            key="gas_price"
                        )
                    
                    if is_view:
                        submit_text = "Call (Read-only)"
                    else:
                        submit_text = "Send Transaction"
                    
                    submitted = st.form_submit_button(submit_text, type="primary")

                # Handle form submission
                if submitted:
                    result_placeholder = st.empty()
                    try:
                        result_placeholder.info("Processing transaction...")

                        # Prepare payload for Flask backend
                        payload = {
                            "contract": contract,
                            "function_name": function_name,
                            "param_values": param_values,
                            "address_inputs": address_inputs,
                            "value_eth": value_eth,
                            "caller_wallet": caller_wallet,
                            "gas_limit": gas_limit,
                            "gas_price": gas_price,
                            "is_view": is_view
                        }

                        # Call Flask backend
                        response = requests.post(
                            "http://127.0.0.1:5000/eth_interact_contract",
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

                                # Display results
                                st.markdown("---")
                                st.subheader("Result")
                                
                                if is_view:
                                    result_placeholder.success("✅ Function call completed!")
                                    st.write(f"**Return value:** {result.get('return_value', 'N/A')}")
                                else:
                                    if result.get('transaction_hash'):
                                        result_placeholder.success("✅ Transaction sent successfully!")
                                        st.write(f"**Transaction Hash:** {result['transaction_hash']}")
                                        st.write(f"**Gas Used:** {result.get('gas_used', 'N/A')}")
                                        st.write(f"**Status:** {result.get('status', 'N/A')}")
                                    else:
                                        result_placeholder.error("❌ Transaction failed")

                    except requests.exceptions.RequestException as e:
                        result_placeholder.error(f"Backend connection error: {e}")
                    except Exception as e:
                        result_placeholder.error(f"Error: {e}")
                        
    except Exception as e:
        st.error(f"Error loading contracts: {e}")

else:
    st.subheader("Other features")
    st.write("Placeholder section for future Ethereum DApp features.")

# ==============================
# Footer
# ==============================
st.markdown("---")
st.write("© 2025 - Ethereum Toolchain")
