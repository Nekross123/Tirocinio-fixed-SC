# MIT License
#
# Copyright (c) 2025 Manuel Boi, Palumbo Lorenzo, Piras Mauro - Università degli Studi di Cagliari
#
# Interactive Contract Interface for Ethereum
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


class InteractiveContractInterface:
    """
    Interactive guided interface for Ethereum contract interaction.
    Provides step-by-step parameter collection similar to Solana module.
    """
    
    def __init__(self):
        self.wallets_path = os.path.join("ethereum_module", "ethereum_wallets")
        
    def get_available_contracts(self) -> List[str]:
        """Get list of available deployed contracts."""
        return fetch_deployed_contracts()
    
    def get_available_wallets(self) -> List[str]:
        """Get list of available wallet files."""
        if not os.path.exists(self.wallets_path):
            return []
        return [f for f in os.listdir(self.wallets_path) if f.endswith('.json')]
    
    def get_contract_info(self, contract_id: str) -> Dict[str, Any]:
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
    
    def get_function_guidance(self, contract_id: str, function_name: str) -> Dict[str, Any]:
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
            "warnings": self._get_function_warnings(contract_id, function_name)
        }
        
        # Process parameters
        for inp in function_abi.get('inputs', []):
            param_info = {
                "name": inp['name'],
                "type": inp['type'],
                "validation": self._get_parameter_validation(inp['type']),
            }
            guidance["parameters"].append(param_info)
        
        return guidance
    

    
    def _get_parameter_validation(self, param_type: str) -> Dict[str, Any]:
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
    

        return examples.get(param_type, ["Enter value"])
    

    
    def _get_function_warnings(self, contract_id: str, function_name: str) -> List[str]:
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
    
    def collect_parameters_interactive(self, guidance: Dict[str, Any]) -> Dict[str, Any]:
        """
        Collect parameters interactively from user.
        This is a base method that should be overridden by UI implementations.
        """
        # This method would be implemented differently for different UIs
        # (Streamlit, CLI, etc.)
        raise NotImplementedError("This method should be implemented by UI-specific classes")
    
    def execute_function_call(self, contract_id: str, function_name: str, 
                            parameters: Dict[str, Any], wallet: str, 
                            value_eth: str = "0", network: Optional[str] = None) -> Dict[str, Any]:
        """Execute the function call with collected parameters."""
        try:
            # Prepare parameters for interact_with_contract
            param_values = {}
            address_inputs = []
            
            # Separate regular parameters from address parameters
            guidance = self.get_function_guidance(contract_id, function_name)
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


def create_interactive_session(contract_id: str, function_name: str) -> Dict[str, Any]:
    """Create a complete interactive session for a function call."""
    interface = InteractiveContractInterface()
    
    try:
        # Get contract info
        contract_info = interface.get_contract_info(contract_id)
        
        # Get function guidance
        guidance = interface.get_function_guidance(contract_id, function_name)
        
        return {
            "success": True,
            "contract_info": contract_info,
            "function_guidance": guidance,
            "interface": interface
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }