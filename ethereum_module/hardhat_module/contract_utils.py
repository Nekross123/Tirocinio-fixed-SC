# MIT License
#
# Copyright (c) 2025 Manuel Boi - Università degli Studi di Cagliari
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import os
import json
from web3 import Web3
from eth_account import Account
from ethereum_module.ethereum_utils import (
    create_web3_instance,
    load_wallet_from_file,
    wait_for_transaction_receipt
)
from ethereum_module.hardhat_module.meta_transaction import metaTransaction

hardhat_base_path = os.path.join("ethereum_module", "hardhat_module")


def fetch_deployed_contracts():
    """Fetch list of deployed contracts from deployments directory."""
    deployments_dir = os.path.join(hardhat_base_path, "deployments")
    if not os.path.exists(deployments_dir):
        return []
    
    contracts = []
    for file_name in os.listdir(deployments_dir):
        if file_name.endswith('.json'):
            # Remove .json extension and extract contract name
            contract_name = file_name.replace('.json', '')
            contracts.append(contract_name)
    
    return list(set(contracts))  # Remove duplicates


def load_abi_for_contract(contract_deployment_id):
    """Load ABI for a specific contract deployment."""
    deployments_dir = os.path.join(hardhat_base_path, "deployments")
    deployment_file = os.path.join(deployments_dir, f"{contract_deployment_id}.json")
    
    if not os.path.exists(deployment_file):
        raise FileNotFoundError(f"Deployment file not found for {contract_deployment_id}")
    
    with open(deployment_file, 'r', encoding='utf-8') as f:
        deployment_info = json.load(f)
    
    return deployment_info.get('abi', [])


def fetch_functions_for_contract(contract_deployment_id):
    """Fetch available functions for a deployed contract."""
    try:
        abi = load_abi_for_contract(contract_deployment_id)
        functions = []
        
        for item in abi:
            if item.get('type') == 'function':
                functions.append(item['name'])
        
        return functions
    except Exception as e:
        print(f"Error fetching functions: {e}")
        return []


def fetch_contract_context(contract_deployment_id, function_name):
    """Fetch context information for a specific contract function."""
    abi = load_abi_for_contract(contract_deployment_id)
    
    for item in abi:
        if item.get('type') == 'function' and item.get('name') == function_name:
            return {
                'inputs': item.get('inputs', []),
                'outputs': item.get('outputs', []),
                'is_payable': item.get('stateMutability') == 'payable',
                'is_view': item.get('stateMutability') in ['view', 'pure'],
                'state_mutability': item.get('stateMutability', 'nonpayable')
            }
    
    raise ValueError(f"Function {function_name} not found in contract {contract_deployment_id}")


