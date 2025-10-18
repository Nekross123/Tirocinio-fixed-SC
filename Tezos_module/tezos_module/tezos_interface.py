# MIT License
#
# Copyright (c) 2025 Manuel Boi, Palumbo Lorenzo, Piras Mauro - Università degli Studi di Cagliari
#
# Tezos interface per Flask backend - Bridge functions

from .tezos_utils import (
    get_available_contracts,
    compile_tezos_contract,
    deploy_tezos_contract,
    get_deployed_contracts,
    get_contract_entrypoints,
    call_contract_entrypoint,
    save_contract_file,
    is_tezos_available
)


def compile_and_deploy_tezos_contracts(contract_name=None, deploy=False, initial_balance=0):
    """
    Compila e opzionalmente deploya contratti Tezos.
    Usa il pattern simile a Ethereum per consistenza UI.
    """
    results = []
    
    if not is_tezos_available():
        return {"success": False, "error": "Tezos modules not available", "contracts": []}
    
    # Se non specificato, prendi tutti i contratti
    if contract_name is None:
        contracts = get_available_contracts()
    else:
        contracts = [contract_name] if contract_name in get_available_contracts() else []
    
    if not contracts:
        error_msg = f"Contract '{contract_name}' not found" if contract_name else "No contracts found"
        return {"success": False, "error": error_msg, "contracts": []}
    
    for contract in contracts:
        contract_result = {
            "contract": contract,
            "compiled": False,
            "deployed": False,
            "contract_address": None,
            "transaction_hash": None,
            "errors": []
        }
        
        try:
            # STEP 1: Compilazione
            compile_result = compile_tezos_contract(contract)
            contract_result["compiled"] = compile_result["success"]
            
            if not compile_result["success"]:
                contract_result["errors"].append(compile_result["error"])
                results.append(contract_result)
                continue
            
            # STEP 2: Deploy (se richiesto)
            if deploy:
                deploy_result = deploy_tezos_contract(contract, initial_balance)
                contract_result["deployed"] = deploy_result["success"]
                
                if deploy_result["success"]:
                    contract_result["contract_address"] = deploy_result["contract_address"]
                    contract_result["transaction_hash"] = deploy_result["transaction_hash"]
                else:
                    contract_result["errors"].append(deploy_result["error"])
                    
        except Exception as e:
            contract_result["errors"].append(str(e))
        
        results.append(contract_result)
    
    return {"success": True, "contracts": results}


def fetch_tezos_contracts():
    """Ottiene lista contratti deployati per UI."""
    if not is_tezos_available():
        return []
    return get_deployed_contracts()


def fetch_tezos_entrypoints(contract_name):
    """Ottiene entrypoints per un contratto specifico."""
    if not is_tezos_available():
        return []
    return get_contract_entrypoints(contract_name)


def fetch_tezos_contract_context(contract_name, entrypoint_name):
    """
    Ottiene informazioni su un entrypoint specifico.
    Per ora ritorna struttura base, può essere espansa analizzando il contratto.
    """
    return {
        "contract": contract_name,
        "entrypoint": entrypoint_name,
        "parameters_schema": "dynamic",  # Da implementare analisi schema
        "is_payable": True  # Tezos supporta sempre invio XTZ
    }


def interact_with_tezos_contract(contract_name, entrypoint_name, parameters, tez_amount):
    """
    Interagisce con un contratto Tezos deployato.
    """
    if not is_tezos_available():
        return {"success": False, "error": "Tezos modules not available"}
    
    try:
        # Prepara parametri se forniti
        processed_params = None
        if parameters and parameters.strip():
            # Se contiene virgole, split in lista
            if "," in parameters:
                processed_params = [p.strip() for p in parameters.split(",")]
            else:
                processed_params = [parameters.strip()]
        
        # Chiama l'entrypoint usando le funzioni esistenti
        result = call_contract_entrypoint(
            contract_name=contract_name,
            entrypoint_name=entrypoint_name,
            parameters=processed_params,
            tez_amount=tez_amount
        )
        
        return result
        
    except Exception as e:
        return {"success": False, "error": f"Interaction error: {str(e)}"}


def upload_tezos_contract(contract_name, contract_content):
    """Upload di un nuovo contratto SmartPy."""
    if not is_tezos_available():
        return {"success": False, "error": "Tezos modules not available"}
    
    return save_contract_file(contract_name, contract_content)