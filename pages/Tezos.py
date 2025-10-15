import streamlit as st
from pathlib import Path
import sys 
import os

tezos_toolchain_path = os.path.join(os.path.dirname(__file__), "..", "tezos-contract-2.0", "toolchain")
sys.path.append(tezos_toolchain_path)

from contractUtils import (
    compileContract,
    origination,
    contractInfoResult,
    entrypointAnalyse,
    entrypointCall,
    callInfoResult
)
from folderScan import folderScan
from csvUtils import csvReader, csvWriter
from jsonUtils import getAddress, addressUpdate, jsonWriter
from pytezos import pytezos
import json
from main import executionSetup

st.set_page_config(
    page_title="Tezos Smart Contract Toolchain",
    layout="centered"
)

st.title("🏗️ Tezos Smart Contract Toolchain")
st.caption("An interface to compile, deploy, and interact with Tezos smart contracts.")

def get_deployed_contracts():
    """Wrapper per getAddress con path corretto"""
    try:
        # Cambia temporaneamente la directory per la funzione getAddress
        original_dir = os.getcwd()
        toolchain_dir = os.path.join(os.path.dirname(__file__), "..", "tezos-contract-2.0", "toolchain")
        os.chdir(toolchain_dir)
        
        contracts = getAddress()
        os.chdir(original_dir)
        return contracts
    except Exception as e:
        if 'original_dir' in locals():
            os.chdir(original_dir)
        raise e

def get_available_wallets():
    """Ottieni la lista dei wallet disponibili"""
    try:
        wallet_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "tezos-contract-2.0",
            "tezos_module",
            "tezos_wallets",
            "wallet.json",
        )
        with open(wallet_path, 'r', encoding='utf-8') as f:
            wallets = json.load(f)
        return list(wallets.keys())
    except FileNotFoundError:
        st.error("The wallet.json file was not found in tezos_wallets directory.")
        return []
    except Exception as e:
        st.error(f"Error reading wallets: {e}")
        return []

def get_client(wallet_id):
    try:
        # Cerca il wallet nella nuova directory tezos-contract-2.0/tezos_module/tezos_wallets/
        wallet_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "tezos-contract-2.0",
            "tezos_module",
            "tezos_wallets",
            "wallet.json",
        )
        with open(wallet_path, 'r', encoding='utf-8') as f:
            wallets = json.load(f)
        key = wallets.get(str(wallet_id))
        if not key:
            st.error(f"Wallet with ID {wallet_id} not found in wallet.json.")
            return None
        return pytezos.using(shell="ghostnet", key=key)
    except FileNotFoundError:
        st.error("The wallet.json file was not found. Make sure it is in the correct directory.")
        return None
    except Exception as e:
        st.error(f"Error during client configuration: {e}")
        return None

def compile_view():
    st.header("1. Compile SmartPy Contracts")
    
    # Selezione del wallet nella stessa pagina
    available_wallets = get_available_wallets()
    if not available_wallets:
        st.error("No wallets found. Please create a wallet first.")
        return
    
    col1, col2 = st.columns(2)
    with col1:
        wallet_selection = st.selectbox("Select Wallet:", options=available_wallets, key="compile_wallet")
    with col2:
        # Path corretto alla directory contracts di tezos-contract-2.0
        contracts_path = os.path.join(os.path.dirname(__file__), "..", "tezos-contract-2.0", "contracts")
        contracts = folderScan(contracts_path)
        contract_to_compile = st.selectbox("Select Contract:", options=contracts, key="compile_select")

    if st.button("🚀 Compile"):
        if contract_to_compile and wallet_selection:
            client = get_client(wallet_selection)
            if client:
                # Cambia directory per la compilazione
                original_dir = os.getcwd()
                toolchain_dir = os.path.join(os.path.dirname(__file__), "..", "tezos-contract-2.0", "toolchain")
                os.chdir(toolchain_dir)
                
                contract_path = f"../contracts/{contract_to_compile}/{contract_to_compile}.py"
                with st.spinner(f"Compiling {contract_path}..."):
                    try:
                        compileContract(contractPath=contract_path)
                        os.chdir(original_dir)
                        st.success(f"Contract '{contract_to_compile}' compiled successfully!")
                        st.info("The Michelson files have been generated in the contract's directory.")
                    except Exception as e:
                        os.chdir(original_dir)
                        st.error(f"Error during compilation: {e}")
            else:
                st.error("Could not initialize client with selected wallet.")

