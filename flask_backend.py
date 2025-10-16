from flask import Flask, request, jsonify
from dotenv import load_dotenv
load_dotenv()
import os
import sys
import asyncio

sys.path.append(os.path.join(os.path.dirname(__file__), "Solana_module"))
sys.path.append(os.path.join(os.path.dirname(__file__), "Tezos_module"))

# Solana imports
import solana_module.anchor_module.dapp_automatic_insertion_manager as trace_manager
from solana_module.anchor_module.anchor_utilities import close_anchor_program_dapp
from solana_module.solana_utils import load_keypair_from_file, create_client
import solana_module.anchor_module.compiler_and_deployer_adpp as toolchain
from solana_module.anchor_module.interactive_data_insertion_dapp import (
    fetch_programs,
    load_idl_for_program,
    fetch_instructions_for_program,
    fetch_program_context,
    build_accounts,
    build_payees,
    parse_args,
    build_and_optionally_send_transaction,
    _run_async,
)

# Ethereum imports
try:
    from ethereum_module.ethereum_utils import get_wallet_balance as get_eth_wallet_balance, get_wallet_address
    from ethereum_module.hardhat_module.compiler_and_deployer import compile_and_deploy_contracts
    from ethereum_module.hardhat_module.contract_utils import (
        fetch_deployed_contracts,
        load_abi_for_contract,
        fetch_functions_for_contract,
        fetch_contract_context,
        interact_with_contract
    )
    ETHEREUM_ENABLED = True
except ImportError as e:
    print(f"Ethereum modules not available: {e}")
    ETHEREUM_ENABLED = False

# Tezos imports
try:
    from tezos_module.tezos_interface import (
        compile_and_deploy_tezos_contracts,
        fetch_tezos_contracts,
        fetch_tezos_entrypoints,
        fetch_tezos_contract_context,
        interact_with_tezos_contract,
        is_tezos_available
    )
    TEZOS_ENABLED = True
except ImportError as e:
    print(f"Tezos modules not available: {e}")
    TEZOS_ENABLED = False

app = Flask(__name__)

WALLETS_PATH = os.path.join("Solana_module", "solana_module", "solana_wallets")


async def get_wallet_balance(wallet_file):
    keypair = load_keypair_from_file(f"{WALLETS_PATH}/{wallet_file}")
    if keypair is None:
        return None
    client = create_client("Devnet")
    resp = await client.get_balance(keypair.pubkey())
    await client.close()
    return resp.value / 1_000_000_000  # lamport -> SOL

def get_wallet_pubkey(wallet_file):
    keypair = load_keypair_from_file(f"{WALLETS_PATH}/{wallet_file}")
    if keypair is None:
        return None
    return str(keypair.pubkey())

# ==============================
# ROUTE Wallet Balance
# ==============================
@app.route("/wallet_balance", methods=["POST"])
def wallet_balance():
    wallet_file = request.json.get("wallet_file")
    if not wallet_file:
        return jsonify({"error": "No wallet selected"}), 400

    balance = _run_async(get_wallet_balance(wallet_file))
    pubkey = get_wallet_pubkey(wallet_file)
    if balance is None:
        return jsonify({"error": "Error reading wallet"}), 500
    return jsonify({"balance": balance, "pubkey": pubkey})

