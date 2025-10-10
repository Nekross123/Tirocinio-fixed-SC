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
import re
import json
import subprocess
import platform
import time
from web3 import Web3
from eth_account import Account
from solcx import compile_source, install_solc, set_solc_version
from Toolchain.ethereum_module.ethereum_utils import (
    run_command, 
    create_web3_instance, 
    load_wallet_from_file, 
    choose_wallet, 
    choose_network,
    wait_for_transaction_receipt
)

hardhat_base_path = os.path.join("Toolchain", "ethereum_module", "hardhat_module")


# -------------------------
# Utility Functions
# -------------------------
def _remove_extension(filename: str) -> str:
    """Remove file extension from filename."""
    return os.path.splitext(filename)[0]


def _extract_contract_name_from_source(source_code: str) -> str:
    """Extract the main contract name from Solidity source code."""
    # Look for contract declarations
    contract_matches = re.findall(r'contract\s+(\w+)', source_code)
    if contract_matches:
        # Return the last contract found (usually the main one)
        return contract_matches[-1]
    return None


def _detect_solidity_version(source_code: str) -> str:
    """Detect Solidity version from pragma statement."""
    pragma_match = re.search(r'pragma\s+solidity\s+([^;]+);', source_code)
    if pragma_match:
        version_spec = pragma_match.group(1).strip()
        # Extract version number (e.g., "^0.8.0" -> "0.8.0")
        version_match = re.search(r'(\d+\.\d+\.\d+)', version_spec)
        if version_match:
            return version_match.group(1)
    return "0.8.19"  # Default version


# =====================================================
# MAIN COMPILE AND DEPLOY FUNCTION
# =====================================================
def compile_and_deploy_contracts(wallet_name=None, network="localhost", deploy=False, single_contract=None):
    """
    Compile and optionally deploy Solidity contracts.
    Similar to the Solana version but adapted for Ethereum.
    """
    results = []
    contracts_path = os.path.join(hardhat_base_path, "contracts")

    # Validate network
    allowed_networks = {"localhost", "sepolia", "goerli", "mainnet"}
    if network not in allowed_networks:
        return {"success": False, "error": f"Network not supported: {network}", "contracts": []}

    # Read contract files
    file_names, contracts_source = _read_sol_files(contracts_path, single_contract)
    if not file_names:
        if single_contract:
            return {"success": False, "error": f"Contract '{single_contract}' not found", "contracts": []}
        else:
            return {"success": False, "error": "No contracts found", "contracts": []}

    # Process each contract
    for file_name, source_code in zip(file_names, contracts_source):
        contract_name = _remove_extension(file_name)
        contract_result = {
            "contract": contract_name,
            "compiled": False,
            "deployed": False,
            "address": None,
            "transaction_hash": None,
            "gas_used": None,
            "errors": []
        }

        try:
            # Compile contract
            compiled_data = _compile_contract(contract_name, source_code)
            if compiled_data:
                contract_result["compiled"] = True
                
                # Save compiled artifacts
                _save_contract_artifacts(contract_name, compiled_data, source_code)
                
                # Deploy if requested
                if deploy:
                    if wallet_name:
                        deploy_result = _deploy_contract(
                            contract_name, 
                            compiled_data, 
                            wallet_name, 
                            network
                        )
                        
                        if deploy_result["success"]:
                            contract_result["deployed"] = True
                            contract_result["address"] = deploy_result["address"]
                            contract_result["transaction_hash"] = deploy_result["transaction_hash"]
                            contract_result["gas_used"] = deploy_result["gas_used"]
                        else:
                            contract_result["errors"].append(deploy_result["error"])
                    else:
                        contract_result["errors"].append("No wallet specified for deployment")
            else:
                contract_result["errors"].append("Compilation failed")

        except Exception as e:
            contract_result["errors"].append(str(e))

        results.append(contract_result)

    return {"success": True, "contracts": results}


