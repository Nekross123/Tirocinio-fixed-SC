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
    from ethereum_module.hardhat_module.compiler_and_deployer import compile_and_deploy_contracts
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
        validate_constructor_args
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

        # Constructor Parameters Section (only for single contract deployment)
        constructor_args = []
        constructor_valid = True
        
        if deploy_flag and compile_mode == "Single contract" and selected_contract_file != "--":
            st.markdown("### 🔧 Constructor Parameters")
            
            # Try to compile contract to get ABI and check constructor parameters
            try:
                from ethereum_module.hardhat_module.compiler_and_deployer import _compile_contract
                contract_name = selected_contract_file.replace('.sol', '')
                contracts_path = os.path.join(root_path, "ethereum_module", "hardhat_module", "contracts")
                contract_file_path = os.path.join(contracts_path, selected_contract_file)
                
                if os.path.exists(contract_file_path):
                    with open(contract_file_path, 'r', encoding='utf-8') as f:
                        source_code = f.read()
                    
                    compiled_data = _compile_contract(contract_name, source_code)
                    
                    if compiled_data and 'abi' in compiled_data:
                        # Show constructor parameter preview
                        display_constructor_preview(contract_name, compiled_data['abi'])
                        
                        # Collect constructor arguments if needed
                        constructor_args = collect_constructor_args_streamlit(contract_name, compiled_data['abi'])
                        constructor_valid = constructor_args is not None
                        
                        if constructor_args:
                            # Store in session state for deployment
                            st.session_state[f'constructor_args_{contract_name}'] = constructor_args
                    else:
                        st.warning("⚠️ Could not compile contract to detect constructor parameters. Using defaults.")
                        
            except Exception as e:
                st.warning(f"⚠️ Could not analyze constructor parameters: {str(e)}")

        # Button conditions
        if compile_mode == "All contracts":
            can_proceed = selected_wallet_file != "--" and selected_network != "--" and len(contract_files) > 0
        else:
            can_proceed = (selected_wallet_file != "--" and 
                          selected_contract_file != "--" and 
                          selected_network != "--" and 
                          (not deploy_flag or constructor_valid))

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
                        
                        # Add constructor arguments if available
                        contract_name = selected_contract_file.replace('.sol', '')
                        constructor_key = f'constructor_args_{contract_name}'
                        if constructor_key in st.session_state:
                            deploy_payload["constructor_args"] = st.session_state[constructor_key]
                        
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
                help="Choose the blockchain network to interact with"
            )
            
            st.markdown("---")
            
            # Contract selection
            contract_id = st.selectbox(
                "Select Contract",
                ["--"] + contracts,
                help="Choose a deployed contract to interact with"
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
                        help="Choose a function to interact with"
                    )
                    
                    if function_name != "--":
                        # Show function guidance
                        from ethereum_module.interactive_interface import get_function_guidance
                        guidance = get_function_guidance(contract_id, function_name)
                        
                        st.markdown("---")
                        st.markdown(f"### Function: `{function_name}()`")
                        
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
                                    help="Amount of ETH to send with the transaction",
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
                                    help="Wallet that will send the transaction",
                                    key="caller_wallet"
                                )
                            
                            with col2:
                                gas_limit = st.text_input(
                                    "Gas Limit",
                                    value="300000",
                                    help="Maximum gas for the transaction",
                                    key="gas_limit"
                                )
                            
                            # Submit button
                            submit_button = st.form_submit_button(
                                f"Execute {function_name}()",
                                help=f"Send transaction to execute {function_name}"
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
                help="Choose an execution trace to run"
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
                                st.error(f"❌ Execution failed: {error_msg}")
                                
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
