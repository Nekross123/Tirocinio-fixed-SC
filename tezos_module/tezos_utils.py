# MIT License
#
# Copyright (c) 2025 Manuel Boi - Università degli Studi di Cagliari
#
# Tezos utilities - Wrapper per tezos-contract-2.0 esistente
# NON MODIFICA il codice originale, solo import e wrapper functions

import os
import sys
import json

# Path al codice tezos esistente (NO modifiche)
tezos_base_path = os.path.join(os.path.dirname(__file__), "..", "tezos-contract-2.0")
toolchain_path = os.path.join(tezos_base_path, "toolchain")
contracts_path = os.path.join(tezos_base_path, "contracts")

# Aggiungo il path per importare il codice esistente
sys.path.insert(0, toolchain_path)

# Import delle funzioni esistenti (zero modifiche al codice originale)
try:
    from contractUtils import compileContract, origination, entrypointCall, callInfoResult
    from folderScan import folderScan
    from jsonUtils import addressUpdate, getAddress
    from csvUtils import csvReader
    TEZOS_AVAILABLE = True
except ImportError as e:
    print(f"Tezos modules not available: {e}")
    TEZOS_AVAILABLE = False


def get_available_contracts():
    """Wrapper per folderScan - ottiene lista contratti disponibili."""
    if not TEZOS_AVAILABLE:
        return []
    
    try:
        # Usa la funzione esistente con il path corretto
        contracts = folderScan(contracts_path)
        return contracts
    except Exception as e:
        print(f"Error getting contracts: {e}")
        return []


def compile_tezos_contract(contract_name):
    """Wrapper per compileContract - compila un contratto Tezos."""
    if not TEZOS_AVAILABLE:
        return {"success": False, "error": "Tezos modules not available"}
    
    try:
        # Path al contratto (usa struttura esistente)
        contract_path = os.path.join(contracts_path, contract_name, f"{contract_name}.py")
        
        if not os.path.exists(contract_path):
            return {"success": False, "error": f"Contract file not found: {contract_path}"}
        
        # Usa la funzione esistente senza modificarla
        compileContract(contract_path)
        
        return {
            "success": True,
            "message": f"Contract {contract_name} compiled successfully",
            "contract_path": contract_path
        }
        
    except Exception as e:
        return {"success": False, "error": f"Compilation error: {str(e)}"}


def deploy_tezos_contract(contract_name, initial_balance=0):
    """Wrapper per origination - deploya un contratto Tezos."""
    if not TEZOS_AVAILABLE:
        return {"success": False, "error": "Tezos modules not available"}
    
    try:
        # Path ai file generati dalla compilazione (usa struttura esistente)
        contract_folder = os.path.join(contracts_path, contract_name)
        
        # Try both naming conventions (new and legacy)
        code_file = os.path.join(contract_folder, f"{contract_name}_code.tz")
        storage_file = os.path.join(contract_folder, f"{contract_name}_storage.tz")
        
        # Fallback to legacy naming if new naming not found
        if not os.path.exists(code_file):
            code_file = os.path.join(contract_folder, "step_001_cont_0_contract.tz")
        if not os.path.exists(storage_file):
            storage_file = os.path.join(contract_folder, "step_001_cont_0_storage.tz")
        
        if not os.path.exists(code_file) or not os.path.exists(storage_file):
            return {"success": False, "error": "Contract not compiled. Please compile first."}
        
        # Leggi i file generati
        with open(code_file, 'r') as f:
            michelson_code = f.read()
        with open(storage_file, 'r') as f:
            initial_storage = f.read()
        
        # Usa le funzioni esistenti senza modificarle
        from pytezos import pytezos
        
        # Leggi la chiave dal wallet.json nella nuova cartella tezos_wallets
        wallet_path = os.path.join(os.path.dirname(__file__), "tezos_wallets", "wallet.json")
        with open(wallet_path, 'r') as f:
            wallet_data = json.load(f)
        key = list(wallet_data.values())[0]  # Prendi prima chiave disponibile
        
        client = pytezos.using(shell='https://ghostnet.tezos.marigold.dev', key=key)
        
        # Deploy usando funzione esistente
        op_result = origination(client, michelson_code, initial_storage, initial_balance)
        
        if op_result and hasattr(op_result, 'hash'):
            # Salva indirizzo usando funzione esistente
            contract_address = op_result.contents[0]['metadata']['operation_result']['originated_contracts'][0]
            addressUpdate(contract_name, contract_address)
            
            return {
                "success": True,
                "contract_address": contract_address,
                "transaction_hash": op_result.hash(),
                "message": f"Contract {contract_name} deployed successfully"
            }
        else:
            return {"success": False, "error": "Deployment failed"}
            
    except Exception as e:
        return {"success": False, "error": f"Deployment error: {str(e)}"}


