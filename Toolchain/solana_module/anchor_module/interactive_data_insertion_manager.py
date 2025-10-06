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
from anchorpy import Provider, Wallet
from Toolchain.solana_module.solana_utils import create_client, choose_wallet, load_keypair_from_file, solana_base_path
from Toolchain.solana_module.anchor_module.anchor_utils import fetch_required_accounts, fetch_signer_accounts, generate_pda, \
    fetch_args, check_type, convert_type, fetch_cluster, anchor_base_path, load_idl, choose_program, choose_instruction, \
    check_if_array
from Toolchain.solana_module.anchor_module.transaction_manager import build_transaction, measure_transaction_size, compute_transaction_fees, send_transaction


# ====================================================
# PUBLIC FUNCTIONS
# ====================================================

def choose_program_to_run():
    repeat = True

    # Repeat is needed to manage the going back from the following menus
    while repeat:
        chosen_program = choose_program()
        if not chosen_program:
            return True
        else:
            repeat = _choose_instruction_to_run(chosen_program)




# ====================================================
# PRIVATE FUNCTIONS
# ====================================================

def _choose_instruction_to_run(program_name):
    idl_file_path = f'{anchor_base_path}/.anchor_files/{program_name}/anchor_environment/target/idl/{program_name}.json'
    idl = load_idl(idl_file_path)

    repeat = True

    while repeat:
        chosen_instruction = choose_instruction(idl)
        if not chosen_instruction:
            return True
        else:
            repeat = _setup_required_accounts(chosen_instruction, idl, program_name)

    return False # Needed to come back to main menu after finishing

def _setup_required_accounts(instruction, idl, program_name):
    required_accounts = fetch_required_accounts(instruction, idl)
    signer_accounts = fetch_signer_accounts(instruction, idl)
    final_accounts = dict()
    signer_accounts_keypairs = dict()
    remaining_accounts = []  # Per i payees
    repeat = True

    i = 0
    while repeat:
        while i < len(required_accounts):
            required_account = required_accounts[i]
            print(f"\nNow working with {required_account} account.")
            print("Is this account a Wallet or a PDA?")
            print(f"1) Wallet")
            print(f"2) PDA")
            print(f"0) Go back")

            choice = input()

            if choice == '1':
                chosen_wallet = choose_wallet()
                if chosen_wallet is not None:
                    keypair = load_keypair_from_file(f"{solana_base_path}/solana_wallets/{chosen_wallet}")
                    final_accounts[required_account] = keypair.pubkey()
                    # If it is a signer account, save its keypair into signer_accounts_keypairs
                    if required_account in signer_accounts:
                        signer_accounts_keypairs[required_account] = keypair
                    print(f"{required_account} account added.")
                    i += 1
            elif choice == '2':
                pda_key = generate_pda(program_name, False)
                if pda_key is not None:
                    final_accounts[required_account] = pda_key
                    i += 1
            elif choice == '0':
                if i == 0:
                    return True
                else:
                    i -= 1  # Necessary to come back
            else:
                print(f"Please insert a valid choice.")

        # Dopo aver configurato gli account richiesti, gestisci i payees per l'istruzione initialize
        # Gestisci sia il caso in cui instruction sia una stringa che un dizionario
        instruction_name = instruction if isinstance(instruction, str) else instruction.get('name', instruction)
        
        if instruction_name == 'initialize':
            repeat = _setup_payees(remaining_accounts)
            if repeat:
                if i == 0:
                    return True
                else:
                    i -= 1
                continue

        repeat = _setup_args(instruction, idl, program_name, final_accounts, signer_accounts_keypairs, remaining_accounts)
        if i == 0:
            return True
        else:
            i -= 1

    return False

