 # MIT License
#
# Copyright (c) 2025 Manuel Boi, Palumbo Lorenzo, Piras Mauro - Università degli Studi di Cagliari
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
from Solana_module.solana_module.solana_utils import solana_base_path, choose_wallet, load_keypair_from_file, selection_menu
from solana.rpc.async_api import AsyncClient


anchor_base_path = os.path.dirname(os.path.abspath(__file__))



def fetch_initialized_programs():
    """Return the list of Anchor programs we already initialized.

    Basically I just scan the .anchor_files folder and collect programs
    that have the generated anchorpy client (anchorpy_files). If that exists,
    we can interact with the program from Python.
    """
    path_to_explore = f"{anchor_base_path}/.anchor_files"
    programs_with_anchorpy_files = []

    if not os.path.exists(path_to_explore):
        return programs_with_anchorpy_files

    for program in os.listdir(path_to_explore):
        program_path = os.path.join(path_to_explore, program)

        if os.path.isdir(program_path):
            anchorpy_path = os.path.join(program_path, 'anchorpy_files')
            if os.path.isdir(anchorpy_path):
                programs_with_anchorpy_files.append(program)

    return programs_with_anchorpy_files

def fetch_program_instructions(idl):
    """Extract instruction names from an IDL object.

    The IDL format stores a list of instruction definitions; here I only
    care about their names because that’s what we show in menus.
    """
    instructions = []
    for instruction in idl['instructions']:
        instructions.append(instruction['name'])
    return instructions

def fetch_required_accounts(instruction, idl):
    """Return account names required by a given instruction (snake_case).

    Note: I skip 'systemProgram' on purpose because it’s implicit on Solana,
    and we usually don’t ask the user to pick it manually.
    """
    instruction_dict = next((instr for instr in idl['instructions'] if instr['name'] == instruction), None)
    if instruction_dict is None:
        print(f"Istruzione '{instruction}' non trovata nell'IDL.")
        st.info(f"Istruzione '{instruction}' non trovata nell'IDL.")
        return []
    required_accounts = [_camel_to_snake(account['name']) for account in instruction_dict['accounts'] if account['name'] != 'systemProgram']
    return required_accounts

def choose_program():
    """Ask the user to pick one of the initialized programs (simple menu)."""
    programs = fetch_initialized_programs()
    if not programs:
        print("No program has been initialized yet")
        return
    else:
        return selection_menu('program', programs)

def choose_instruction(idl):
    """Ask the user to pick one instruction from the provided IDL."""
    instructions = fetch_program_instructions(idl)
    if not instructions:
        print("No instruction found for this program")
        return
    else:
        return selection_menu('instruction', instructions)

def fetch_cluster(program_name):
    """Read the Anchor.toml of a program to figure out the chosen cluster.

    If the cluster isn’t one of Localnet/Devnet/Mainnet, it means we didn’t
    deploy with this toolchain, so I fall back to Devnet and mark is_deployed=False
    to avoid sending transactions by accident.
    """
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
    """Load an IDL JSON file from disk and return it as a dict."""
    with open(file_path, 'r') as f:
        return json.load(f)

def fetch_signer_accounts(instruction, idl):
    """Return the list of accounts that must sign for this instruction."""
    instruction_dict = next(instr for instr in idl['instructions'] if instr['name'] == instruction)
    required_signer_accounts = [account['name'] for account in instruction_dict['accounts'] if account['isSigner']]

    return required_signer_accounts

def generate_pda(program_name, launched_from_utilities):
    """Interactive PDA generation helper.

    Options:
    - seeds: derive PDA using a list of seeds
    - random: generate a random base58 string and treat it like an address
    - manual: paste a base58 address yourself (only enabled from the flow that needs it)
    """
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
    """Return the list of args (name/type) for an instruction, using snake_case names."""
    # Find instruction
    instruction_dict = next(instr for instr in idl['instructions'] if instr['name'] == instruction)

    # Extract args
    required_args = [{'name': _camel_to_snake(arg['name']), 'type': arg['type']} for arg in instruction_dict['args']]

    return required_args

def check_if_array(arg):
    """Detect if an arg is a fixed-size array and return (element_type, length).

    If the element type is unsupported, I still return the length so callers
    can validate sizes even when they can’t parse values.
    """
    if isinstance(arg['type'], dict) and 'array' in arg['type']:
        array_type = check_type(arg['type']['array'][0])
        array_length = arg['type']['array'][1]
        if array_type is None:
            return None, array_length
        return array_type, array_length
    else:
        return None, None
    
