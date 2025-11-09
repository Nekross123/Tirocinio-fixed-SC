import streamlit as st
import os
import sys
import requests
import json
import asyncio

root_path = os.path.join(os.path.dirname(__file__), "..")
sys.path.append(root_path)

# ==============================
# Import Ethereum modules
# ==============================
try:
    from ethereum_module.hardhat_module.compiler_and_deployer import compile_contract,deploy_contracts
    import ethereum_module.ethereum_utils as eth_utils
    from ethereum_module.hardhat_module.contract_utils import (
        fetch_deployed_contracts,
        load_abi_for_contract,
        fetch_functions_for_contract,
        fetch_contract_context,
        format_function_info,
        interact_with_contract
    )
    from ethereum_module.streamlit_interactive import run_interactive_contract_interface
    from ethereum_module.streamlit_constructor_interface import (
        collect_constructor_args_streamlit,
        display_constructor_preview,
        validate_constructor_args,
        is_constructor_payable
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
    "Select Action",
    ("Manage Wallets", "Upload new contract", "Compile & Deploy", "Interactive data insertion", "Execution Traces")
)

WALLETS_PATH = os.path.join(root_path, "ethereum_module", "ethereum_wallets")
CONTRACTS_PATH = os.path.join(root_path, "ethereum_module", "hardhat_module", "contracts")
DEPLOYMENTS_PATH = os.path.join(root_path, "ethereum_module", "hardhat_module", "deployments")

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
    
        selected_network = st.selectbox(
                "Select a network", 
                ["--", "localhost", "devnet", "mainnet"]
            )
        
        if selected_wallet_file != "--" and st.button("Show balance and address"):
            try:
                res = requests.post(
                    "http://127.0.0.1:5000/eth_wallet_balance",
                    json={"wallet_file": selected_wallet_file , "network": selected_network}
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
            
            st.success(f"Contract uploaded successfully!")
            st.info(f" **File name**: {contract_name}")
            st.info(f" **Saved to**: `{contract_path}`")
            st.info(f" You can now compile and deploy this contract in the 'Compile & Deploy' section.")
            
        except Exception as e:
            st.error(f" Error saving contract: {e}")

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

        contract_files = [f for f in os.listdir(CONTRACTS_PATH) if f.endswith(".sol")]
        selected_contract_file = st.selectbox("Select contract", ["--"] + contract_files)
        
        st.markdown("----")

        #  LOGICA SESSIONE DI DEPLOY
        if all([selected_wallet_file != "--", selected_network != "--", selected_contract_file != "--"]):
            contract_name = selected_contract_file.replace('.sol', '')
            session_key = f'deploy_session_{contract_name}'
            
            # 1. CREAZIONE SESSIONE
            if session_key not in st.session_state:
                st.info(" Click to initialize deployment session")
                
                if st.button("Initialize Deployment Session"):
                    with st.spinner("Creating deployment session..."):
                        try:
                            session_payload = {
                                "action": "create_session",
                                "contract_file": selected_contract_file,
                                "wallet_file": selected_wallet_file, 
                                "network": selected_network
                            }

                           
                            
                            session_res = requests.post(
                                "http://127.0.0.1:5000/eth_deployment_session", 
                                json=session_payload,
                                timeout=30
                            )
                            
                            if session_res.status_code == 200:
                                session_data = session_res.json()
                                if session_data["success"]:
                                    st.session_state[session_key] = session_data
                                    st.rerun()  # Ricarica per mostrare il form
                                else:
                                    st.error(f" {session_data.get('error', 'Session creation failed')}")
                            else:
                                st.error(" Failed to connect to backend")
                                
                        except requests.exceptions.Timeout:
                            st.error(" Session creation timeout")
                        except Exception as e:
                            st.error(f" Session error: {str(e)}")
            
            # 2. RACCOLTA PARAMETRI (se sessione attiva)
            elif session_key in st.session_state:
                session_data = st.session_state[session_key]
                
                st.success(" Deployment session active!")
                st.markdown("### Constructor Parameters")
                
                # Mostra parametri costruttore
                display_constructor_preview(contract_name, session_data['abi'])
                
                # Raccogli parametri
                constructor_args = collect_constructor_args_streamlit(
                    contract_name, 
                    session_data['abi']
                )
                
                # Gestisci constructor payable
                value_in_ether = 0
                if is_constructor_payable(session_data['abi']):
                    value_in_ether = st.number_input(
                        " Send ETH with deployment:",
                        min_value=0.0,
                        value=0.0,
                        step=0.1,
                        key=f"eth_value_{contract_name}"
                    )
                
                # 3. DEPLOY
                if st.button(" Deploy Contract", type="primary") and constructor_args is not None:
                    
                    with st.spinner("Deploying contract..."):
                        try:
                            deploy_payload = {
                                "action": "deploy",
                                "session_id": session_data["session_id"],
                                "constructor_args": constructor_args,
                                "value_in_ether": value_in_ether
                            }

                           
                            
                            deploy_res = requests.post(
                                "http://127.0.0.1:5000/eth_deployment_session", 
                                json=deploy_payload,
                                timeout=120  # Timeout lungo per il deploy
                            )
                            
                            if deploy_res.status_code == 200:
                                deploy_result = deploy_res.json()
                                
                                if deploy_result["success"]:
                                    st.success(" Contract deployed successfully!")
                                    
                                    # Mostra dettagli deploy
                                    if deploy_result.get("address"):
                                        st.info(f"Contract Address:{deploy_result["address"]}" )
                                    if deploy_result.get("transaction_hash"):
                                            st.info(f"Transaction Hash: `{deploy_result['transaction_hash']}`")
                                    if deploy_result.get("gas_used"):
                                        st.info(f"Gas Used: {deploy_result['gas_used']}")
                                    
                                    #  Cleanup sessione
                                    del st.session_state[session_key]
                                    
                                else:
                                    st.error(f" Deployment failed: {deploy_result.get('error', 'Unknown error')}")
                                    # Mantieni la sessione per ritentare
                            else:
                                st.error(" Deployment request failed")
                                
                        except requests.exceptions.Timeout:
                            st.error(" Deployment timeout - transaction might still be processing")
                        except Exception as e:
                            st.error(f" Deployment error: {str(e)}")
            
            # Messaggio se manca qualche selezione
            else:
                st.info("Please select wallet, network and contract to continue")
            


elif selected_action == "Interactive data insertion":
    st.caption("Interactive guided interface for smart contract functions.")
    
    try:
        from ethereum_module.streamlit_interactive import (
            display_contract_selection,
            display_function_selection,
            get_available_contracts,
            run_interactive_contract_interface
        )
        
        # Get available contracts
        contracts = get_available_contracts()
        
        if not contracts:
            st.warning("No contracts deployed yet. Please compile and deploy a contract first.")
        else:
            # Network selection at the beginning
            st.markdown("### Network Selection")
            available_networks = ["sepolia", "localhost", "goerli", "mainnet"]
            
            selected_network = st.selectbox(
                "Select Network",
                available_networks,
                index=0,  # Default to sepolia
            )
            
            st.markdown("---")
            
            # Contract selection
            contract_id = st.selectbox(
                "Select Contract",
                ["--"] + contracts,
            )
            
            if contract_id != "--":
                # Show contract info
                from ethereum_module.interactive_interface import get_contract_info
                contract_info = get_contract_info(contract_id)
                
                with st.expander("Contract Information"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Address:** `{contract_info['address']}`")
                        st.write(f"**Network:** {contract_info['network']}")
                    with col2:
                        st.write(f"**Deployed:** {contract_info.get('deployed_at', 'N/A')}")
                        if contract_info.get('transaction_hash'):
                            st.write(f"**Transaction:** `{contract_info['transaction_hash'][:20]}...`")
                        else:
                            st.write("**Transaction:** N/A")
                
                # Show network info
                contract_network = contract_info['network']
                if contract_network:
                    st.info(f"This contract is deployed on **{contract_network}** network. Make sure to select the same network for interaction.")
                
                # Get interaction functions
                functions = fetch_functions_for_contract(contract_id)
                function_names = [f['name'] for f in functions]
                
                if not functions:
                    st.warning("No interaction functions available for this contract.")
                else:
                    # Function selection
                    function_name = st.selectbox(
                        "Select Function",
                        ["--"] + function_names,
                        
                    )
                    
                    if function_name != "--":
                        # Show function guidance
                        from ethereum_module.interactive_interface import get_function_guidance
                        guidance = get_function_guidance(contract_id, function_name)
                        
                        st.markdown("---")
                        st.markdown(f"### Function: `{function_name}`")
                        
                        # Parameters form
                        with st.form(key=f"interact_{function_name}_form"):
                            param_values = {}
                            address_inputs = []
                            
                            # Function parameters
                            if guidance['parameters']:
                                st.markdown("#### Function Parameters")
                                
                                for param in guidance['parameters']:
                                    st.markdown(f"**{param['name']}** ({param['type']})")
                                    
                                    if param['type'] == 'address':
                                        # Address parameter handling
                                        method = st.selectbox(
                                            f"Method for {param['name']}",
                                            ["Wallet Address", "Manual Address", "Contract Address"],
                                            key=f"method_{param['name']}"
                                        )
                                        
                                        addr_data = {"name": param['name'], "method": method}
                                        
                                        if method == "Wallet Address":
                                            wallet_files = [f for f in os.listdir("ethereum_module/ethereum_wallets") if f.endswith('.json')]
                                            addr_data['wallet'] = st.selectbox(
                                                f"Wallet for {param['name']}",
                                                ["--"] + wallet_files,
                                                key=f"wallet_{param['name']}"
                                            )
                                        elif method == "Manual Address":
                                            addr_data['address_manual'] = st.text_input(
                                                f"Address for {param['name']}",
                                                placeholder="0x...",
                                                key=f"manual_{param['name']}"
                                            )
                                        else:  # Contract Address
                                            addr_data['contract'] = st.selectbox(
                                                f"Contract for {param['name']}",
                                                ["--"] + contracts,
                                                key=f"contract_{param['name']}"
                                            )
                                        
                                        address_inputs.append(addr_data)
                                        
                                    elif param['type'].startswith('uint') or param['type'].startswith('int'):
                                        param_values[param['name']] = st.text_input(
                                            f"Value",
                                            placeholder=f"Enter {param['type']} value",
                                            key=f"param_{param['name']}"
                                        )
                                    elif param['type'] == 'string':
                                        param_values[param['name']] = st.text_input(
                                            f"Value",
                                            placeholder="Enter string value",
                                            key=f"param_{param['name']}"
                                        )
                                    elif param['type'] == 'bool':
                                        param_values[param['name']] = st.selectbox(
                                            f"Value",
                                            ["--", "true", "false"],
                                            key=f"param_{param['name']}"
                                        )
                                    else:
                                        param_values[param['name']] = st.text_input(
                                            f"Value ({param['type']})",
                                            key=f"param_{param['name']}"
                                        )
                                    
                                    st.markdown("---")
                            
                            # ETH Value for payable functions
                            value_eth = "0"
                            if guidance['is_payable']:
                                st.markdown("#### Ether Value")
                                value_eth = st.text_input(
                                    "ETH Amount",
                                    value="0",
                                    placeholder="0.1",
                                    
                                    key="value_eth"
                                )
                            
                            # Transaction settings
                            st.markdown("#### Transaction Settings")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                wallet_files = [f for f in os.listdir("ethereum_module/ethereum_wallets") if f.endswith('.json')]
                                caller_wallet = st.selectbox(
                                    "Sender Wallet",
                                    ["--"] + wallet_files,
                                    key="caller_wallet"
                                )
                            
                            with col2:
                                gas_limit = st.text_input(
                                    "Gas Limit",
                                    value="300000",
                                    key="gas_limit"
                                )
                            
                            
                            # Submit button
                            submit_button = st.form_submit_button(
                                f"Execute {function_name}",
                            )
                            
                            if submit_button:


                                # Validate inputs
                                if caller_wallet == "--":
                                    st.error("Please select a sender wallet")
                                else:
                                    # Execute transaction
                                    with st.spinner(f"Executing {function_name}..."):
                                        try:
                                            result = interact_with_contract(
                                                contract_deployment_id=contract_id,
                                                function_name=function_name,
                                                param_values=param_values,
                                                address_inputs=address_inputs,
                                                value_eth=value_eth,
                                                caller_wallet=caller_wallet,
                                                gas_limit=int(gas_limit),
                                                gas_price=20,  # Default gas price
                                                network=selected_network
                                            )
                                            
                                            if result['success']:
                                                st.success(f"{function_name}() executed successfully!")
                                                
                                                if not result.get('is_view', False):
                                                    st.info(f"**Transaction Hash:** `{result['transaction_hash']}`")
                                                    st.info(f"**Gas Used:** {result['gas_used']}")
                                                else:
                                                    st.info(f"**Return Value:** {result['return_value']}")
                                            else:
                                                st.error(f"Error: {result['error']}")
                                                
                                        except Exception as e:
                                            st.error(f"Execution failed: {str(e)}")
            else:
                st.info("Please select a contract to start interacting.")
    
    except ImportError as e:
        st.error(f"Interactive interface not available: {e}")
    except Exception as e:
        st.error(f"Error loading interactive interface: {e}")

elif selected_action == "Execution Traces":
    st.markdown("###  Execution Traces")
    st.caption("Select and execute Ethereum contract execution traces")
    
    try:
        from ethereum_module.hardhat_module.automatic_execution_manager import (
            get_execution_traces,
            exec_contract_automatically
        )
        
        # Get available traces
        traces = get_execution_traces()
        
        if not traces:
            st.warning("⚠️ No execution traces found in the execution_traces folder")
            st.info("💡 Create execution trace files in `ethereum_module/hardhat_module/execution_traces/`")
        else:
            # Trace selection
            st.markdown("####  Select Execution Trace")
            selected_trace = st.selectbox(
                "Available execution traces:",
                ["--Select Trace--"] + traces,
            )
            
            # Store in variable as requested
            contract_deployment_id = None
            if selected_trace != "--Select Trace--":
                contract_deployment_id = selected_trace.replace('.json', '')
                
                # Display trace info
                st.info(f" Selected trace: **{contract_deployment_id}**")
                
                # Execute button
                if st.button("⚡ Execute Trace", type="primary"):
                    with st.spinner("Executing trace..."):
                        try:
                            # Call the function from automatic_execution_manager
                            result = exec_contract_automatically(contract_deployment_id)
                            if result and result.get('success'):
                                st.success("✅ Execution completed successfully!")
                                
                                # Show execution results
                                with st.expander("📊 Execution Results", expanded=True):
                                    st.json(result)
                            else:
                                error_msg = result.get('error', 'Unknown error') if result else 'No result returned'
                                st.error(f"❌ Execution failed : {error_msg}")
                                
                        except Exception as e:
                            st.error(f"❌ Error executing trace: {str(e)}")
            else:
                st.info("Please select an execution trace to run.")
                
    except ImportError as e:
        st.error(f"Execution traces module not available: {e}")
    except Exception as e:
        st.error(f"Error loading execution traces: {e}")


# ==============================
# Footer
# ==============================
st.markdown("---")
st.write("© 2025 - Ethereum Toolchain")
