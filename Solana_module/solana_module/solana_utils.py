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


import json
import os
from solders.keypair import Keypair
from solana.rpc.async_api import AsyncClient
import subprocess
import platform


# Percorso base del progetto, utile per tutti i path relativi ad Anchor
anchor_base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

solana_base_path = os.path.dirname(os.path.abspath(__file__))


# ====================================================
# PUBLIC FUNCTIONS
# ====================================================

def load_keypair_from_file(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            data = json.load(f)
            return Keypair.from_bytes(data)
    else:
        return None

def create_client(cluster):
    # Define rpc basing on the cluster
    rpc_url = None
    if cluster == "Localnet":
        rpc_url = "http://localhost:8899"
    elif cluster == "Devnet":
        rpc_url = "https://api.devnet.solana.com"
    elif cluster == "Mainnet":
        rpc_url = "https://api.mainnet-beta.solana.com"

    # Crete client
    client = AsyncClient(rpc_url)
    return client

def choose_wallet():
    wallet_names = _get_wallet_names()
    chosen_wallet = selection_menu('wallet', wallet_names)
    return chosen_wallet

def choose_cluster():
    allowed_choices = ['Localnet', 'Devnet', 'Mainnet']
    return selection_menu('cluster', allowed_choices)

def selection_menu(to_be_chosen, choices):
    # Generate list of numbers corresponding to the number of choices
    allowed_choices = list(map(str, range(1, len(choices) + 1))) + ['0']
    choice = None

    # Print available choices
    while choice not in allowed_choices:
        print(f"Please choose {to_be_chosen}:")
        for idx, program_name in enumerate(choices, 1):
            print(f"{idx}) {program_name}")
        print("0) Go back")

        choice = input()
        if choice == '0':
            return
        elif choice in allowed_choices:
            # Manage choice
            return choices[int(choice) - 1]
        else:
            print("Please choose a valid choice.")

def perform_program_closure(program_id, cluster, wallet_name):
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
    if operating_system == "Windows":
        result = subprocess.run(["wsl", command], capture_output=True, text=True) # On Windows, use WSL to execute commands in a Linux shell
    elif platform.system() == "Darwin" or platform.system() == "Linux":
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
    else:
        result = None

    return result





# ====================================================
# PRIVATE FUNCTIONS
# ====================================================

def _get_wallet_names():
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
    if cluster == "Localnet":
        return 'localhost'
    elif cluster == "Devnet":
        return 'devnet'
    elif cluster == "Mainnet":
        return 'mainnet'
    else:
        return None