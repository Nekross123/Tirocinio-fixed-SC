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
import toml
import re
import os
import platform
from solana_module.solana_utils import choose_wallet, run_command, choose_cluster
from solana_module.anchor_module.anchor_utils import anchor_base_path, load_idl


# ====================================================
# PUBLIC FUNCTIONS
# ====================================================

def compile_programs():
    program_id = None
    programs_path = f"{anchor_base_path}/anchor_programs" # Path where anchor programs are placed

    operating_system = platform.system()

    # Read programs
    file_names, programs = _read_rs_files(programs_path)

    if not file_names:
        print('No programs to compile in anchor_programs folder.')
        return

    # For each program
    for file_name,program in zip(file_names, programs):
        print(f"Compiling program: {file_name}")
        file_name_without_extension = file_name.removesuffix(".rs") # Get filename without .rs extension

        # Compiling phase
        done, program_id = _compile_program(file_name_without_extension, operating_system, program) # Compile program
        if not done:
            return

        result =_convert_idl_for_anchorpy(file_name_without_extension)
        if result is None:
            return

        # Anchorpy initialization phase
        if program_id: # If deploy succeed, initialize anchorpy
            _initialize_anchorpy(file_name_without_extension, program_id, operating_system)

        # Deploying phase
        allowed_choice = ['y', 'n', 'Y', 'N']
        choice = None
        while choice not in allowed_choice:
            print("Deploy compiled program? (y/n):")
            choice = input()
            if choice == "y" or choice == "Y":
                _deploy_program(file_name_without_extension, operating_system)
            elif choice == "n" or choice == "N":
                return
            else:
                print('Please insert a valid choice.')




# ====================================================
# PRIVATE FUNCTIONS
# ====================================================


# ====================================================
# Compiling phase functions
# ====================================================

def _read_rs_files(programs_path):
    # Check if the folder exists
    if not os.path.isdir(programs_path):
        print(f"The path '{programs_path}' does not exist.")
    else:
        # Get all .rs in the programs path
        file_names = [f for f in os.listdir(programs_path) if f.endswith(".rs")]

        # Read content of each file and store it in anchor_programs list
        anchor_programs = []
        for file_name in file_names:
            full_path = os.path.join(programs_path, file_name)
            with open(full_path, "r", encoding="utf-8") as f:
                anchor_programs.append(f.read())

        return file_names, anchor_programs


#this function adds the feature init-if-needed in the Cargo.toml file 
def addInitIfNeeded(cargo_path):

    try:
            # We modify the files , only if it exists
            if os.path.exists(cargo_path):
                cargo_config = toml.load(cargo_path)
                
                # Modifica la dipendenza anchor-lang per includere la feature init-if-needed
                if 'dependencies' in cargo_config and 'anchor-lang' in cargo_config['dependencies']:
                    if isinstance(cargo_config['dependencies']['anchor-lang'], dict):
                        if 'features' in cargo_config['dependencies']['anchor-lang']:
                            if 'init-if-needed' not in cargo_config['dependencies']['anchor-lang']['features']:
                                cargo_config['dependencies']['anchor-lang']['features'].append('init-if-needed')
                        else:
                            cargo_config['dependencies']['anchor-lang']['features'] = ['init-if-needed']
                    else:
                        version = cargo_config['dependencies']['anchor-lang']
                        cargo_config['dependencies']['anchor-lang'] = {
                            'version': version,
                            'features': ['init-if-needed']
                        }
                
                # Saves changes in the Cargo.toml file 
                with open(cargo_path, 'w') as f:
                    toml.dump(cargo_config, f)
                
                print(f"Cargo.toml creato/modificato con feature init-if-needed")
            else:
                print(f"Errore: Cargo.toml non trovato in {cargo_path}")
    except Exception as e:
            print(f"Errore durante la modifica di Cargo.toml: {e}")


def _compile_program(program_name, operating_system, program):
    # Initialization phase
    done = _perform_anchor_initialization(program_name, operating_system)
    if not done:
        return False
    else:
        # After initialization, create/modify the Cargo.toml file with the desired feature
        cargo_toml_path = f"{anchor_base_path}/.anchor_files/{program_name}/anchor_environment/programs/anchor_environment/Cargo.toml"
        addInitIfNeeded(cargo_toml_path)
        
        
    

    # Build phase
    done, program_id = _perform_anchor_build(program_name, program, operating_system)
    if not done:
        return False

    return True, program_id

def _perform_anchor_initialization(program_name, operating_system):
    # Define Anchor initialization commands to be executed
    initialization_commands = [
        f"mkdir -p {anchor_base_path}/.anchor_files/{program_name}", # Create folder for new program
        f"cd {anchor_base_path}/.anchor_files/{program_name}",  # Change directory to new folder
        "anchor init anchor_environment",  # Initialize anchor environment
    ]

    # Merge commands with '&&' to execute them on the same shell
    initialization_concatenated_command = " && ".join(initialization_commands)

    # Run Anchor initialization
    return _run_anchor_initialization_commands(operating_system, initialization_concatenated_command)

    

