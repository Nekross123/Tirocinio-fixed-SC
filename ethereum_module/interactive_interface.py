# Interactive Contract Interface for Ethereum - Functional Approach
#

import os
import json
from typing import Dict, List, Any, Optional
from ethereum_module.hardhat_module.contract_utils import (
    fetch_deployed_contracts,
    load_abi_for_contract, 
    fetch_functions_for_contract,
    get_deployment_info,
    interact_with_contract
)


# ========================================
# UTILITY FUNCTIONS
# ========================================
def get_available_contracts() -> List[str]:
    """Get list of available deployed contracts."""
    return fetch_deployed_contracts()


def get_available_wallets() -> List[str]:
    """Get list of available wallet files."""
    wallets_path = os.path.join("ethereum_module", "ethereum_wallets")
    if not os.path.exists(wallets_path):
        return []
    return [f for f in os.listdir(wallets_path) if f.endswith('.json')]


def get_contract_info(contract_id: str) -> Dict[str, Any]:
    """Get comprehensive contract information."""
    deployment_info = get_deployment_info(contract_id)
    functions = fetch_functions_for_contract(contract_id)
    
    return {
        "name": contract_id,
        "address": deployment_info['address'],
        "network": deployment_info['network'],
        "deployed_at": deployment_info.get('deployed_at'),
        "transaction_hash": deployment_info.get('transaction_hash'),
        "interaction_functions": functions
    }


def get_function_guidance(contract_id: str, function_name: str) -> Dict[str, Any]:
    """Get detailed guidance for a specific function."""
    abi = load_abi_for_contract(contract_id)
    
    # Find function in ABI
    function_abi = None
    for item in abi:
        if item.get('type') == 'function' and item.get('name') == function_name:
            function_abi = item
            break
    
    if not function_abi:
        raise ValueError(f"Function {function_name} not found")
    
    # Build guidance
    guidance = {
        "function_name": function_name,
        "state_mutability": function_abi.get('stateMutability', 'nonpayable'),
        "is_payable": function_abi.get('stateMutability') == 'payable',
        "parameters": [],
        "warnings": get_function_warnings(contract_id, function_name)
    }
    
    # Process parameters
    for inp in function_abi.get('inputs', []):
        param_info = {
            "name": inp['name'],
            "type": inp['type'],
            "validation": get_parameter_validation(inp['type']),
        }
        guidance["parameters"].append(param_info)
    
    return guidance


def get_parameter_validation(param_type: str) -> Dict[str, Any]:
    """Get validation rules for parameter type."""
    if param_type.startswith('uint'):
        return {"type": "integer", "min": 0, "format": "Must be a positive integer"}
    elif param_type.startswith('int'):
        return {"type": "integer", "format": "Must be an integer"}
    elif param_type == 'string':
        return {"type": "string", "format": "Any text string"}
    elif param_type == 'bool':
        return {"type": "boolean", "format": "true or false"}
    elif param_type == 'address':
        return {"type": "address", "format": "Valid Ethereum address (0x...)"}
    else:
        return {"type": "custom", "format": f"Value of type {param_type}"}


def get_function_warnings(contract_id: str, function_name: str) -> List[str]:
    """Get warnings and important notes for function."""
    warnings = {
        "auction": {
            "start": ["Only the seller who deployed the contract can start the auction"],
            "bid": [
                "Your bid must be higher than the current highest bid",
                "The ETH you send will be locked until auction ends",
                "If someone outbids you, you can withdraw your funds"
            ],
            "end": [
                "Can only be called after auction time expires",
                "Only the seller can end the auction"
            ],
            "withdraw": ["Only works if you have funds to withdraw (lost bids)"]
        }
    }
    
    contract_type = contract_id.split('_')[0]
    return warnings.get(contract_type, {}).get(function_name, [])


def execute_function_call(contract_id: str, function_name: str, 
                        parameters: Dict[str, Any], wallet: str, 
                        value_eth: str = "0", network: Optional[str] = None) -> Dict[str, Any]:
    """Execute the function call with collected parameters."""
    try:
        # Prepare parameters for interact_with_contract
        param_values = {}
        address_inputs = []
        
        # Separate regular parameters from address parameters
        guidance = get_function_guidance(contract_id, function_name)
        for param_info in guidance["parameters"]:
            param_name = param_info["name"]
            param_type = param_info["type"]
            
            if param_type == 'address':
                # Handle address parameters specially
                address_inputs.append({
                    'name': param_name,
                    'method': parameters[param_name]['method'],
                    'wallet': parameters[param_name].get('wallet'),
                    'address_manual': parameters[param_name].get('address_manual'),
                    'contract': parameters[param_name].get('contract')
                })
            else:
                param_values[param_name] = parameters[param_name]
        
        # Execute interaction
        result = interact_with_contract(
            contract_deployment_id=contract_id,
            function_name=function_name,
            param_values=param_values,
            address_inputs=address_inputs,
            value_eth=value_eth,
            caller_wallet=wallet,
            gas_limit=300000,  # Default gas limit
            gas_price=20,      # Default gas price
            network=network
        )
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Execution failed: {str(e)}"
        }


# ========================================
# MAIN INTERFACE FUNCTION
# ========================================

def create_interactive_session(contract_id: str, function_name: str) -> Dict[str, Any]:
    """Create a complete interactive session for a function call."""
    try:
        # Get contract info
        contract_info = get_contract_info(contract_id)
        
        # Get function guidance
        guidance = get_function_guidance(contract_id, function_name)
        
        return {
            "success": True,
            "contract_info": contract_info,
            "function_guidance": guidance
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# ========================================
# CONVENIENCE FUNCTIONS
# ========================================

def get_all_contracts_info() -> List[Dict[str, Any]]:
    """Get information for all available contracts."""
    contracts = get_available_contracts()
    return [get_contract_info(contract_id) for contract_id in contracts]


def get_contract_functions_with_guidance(contract_id: str) -> Dict[str, Any]:
    """Get all functions for a contract with their guidance."""
    functions = fetch_functions_for_contract(contract_id)
    functions_with_guidance = {}
    
    for func_name in functions:
        try:
            functions_with_guidance[func_name] = get_function_guidance(contract_id, func_name)
        except Exception as e:
            functions_with_guidance[func_name] = {"error": str(e)}
    
    return functions_with_guidance