def get_deployed_contracts():
    """Wrapper per getAddress - ottiene lista contratti deployati."""
    if not TEZOS_AVAILABLE:
        return []
    
    try:
        # Usa la funzione esistente senza modificarla
        addresses = getAddress()
        return list(addresses.keys()) if addresses else []
    except Exception as e:
        print(f"Error getting deployed contracts: {e}")
        return []


def get_contract_entrypoints(contract_name):
    """Ottiene gli entrypoints di un contratto deployato."""
    if not TEZOS_AVAILABLE:
        return []
    
    try:
        addresses = getAddress()
        if contract_name not in addresses:
            return []
        
        contract_address = addresses[contract_name]
        
        # Usa PyTezos per analizzare il contratto (come nel codice originale)
        from pytezos import pytezos
        contract_interface = pytezos.contract(contract_address)
        entrypoints = contract_interface.entrypoints
        
        # Rimuovi 'default' se presente (come nel codice originale)
        if len(entrypoints) > 1 and "default" in entrypoints:
            del entrypoints["default"]
        
        return list(entrypoints.keys())
        
    except Exception as e:
        print(f"Error getting entrypoints: {e}")
        return []


def call_contract_entrypoint(contract_name, entrypoint_name, parameters=None, tez_amount=0):
    """Wrapper per entrypointCall - chiama un entrypoint del contratto."""
    if not TEZOS_AVAILABLE:
        return {"success": False, "error": "Tezos modules not available"}
    
    try:
        addresses = getAddress()
        if contract_name not in addresses:
            return {"success": False, "error": f"Contract {contract_name} not deployed"}
        
        contract_address = addresses[contract_name]
        
        # Setup client come nel codice originale
        from pytezos import pytezos
        
        # Leggi la chiave dal wallet.json nella nuova cartella tezos_wallets
        wallet_path = os.path.join(os.path.dirname(__file__), "tezos_wallets", "wallet.json")
        with open(wallet_path, 'r') as f:
            wallet_data = json.load(f)
        key = list(wallet_data.values())[0]  # Prendi prima chiave disponibile
        
        client = pytezos.using(shell='https://ghostnet.tezos.marigold.dev', key=key)
        
        # Usa la funzione esistente senza modificarla
        op_result = entrypointCall(
            client=client,
            contractAddress=contract_address,
            entrypointName=entrypoint_name,
            parameters=parameters,
            tezAmount=tez_amount
        )
        
        # Analizza risultato usando funzione esistente
        info_result = callInfoResult(opResult=op_result)
        info_result["contract"] = contract_name
        info_result["entryPoint"] = entrypoint_name
        
        return {
            "success": True,
            "result": info_result,
            "message": f"Entrypoint {entrypoint_name} called successfully"
        }
        
    except Exception as e:
        return {"success": False, "error": f"Entrypoint call error: {str(e)}"}


def save_contract_file(contract_name, contract_content):
    """Salva un nuovo contratto nella struttura esistente."""
    try:
        # Crea directory se non esiste (usa struttura esistente)
        contract_dir = os.path.join(contracts_path, contract_name)
        os.makedirs(contract_dir, exist_ok=True)
        
        # Salva il file Python (come nella struttura esistente)
        contract_file = os.path.join(contract_dir, f"{contract_name}.py")
        with open(contract_file, 'w', encoding='utf-8') as f:
            f.write(contract_content)
        
        return {
            "success": True,
            "file_path": contract_file,
            "message": f"Contract {contract_name} saved successfully"
        }
        
    except Exception as e:
        return {"success": False, "error": f"Save error: {str(e)}"}


# Funzioni di utilità per il frontend
def get_tezos_base_path():
    """Ritorna il path base di tezos-contract-2.0."""
    return tezos_base_path


def is_tezos_available():
    """Controlla se i moduli Tezos sono disponibili."""
    return TEZOS_AVAILABLE