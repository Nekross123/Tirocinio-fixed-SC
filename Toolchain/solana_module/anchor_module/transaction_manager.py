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


import sys
from pathlib import Path
import importlib
from solders.message import MessageV0
from solders.transaction import VersionedTransaction
from solders.transaction import Transaction
from Toolchain.solana_module.anchor_module.anchor_utils import anchor_base_path


# ====================================================
# PUBLIC FUNCTIONS
# ====================================================

from solders.message import MessageV0
from solders.transaction import VersionedTransaction

async def build_transaction(program_name, instruction, accounts, args, signer_account_keypairs, client, provider):
    # Ottieni la funzione da anchorpy
    function = _import_function(program_name, instruction)
    ix = _prepare_function(accounts, args, function)

    # Ottieni blockhash
    resp = await client.get_latest_blockhash()
    recent_blockhash = resp.value.blockhash

    # Costruisci MessageV0 usando try_compile
    message = MessageV0.try_compile(
        payer=provider.wallet.payer.pubkey(),
        instructions=[ix],
        address_lookup_table_accounts=[],
        recent_blockhash=recent_blockhash
    )

    # Ottieni tutti i firmatari (payer + altri)
    keypairs = list(signer_account_keypairs.values())
    if provider.wallet.payer not in keypairs:
        keypairs.insert(0, provider.wallet.payer)

    # Costruisci la transazione versionata
    tx = VersionedTransaction(message, keypairs)

    return tx


def measure_transaction_size(tx):
    # Check transaction type
    if isinstance(tx, Transaction):
        # Compute transaction size
        serialized_tx = tx.serialize()
    elif isinstance(tx, VersionedTransaction):
        # Manually serialize transaction
        serialized_tx = bytes(tx)
    else:
        return None

    # Compute size
    size_in_bytes = len(serialized_tx)
    return size_in_bytes

async def compute_transaction_fees(client, tx):
    # Check transaction type
    if isinstance(tx, Transaction):
        tx_message = tx.compile_message()
    elif isinstance(tx, VersionedTransaction):
        tx_message = tx.message
    else:
        return None

    # Compute fee from message
    response = await client.get_fee_for_message(tx_message)
    if response.value:
        return response.value
    else:
        print("Failed to fetch fee information")
        return None

async def send_transaction(provider, tx):
    return await provider.send(tx)




# ====================================================
# PRIVATE FUNCTIONS
# ====================================================

def _import_function(program_name: str, instruction_name: str):
    # Update absolute path in the root folder of the package
    program_root = Path(f"{anchor_base_path}/.anchor_files/{program_name}").resolve()

    if not program_root.exists():
        raise FileNotFoundError(f"The folder {program_root} does not exist. Check program name")

    # Path to the instruction
    module_path = program_root / "anchorpy_files" / "instructions" / f"{instruction_name}.py"

    if not module_path.exists():
        raise FileNotFoundError(f"The file {module_path} does not exist. Verify instruction name.")

    # Add program root to sys.path to enable relative imports
    if str(program_root) not in sys.path:
        sys.path.append(str(program_root))

    # Complete name of the module to import
    module_name = f"anchorpy_files.instructions.{instruction_name}"

    # Dynamic import of the module
    module = importlib.import_module(module_name)

    # Verify that the function exists
    if not hasattr(module, instruction_name):
        raise AttributeError(f"The module {module_name} does not contain the function {instruction_name}.")

    return getattr(module, instruction_name)

def _prepare_function(accounts, args, function):
    if accounts:
        if args:
            # Call instruction with given accounts and args
            ix = function(accounts=accounts, args=args)
        else:
            # Call instruction only with given accounts
            ix = function(accounts=accounts)
    else:
        if args:
            # Call instruction with given accounts and args
            ix = function(args=args)
        else:
            # Call instruction only with given accounts
            ix = function()

    return  ix