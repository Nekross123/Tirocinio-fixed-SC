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


import os
import json
import re
import toml
import importlib
import importlib.util
from based58 import b58encode
from solders.pubkey import Pubkey
from solana_module.solana_utils import solana_base_path, choose_wallet, load_keypair_from_file, selection_menu


anchor_base_path = f"{solana_base_path}/anchor_module"


# ====================================================
# PUBLIC FUNCTIONS
# ====================================================

def fetch_initialized_programs():
    path_to_explore = f"{anchor_base_path}/.anchor_files"
    programs_with_anchorpy_files = []

    # Check if the base directory exists before proceeding
    if not os.path.exists(path_to_explore):
        return programs_with_anchorpy_files

    # Iterate program folders
    for program in os.listdir(path_to_explore):
        program_path = os.path.join(path_to_explore, program)

        # Check if anchorpy_files folder is present
        if os.path.isdir(program_path):
            anchorpy_path = os.path.join(program_path, 'anchorpy_files')
            if os.path.isdir(anchorpy_path):
                programs_with_anchorpy_files.append(program)

    return programs_with_anchorpy_files

def fetch_program_instructions(idl):
    instructions = []
    # Extract instructions
    for instruction in idl['instructions']:
        instructions.append(instruction['name'])
    return instructions

def fetch_required_accounts(instruction, idl):
    # Find the instruction in the IDL
    instruction_dict = next(instr for instr in idl['instructions'] if instr['name'] == instruction)

    # Extract required accounts, excluding the systemProgram
    required_accounts = [_camel_to_snake(account['name']) for account in instruction_dict['accounts'] if account['name'] != 'systemProgram']

    return required_accounts

def choose_program():
    programs = fetch_initialized_programs()
    if not programs:
        print("No program has been initialized yet")
        return
    else:
        return selection_menu('program', programs)

def choose_instruction(idl):
    instructions = fetch_program_instructions(idl)
    if not instructions:
        print("No instruction found for this program")
        return
    else:
        return selection_menu('instruction', instructions)

def fetch_cluster(program_name):
    file_path = f"{anchor_base_path}/.anchor_files/{program_name}/anchor_environment/Anchor.toml"
    config = toml.load(file_path)
    cluster = config['provider']['cluster']
    if cluster == "Localnet" or cluster == "Devnet" or cluster == "Mainnet":
        return cluster, True
    else:
        print("The program hasn't been deployed with this toolchain. It won't be possible to send transaction.")
        print('Proceeding to compute transaction size and fees...')
        return 'Devnet', False

def load_idl(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)

def fetch_signer_accounts(instruction, idl):
    # Find the instruction in the IDL
    instruction_dict = next(instr for instr in idl['instructions'] if instr['name'] == instruction)

    # Extract signer accounts
    required_signer_accounts = [account['name'] for account in instruction_dict['accounts'] if account['isSigner']]

    return required_signer_accounts

def generate_pda(program_name, launched_from_utilities):
    pda_key = ''
    allowed_choices = ['1','2','0']
    if not launched_from_utilities:
        allowed_choices.append('3')

    repeat = True
    while repeat:
        choice = None
        while choice not in allowed_choices:
            print("How do you want to generate the PDA account?")
            print("1) Generate using seeds")
            print("2) Generate randomly")
            if not launched_from_utilities:
                print("3) Insert manually")
            print("0) Go back")

            choice = input()

            if choice == "1":
                pda_key, repeat = _choose_number_of_seed(program_name)
            elif choice == "2":
                random_bytes = os.urandom(32)
                base58_str = b58encode(random_bytes).decode("utf-8")
                pda_key = Pubkey.from_string(base58_str)
                print(f'Extracted pda is: {pda_key}')
                return pda_key
            elif choice == "3" and not launched_from_utilities:
                while len(pda_key) != 44:
                    print("Insert PDA key. It must be 44 characters long. (Insert 0 to go back)")
                    pda_key = input()
                    if pda_key == '0':
                        choice = None
                        break
                    else:
                        return Pubkey.from_string(pda_key)
            elif choice == "0":
                return None

    return pda_key

def fetch_args(instruction, idl):
    # Find instruction
    instruction_dict = next(instr for instr in idl['instructions'] if instr['name'] == instruction)

    # Extract args
    required_args = [{'name': _camel_to_snake(arg['name']), 'type': arg['type']} for arg in instruction_dict['args']]

    return required_args