# =====================================================
# HELPER FUNCTIONS
# =====================================================
def _read_sol_files(contracts_path, single_contract=None):
    """Read Solidity contract files from the contracts directory."""
    if not os.path.isdir(contracts_path):
        return [], []
    
    all_files = [f for f in os.listdir(contracts_path) if f.endswith(".sol")]
    
    if single_contract:
        if single_contract in all_files:
            file_names = [single_contract]
        else:
            return [], []
    else:
        file_names = all_files
    
    contracts_source = []
    for file_name in file_names:
        with open(os.path.join(contracts_path, file_name), "r", encoding="utf-8") as f:
            contracts_source.append(f.read())
    
    return file_names, contracts_source


def _compile_contract(contract_name, source_code):
    """
    Compile a Solidity contract using py-solc-x.
    Based on Prof. Andrea Pinna's compiler approach from bcschool2023.
    """
    try:
        # Detect and install Solidity version
        solc_version = _detect_solidity_version(source_code)
        
        try:
            install_solc(solc_version)
            set_solc_version(solc_version)
        except Exception as e:
            print(f"Warning: Could not install/set Solidity version {solc_version}: {e}")
            # Try with default version like the professor uses
            try:
                install_solc("0.8.18")
                set_solc_version("0.8.18")
            except:
                pass

        # Compile the contract - same approach as professor's compile function
        compiled_contracts = compile_source(source_code, output_values=['abi', 'bin'])
        
        # Extract the main contract - following prof's pattern
        contract_interface = None
        
        # Try to find contract by name first
        for contract_id, interface in compiled_contracts.items():
            if contract_name.lower() in contract_id.lower():
                contract_interface = interface
                break
        
        # If not found, take the first one (prof's fallback approach)
        if not contract_interface:
            contract_interface = list(compiled_contracts.values())[0]
        
        return contract_interface

    except Exception as e:
        print(f"Compilation error for {contract_name}: {e}")
        return None


def _save_contract_artifacts(contract_name, compiled_data, source_code):
    """Save compiled contract artifacts (ABI, bytecode) to files."""
    artifacts_dir = os.path.join(hardhat_base_path, "artifacts")
    os.makedirs(artifacts_dir, exist_ok=True)
    
    # Save ABI
    abi_file = os.path.join(artifacts_dir, f"{contract_name}_abi.json")
    with open(abi_file, 'w', encoding='utf-8') as f:
        json.dump(compiled_data['abi'], f, indent=2)
    
    # Save bytecode
    bytecode_file = os.path.join(artifacts_dir, f"{contract_name}_bytecode.json")
    bytecode_data = {
        "bytecode": compiled_data['bin'],
        "bytecode_runtime": compiled_data.get('bin-runtime', ''),
        "source_code": source_code
    }
    with open(bytecode_file, 'w', encoding='utf-8') as f:
        json.dump(bytecode_data, f, indent=2)


def _deploy_contract(contract_name, compiled_data, wallet_name, network):
    """Deploy a compiled contract to the specified network."""
    try:
        # Load wallet
        wallet_path = os.path.join("Toolchain", "ethereum_module", "ethereum_wallets", wallet_name)
        wallet_data = load_wallet_from_file(wallet_path)
        if not wallet_data:
            return {"success": False, "error": "Could not load wallet"}

        # Create Web3 instance
        w3 = create_web3_instance(network)
        if not w3.is_connected():
            return {"success": False, "error": f"Could not connect to network: {network}"}

        # Create account from private key
        account = Account.from_key(wallet_data["private_key"])

        # Get contract bytecode and ABI
        contract_bytecode = compiled_data['bin']
        contract_abi = compiled_data['abi']

        # Create contract object
        contract = w3.eth.contract(abi=contract_abi, bytecode=contract_bytecode)

        # Get nonce
        nonce = w3.eth.get_transaction_count(account.address)

        # Build deployment transaction
        transaction = contract.constructor().build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gas': 3000000,  # Default gas limit
            'gasPrice': w3.eth.gas_price,
        })

        # Sign transaction
        signed_txn = w3.eth.account.sign_transaction(transaction, wallet_data["private_key"])

        # Send transaction - handle different web3.py versions
        raw_transaction = getattr(signed_txn, 'rawTransaction', getattr(signed_txn, 'raw_transaction', signed_txn))
        tx_hash = w3.eth.send_raw_transaction(raw_transaction)
        
        # Wait for transaction receipt
        receipt = wait_for_transaction_receipt(tx_hash.hex(), network)
        
        if receipt and receipt.status == 1:
            # Save deployment info
            _save_deployment_info(contract_name, receipt.contractAddress, tx_hash.hex(), network, contract_abi)
            
            return {
                "success": True,
                "address": receipt.contractAddress,
                "transaction_hash": tx_hash.hex(),
                "gas_used": receipt.gasUsed
            }
        else:
            return {"success": False, "error": "Transaction failed or contract not deployed"}

    except Exception as e:
        return {"success": False, "error": f"Deployment error: {str(e)}"}


