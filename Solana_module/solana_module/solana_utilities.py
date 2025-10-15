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


import asyncio
from Solana_module.solana_module.solana_utils import choose_wallet, create_client, load_keypair_from_file, solana_base_path, \
    choose_cluster, perform_program_closure


# ====================================================
# PUBLIC FUNCTIONS
# ====================================================

def request_balance():
    chosen_wallet = choose_wallet()
    if chosen_wallet is not None:
        keypair = load_keypair_from_file(f"{solana_base_path}/solana_wallets/{chosen_wallet}")
        client = _manage_client_creation()
        asyncio.run(_print_account_balance(client, keypair.pubkey()))

def get_public_key():
    chosen_wallet = choose_wallet()
    if chosen_wallet is not None:
        keypair = load_keypair_from_file(f"{solana_base_path}/solana_wallets/{chosen_wallet}")
        print(f"The public key is {keypair.pubkey()}")

def close_program():
    repeat1 = True
    while repeat1:
        print('Insert the program ID to close (or 0 to go back).')
        program_id = input()
        if program_id == '0':
            return

        repeat2 = True
        while repeat2:
            chosen_wallet = choose_wallet()
            if chosen_wallet is None:
                repeat2 = False
            else:
                repeat1 = False

                cluster = choose_cluster()
                if cluster is not None:
                    repeat2 = False

                    # Confirmation phase
                    allowed_choices = ['y', 'Y', 'n', 'N']
                    choice = None
                    while choice not in allowed_choices:
                        print('Are you sure you want to close the program? (y/n)')
                        choice = input()
                        if choice == 'y' or choice == 'Y':
                            perform_program_closure(program_id, cluster, chosen_wallet)
                        elif choice == 'n' or choice == 'N':
                            return
                        else:
                            print('Please insert a valid choice.')




# ====================================================
# PRIVATE FUNCTIONS
# ====================================================

def _manage_client_creation():
    clusters = ["Localnet", "Devnet", "Mainnet"]
    allowed_choices = list(map(str, range(1, len(clusters) + 1)))
    choice = None

    while choice not in allowed_choices:
        print("For which network you want to check balance?")
        for idx, cluster in enumerate(clusters, 1):
            print(f"{idx}. {cluster}")
        choice = input()

    client = create_client(clusters[int(choice) - 1])
    return client

async def _print_account_balance(client, pubkey):
    try:
        resp = await client.get_balance(pubkey)
        balance_in_sol = resp.value / 1_000_000_000  # Converte lamports in SOL
        print(f"Account {pubkey} balance: {balance_in_sol} SOL")
        return resp.value
    except ConnectionError:
        print('Error: Could not get account balance')

        