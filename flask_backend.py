from flask import Flask, request, jsonify
import os
import sys
import asyncio

sys.path.append(os.path.join(os.path.dirname(__file__), "Toolchain"))

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

app = Flask(__name__)

WALLETS_PATH = os.path.join("Toolchain", "solana_module", "solana_wallets")


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
# ROUTE Saldo Wallet
# ==============================
@app.route("/wallet_balance", methods=["POST"])
def wallet_balance():
    wallet_file = request.json.get("wallet_file")
    if not wallet_file:
        return jsonify({"error": "Nessun wallet selezionato"}), 400

    balance = _run_async(get_wallet_balance(wallet_file))
    pubkey = get_wallet_pubkey(wallet_file)
    if balance is None:
        return jsonify({"error": "Errore nel leggere il wallet"}), 500
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
    traces_path = os.path.join(os.path.dirname(__file__), "Toolchain", "solana_module", "anchor_module", "execution_traces")
    trace_file_path = os.path.join(traces_path, selected_trace_file) if selected_trace_file else None

    if not selected_trace_file or not os.path.isfile(trace_file_path):
        print("Trace file non trovato:", trace_file_path)
        return jsonify({"success": False, "error": "Trace file non trovato"}), 400

    try:
        result = asyncio.run(trace_manager.run_execution_trace(selected_trace_file))
        return jsonify({"success": True, "result": result})
    except Exception as e:
        import traceback
        print("Errore automatic_data_insertion:", traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500

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
                "error": "Parametri mancanti: progit gram, instruction, provider_wallet sono richiesti"
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
        return jsonify({"success": False, "error": f"Errore interno: {str(e)}"}), 500

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
    base_path = os.path.join(os.path.dirname(__file__), "Toolchain", "solana_module", "anchor_module", ".anchor_files")

    # Percorso completo della cartella del programma
    program_dir = os.path.join(base_path, selected_program) if selected_program else None

    # Controlla che sia una cartella valida
    if not selected_program or not os.path.exists(program_dir) or not os.path.isdir(program_dir):
        print("Cartella del programma non trovata:", program_dir)
        return jsonify({"success": False, "error": "Cartella del programma non trovata"}), 400

    try:
        result = close_anchor_program_dapp(selected_program)
        return jsonify({"success": True, "result": result})
    except Exception as e:
        import traceback
        print("Errore in close_program:", traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=False, port=5000)