def check_if_vec(arg):
    """Detect if an arg is a Vec and return the element type (or None)."""
    if isinstance(arg['type'], dict) and 'vec' in arg['type']:
        vec_type = check_type(arg['type']['vec'])
        if vec_type is None:
            return None
        return vec_type
    else:
        return None

def check_if_bytes_type(arg):
    """Small helper to spot raw bytes parameters."""
    if arg == "bytes":
            return True

def check_type(type):
    """Map IDL primitive types into a friendly label I use in prompts.

    Returns one of: integer | boolean | floating point number | string | bytes
    or an "Unsupported type" message that also echoes the original type.
    """
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
    """Parse a string value into the expected Python type based on our labels.

    This is used to convert user input (from CLI/Streamlit) into actual
    integers/floats/bools, or keep strings/bytes as needed.
    """
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
    """Prompt to manually type a token account address (44 chars)."""

    return input("Insert the token account(must be 44 characters long)")


def bind_actors(trace_name):
    """Bind each actor from a JSON trace to a wallet file.

    I look into solana_wallets and try to assign the first N wallet files
    to the N actors in the trace. If there aren’t enough files, I explain why.
    """

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
    """Return the 'args' dict from a trace entry."""
    return trace["args"]


def find_sol_arg(trace):
    """Return the 'solana' section from a trace entry."""
    return trace["solana"]

def build_complete_dict(actors , sol_args , args):
    """Merge actors + solana + args into one dictionary.

    Handy to have a single lookup table when building accounts and parameters.
    """
    

     
    return actors | sol_args | args

def is_pda(entry):
    """Best-effort check to see if a string looks like a PDA address.

    Heuristic:
    - If it ends with .json -> it’s a wallet file, not a PDA
    - If it decodes to a Pubkey and is on-curve -> it’s a wallet (not PDA)
    - Otherwise, treat it as PDA.
    """
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
    """Best-effort check to see if a string is a wallet (file or on-curve key)."""
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
    """Auto-fill PDAs in a merged dict using rules in the JSON trace.

    Supports three modes for each PDA-shaped entry:
    - opt == 's': derive with seeds (strings, wallet pubkeys, or PDA bytes)
    - opt == 'r': generate a random-like address
    - opt == 'p': use a provided base58 address
    """
    
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
                                    # Se il seed è un PDA (stringa di 44 caratteri), convertilo in Pubkey
                                    if isinstance(seed, str) and len(seed) == 44:
                                        pda_pubkey = Pubkey.from_string(seed)
                                        seeds[i] = bytes(pda_pubkey)
                                    else:
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
    """Figure out the network by looking at the RPC endpoint URL."""
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
    """Convert CamelCase (from IDL) to snake_case (friendlier for Python CLI)."""
    # Use regex to add a _ before uppercase letters, excluded the first letter
    snake_str = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', camel_str)
    # Converto to lower case the whole string, leaving only the first letter as it is
    return snake_str[0] + snake_str[1:].lower()

def _choose_number_of_seed(program_name):
    """Ask how many seeds to use for PDA derivation and then collect them."""
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
    """Interactively collect each seed and build the PDA using program_id.

    Critical bit: I dynamically import program_id from the generated folder,
    because it’s specific to each initialized Anchor project.
    """
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


def upload_anchor_program():
    """UI to upload a Rust (.rs) program file and place it under anchor_programs.

    I also sanity-check that the file likely contains an Anchor program by
    searching for a declare_id!(...) macro, just to help the user.
    """

    st.subheader("📦 Upload Solana Program")

    uploaded_file = st.file_uploader(
        "Drag and drop your Solana program file (.rs) here",
        type=['rs'],
        help="Upload a Rust source file for your Solana program"
    )

    if uploaded_file is not None:
        try:
            # Legge il contenuto del file
            file_content = uploaded_file.read().decode("utf-8")

            # Facoltativo: controlla se sembra un file Rust di Anchor
            if not re.search(r"declare_id!\(", file_content):
                st.warning("⚠️ Il file non contiene una dichiarazione `declare_id!()`. Verifica che sia un programma Anchor valido.")

            # Percorso base per i programmi Anchor
            programs_folder = os.path.join(anchor_base_path, "anchor_programs")
            os.makedirs(programs_folder, exist_ok=True)

            file_path = os.path.join(programs_folder, uploaded_file.name)

            # Salva il file nel percorso desiderato
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(file_content)

            st.success(f"✅ Program `{uploaded_file.name}` uploaded successfully!")
            st.info(f"📁 Saved to: `anchor_programs/{uploaded_file.name}`")

        except UnicodeDecodeError:
            st.error("❌ Errore di codifica. Assicurati che il file sia in formato testo UTF-8.")
        except Exception as e:
            st.error(f"❌ Error uploading file: {str(e)}")