def check_if_array(arg):
    if isinstance(arg['type'], dict) and 'array' in arg['type']:
        array_type = check_type(arg['type']['array'][0])
        array_length = arg['type']['array'][1]
        if array_type is None:
            return None, array_length
        return array_type, array_length
    else:
        return None, None

def check_type(type):
    if (type == "u8" or type == "u16" or type == "u32" or type == "u64" or type == "u128" or type == "u256"
            or type == "i8" or type == "i16" or type == "i32" or type == "i64" or type == "i128" or type == "i256"):
        return "integer"
    elif type == "bool":
        return "boolean"
    elif type == "f32" or type == "f64":
        return "floating point number"
    elif type == "string":
        return "string"
    else:
        return "Unsupported type"

def convert_type(type, value):
    try:
        if type == "integer":
            return int(value)
        elif type == "boolean":
            if value.lower() == 'true':
                return True
            elif value.lower() == 'false':
                return False
        elif type == "floating point number":
            return float(value)
        elif type == "string":
            return value
        else:
            raise ValueError("Unsupported type")
    except ValueError:
        return None




# ====================================================
# PRIVATE FUNCTIONS
# ====================================================

def _camel_to_snake(camel_str):
    # Use regex to add a _ before uppercase letters, excluded the first letter
    snake_str = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', camel_str)
    # Converto to lower case the whole string, leaving only the first letter as it is
    return snake_str[0] + snake_str[1:].lower()

def _choose_number_of_seed(program_name):
    pda_key = None
    repeat = True

    while repeat:
        print("How many seeds do you want to use? (Insert 0 to go back)")
        n_seeds = int(input())
        if n_seeds == 0:
            return None, True
        pda_key, repeat = _manage_seed_insertion(program_name, n_seeds)

    return pda_key, False

def _manage_seed_insertion(program_name, n_seeds):
    # Dynamically import program id
    module_path = f"{anchor_base_path}/.anchor_files/{program_name}/anchorpy_files/program_id.py"
    spec = importlib.util.spec_from_file_location("program_id", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    program_id = module.PROGRAM_ID

    allowed_choices = ['1','2','3','0']
    seeds = [None] * n_seeds

    i = 0
    while i < n_seeds:
        # Reset choice for next seed insertions
        choice = None
        while choice not in allowed_choices:
            print(f"How do you want to insert the seed n. {i+1}?")
            print("1) Generate using a wallet")
            print("2) Generate randomly")
            print("3) Insert manually")
            print("0) Go back")

            choice = input()

            if choice == "1":
                chosen_wallet = choose_wallet()
                if chosen_wallet is not None:
                    keypair = load_keypair_from_file(f"{solana_base_path}/solana_wallets/{chosen_wallet}")
                    seed = keypair.pubkey()
                    seeds[i] = bytes(seed)
                    i += 1

            elif choice == "2":
                seed = os.urandom(32)
                print(f'Extracted seed (hex): {seed.hex()}')
                seeds[i] = seed
                i += 1
            elif choice == "3":
                print("Insert seed (Insert 0 to go back)")
                print("Note: If entering a Pubkey, use the full base58 string (44 characters)")
                seed = input()
                if seed == '0':
                    return None, True
                
                # Check if the input looks like a Pubkey (44 characters, base58)
                if len(seed) == 44:
                    try:
                        # Try to parse as Pubkey and use its bytes
                        pubkey = Pubkey.from_string(seed)
                        seeds[i] = bytes(pubkey)
                        print(f"Parsed as Pubkey: {pubkey}")
                        i += 1
                    except Exception as e:
                        print(f"Invalid Pubkey format: {e}")
                        print("Treating as regular string instead...")
                        seeds[i] = seed.encode()
                        i += 1
                else:
                    # Treat as regular string
                    seeds[i] = seed.encode()
                    i += 1
            elif choice == "0":
                if i == 0:
                    return None, True
                else:
                    i -= 1

    try:
        pda_key = Pubkey.find_program_address(seeds, program_id)[0]
        print(f'Generated key is: {pda_key}')
        return pda_key, False
    except Exception as e:
        print(f"Error generating PDA: {e}")
        print("This combination of seeds doesn't produce a valid PDA. Try different seeds.")
        return None, True
