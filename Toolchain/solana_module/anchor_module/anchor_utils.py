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
import pandas as pd
import streamlit as st
import os
import json
import re
import toml
import importlib
import importlib.util
from based58 import b58encode
from solders.pubkey import Pubkey
from Toolchain.solana_module.solana_utils import solana_base_path, choose_wallet, load_keypair_from_file, selection_menu
from solana.rpc.async_api import AsyncClient


anchor_base_path = os.path.dirname(os.path.abspath(__file__))


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
    instruction_dict = next((instr for instr in idl['instructions'] if instr['name'] == instruction), None)
    if instruction_dict is None:
        print(f"Istruzione '{instruction}' non trovata nell'IDL.")
        st.info(f"Istruzione '{instruction}' non trovata nell'IDL.")
        return []
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
                print("to find the seeds needed for the generation of the pda search an array named seeds in the smart contract")
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
    
def check_if_vec(arg):
    if isinstance(arg['type'], dict) and 'vec' in arg['type']:
        vec_type = check_type(arg['type']['vec'])
        if vec_type is None:
            return None
        return vec_type
    else:
        return None

def check_if_bytes_type(arg):
    if arg == "bytes":
            return True

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
    elif type == "bytes":
        return "bytes"
    else:
        return f"Unsupported type\nThe type you are trying to use is -> {type}\n"

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
    
def input_token_account_manually():

    return input("Insert the token account(must be 44 characters long)")


def bind_actors(trace_name):

    #this function binds each actor with a wallet
    with open(f"{anchor_base_path}/execution_traces/{trace_name}", "r") as f:
        data = json.load(f)

    association = dict()
    trace_actors  = data["trace_actors"]
    wallets_path = f'{solana_base_path}/solana_wallets'
    
    # Filter only .json wallet files
    all_files = os.listdir(wallets_path)
    wallets = [f for f in all_files if f.endswith('.json') and os.path.isfile(os.path.join(wallets_path, f))]
    
    if len(wallets) < len(trace_actors):
        print(f"Not enough wallet files! Found {len(wallets)} wallets but need {len(trace_actors)} for actors: {trace_actors}")
        print(f"Available wallets: {wallets}")
        return {}

    try:
        for j in range(len(trace_actors)):
            association[trace_actors[j]] = wallets[j]
            print(f"  Actor '{trace_actors[j]}' -> Wallet '{wallets[j]}'")
    except IndexError:
        print("The wallets are less than the actors, impossible to associate.\nCreate more wallets or reduce the number of actors")
        return {}

    print("All the actors have been associated")
    return association

def find_args(trace):
    return trace["args"]


def find_sol_arg(trace):
    return trace["solana"]

#this function build the complete dictionary of whatever you need for the contract form the json trace file
def build_complete_dict(actors , sol_args , args):
    

     
    return actors | sol_args | args

def is_pda(entry):
    # Caso 1: file locale JSON
    if entry.lower().endswith(".json"):
        return False

    # Caso 2: tentativo di address
    try:
        pubkey = Pubkey.from_string(entry)
        return False if pubkey.is_on_curve() else True
    except ValueError:
        print("invalid address or wallet")

def is_wallet(entry):
    # Caso 1: file locale JSON
    if entry.lower().endswith(".json"):
        return True  # è un wallet file

    # Caso 2: tentativo di address
    try:
        pubkey = Pubkey.from_string(entry)
        return pubkey.is_on_curve()  # True = wallet address, False = PDA
    except ValueError:
        # Non è né un file né un address valido
        return False


def generate_pda_automatically(actors ,program_name ,sol_args , args):
    


     
    complete_dict = build_complete_dict(actors , sol_args , args)





    for arg in complete_dict:
        value = complete_dict[arg]

        

        if isinstance(value, dict):

            
            param_list = []


            
            #takes the parameters of a pda  , the option for the type are  (s, r, p) and then there are the parameters for the seeds,
            #s -> seeds
            #r -> random you can omit the param list if you choose this option
            #p -> pda (you have to put the pda key in the param list)
            try:
                opt = value["opt"]
            except KeyError:
                    print(f'No opt found ,you have to put one of the three options (s, r, p) in order to generate a PDA')


            try:
                param_list = value["param"]

            except KeyError:
                #this is useful in case you choose the random option and do not want to insert the param list , you can choose to put an empty list anyway
                print(f'No param found , you choose to generate a random PDA')
                pass
            
            n_seeds = len(param_list)
            
            pda_key = None

            if opt == "s":
                        
                        


                        module_path = f"{anchor_base_path}/.anchor_files/{program_name}/anchorpy_files/program_id.py"
                        spec = importlib.util.spec_from_file_location("program_id", module_path)
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        program_id = module.PROGRAM_ID

                        seeds = [None] * n_seeds
                        i = 0
                        for param in param_list:
                                
                                
                                
                                

                                if param not in complete_dict:
                                    seed = param
                                    seeds[i] = seed.encode()
                                    i += 1 
                                elif is_wallet(complete_dict[param]):
                                        chosen_wallet = complete_dict[param]
                                        if chosen_wallet is not None:
                                            keypair = load_keypair_from_file(f"{solana_base_path}/solana_wallets/{chosen_wallet}")
                                            seed = keypair.pubkey()
                                            seeds[i] = bytes(seed)
                                            i += 1

                                else:
                                    seed = complete_dict[param]
                                    seeds[i] = seed.encode()
                                    i += 1 


                        

                        pda_key = Pubkey.find_program_address(seeds, program_id)[0]
                        st.info(f'Generated key is: {pda_key}')
                        complete_dict[arg] = str(pda_key)

            elif opt == "r":

                        
                        random_bytes = os.urandom(32)
                        base58_str = b58encode(random_bytes).decode("utf-8")
                        pda_key = Pubkey.from_string(base58_str)
                        print(f'Extracted pda is: {pda_key}')
                       
            elif opt == "p":
                

                pda_key = param_list[0]
                if len(pda_key) == 44:
                        
                        pda_key =  Pubkey.from_string(pda_key)
                        print(f'Extracted pda is: {pda_key}')
                else :
                      print("The PDA key must be 44 characters long")

    
    
    return complete_dict

def get_network_from_client(client):
    """
    Determina la rete basandosi sull'endpoint del client
    """
    endpoint = client._provider.endpoint_uri
    
    if "devnet" in endpoint.lower():
        return "devnet"
    elif "testnet" in endpoint.lower():
        return "testnet"
    elif "mainnet" in endpoint.lower() or "api.mainnet" in endpoint.lower():
        return "mainnet-beta"
    elif "localhost" in endpoint or "127.0.0.1" in endpoint or "8899" in endpoint:
        return "localnet"
    else:
        return "unknown"

    




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
                seed = input()
                if seed == '0':
                    return None, True
                seeds[i] = seed.encode()
                i += 1
            elif choice == "0":
                if i == 0:
                    return None, True
                else:
                    i -= 1

    pda_key = Pubkey.find_program_address(seeds, program_id)[0]
    print(f'Generated key is: {pda_key}')
    return pda_key, False