def _perform_anchor_build(program_name, program, operating_system):
    # Define Anchor build commands to be executed
    build_commands = [
        f"cd {anchor_base_path}/.anchor_files/{program_name}/anchor_environment",  # Change directory to new anchor environment
        "cargo update -p bytemuck_derive@1.9.3", # bytemyck_derive is now 1.9.2, but can change frequently
        "anchor build"  # Build program
    ]

    # Merge commands with '&&' to execute them on the same shell
    build_concatenated_command = " && ".join(build_commands)

    # Run Anchor build
    return _run_anchor_build_commands(program_name, program, operating_system, build_concatenated_command)

def _run_anchor_initialization_commands(operating_system, initialization_concatenated_command):
    # Initialize Anchor project
    print("Initializing Anchor project...")
    result = run_command(operating_system, initialization_concatenated_command)

    # Error checks
    if result is None:
        print("Unsupported operating system.")
        return False
    # If there are error while initializing Anchor project, print them
    elif result.stderr:
        print(result.stderr)

    return True # Sometimes stderr is just a warning, so we return true anyway

def _run_anchor_build_commands(program_name, program, operating_system, build_concatenated_command):
    print("Building Anchor program, this may take a while... Please be patient.")
    program_id = _write_program_in_lib_rs(program_name, program)
    result = run_command(operating_system, build_concatenated_command)
    if result is None:
        print("Unsupported operating system.")
        return False
    elif '-Znext' in result.stderr:
        # try by imposing cargo version 3
        _impose_cargo_lock_version(program_name)
        result = run_command(operating_system, build_concatenated_command)
        if result.stderr:
            print(result.stderr)

    return True, program_id # Sometimes stderr is just a warning, so we return true anyway

def _write_program_in_lib_rs(program_name, program):
    program, program_id = _update_program_id(program_name, program)
    lib_rs_path = f"{anchor_base_path}/.anchor_files/{program_name}/anchor_environment/programs/anchor_environment/src/lib.rs"
    with open(lib_rs_path, 'w') as file:
        file.write(program)
    return program_id

def _update_program_id(program_name, program):
    file_path = f"{anchor_base_path}/.anchor_files/{program_name}/anchor_environment/programs/anchor_environment/src/lib.rs"

    # Read program id generated by Anchor
    with open(file_path, 'r') as file:
        content = file.read()
        match = re.search(r'declare_id!\s*\(\s*"([^"]+)"\s*\)\s*;', content)
        if match:
            new_program_id = match.group(1)
        else:
            raise ValueError("Program ID not found in file")

    # Substitute program id in the file
    program = re.sub(r'declare_id!\s*\(\s*"([^"]+)"\s*\)\s*;', f'declare_id!("{new_program_id}");', program)
    return program, new_program_id

def _impose_cargo_lock_version(program_name):
    file_path = f"{anchor_base_path}/.anchor_files/{program_name}/anchor_environment/Cargo.lock"
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    with open(file_path, 'w', encoding='utf-8') as file:
        for line in lines:
            # Substitute each value of version with 3
            line = re.sub(r'^version = \d+', 'version = 3', line)
            file.write(line)

