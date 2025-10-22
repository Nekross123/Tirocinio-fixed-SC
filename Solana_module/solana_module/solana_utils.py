import json
import os
from solders.keypair import Keypair
from solana.rpc.async_api import AsyncClient
import subprocess
import platform


# Percorso base del progetto, utile per tutti i path relativi ad Anchor
anchor_base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

solana_base_path = os.path.dirname(os.path.abspath(__file__))


def load_keypair_from_file(file_path):
    """Load a Keypair from a local JSON file.

    The file must contain the 64-byte secret key array exported by solana-keygen.
    Returns a Keypair or None if the file doesn't exist.
    """
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            data = json.load(f)
            return Keypair.from_bytes(data)
    else:
        return None

def create_client(cluster):
    """Create an AsyncClient for the given cluster name.

    Supported clusters: Localnet, Devnet, Mainnet. Returns a ready AsyncClient.
    """
    rpc_url = None
    if cluster == "Localnet":
        rpc_url = "http://localhost:8899"
    elif cluster == "Devnet":
        rpc_url = "https://api.devnet.solana.com"
    elif cluster == "Mainnet":
        rpc_url = "https://api.mainnet-beta.solana.com"
    client = AsyncClient(rpc_url)
    return client

def choose_wallet():
    """Interactive selection of a wallet file from solana_wallets folder."""
    wallet_names = _get_wallet_names()
    chosen_wallet = selection_menu('wallet', wallet_names)
    return chosen_wallet

def choose_cluster():
    """Ask which cluster to use. Returns one of Localnet/Devnet/Mainnet."""
    allowed_choices = ['Localnet', 'Devnet', 'Mainnet']
    return selection_menu('cluster', allowed_choices)

def selection_menu(to_be_chosen, choices):
    """Simple numbered CLI selector that also supports '0' to go back."""
    allowed_choices = list(map(str, range(1, len(choices) + 1))) + ['0']
    choice = None

    while choice not in allowed_choices:
        print(f"Please choose {to_be_chosen}:")
        for idx, program_name in enumerate(choices, 1):
            print(f"{idx}) {program_name}")
        print("0) Go back")

        choice = input()
        if choice == '0':
            return
        elif choice in allowed_choices:
            return choices[int(choice) - 1]
        else:
            print("Please choose a valid choice.")

def perform_program_closure(program_id, cluster, wallet_name):
    """Run 'solana program close' for a deployed program.

    We map cluster to the right URL flag and pass the selected wallet. The
    actual command executes via run_command so it works on Windows/macOS/Linux.
    Returns the CompletedProcess result.
    """
    command_cluster = _associate_command_cluster(cluster)
    if command_cluster is None:
        return

    command = f"solana program close {program_id} --keypair {solana_base_path}/solana_wallets/{wallet_name} --url {command_cluster} --bypass-warning"
    operating_system = platform.system()
    result = run_command(operating_system, command)
    if result.stderr:
        print(result.stderr)
    else:
        print(result.stdout)
    return result

def run_command(operating_system, command):
    """Execute a shell command in a cross-platform way.

    On Windows we delegate to WSL, otherwise we run in the native shell.
    Returns subprocess.CompletedProcess.
    """
    if operating_system == "Windows":
        result = subprocess.run(["wsl", command], capture_output=True, text=True)
    elif platform.system() == "Darwin" or platform.system() == "Linux":
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
    else:
        result = None

    return result



def _get_wallet_names():
    """List all .json keypair files under the local solana_wallets folder."""
    wallets_path = f"{solana_base_path}/solana_wallets"
    wallet_names = []
    # Check if the folder exists
    if not os.path.isdir(wallets_path):
        print(f"The path '{wallets_path}' does not exist.")
    else:
        # Get all .json in the solana_wallets folder
        wallet_names = [f for f in os.listdir(wallets_path) if f.endswith(".json")]

    return wallet_names

def _associate_command_cluster(cluster):
    """Translate cluster name into solana CLI URL shorthand."""
    if cluster == "Localnet":
        return 'localhost'
    elif cluster == "Devnet":
        return 'devnet'
    elif cluster == "Mainnet":
        return 'mainnet'
    else:
        return None