def get_deployment_info(contract_deployment_id):
    """Get deployment information for a contract."""
    deployments_dir = os.path.join(hardhat_base_path, "deployments")
    deployment_file = os.path.join(deployments_dir, f"{contract_deployment_id}.json")
    
    if not os.path.exists(deployment_file):
        raise FileNotFoundError(f"Deployment file not found for {contract_deployment_id}")
    
    with open(deployment_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def build_function_call_data(contract_deployment_id, function_name, param_values, address_inputs):
    """Build function call data from user inputs."""
    abi = load_abi_for_contract(contract_deployment_id)
    function_abi = None
    
    # Find the function in ABI
    for item in abi:
        if item.get('type') == 'function' and item.get('name') == function_name:
            function_abi = item
            break
    
    if not function_abi:
        raise ValueError(f"Function {function_name} not found in ABI")
    
    # Process inputs
    inputs = function_abi.get('inputs', [])
    call_args = []
    
    for inp in inputs:
        param_name = inp['name']
        param_type = inp['type']
        
        if param_type == 'address':
            # Handle address parameters
            address_data = next((addr for addr in address_inputs if addr['name'] == param_name), None)
            if not address_data:
                raise ValueError(f"Address parameter {param_name} not provided")
            
            if address_data['method'] == 'Wallet Address':
                wallet_file = address_data.get('wallet')
                if not wallet_file or wallet_file == '--':
                    raise ValueError(f"Wallet not selected for {param_name}")
                
                wallet_path = os.path.join("ethereum_module", "ethereum_wallets", wallet_file)
                wallet_data = load_wallet_from_file(wallet_path)
                if not wallet_data:
                    raise ValueError(f"Could not load wallet {wallet_file}")
                
                call_args.append(wallet_data['address'])
                
            elif address_data['method'] == 'Manual Address':
                manual_address = address_data.get('address_manual', '').strip()
                if not manual_address:
                    raise ValueError(f"Manual address not provided for {param_name}")
                
                if not Web3.is_address(manual_address):
                    raise ValueError(f"Invalid address format for {param_name}")
                
                call_args.append(Web3.to_checksum_address(manual_address))
                
            elif address_data['method'] == 'Contract Address':
                contract_id = address_data.get('contract')
                if not contract_id or contract_id == '--':
                    raise ValueError(f"Contract not selected for {param_name}")
                
                deployment_info = get_deployment_info(contract_id)
                call_args.append(deployment_info['address'])
                
        else:
            # Handle other parameter types
            param_value = param_values.get(param_name, '').strip()
            
            if not param_value or param_value == '--':
                raise ValueError(f"Parameter {param_name} not provided")
            
            # Type conversion
            if param_type.startswith('uint') or param_type.startswith('int'):
                try:
                    call_args.append(int(param_value))
                except ValueError:
                    raise ValueError(f"Invalid integer value for {param_name}: {param_value}")
                    
            elif param_type == 'bool':
                if param_value.lower() == 'true':
                    call_args.append(True)
                elif param_value.lower() == 'false':
                    call_args.append(False)
                else:
                    raise ValueError(f"Invalid boolean value for {param_name}: {param_value}")
                    
            elif param_type == 'string':
                call_args.append(param_value)
                
            elif param_type == 'bytes' or param_type.startswith('bytes'):
                if param_value.startswith('0x'):
                    call_args.append(bytes.fromhex(param_value[2:]))
                else:
                    call_args.append(param_value.encode('utf-8'))
                    
            else:
                # For other types, try to use the value as-is
                call_args.append(param_value)
    
    return call_args


def interact_with_contract(contract_deployment_id, function_name, param_values, address_inputs,
                          value_eth, caller_wallet, gas_limit, gas_price, network="localhost"):
    """Interact with a deployed contract function."""
    try:
        # Get deployment info
        deployment_info = get_deployment_info(contract_deployment_id)
        contract_address = deployment_info['address']
        abi = deployment_info['abi']
        
        # Load caller wallet
        wallet_path = os.path.join("ethereum_module", "ethereum_wallets", caller_wallet)
        wallet_data = load_wallet_from_file(wallet_path)
        if not wallet_data:
            raise ValueError("Could not load caller wallet")
        
        # Create Web3 instance
        w3 = create_web3_instance(network)
        if not w3.is_connected():
            raise ValueError(f"Could not connect to network: {network}")
        
        # Create contract instance
        contract = w3.eth.contract(address=contract_address, abi=abi)
        
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
                return {
                    "success": True,
                    "return_value": str(result),
                    "is_view": True
                }
            except Exception as e:
                raise ValueError(f"View function call failed: {str(e)}")
        
        else:
            # Send transaction using metaTransaction (Prof. Pinna's approach)
            try:
                # Convert value to wei
                value_wei = w3.to_wei(float(value_eth), 'ether') if value_eth else 0
                
                # Use metaTransaction function like the professor
                receipt = metaTransaction(w3, account, contract, value_wei, function_name, *call_args)
                
                return {
                    "success": True,
                    "transaction_hash": receipt['transactionHash'].hex(),
                    "gas_used": receipt.get('gasUsed', 'N/A'),
                    "status": "Success" if receipt.get('status') == 1 else "Failed",
                    "is_view": False
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Transaction failed: {str(e)}"
                }
                
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def check_contract_deployment_status(contract_deployment_id, network="localhost"):
    """Check if a contract is properly deployed and accessible."""
    try:
        deployment_info = get_deployment_info(contract_deployment_id)
        contract_address = deployment_info['address']
        
        w3 = create_web3_instance(network)
        if not w3.is_connected():
            return False
        
        # Check if there's code at the address
        code = w3.eth.get_code(contract_address)
        return len(code) > 0
        
    except Exception as e:
        print(f"Error checking deployment status: {e}")
        return False


def get_contract_balance(contract_deployment_id, network="localhost"):
    """Get the ETH balance of a deployed contract."""
    try:
        deployment_info = get_deployment_info(contract_deployment_id)
        contract_address = deployment_info['address']
        
        w3 = create_web3_instance(network)
        if not w3.is_connected():
            return None
        
        balance_wei = w3.eth.get_balance(contract_address)
        balance_eth = w3.from_wei(balance_wei, 'ether')
        return float(balance_eth)
        
    except Exception as e:
        print(f"Error getting contract balance: {e}")
        return None