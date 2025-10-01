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

import importlib
import sys
from pathlib import Path
import toml
import shutil
import os
from solana_module.anchor_module.anchor_utils import fetch_initialized_programs, generate_pda, fetch_program_instructions, \
    fetch_args, load_idl, anchor_base_path, check_type, fetch_required_accounts, fetch_signer_accounts, choose_program, \
    choose_instruction, check_if_array
from solana_module.solana_utils import perform_program_closure


# ====================================================
# PUBLIC FUNCTIONS
# ====================================================

def get_initialized_programs():
    initialized_programs = fetch_initialized_programs()
    if len(initialized_programs) == 0:
        print("No program has been initialized yet.")
    else:
        print("Initialized programs:")
        for program in initialized_programs:
            print(f"- {program}")

def get_program_instructions():
    chosen_program = choose_program()
    if not chosen_program:
        return
    else:
        idl_file_path = f'{anchor_base_path}/.anchor_files/{chosen_program}/anchor_environment/target/idl/{chosen_program}.json'
        idl = load_idl(idl_file_path)
        instructions = fetch_program_instructions(idl)
        if instructions is None:
            print("No instructions available for this program.")
        else:
            print("Instructions:")
            for instruction in instructions:
                print(f"- {instruction}")

def get_instruction_accounts():
    chosen_program = choose_program()
    if not chosen_program:
        return
    else:
        idl_file_path = f'{anchor_base_path}/.anchor_files/{chosen_program}/anchor_environment/target/idl/{chosen_program}.json'
        idl = load_idl(idl_file_path)
        chosen_instruction = choose_instruction(idl)
        if not chosen_instruction:
            return
        else:
            accounts = fetch_required_accounts(chosen_instruction, idl)
            signer_accounts = fetch_signer_accounts(chosen_instruction, idl)
            if len(accounts) == 0:
                print("No accounts required by this instruction.")
            else:
                print("Accounts:")
                for account in accounts:
                    if account in signer_accounts:
                        print(f"- {account} (signer)")
                    else:
                        print(f"- {account}")

def get_instruction_args():
    chosen_program = choose_program()
    if not chosen_program:
        return
    else:
        idl_file_path = f'{anchor_base_path}/.anchor_files/{chosen_program}/anchor_environment/target/idl/{chosen_program}.json'
        idl = load_idl(idl_file_path)
        chosen_instruction = choose_instruction(idl)
        if not chosen_instruction:
            return
        else:
            args = fetch_args(chosen_instruction, idl)
            if len(args) == 0:
                print("No arguments required by this instruction.")
            else:
                print("Arguments:")
                for arg in args:
                    array_type, array_length = check_if_array(arg)
                    # If it's not an array
                    if array_type is None and array_length is None:
                        print(f"- {arg['name']} ({check_type(arg['type'])})")
                    # If it's an array of unsupported type
                    elif array_type is None and array_length is not None:
                        print(f"- {arg['name']} (array of unsupported type)")
                    # If it's a supported type array
                    else:
                        print(f"- {arg['name']} ({array_type} array of length {array_length})")

def choose_program_for_pda_generation():
    repeat = True
    while repeat:
        chosen_program = choose_program()
        if not chosen_program:
            return
        else:
            pda = generate_pda(chosen_program, True)
            if pda is not None:
                repeat = False

def close_anchor_program():
    chosen_program = choose_program()
    if not chosen_program:
        return

    cluster, wallet_name = _fetch_cluster_and_wallet(chosen_program)
    program_id = str(_get_program_id(chosen_program))

    # Confirmation phase
    allowed_choices = ['y', 'Y', 'n', 'N']
    choice = None
    while choice not in allowed_choices:
        print('Are you sure you want to close the program? (y/n)')
        choice = input()
        if choice == 'y' or choice == 'Y':
            result = perform_program_closure(program_id, cluster, wallet_name)
            if not result.stderr:
                _remove_initialized_program(chosen_program)
        elif choice == 'n' or choice == 'N':
            return
        else:
            print('Please insert a valid choice.')

def remove_anchor_program():
    chosen_program = choose_program()
    if not chosen_program:
        return

    # Confirmation phase
    allowed_choices = ['y', 'Y', 'n', 'N']
    choice = None
    while choice not in allowed_choices:
        print('Are you sure you want to remove the program from the toolchain? (y/n)')
        choice = input()
        if choice == 'y' or choice == 'Y':
            _remove_initialized_program(chosen_program)
        elif choice == 'n' or choice == 'N':
            return
        else:
            print('Please insert a valid choice.')




# ====================================================
# PRIVATE FUNCTIONS
# ====================================================

def _fetch_cluster_and_wallet(program_name):
    file_path = f"{anchor_base_path}/.anchor_files/{program_name}/anchor_environment/Anchor.toml"
    config = toml.load(file_path)

    # Edit values
    cluster = config['provider']['cluster']
    wallet_path = config['provider']['wallet']
    if wallet_path is None:
        return None, None
    wallet_name = wallet_path.removeprefix('../../../../solana_wallets/')
    return cluster, wallet_name

def _get_program_id(program_name):
    # Update absolute path in the root folder of the package
    program_root = Path(f"{anchor_base_path}/.anchor_files/{program_name}").resolve()

    if not program_root.exists():
        raise FileNotFoundError(f"The folder {program_root} does not exist. Check program name")

    # Path to program id
    module_path = program_root / "anchorpy_files" / "program_id.py"

    if not module_path.exists():
        raise FileNotFoundError(f"The file {module_path} does not exist. Verify instruction name.")

    # Add program root to sys.path to enable relative imports
    if str(program_root) not in sys.path:
        sys.path.append(str(program_root))

    # Complete name of the module to import
    module_name = f"anchorpy_files.program_id"

    # Dynamic import of the module
    module = importlib.import_module(module_name)

    # Verify that the function exists
    if not hasattr(module, 'PROGRAM_ID'):
        raise AttributeError(f"The module {module_name} does not contain the program id.")

    return getattr(module, "PROGRAM_ID")

def _remove_initialized_program(program_name):
    folder_to_remove = f"{anchor_base_path}/.anchor_files/{program_name}"

    if os.path.exists(folder_to_remove):  # Check if folder exists
        shutil.rmtree(folder_to_remove)
        print("Program removed from toolchain.")
    else:
        print("Program folder does not exists.")