# ==============================
# ROUTE Compile & Deploy
# ==============================
@app.route("/compile_deploy", methods=["POST"])
def compile_deploy():
    wallet_file = request.json.get("wallet_file")
    deploy_flag = request.json.get("deploy", True)
    selected_cluster = request.json.get("cluster", "Devnet")
    single_program = request.json.get("single_program", None)  # Nome del singolo programma
    
    try:
        result = toolchain.compile_and_deploy_programs(
            wallet_name=wallet_file,
            cluster=selected_cluster,
            deploy=deploy_flag,
            single_program=single_program
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    

# ==============================
# ROUTE Automatic Data Insertion
# ==============================
@app.route("/automatic_data_insertion", methods=["POST"])
def automatic_data_insertion():
    selected_trace_file = request.json.get("trace_file")
    print(f"DEBUG: Received trace file request: {selected_trace_file}")
    print(f"DEBUG: Full request JSON: {request.json}")
    
    if not selected_trace_file:
        print("DEBUG: No trace file specified in request")
        return jsonify({"success": False, "error": "No trace file specified"}), 400
    
    # Determina il tipo di blockchain basato sull'estensione del file
    if selected_trace_file.endswith('.json'):
        # Solana traces (JSON)
        traces_path = os.path.join(os.path.dirname(__file__), "Solana_module", "solana_module", "anchor_module", "execution_traces")
        trace_file_path = os.path.join(traces_path, selected_trace_file)
        
        if not selected_trace_file or not os.path.isfile(trace_file_path):
            print("Solana trace file not found:", trace_file_path)
            return jsonify({"success": False, "error": "Solana trace file not found"}), 400
        
        try:
            result = asyncio.run(trace_manager.run_execution_trace(selected_trace_file))
            return jsonify({"success": True, "result": result})
        except Exception as e:
            import traceback
            print("Errore Solana automatic_data_insertion:", traceback.format_exc())
            return jsonify({"success": False, "error": str(e)}), 500
    
    elif selected_trace_file.endswith('.csv'):
        # Tezos traces (CSV)
        traces_path = os.path.join(os.path.dirname(__file__), "Tezos_module", "toolchain", "execution_traces")
        trace_file_path = os.path.join(traces_path, selected_trace_file)
        
        if not selected_trace_file or not os.path.isfile(trace_file_path):
            print("Tezos trace file not found:", trace_file_path)
            return jsonify({"success": False, "error": "Tezos trace file not found"}), 400
        
        try:
            # Qui dovresti chiamare il gestore di tracce Tezos
            # Per ora ritorniamo un messaggio di successo
            return jsonify({"success": True, "result": "Tezos trace execution not yet implemented"})
        except Exception as e:
            import traceback
            print("Errore Tezos automatic_data_insertion:", traceback.format_exc())
            return jsonify({"success": False, "error": str(e)}), 500
    
    else:
        return jsonify({"success": False, "error": "Unsupported trace file format. Use .json for Solana or .csv for Tezos"}), 400

# ==============================
# ROUTE Interactive Data Insertion
# ==============================
@app.route("/interactive_transaction", methods=["POST"])
def interactive_transaction():
    try:
        data = request.json
        
        program = data.get("program")
        instruction = data.get("instruction")
        account_inputs = data.get("account_inputs", [])
        signer_accounts = data.get("signer_accounts", [])
        payees = data.get("payees", [])
        arg_values = data.get("arg_values", {})
        provider_wallet = data.get("provider_wallet")
        send_now = data.get("send_now", True)
        
        # Validate required fields
        if not program or not instruction or not provider_wallet:
            return jsonify({
                "success": False,
                "error": "Missing parameters: program, instruction, provider_wallet are required"
            }), 400
        
        # Fetch context
        ctx = fetch_program_context(program, instruction)
        args_spec = ctx['args_spec']
        
        # Build accounts
        accounts_dict, signer_keypairs = build_accounts(program, account_inputs, signer_accounts)
        
        # Build payees (only for initialize)
        remaining_accounts = build_payees(payees) if instruction == 'initialize' else []
        
        # Parse args
        final_args = parse_args(args_spec, arg_values, instruction, remaining_accounts)
        
        # Build and optionally send transaction
        result = build_and_optionally_send_transaction(
            program,
            instruction,
            accounts_dict,
            final_args,
            signer_keypairs,
            remaining_accounts,
            provider_wallet,
            send_now,
        )
        
        return jsonify({
            "success": True,
            "result": result
        })
        
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": f"Internal server error: {str(e)}"}), 500

# ==============================
# ROUTE Get Programs
# ==============================
@app.route("/get_programs", methods=["GET"])
def get_programs():
    try:
        programs = fetch_programs()
        return jsonify({"success": True, "programs": programs})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ==============================
# ROUTE Get Instructions 
# ==============================
@app.route("/get_instructions", methods=["POST"])
def get_instructions():
    try:
        program = request.json.get("program")
        if not program:
            return jsonify({"success": False, "error": "Program name required"}), 400
        
        instructions = fetch_instructions_for_program(program)
        return jsonify({"success": True, "instructions": instructions})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ==============================
# ROUTE Get Program Context 
# ==============================
@app.route("/get_program_context", methods=["POST"])
def get_program_ctx():
    try:
        program = request.json.get("program")
        instruction = request.json.get("instruction")
        
        if not program or not instruction:
            return jsonify({"success": False, "error": "Program and instruction required"}), 400
        
        ctx = fetch_program_context(program, instruction)
        
        # Convert to JSON-serializable format
        return jsonify({
            "success": True,
            "context": {
                "required_accounts": ctx['required_accounts'],
                "signer_accounts": ctx['signer_accounts'],
                "args_spec": ctx['args_spec']
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ==============================
# ROUTE Placeholder Chiudi Programma
# ==============================
@app.route("/close_program", methods=["POST"])
def close_program():
    selected_program = request.json.get("program")
    base_path = os.path.join(os.path.dirname(__file__), "Solana_module", "solana_module", "anchor_module", ".anchor_files")

    # Percorso completo della cartella del programma
    program_dir = os.path.join(base_path, selected_program) if selected_program else None

    # Controlla che sia una cartella valida
    if not selected_program or not os.path.exists(program_dir) or not os.path.isdir(program_dir):
        print("Program folder not found:", program_dir)
        return jsonify({"success": False, "error": "Program folder not found"}), 400

    try:
        result = close_anchor_program_dapp(selected_program)
        return result
    except Exception as e:
        import traceback
        print("Error in close_program:", traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500


# ==============================
# ETHEREUM ROUTES
# ==============================

ETH_WALLETS_PATH = os.path.join("ethereum_module", "ethereum_wallets")

@app.route("/eth_wallet_balance", methods=["POST"])
def eth_wallet_balance():
    """Get Ethereum wallet balance and address."""
    if not ETHEREUM_ENABLED:
        return jsonify({"error": "Ethereum modules not available"}), 500
        
    wallet_file = request.json.get("wallet_file")
    if not wallet_file:
        return jsonify({"error": "No wallet selected"}), 400

    try:
        wallet_path = os.path.join(ETH_WALLETS_PATH, wallet_file)
        print(f"DEBUG: Wallet path: {wallet_path}")
        print(f"DEBUG: File exists: {os.path.exists(wallet_path)}")
        
        balance = get_eth_wallet_balance(wallet_path, "sepolia")
        print(f"DEBUG: Balance: {balance}")
        
        address = get_wallet_address(wallet_path)
        print(f"DEBUG: Address: {address}")
        
        if balance is None or address is None:
            return jsonify({"error": f"Error reading wallet - Balance: {balance}, Address: {address}"}), 500
            
        return jsonify({"balance": balance, "address": address})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/eth_compile_deploy", methods=["POST"])
def eth_compile_deploy():
    """Compile and deploy Ethereum contracts."""
    if not ETHEREUM_ENABLED:
        return jsonify({"error": "Ethereum modules not available"}), 500
        
    wallet_file = request.json.get("wallet_file")
    deploy_flag = request.json.get("deploy", True)
    network = request.json.get("network", "sepolia")
    single_contract = request.json.get("single_contract", None)
    
    try:
        result = compile_and_deploy_contracts(
            wallet_name=wallet_file,
            network=network,
            deploy=deploy_flag,
            single_contract=single_contract
        )
        return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/eth_get_contracts", methods=["GET"])
def eth_get_contracts():
    """Get list of deployed Ethereum contracts."""
    if not ETHEREUM_ENABLED:
        return jsonify({"error": "Ethereum modules not available"}), 500
        
    try:
        contracts = fetch_deployed_contracts()
        return jsonify({"success": True, "contracts": contracts})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/eth_get_functions", methods=["POST"])
def eth_get_functions():
    """Get functions for a specific contract."""
    if not ETHEREUM_ENABLED:
        return jsonify({"error": "Ethereum modules not available"}), 500
        
    try:
        contract = request.json.get("contract")
        if not contract:
            return jsonify({"success": False, "error": "Contract name required"}), 400
        
        functions = fetch_functions_for_contract(contract)
        return jsonify({"success": True, "functions": functions})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/eth_get_contract_context", methods=["POST"])
def eth_get_contract_context():
    """Get contract function context."""
    if not ETHEREUM_ENABLED:
        return jsonify({"error": "Ethereum modules not available"}), 500
        
    try:
        contract = request.json.get("contract")
        function_name = request.json.get("function_name")
        
        if not contract or not function_name:
            return jsonify({"success": False, "error": "Contract and function name required"}), 400
        
        ctx = fetch_contract_context(contract, function_name)
        return jsonify({"success": True, "context": ctx})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/eth_interact_contract", methods=["POST"])
def eth_interact_contract():
    """Interact with a deployed contract function."""
    if not ETHEREUM_ENABLED:
        return jsonify({"error": "Ethereum modules not available"}), 500
        
    try:
        data = request.json
        
        contract = data.get("contract")
        function_name = data.get("function_name")
        param_values = data.get("param_values", {})
        address_inputs = data.get("address_inputs", [])
        value_eth = data.get("value_eth", "0")
        caller_wallet = data.get("caller_wallet")
        gas_limit = data.get("gas_limit", "300000")
        gas_price = data.get("gas_price", "20")
        is_view = data.get("is_view", False)
        
        # Validate required fields
        if not contract or not function_name or not caller_wallet:
            return jsonify({
                "success": False,
                "error": "Contract, function_name, and caller_wallet are required"
            }), 400
        
        # Interact with contract
        result = interact_with_contract(
            contract_deployment_id=contract,
            function_name=function_name,
            param_values=param_values,
            address_inputs=address_inputs,
            value_eth=value_eth,
            caller_wallet=caller_wallet,
            gas_limit=gas_limit,
            gas_price=gas_price,
            network="sepolia"  # Default network for now
        )
        
        if result["success"]:
            return jsonify({"success": True, "result": result})
        else:
            return jsonify({"success": False, "error": result["error"]}), 400
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": f"Internal error: {str(e)}"}), 500


# ==============================
# TEZOS ROUTES
# ==============================

@app.route("/tezos_compile_deploy", methods=["POST"])
def tezos_compile_deploy():
    """Compile and deploy Tezos contracts."""
    if not TEZOS_ENABLED:
        return jsonify({"error": "Tezos modules not available"}), 500
        
    contract_name = request.json.get("contract_name")
    deploy_flag = request.json.get("deploy", True)
    initial_balance = request.json.get("initial_balance", 0)
    
    try:
        result = compile_and_deploy_tezos_contracts(
            contract_name=contract_name,
            deploy=deploy_flag,
            initial_balance=initial_balance
        )
        return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/tezos_get_contracts", methods=["GET"])
def tezos_get_contracts():
    """Get list of deployed Tezos contracts."""
    if not TEZOS_ENABLED:
        return jsonify({"error": "Tezos modules not available"}), 500
        
    try:
        contracts = fetch_tezos_contracts()
        return jsonify({"success": True, "contracts": contracts})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/tezos_get_entrypoints", methods=["POST"])
def tezos_get_entrypoints():
    """Get entrypoints for a specific Tezos contract."""
    if not TEZOS_ENABLED:
        return jsonify({"error": "Tezos modules not available"}), 500
        
    try:
        contract = request.json.get("contract")
        if not contract:
            return jsonify({"success": False, "error": "Contract name required"}), 400
        
        entrypoints = fetch_tezos_entrypoints(contract)
        return jsonify({"success": True, "entrypoints": entrypoints})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/tezos_get_contract_context", methods=["POST"])
def tezos_get_contract_context():
    """Get contract entrypoint context."""
    if not TEZOS_ENABLED:
        return jsonify({"error": "Tezos modules not available"}), 500
        
    try:
        contract = request.json.get("contract")
        entrypoint = request.json.get("entrypoint")
        
        if not contract or not entrypoint:
            return jsonify({"success": False, "error": "Contract and entrypoint required"}), 400
        
        ctx = fetch_tezos_contract_context(contract, entrypoint)
        return jsonify({"success": True, "context": ctx})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/tezos_interact_contract", methods=["POST"])
def tezos_interact_contract():
    """Interact with a deployed Tezos contract."""
    if not TEZOS_ENABLED:
        return jsonify({"error": "Tezos modules not available"}), 500
        
    try:
        data = request.json
        
        contract = data.get("contract")
        entrypoint = data.get("entrypoint")
        parameters = data.get("parameters", "")
        tez_amount = data.get("tez_amount", 0)
        
        # Validate required fields
        if not contract or not entrypoint:
            return jsonify({
                "success": False,
                "error": "Contract and entrypoint are required"
            }), 400
        
        # Interact with contract
        result = interact_with_tezos_contract(
            contract_name=contract,
            entrypoint_name=entrypoint,
            parameters=parameters,
            tez_amount=tez_amount
        )
        
        if result["success"]:
            return jsonify({"success": True, "result": result["result"]})
        else:
            return jsonify({"success": False, "error": result["error"]}), 400
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": f"Internal error: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=False, port=5000)
