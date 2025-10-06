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
from Toolchain.solana_module.solana_utils import choose_wallet, run_command, choose_cluster
from Toolchain.solana_module.anchor_module.anchor_utils import anchor_base_path, load_idl


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

# This function analyzes the Rust program code and automatically detects which external 
# dependencies are needed based on the use statements and imports.
def _detect_dependencies_from_code(program_code):
    """Detect dependencies needed based on imports in the Rust code"""
    dependencies = {}
    
    # Check for pyth_sdk_solana
    if 'use pyth_sdk_solana' in program_code or 'pyth_sdk_solana::' in program_code:
        dependencies['pyth-sdk-solana'] = "0.10"
    
    # Check for switchboard
    if 'use switchboard_' in program_code or 'switchboard_' in program_code:
        dependencies['switchboard-solana'] = "0.29"
    
    # Check for spl-token (but don't add it directly if anchor-spl is present)
    if 'use spl_token' in program_code or 'spl_token::' in program_code:
        dependencies['spl-token'] = "7.0"
    
    # Check for spl-associated-token-account
    if 'use spl_associated_token_account' in program_code or 'spl_associated_token_account::' in program_code:
        dependencies['spl-associated-token-account'] = "4.0"
    
    # Check for mpl-token-metadata
    if 'use mpl_token_metadata' in program_code or 'mpl_token_metadata::' in program_code:
        dependencies['mpl-token-metadata'] = "4.1"
    
    return dependencies


def _check_for_anchor_spl_usage(program_code):
    """Check if the program uses anchor-spl features"""
    anchor_spl_indicators = [
        'use anchor_spl',
        'anchor_spl::',
        'Token,',
        'TokenAccount,',
        'AssociatedToken',
        'SetAuthority',
        'Transfer',
        'token::',
        'associated_token::'
    ]
    
    return any(indicator in program_code for indicator in anchor_spl_indicators)


