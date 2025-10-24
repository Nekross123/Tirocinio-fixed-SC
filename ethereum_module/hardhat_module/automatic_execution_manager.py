import json
import os
import streamlit as st
from ethereum_module.hardhat_module.contract_utils import (
    interact_with_contract,
    get_deployment_info,
    load_wallet_from_file,
    create_web3_instance,
    build_function_call_data,
    fetch_contract_context,
    get_default_network
)
from ethereum_module.hardhat_module.meta_transaction import metaTransaction
from ethereum_module.ethereum_utils import ethereum_base_path, hardhat_base_path ,read_json , \
bind_actors , build_complete_dict , set_guidance_parameters
from ethereum_module.interactive_interface import get_function_guidance
from eth_account import Account
import traceback


traces_path = os.path.join(hardhat_base_path, "execution_traces")
def get_execution_traces():
    """Get list of available execution traces."""
   
    if not os.path.exists(traces_path):
        return []
    
    traces = []
    for file in os.listdir(traces_path):
        if file.endswith('.json'):
            traces.append(file)
    return traces

#def exec_contract_automatically(contract_deployment_id, 
#                        ):

def exec_contract_automatically(contract_deployment_id):
    """Execute all functions in the trace execution automatically."""
    # Use global default network if none specified
    #address_inputs questi sono gli indirizzi da sostituire nei parametri di tipo address , da aggiungere 
    address_inputs = []
    
    contract_file = contract_deployment_id + ".json"
    json_file = read_json(f"{traces_path}/{contract_file}")
    
    if json_file is None:
        st.error(f"❌ Failed to read trace file: {contract_file}")
        return

    
    
    # Get network configuration
    network = json_file["configuration"]["ethereum"]["network"]
    
    # Get all trace execution steps
    trace_executions = json_file["trace_execution"]
    
    
    # Store results for all function executions
    all_results = []

    try:
        # Get deployment info (common for all functions)
        deployment_info = get_deployment_info(contract_deployment_id)
        contract_address = deployment_info['address']
        abi = deployment_info['abi']
        
        # Create Web3 instance (common for all functions)
        w3 = create_web3_instance(network)
        if not w3.is_connected():
            raise ValueError(f"Could not connect to network: {network}")
        
        # Create contract instance (common for all functions)
        contract = w3.eth.contract(address=contract_address, abi=abi)
        
        # Get actors binding once for all steps
        actors_dict = bind_actors(contract_deployment_id)
        if not actors_dict:
            st.error("❌ Failed to bind actors to wallets")
            return {
                "success": False,
                "error": "Failed to bind actors to wallets",
                "results": []
            }
        
        st.info(f"📋 Actor-Wallet binding: {actors_dict}")
        
        # Execute each function in the trace
        for i, execution_step in enumerate(trace_executions):
            st.info(f"🔄 Executing step {i+1}/{len(trace_executions)}: {execution_step['function_name']}")
            
            try:
                # Get function name and parameters
                function_name = execution_step["function_name"]
                
                # Build step-specific complete_dict
                step_complete_dict = {}
                
                # Add args from execution step
                if "args" in execution_step:
                    step_complete_dict.update(execution_step["args"])
                
                # Add ethereum config from execution step
                if "ethereum" in execution_step:
                    ethereum_config = execution_step["ethereum"]
                    step_complete_dict.update(ethereum_config)
                
                # Get sender wallet actor name for this step
                sender_wallet_actor = step_complete_dict.get("sender_wallet", None)
                if sender_wallet_actor is None:
                    st.error(f"❌ sender_wallet not specified for step {i+1}")
                    all_results.append({
                        "step": i+1,
                        "function_name": function_name,
                        "success": False,
                        "error": "sender_wallet not specified in execution step"
                    })
                    continue
                
                # Resolve actor name to actual wallet file
                actual_wallet_file = actors_dict.get(sender_wallet_actor, None)
                if actual_wallet_file is None:
                    st.error(f"❌ Actor '{sender_wallet_actor}' not found in binding")
                    all_results.append({
                        "step": i+1,
                        "function_name": function_name,
                        "success": False,
                        "error": f"Actor '{sender_wallet_actor}' not found in actor binding"
                    })
                    continue
                
                st.info(f"📝 Using wallet: '{actual_wallet_file}' for actor: '{sender_wallet_actor}'")
                
                # Load wallet for this step
                wallet_path = os.path.join("ethereum_module", "ethereum_wallets", actual_wallet_file)
                wallet_data = load_wallet_from_file(wallet_path)
                if not wallet_data:
                    st.error(f"❌ Could not load wallet: {actual_wallet_file}")
                    all_results.append({
                        "step": i+1,
                        "function_name": function_name,
                        "success": False,
                        "error": f"Could not load wallet file: {actual_wallet_file}"
                    })
                    continue
                
                # Get function guidance and parameters
                guidance = get_function_guidance(contract_deployment_id, function_name)
                param_values = set_guidance_parameters(guidance, step_complete_dict)
                
                # Build function call arguments
                call_args = build_function_call_data(contract_deployment_id, function_name, param_values, address_inputs)
                
                # Get function context
                ctx = fetch_contract_context(contract_deployment_id, function_name)
                
                # Create account from private key
                account = Account.from_key(wallet_data["private_key"])
                
                if ctx['is_view']:
                    # Call view function (no transaction)
                    try:
                        result = getattr(contract.functions, function_name)(*call_args).call()
                        step_result = {
                            "step": i+1,
                            "function_name": function_name,
                            "success": True,
                            "return_value": str(result)
                        }
                        all_results.append(step_result)
                        st.success(f"✅ Step {i+1} completed - View function result: {result}")
                        
                    except Exception as e:
                        step_result = {
                            "step": i+1,
                            "function_name": function_name,
                            "success": False,
                            "error": f"View function call failed: {str(e)}"
                        }
                        all_results.append(step_result)
                        st.error(f"❌ Step {i+1} failed - View function error: {str(e)}")
                
                else:
                    # Send transaction
                    try:
                        # Get ETH value for this step
                        value_eth = step_complete_dict.get("eth_value", 0)
                        value_wei = w3.to_wei(float(value_eth), 'ether') if value_eth else 0
                        
                        # Use metaTransaction function
                        receipt = metaTransaction(w3, account, contract, value_wei, function_name, *call_args)
                        
                        step_result = {
                            "step": i+1,
                            "function_name": function_name,
                            "success": True,
                            "transaction_hash": receipt['transactionHash'].hex(),
                            "gas_used": receipt.get('gasUsed', 'N/A'),
                            "size_in_bytes": receipt.get('size_in_bytes', 0)
                        }
                        all_results.append(step_result)
                        st.success(f"✅ Step {i+1} completed - Transaction: {receipt['transactionHash'].hex()}")
                        
                    except Exception as e:
                        step_result = {
                            "step": i+1,
                            "function_name": function_name,
                            "success": False,
                            "error": f"Transaction failed: {str(e)}"
                        }
                        all_results.append(step_result)
                        st.error(f"❌ Step {i+1} failed - Transaction error: {str(e)}")
                        
            except Exception as e:
                # Try to get actor and wallet info if they were defined
                try:
                    actor_info = {
                        "sender_actor": sender_wallet_actor,
                        "sender_wallet": actual_wallet_file
                    }
                except NameError:
                    # Variables not yet defined in this step
                    actor_info = {
                        "sender_actor": execution_step.get("ethereum", {}).get("sender_wallet", "unknown"),
                        "sender_wallet": "not_resolved"
                    }
                
                step_result = {
                    "step": i+1,
                    "function_name": execution_step.get("function_name", "unknown"),
                    "success": False,
                    "error": f"Step execution failed: {str(e)}",
                    **actor_info
                }
                all_results.append(step_result)
                st.error(f"❌ Step {i+1} failed - General error: {str(e)}")
        
        # Prepare final results
        final_results = {
            "network": network,
            "platform": "Ethereum",
            "trace_title": f"{contract_deployment_id}_results",
            "results": all_results
        }
        
        # Save results to JSON file
        result_filename = f"{contract_deployment_id}_result.json"
        result_filepath = os.path.join(traces_path, result_filename)
        
        try:
            with open(result_filepath, 'w', encoding='utf-8') as f:
                json.dump(final_results, f, indent=2, ensure_ascii=False)
            
            st.success(f"✅ Results saved to: {result_filename}")
            
            # Add download button
            with open(result_filepath, 'r', encoding='utf-8') as f:
                json_data = f.read()
            
            st.download_button(
                label="📥 Download Results JSON",
                data=json_data,
                file_name=result_filename,
                mime="application/json",
                help=f"Download the execution results as {result_filename}"
            )
            
        except Exception as e:
            st.warning(f"⚠️ Could not save results file: {str(e)}")
        
        return final_results
                
    except Exception as e:
        # Prepare error results
        error_results = {
            "network": network if 'network' in locals() else "unknown",
            "platform": "Ethereum",
            "trace_title": f"{contract_deployment_id}_results",
            "error": f"Global execution failed: {str(e)}",
            "results": all_results  # Return any partial results
        }
        st.error(f"❌ Execution failed: {str(e)}")
        st.error(traceback.format_exc())
        # Save error results to JSON file
        result_filename = f"{contract_deployment_id}_result.json"
        result_filepath = os.path.join(traces_path, result_filename)
        try:
            with open(result_filepath, 'w', encoding='utf-8') as f:
                json.dump(error_results, f, indent=2, ensure_ascii=False)
            st.error(f"❌ Execution failed but partial results saved to: {result_filename}")
            with open(result_filepath, 'r', encoding='utf-8') as f:
                json_data = f.read()
            st.download_button(
                label="📥 Download Partial Results JSON",
                data=json_data,
                file_name=result_filename,
                mime="application/json",
                help=f"Download the partial execution results as {result_filename}"
            )
        except Exception as save_error:
            st.warning(f"⚠️ Could not save error results file: {str(save_error)}")
        return error_results

def find_execution_traces():
    """Compatibility function - alias for get_execution_traces()"""
    return get_execution_traces()

# Main streamlit app
if __name__ == "__main__":
    streamlit_execution_interface()