def _setup_payees(remaining_accounts):
    """Gestisce la configurazione dei payees per l'istruzione initialize"""
    print(f"\n=== PAYEES SETUP ===")
    print("Now you need to add payees (recipients of the payment splitting).")
    print("How many payees do you want to add?")
    
    while True:
        try:
            num_payees = input("Number of payees (or 0 to go back): ")
            if num_payees == '0':
                return True
            
            num_payees = int(num_payees)
            if num_payees <= 0:
                print("Please enter a positive number.")
                continue
            break
        except ValueError:
            print("Please enter a valid number.")
    
    remaining_accounts.clear()  # Clear existing payees
    
    for i in range(num_payees):
        print(f"\n--- Payee {i+1}/{num_payees} ---")
        while True:
            print("Select payee wallet:")
            chosen_wallet = choose_wallet()
            if chosen_wallet is None:
                print("Please select a valid wallet.")
                continue
            
            keypair = load_keypair_from_file(f"{solana_base_path}/solana_wallets/{chosen_wallet}")
            pubkey = keypair.pubkey()
            
            # Check if this payee is already added
            if any(acc['pubkey'] == pubkey for acc in remaining_accounts):
                print("This payee has already been added. Please choose a different wallet.")
                continue
            
            remaining_accounts.append({
                'pubkey': pubkey,
                'is_signer': False,
                'is_writable': False
            })
            print(f"Payee {i+1} added: {pubkey}")
            break
    
    print(f"\nTotal payees added: {len(remaining_accounts)}")
    return False

def _setup_args(instruction, idl, program_name, accounts, signer_account_keypairs, remaining_accounts=None):
    required_args = fetch_args(instruction, idl)
    repeat = _manage_args(required_args, program_name, instruction, accounts, signer_account_keypairs, remaining_accounts)
    if repeat:
        return True
    else:
        return False

def _manage_args(args, program_name, instruction, accounts, signer_account_keypairs, remaining_accounts=None):
    final_args = dict()
    repeat = True
    i = 0

    while repeat:
        while i < len(args):
            arg = args[i]
            print(f"Insert {arg['name']} value. ", end="", flush=True)

            # Arrays e Vec management
            array_type, array_length = check_if_array(arg)
            
            if array_type == "Unsupported type":
                print(f"Unsupported type for arg {arg['name']}")
                return False
                
            elif array_type is not None:  # È un array o un vec
                if array_length is not None:
                    # Array a lunghezza fissa
                    print(f"It is an array of {array_type} type and length {array_length}. Please insert array values separated by spaces (Insert 00 to go back to previous section).")
                else:
                    # Vec (vettore dinamico)
                    print(f"It is a vector of {array_type} type.")
                    
                    # Special handling for shares_amounts in initialize instruction
                    # Gestisci sia il caso in cui instruction sia una stringa che un dizionario
                    instruction_name = instruction if isinstance(instruction, str) else instruction.get('name', instruction)
                    
                    if arg['name'] == 'shares_amounts' and instruction_name == 'initialize' and remaining_accounts:
                        print(f"You have {len(remaining_accounts)} payees, so you need to provide {len(remaining_accounts)} share amounts.")
                        print("Please insert share amounts separated by spaces (each amount > 0):")
                    else:
                        print("Please insert vector values separated by spaces (empty input for empty vector):")
                    
                    print("(Insert 00 to go back to previous section)")
                
                # Input unico per entrambi i casi
                value = input()
                
                if value == '00':
                    if i == 0:
                        return True
                    else:
                        i -= 1
                        continue
                
                # Gestione input vuoto solo per vec
                if value.strip() == "" and array_length is None:
                    # Vettore vuoto
                    final_args[arg['name']] = []
                    print("Empty vector created")
                    i += 1
                    continue
                
                # Parsing dei valori
                array_values = value.split()
                
                # Special validation for shares_amounts
                # Gestisci sia il caso in cui instruction sia una stringa che un dizionario
                instruction_name = instruction if isinstance(instruction, str) else instruction.get('name', instruction)
                
                if arg['name'] == 'shares_amounts' and instruction_name == 'initialize' and remaining_accounts:
                    if len(array_values) != len(remaining_accounts):
                        print(f"Error: You have {len(remaining_accounts)} payees but provided {len(array_values)} share amounts.")
                        print("The number of share amounts must match the number of payees.")
                        continue
                
                # Check lunghezza solo per array fissi
                if array_length is not None and len(array_values) != array_length:
                    print(f"Error: Expected array of length {array_length}, but got {len(array_values)}")
                    continue
                
                # Conversione valori
                valid_values = []
                conversion_error = False
                
                for j in range(len(array_values)):
                    converted_value = convert_type(array_type, array_values[j])
                    if converted_value is not None:
                        # Special validation for shares_amounts (must be > 0)
                        # Gestisci sia il caso in cui instruction sia una stringa che un dizionario
                        instruction_name = instruction if isinstance(instruction, str) else instruction.get('name', instruction)
                        
                        if arg['name'] == 'shares_amounts' and instruction_name == 'initialize':
                            if converted_value <= 0:
                                print(f"Error: Share amount at index {j} must be greater than 0.")
                                conversion_error = True
                                break
                        valid_values.append(converted_value)
                    else:
                        print(f"Invalid input at index {j}. Please try again.")
                        conversion_error = True
                        break
                
                if not conversion_error:
                    if array_length is None:
                        print(f"Vector will contain {len(valid_values)} elements")
                    final_args[arg['name']] = valid_values
                    i += 1

            else:
                # Single value management
                type = check_type(arg['type'])
                if type == "Unsupported type":
                    print(f"Unsupported type for arg {arg['name']}")
                    return False
                    
                print(f"It is a {type} (Insert 00 to go back to previous section).")
                text_input = input()
                
                if text_input == '00':
                    if i == 0:
                        return True
                    else:
                        i -= 1
                        continue
                
                converted_value = convert_type(type, text_input)
                if converted_value is not None:
                    final_args[arg['name']] = converted_value
                    i += 1
                else:
                    print("Invalid input. Please try again.")

        repeat = _manage_provider(program_name, instruction, accounts, final_args, signer_account_keypairs, remaining_accounts)
        if i == 0:
            if repeat:
                return True
            else:
                return False
        else:
            i -= 1

    return False

