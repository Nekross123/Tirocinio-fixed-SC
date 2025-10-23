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

#def exec_contract_automatically(contract_deployment_id, param_values=None, address_inputs=None,
#                          value_eth=None, caller_wallet=None, gas_limit=None, gas_price=None, network=None):

def exec_contract_automatically(contract_deployment_id):
    """Interact with a deployed contract function."""
    # Use global default network if none specified
    address_inputs
    contract_file = contract_deployment_id + ".json"
    json_file = read_json(f"{traces_path}/{contract_file}")
    
    if json_file is None:
        st.error(f"❌ Failed to read trace file: {contract_file}")
        return

    st.info((f"✅ Successfully read trace file: {json_file}"))
    
    function_name = json_file["trace_execution"][0]["function_name"]
    network = json_file["configuration"]["ethereum"]["network"]
    complete_dict = build_complete_dict(contract_deployment_id)
    sender_wallet = complete_dict["sender_wallet"]

    guidance = get_function_guidance(contract_deployment_id, function_name)

    param_values = set_guidance_parameters(guidance ,complete_dict)

    
    
    st.info(f"Param values: {param_values}")
    
    #try:
    #    # Get deployment info
    #    deployment_info = get_deployment_info(contract_deployment_id)
    #    contract_address = deployment_info['address']
    #    abi = deployment_info['abi']
    #    
    #    # Load caller wallet
    #    wallet_path = os.path.join("ethereum_module", "ethereum_wallets", sender_wallet)
    #    wallet_data = load_wallet_from_file(wallet_path)
    #    if not wallet_data:
    #        raise ValueError("Could not load caller wallet")
    #    
    #    # Create Web3 instance
    #    w3 = create_web3_instance(network)
    #    if not w3.is_connected():
    #        raise ValueError(f"Could not connect to network: {network}")
    #    
    #    # Create contract instance
    #    contract = w3.eth.contract(address=contract_address, abi=abi)
    #    
    #    # Build function call arguments
    #    call_args = build_function_call_data(contract_deployment_id, function_name, param_values, address_inputs)
    #    
    #    # Get function context
    #    ctx = fetch_contract_context(contract_deployment_id, function_name)
    #    
    #    # Create account from private key
    #    account = Account.from_key(wallet_data["private_key"])
    #    
    #    if ctx['is_view']:
    #        # Call view function (no transaction)
    #        try:
    #            result = getattr(contract.functions, function_name)(*call_args).call()
    #            return {
    #                "success": True,
    #                "return_value": str(result),
    #                "is_view": True
    #            }
    #        except Exception as e:
    #            raise ValueError(f"View function call failed: {str(e)}")
    #    
    #    else:
    #        # Send transaction using metaTransaction (Prof. Pinna's approach)
    #        try:
    #            # Convert value to wei
    #            value_wei = w3.to_wei(float(value_eth), 'ether') if value_eth else 0
    #            
    #            # Use metaTransaction function like the professor
    #            receipt = metaTransaction(w3, account, contract, value_wei, function_name, *call_args)
    #            
    #            return {
    #                "success": True,
    #                "transaction_hash": receipt['transactionHash'].hex(),
    #                "gas_used": receipt.get('gasUsed', 'N/A'),
    #                "size_in_bytes": receipt.get('size_in_bytes', 0),
    #                "status": "Success" if receipt.get('status') == 1 else "Failed",
    #                "is_view": False
    #            }
    #            
    #        except Exception as e:
    #            return {
    #                "success": False,
    #                "error": f"Transaction failed: {str(e)}"
    #            }
    #            
    #except Exception as e:
    #    return {
    #        "success": False,
    #        "error": str(e)
    #    }

def find_execution_traces():
    """Compatibility function - alias for get_execution_traces()"""
    return get_execution_traces()

# Main streamlit app
if __name__ == "__main__":
    streamlit_execution_interface()