def deploy_view():
    st.header("2. Deploy a Contract (Origination)")
    
    # Selezione del wallet nella stessa pagina
    available_wallets = get_available_wallets()
    if not available_wallets:
        st.error("No wallets found. Please create a wallet first.")
        return
    
    col1, col2 = st.columns(2)
    with col1:
        wallet_selection = st.selectbox("Select Wallet:", options=available_wallets, key="deploy_wallet")
    with col2:
        # Path corretto alla directory contracts di tezos-contract-2.0
        contracts_path = os.path.join(os.path.dirname(__file__), "..", "tezos-contract-2.0", "contracts")
        contracts = folderScan(contracts_path)
        contract_to_deploy = st.selectbox("Select Contract:", options=contracts, key="deploy_select")

    initial_balance = st.number_input("Initial balance (in tez):", min_value=0, value=1, step=1)

    if st.button("🌐 Deploy"):
        if contract_to_deploy and wallet_selection:
            client = get_client(wallet_selection)
            if not client:
                st.error("Could not initialize client with selected wallet.")
                return
            
            # Usa path assoluti per i file Michelson
            contracts_path = os.path.join(os.path.dirname(__file__), "..", "tezos-contract-2.0", "contracts")
            contract_folder = os.path.join(contracts_path, contract_to_deploy)
            
            # Debug: mostra tutti i file nella cartella del contratto
            if os.path.exists(contract_folder):
                files_in_folder = os.listdir(contract_folder)
                st.info(f"📁 Files in contract folder: {files_in_folder}")
            else:
                st.error(f"Contract folder not found: {contract_folder}")
                return
            
            # Try both naming conventions (new and legacy)
            michelson_path = os.path.join(contract_folder, f"{contract_to_deploy}_code.tz")
            storage_path = os.path.join(contract_folder, f"{contract_to_deploy}_storage.tz")
            
            # Fallback to legacy naming if new naming not found
            if not os.path.exists(michelson_path):
                michelson_path = os.path.join(contract_folder, "step_001_cont_0_contract.tz")
            if not os.path.exists(storage_path):
                storage_path = os.path.join(contract_folder, "step_001_cont_0_storage.tz")

            if not os.path.exists(michelson_path) or not os.path.exists(storage_path):
                st.error(f"Contract not compiled. Compile it before deploying.")
                st.info(f"Looking for:\n- {michelson_path}\n- {storage_path}")
                return

            michelson_code = Path(michelson_path).read_text()
            storage_code = Path(storage_path).read_text()

            with st.spinner("Origination in progress... The operation may take a few minutes."):
                try:
                    # Cambia directory per addressUpdate
                    original_dir = os.getcwd()
                    toolchain_dir = os.path.join(os.path.dirname(__file__), "..", "tezos-contract-2.0", "toolchain")
                    
                    op_result = origination(
                        client=client,
                        michelsonCode=michelson_code,
                        initialStorage=storage_code,
                        initialBalance=initial_balance
                    )
                    if op_result:
                        contract_info = contractInfoResult(op_result=op_result)
                        
                        # Cambia dir per addressUpdate che usa path relativo
                        os.chdir(toolchain_dir)
                        addressUpdate(contract=contract_to_deploy, newAddress=contract_info["address"])
                        os.chdir(original_dir)
                        
                        st.success(f"Contract '{contract_to_deploy}' deployed successfully!")
                        st.write("New contract address:")
                        st.code(contract_info["address"], language="text")
                        st.write("Operation hash:")
                        st.code(contract_info["hash"], language="text")
                    else:
                        st.error("Origination failed. Check the console log for details.")
                except Exception as e:
                    if 'original_dir' in locals():
                        os.chdir(original_dir)
                    st.error(f"Error during deployment: {e}")