def _convert_idl_for_anchorpy(program_name):
    idl_file_path = f'{anchor_base_path}/.anchor_files/{program_name}/anchor_environment/target/idl/{program_name}.json'

    if not os.path.exists(idl_file_path):
        print('Error during build')
        return

    idl_31 = load_idl(idl_file_path)

    idl_29 = {
        "version": idl_31["metadata"]["version"],
        "name": idl_31["metadata"]["name"],
        "instructions": [],
        "accounts": [],
        "errors": idl_31.get("errors", [])
    }

    found_defined_types = set()
    
    def fix_defined_types(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == "type":
                    if v == "pubkey":
                        obj[k] = "publicKey"
                    elif isinstance(v, dict) and "defined" in v:
                        defined_type = v["defined"]
                        if isinstance(defined_type, dict):
                            defined_type = defined_type.get("name")
                        if defined_type:
                            found_defined_types.add(defined_type)
                            obj[k] = {"defined": defined_type}
                    else:
                        obj[k] = fix_defined_types(v)
                else:
                    obj[k] = fix_defined_types(v)
        elif isinstance(obj, list):
            obj = [fix_defined_types(i) for i in obj]
        return obj



    # Convert instructions
    for instruction in idl_31["instructions"]:
        converted_instruction = {
            "name": instruction["name"],
            "accounts": [],
            "args": fix_defined_types(instruction.get("args", []))
        }

        for account in instruction["accounts"]:
            converted_account = {
                "name": _snake_to_camel(account["name"]),
                "isMut": account.get("writable", False),
                "isSigner": account.get("signer", False)
            }
            converted_instruction["accounts"].append(converted_account)

        idl_29["instructions"].append(converted_instruction)

    # Convert accounts
    type_definitions = {t["name"]: t["type"] for t in idl_31.get("types", [])}

    for account in idl_31.get("accounts", []):
        account_name = account["name"]
        account_type = type_definitions.get(account_name, {})
        fixed_type = fix_defined_types(account_type)

        if "fields" in fixed_type:
            fixed_type["fields"] = fix_defined_types(fixed_type["fields"])

        idl_29["accounts"].append({
            "name": account_name,
            "type": fixed_type
        })


    # Add types (with dummy variants if needed)
    idl_29["types"] = []
    for t in idl_31.get("types", []):
        fixed_type = fix_defined_types(t["type"])
        idl_29["types"].append({
            "name": t["name"],
            "type": fixed_type
        })

    existing_type_names = {t["name"] for t in idl_29["types"]}
    for type_name in found_defined_types:
        if type_name not in existing_type_names:
            idl_29["types"].append({
                "name": type_name,
                "type": {
                    "kind": "enum",
                    "variants": [
                        { "name": "Variant1" },
                        { "name": "Variant2" }
                    ]
                }
            })

    # Save corrected file
    with open(idl_file_path, 'w') as file:
        file.write(json.dumps(idl_29, indent=2))

    return True



def _snake_to_camel(snake_str):
    return re.sub(r'_([a-z])', lambda match: match.group(1).upper(), snake_str)


# ====================================================
# Anchorpy initialization phase functions
# ====================================================

def _initialize_anchorpy(program_name, program_id, operating_system):
    idl_path = f"{anchor_base_path}/.anchor_files/{program_name}/anchor_environment/target/idl/{program_name}.json"
    output_directory = f"{anchor_base_path}/.anchor_files/{program_name}/anchorpy_files/"
    anchorpy_initialization_command = f"anchorpy client-gen {idl_path} {output_directory} --program-id {program_id}"

    _run_initializing_anchorpy_commands(operating_system, anchorpy_initialization_command)

def _run_initializing_anchorpy_commands(operating_system, anchorpy_initialization_command):
    print("Initializing anchorpy...")
    result = run_command(operating_system, anchorpy_initialization_command)
    if result is None:
        print("Unsupported operating system.")
    elif result.stderr:
        print(result.stderr)
    else:
        print("Anchorpy initialized successfully")


# ====================================================
# Deploying phase functions
# ====================================================

def _deploy_program(program_name, operating_system):
    wallet_name = choose_wallet()
    if wallet_name is None:
        return

    # Manage cluster choice
    cluster = choose_cluster()

    # Modify generated file to set chosen cluster
    _modify_cluster_wallet(program_name, cluster, wallet_name)

    # Define deploy commands to be executed
    deploy_commands = [
        f"cd {anchor_base_path}/.anchor_files/{program_name}/anchor_environment/",  # Change directory to environment folder
        "anchor deploy",  # Deploy program
    ]

    # Merge commands with '&&' to execute them on the same shell
    deploy_concatenated_command = " && ".join(deploy_commands)

    # Run Anchor deploy
    _run_deploying_commands(operating_system, deploy_concatenated_command)

def _modify_cluster_wallet(program_name, cluster, wallet_name):
    file_path = f"{anchor_base_path}/.anchor_files/{program_name}/anchor_environment/Anchor.toml"
    config = toml.load(file_path)

    # Edit values
    config['provider']['cluster'] = cluster
    config['provider']['wallet'] = f"../../../../solana_wallets/{wallet_name}"

    # Save modifications
    with open(file_path, 'w') as file:
        toml.dump(config, file)

def _run_deploying_commands(operating_system, deploy_concatenated_command):
    print("Deploying program...")
    result = run_command(operating_system, deploy_concatenated_command)
    if result is None:
        print("Unsupported operating system.")
        return None
    elif result.stderr:
        print(result.stderr)
        return None
    else:
        program_id, signature = _get_deploy_details(result.stdout)
        print("Deploy success")
        print(f"Program ID: {program_id}")
        print(f"Signature: {signature}")
        return program_id

def _get_deploy_details(output):
    # RegEx to find Program ID and signature
    program_id_pattern = r"Program Id: (\S+)"
    signature_pattern = r"Signature: (\S+)"

    # Find Program ID
    program_id_match = re.search(program_id_pattern, output)
    program_id = program_id_match.group(1) if program_id_match else None

    # Find Signature
    signature_match = re.search(signature_pattern, output)
    signature = signature_match.group(1) if signature_match else None

    return program_id, signature
