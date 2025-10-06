from flask import Flask, request, jsonify
import os
import sys
import asyncio

sys.path.append(os.path.join(os.path.dirname(__file__), "Toolchain"))

from solana_module.solana_utils import load_keypair_from_file, create_client
import solana_module.anchor_module.compiler_and_deployer_adpp as toolchain
import solana_module.anchor_module.dapp_automatic_insertion_manager as trace_manager
from solana_module.anchor_module.anchor_utilities import close_anchor_program_dapp

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

    balance = asyncio.run(get_wallet_balance(wallet_file))
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