def interact_view():
    st.header("3. Interact with a Contract")
    
    # Selezione del wallet nella stessa pagina
    available_wallets = get_available_wallets()
    if not available_wallets:
        st.error("No wallets found. Please create a wallet first.")
        return
    
    wallet_selection = st.selectbox("Select Wallet:", options=available_wallets, key="interact_wallet")
    
    try:
        deployed_contracts = get_deployed_contracts()
        if not deployed_contracts:
            st.warning("No deployed contracts found in `addressList.json`.")
            return
    except Exception as e:
        st.error(f"`addressList.json` not found or corrupted: {str(e)}")
        return

    contract_name = st.selectbox("Select a contract to interact with:", options=list(deployed_contracts.keys()))

    if contract_name and wallet_selection:
        client = get_client(wallet_selection)
        if not client:
            st.error("Could not initialize client with selected wallet.")
            return
        contract_address = deployed_contracts[contract_name]
        st.info(f"Contract address: `{contract_address}`")

        try:
            entrypoints_schema = entrypointAnalyse(client=client, contractAddress=contract_address)
            entrypoint_name = st.selectbox("Select an entrypoint:", options=list(entrypoints_schema.keys()))

            params_input = ""
            if entrypoints_schema.get(entrypoint_name) != "unit":
                params_input = st.text_input("Enter the parameters (comma-separated if multiple):", placeholder="value1,value2")

            tez_amount = st.number_input("Amount of Tez to send:", min_value=0.0, value=0.0, step=0.1, format="%.6f")

            if st.button("➡️ Execute Call"):
                parameters = params_input.split(',') if params_input else []
                with st.spinner(f"Calling entrypoint '{entrypoint_name}'..."):
                    try:
                        op_result = entrypointCall(
                            client=client,
                            contractAddress=contract_address,
                            entrypointName=entrypoint_name,
                            parameters=parameters,
                            tezAmount=tez_amount
                        )
                        info_result = callInfoResult(opResult=op_result)
                        info_result["contract"] = contract_name
                        info_result["entryPoint"] = entrypoint_name

                        st.success("Call executed successfully!")
                        st.json(info_result)

                        if st.checkbox("Save result to CSV/JSON"):
                            exportResult(info_result)
                            st.info("Results exported.")

                    except Exception as e:
                        st.error(f"Error during call: {e}")
        except Exception as e:
            st.error(f"Unable to analyze contract entrypoints: {e}")

def trace_view():
    st.header("4. Execute Trace from CSV File")
    st.info("This function executes a series of predefined transactions from the files in `execution_traces/`.")

    if st.button("▶️ Start Trace Execution"):
        try:
            execution_traces = csvReader()
            if not execution_traces:
                st.warning("No execution traces found.")
                return

            with st.spinner("Executing traces..."):
                all_results = {}
                for contract, rows in execution_traces.items():
                    st.write(f"--- Executing trace for **{contract}** ---")
                    results = executionSetup(contract=contract, rows=rows)
                    all_results[contract] = results
                    for element, result in results.items():
                        st.write(f"Step `{element}` completed.")
                        exportResult(result)

            st.success("All traces have been executed and the results saved.")
            st.json(all_results)

        except Exception as e:
            st.error(f"Error during trace execution: {e}")

def exportResult(opResult):
    fileName = "transactionsOutput"
    csvWriter(fileName=fileName+".csv", op_result=opResult)
    jsonWriter(fileName=fileName+".json", opReport=opResult)
    st.success(f"Result of operation {opResult['entryPoint']} saved to file.")

st.sidebar.header("Features")
operation = st.sidebar.radio(
    "Select an operation:",
    ("Compile", "Deploy", "Interact", "Execute Trace")
)

if operation == "Compile":
    compile_view()
elif operation == "Deploy":
    deploy_view()
elif operation == "Interact":
    interact_view()
elif operation == "Execute Trace":
    trace_view()