def _save_deployment_info(contract_name, contract_address, tx_hash, network, abi):
    """Save deployment information to a JSON file."""
    deployments_dir = os.path.join(hardhat_base_path, "deployments")
    os.makedirs(deployments_dir, exist_ok=True)
    
    deployment_info = {
        "contract_name": contract_name,
        "address": contract_address,
        "transaction_hash": tx_hash,
        "network": network,
        "deployed_at": time.time(),
        "abi": abi
    }
    
    deployment_file = os.path.join(deployments_dir, f"{contract_name}_{network}.json")
    with open(deployment_file, 'w', encoding='utf-8') as f:
        json.dump(deployment_info, f, indent=2)


# =====================================================
# UTILITY FUNCTIONS FOR FRONTEND INTEGRATION
# =====================================================
def get_deployed_contracts():
    """Get list of deployed contracts."""
    deployments_dir = os.path.join(hardhat_base_path, "deployments")
    if not os.path.exists(deployments_dir):
        return []
    
    contracts = []
    for file_name in os.listdir(deployments_dir):
        if file_name.endswith('.json'):
            contract_name = file_name.replace('.json', '')
            contracts.append(contract_name)
    
    return contracts


def get_contract_abi(contract_name):
    """Get ABI for a specific contract."""
    artifacts_dir = os.path.join(hardhat_base_path, "artifacts")
    abi_file = os.path.join(artifacts_dir, f"{contract_name}_abi.json")
    
    if os.path.exists(abi_file):
        with open(abi_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def get_deployment_info(contract_deployment_id):
    """Get deployment information for a specific contract deployment."""
    deployments_dir = os.path.join(hardhat_base_path, "deployments")
    deployment_file = os.path.join(deployments_dir, f"{contract_deployment_id}.json")
    
    if os.path.exists(deployment_file):
        with open(deployment_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


# =====================================================
# HARDHAT INTEGRATION (OPTIONAL)
# =====================================================
def _init_hardhat_project(project_name):
    """Initialize a new Hardhat project (optional feature)."""
    operating_system = platform.system()
    target_dir = os.path.join(hardhat_base_path, ".hardhat_projects", project_name)
    
    commands = [
        f"mkdir -p {target_dir}",
        f"cd {target_dir}",
        "npm init -y",
        "npm install --save-dev hardhat",
        "npx hardhat init --yes"
    ]
    
    result = run_command(operating_system, " && ".join(commands))
    return result is not None and result.returncode == 0


def _compile_with_hardhat(contract_name):
    """Compile using Hardhat (alternative compilation method)."""
    operating_system = platform.system()
    hardhat_project_dir = os.path.join(hardhat_base_path, ".hardhat_projects", contract_name)
    
    if not os.path.exists(hardhat_project_dir):
        if not _init_hardhat_project(contract_name):
            return False
    
    # Copy contract to hardhat contracts directory
    source_file = os.path.join(hardhat_base_path, "contracts", f"{contract_name}.sol")
    dest_file = os.path.join(hardhat_project_dir, "contracts", f"{contract_name}.sol")
    
    try:
        import shutil
        shutil.copy2(source_file, dest_file)
    except Exception as e:
        print(f"Error copying contract: {e}")
        return False
    
    # Compile with Hardhat
    commands = [
        f"cd {hardhat_project_dir}",
        "npx hardhat compile"
    ]
    
    result = run_command(operating_system, " && ".join(commands))
    return result is not None and result.returncode == 0