#this function adds the feature init-if-needed in the Cargo.toml file and other dependencies
# Updated  function:
# Renamed to be more descriptive of its expanded purpose
# Now takes the program code as a parameter
# Automatically adds detected dependencies to Cargo.toml
# Currently detects: pyth-sdk-solana, switchboard-solana,
# spl-token, spl-associated-token-account, and mpl-token-metadata
def addInitIfNeeded(cargo_path, program_code):
    try:
        # We modify the files, only if it exists
        if os.path.exists(cargo_path):
            cargo_config = toml.load(cargo_path)
            
            # Ensure dependencies section exists
            if 'dependencies' not in cargo_config:
                cargo_config['dependencies'] = {}
            
            # Check if anchor-spl is needed
            needs_anchor_spl = _check_for_anchor_spl_usage(program_code)
            
            # Handle anchor-lang dependency - check if it exists first
            if 'anchor-lang' in cargo_config['dependencies']:
                if isinstance(cargo_config['dependencies']['anchor-lang'], dict):
                    # Already a dict with version and features
                    if 'features' in cargo_config['dependencies']['anchor-lang']:
                        if 'init-if-needed' not in cargo_config['dependencies']['anchor-lang']['features']:
                            cargo_config['dependencies']['anchor-lang']['features'].append('init-if-needed')
                    else:
                        cargo_config['dependencies']['anchor-lang']['features'] = ['init-if-needed']
                else:
                    # It's just a version string, convert to dict
                    version = cargo_config['dependencies']['anchor-lang']
                    cargo_config['dependencies']['anchor-lang'] = {
                        'version': version,
                        'features': ['init-if-needed']
                    }
            else:
                # anchor-lang doesn't exist, add it
                cargo_config['dependencies']['anchor-lang'] = {
                    'version': "0.31.1",
                    'features': ['init-if-needed']
                }
                print("Added anchor-lang dependency with init-if-needed feature")
            
            # Add anchor-spl if needed and not already present
            if needs_anchor_spl:
                if 'anchor-spl' not in cargo_config['dependencies']:
                    cargo_config['dependencies']['anchor-spl'] = "0.31.1"
                    print(f"Added dependency: anchor-spl = \"0.31.1\"")
                
                # Ensure features section exists
                if 'features' not in cargo_config:
                    cargo_config['features'] = {}
                
                # Handle idl-build feature
                if 'idl-build' in cargo_config['features']:
                    # Ensure it's a list
                    if not isinstance(cargo_config['features']['idl-build'], list):
                        cargo_config['features']['idl-build'] = []
                    
                    # Add anchor-lang/idl-build if not present
                    if 'anchor-lang/idl-build' not in cargo_config['features']['idl-build']:
                        cargo_config['features']['idl-build'].append('anchor-lang/idl-build')
                    
                    # Add anchor-spl/idl-build if not present
                    if 'anchor-spl/idl-build' not in cargo_config['features']['idl-build']:
                        cargo_config['features']['idl-build'].append('anchor-spl/idl-build')
                else:
                    # Create idl-build feature with both dependencies
                    cargo_config['features']['idl-build'] = ['anchor-lang/idl-build', 'anchor-spl/idl-build']
                    print("Added idl-build feature with anchor-spl support")
            else:
                # Even if anchor-spl is not needed, ensure idl-build has anchor-lang
                if 'features' not in cargo_config:
                    cargo_config['features'] = {}
                
                if 'idl-build' in cargo_config['features']:
                    if not isinstance(cargo_config['features']['idl-build'], list):
                        cargo_config['features']['idl-build'] = []
                    if 'anchor-lang/idl-build' not in cargo_config['features']['idl-build']:
                        cargo_config['features']['idl-build'].append('anchor-lang/idl-build')
                else:
                    cargo_config['features']['idl-build'] = ['anchor-lang/idl-build']
            
            # Detect and add other dependencies based on the program code
            detected_deps = _detect_dependencies_from_code(program_code)
            for dep_name, dep_version in detected_deps.items():
                # Always add detected dependencies, including spl-token even with anchor-spl
                if dep_name not in cargo_config['dependencies']:
                    cargo_config['dependencies'][dep_name] = dep_version
                    print(f"Added dependency: {dep_name} = \"{dep_version}\"")
            
            # Force add spl-token if any token-related usage is detected (common requirement)
            token_indicators = [
                'Token', 'TokenAccount', 'Mint', 'transfer', 'mint_to', 
                'burn', 'freeze_account', 'thaw_account', 'set_authority',
                'spl_token::', 'token::', 'TokenInstruction'
            ]
            
            if any(indicator in program_code for indicator in token_indicators):
                if 'spl-token' not in cargo_config['dependencies']:
                    cargo_config['dependencies']['spl-token'] = "7.0"
                    print(f"Added dependency: spl-token = \"7.0\" (detected token usage)")
            
            # Ensure all required features are present
            required_features = ['default', 'cpi', 'no-entrypoint', 'no-idl', 'no-log-ix-name']
            for feature in required_features:
                if feature not in cargo_config['features']:
                    if feature == 'default':
                        cargo_config['features'][feature] = []
                    elif feature == 'cpi':
                        cargo_config['features'][feature] = ['no-entrypoint']
                    else:
                        cargo_config['features'][feature] = []
            
            # Ensure lib section exists with correct crate-type and name
            if 'lib' not in cargo_config:
                cargo_config['lib'] = {}
            
            if 'crate-type' not in cargo_config['lib']:
                cargo_config['lib']['crate-type'] = ['cdylib', 'lib']
            
            if 'name' not in cargo_config['lib']:
                # Use the package name from the config
                package_name = cargo_config.get('package', {}).get('name', 'anchor_environment')
                cargo_config['lib']['name'] = package_name
            
            # Save changes in the Cargo.toml file 
            with open(cargo_path, 'w') as f:
                toml.dump(cargo_config, f)
            
            print(f"Cargo.toml updated successfully with required dependencies and features")
        else:
            print(f"Error: Cargo.toml not found in {cargo_path}")
            return False
            
    except Exception as e:
        print(f"Error during Cargo.toml modification: {e}")
        return False
    
    return True


def _compile_program(program_name, operating_system, program):
    # Initialization phase
    done = _perform_anchor_initialization(program_name, operating_system)
    if not done:
        return False
    else:
        # After initialization, create/modify the Cargo.toml file with the desired feature and dependencies
        cargo_toml_path = f"{anchor_base_path}/.anchor_files/{program_name}/anchor_environment/programs/anchor_environment/Cargo.toml"
        addInitIfNeeded(cargo_toml_path, program)
        
        
    

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