def _manage_provider(program_name, instruction, accounts, args, signer_account_keypairs, remaining_accounts=None):
    print("Now working with the transaction provider.")
    chosen_wallet = choose_wallet()
    if chosen_wallet is None:
        return True
    else:
        keypair = load_keypair_from_file(f"{solana_base_path}/solana_wallets/{chosen_wallet}")
        cluster, is_deployed = fetch_cluster(program_name)
        client = create_client(cluster)
        provider_wallet = Wallet(keypair)
        provider = Provider(client, provider_wallet)
        return asyncio.run(_manage_transaction(program_name, instruction, accounts, args, signer_account_keypairs, client, provider, is_deployed, remaining_accounts))

async def _manage_transaction(program_name, instruction, accounts, args, signer_account_keypairs, client, provider, is_deployed, remaining_accounts=None):
    # Build transaction
    tx = await build_transaction(program_name, instruction, accounts, args, signer_account_keypairs, client, provider, remaining_accounts)
    print('Transaction built. Computing size and fees...')

    # Measure transaction size
    transaction_size = measure_transaction_size(tx)
    if transaction_size is None:
        print('Error while measuring transaction size.')
    else:
        print(f"Transaction size: {transaction_size} bytes")

    # Compute transaction fees
    transaction_fees = await compute_transaction_fees(client, tx)
    if transaction_fees is None:
        print('Error while computing transaction fees.')
    else:
        print(f"Transaction fee: {transaction_fees} lamports")

    if is_deployed:
        allowed_choices = ['1','0']
        choice = None
        while choice not in allowed_choices:
            print('Choose an option.')
            print('1) Send transaction')
            print('0) Go back to Anchor menu')
            choice = input()
            if choice == '1':
                transaction = await send_transaction(provider, tx)
                print(f'Transaction sent. Hash: {transaction}')
            elif choice == '0':
                return False
            else:
                print('Invalid option. Please choose a valid option.')
    else:
        return False