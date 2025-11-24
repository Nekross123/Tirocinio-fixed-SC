import streamlit as st
import json
from io import StringIO
import pandas as pd
import os
import re
import asyncio
from solders.pubkey import Pubkey
from anchorpy import Wallet, Provider
from Solana_module.solana_module.anchor_module.transaction_manager import build_transaction, measure_transaction_size, \
    compute_transaction_fees, send_transaction
from Solana_module.solana_module.solana_utils import load_keypair_from_file, solana_base_path, create_client
from Solana_module.solana_module.anchor_module.anchor_utils import anchor_base_path, fetch_initialized_programs, \
    fetch_program_instructions, fetch_required_accounts, fetch_signer_accounts, fetch_args, check_type, convert_type, \
    fetch_cluster, load_idl, check_if_array , check_if_vec , bind_actors , is_pda  , generate_pda_automatically , find_sol_arg , \
    get_network_from_client , find_args ,is_wallet

from solana.rpc.async_api import AsyncClient

async def run_execution_trace(file_name):
    """Run automatic JSON execution trace with minimal Streamlit feedback.

    Reads a JSON trace, resolves wallets/PDAs/args, optionally waits for slots,
    builds the transaction, computes size/fees, optionally sends, and collects
    results to display and allow download.
    """
    
    
    status_placeholder = st.empty()
    
    
    status_placeholder.info(f" Executing automatic trace: **{file_name}**...")
    
    
    initialized_programs = fetch_initialized_programs()
    if len(initialized_programs) == 0:
        status_placeholder.error(" No program has been initialized yet. Please compile an Anchor program first.")
        return {"success": False, "error": "No program initialized"}

    if file_name is None:
        status_placeholder.error(" No trace file selected")
        return {"success": False, "error": "No trace file selected"}

    results = []

    json_file = _read_json(f"{anchor_base_path}/execution_traces/{file_name}")
    if json_file is None:
        status_placeholder.error(f"Failed to read trace file: {file_name}")
        return {"success": False, "error": "Failed to read trace file"}
        
    actors = bind_actors(file_name)
    if not actors:
        status_placeholder.error("Failed to bind actors to wallets")
        return {"success": False, "error": "Failed to bind actors"}

    client = AsyncClient("https://api.devnet.solana.com")
    network = get_network_from_client(client)
    program_name = json_file["trace_title"]
    
    # Track accounts created during trace execution
    created_accounts = set()

    try:
        for trace in json_file["trace_execution"]:

            args = find_args(trace)

            st.info(f"Processing execution trace with ID {trace['sequence_id']}.") 
            sol_args = find_sol_arg(trace)

            
            complete_dict = generate_pda_automatically(actors ,program_name , sol_args , args)

            # Get execution trace ID
            trace_id = trace["sequence_id"]
            print(f"Working on execution trace with ID {trace_id}...")

            # Manage program
            program_name = json_file["trace_title"]


            idl_file_path = f'{anchor_base_path}/.anchor_files/{program_name}/anchor_environment/target/idl/{program_name}.json'
            idl = load_idl(idl_file_path)
            instructions = fetch_program_instructions(idl)
            instruction = trace["function_name"]

            if instruction not in instructions:
                print(f"Instruction {instruction} not found for the program {program_name} (execution trace {trace_id}).")

            required_accounts = fetch_required_accounts(instruction, idl)
            signer_accounts = fetch_signer_accounts(instruction, idl)
            final_accounts = dict()
            signer_accounts_keypairs = dict()
            

            extracted_key = trace["waiting_time"]
            if extracted_key > 0:

                target_slot = int(extracted_key)

                first_response = await client.get_slot()
                first_current_slot = first_response.value
                target_end_slot = first_current_slot + target_slot

                print(f"Waiting for slot {target_slot} ...")

                while True:
                        try:
                            response = await client.get_slot()
                            current_slot = response.value
                            current_value = target_end_slot - current_slot

                            if current_value <= 0:
                                print(f"Target reached! Current slot: {target_slot - current_value}, target was: {target_slot}")
                                break

                            print(f"Current slot: {target_slot - current_value}, target slot: {target_slot}")
                            await asyncio.sleep(1)

                        except Exception as e:
                            print(f"Error checking slot: {e}")
                            await asyncio.sleep(2)




            remaining_accounts = []
            
            for account in required_accounts:
                # PDA account
                if is_pda(complete_dict[account]):
                    
                    try:
                        pda_key = Pubkey.from_string(complete_dict[account])
                        final_accounts[account] = pda_key
                    except Exception as e:
                        print(f"Invalid PDA key format for account {account}: {extracted_key}. Error: {e}")
                        st.error(f"Invalid PDA key format for account {account}")
                        continue


                elif not is_wallet(complete_dict[account]):
                    wallet_value = complete_dict[complete_dict[account]]

                    print(f"Account {account} is a wallet with value {wallet_value}")
                    file_path = f"{solana_base_path}/solana_wallets/{wallet_value}"

                    keypair = load_keypair_from_file(file_path)
                    if keypair is None:
                        print(f"Wallet for account {account} not found at path {file_path}.")
                        st.error(f"Wallet not found: {file_path}")
                        continue
                    if account in signer_accounts:
                        signer_accounts_keypairs[account] = keypair
                    final_accounts[account] = keypair.pubkey()




                elif not is_pda(complete_dict[account]) and is_wallet(complete_dict[account]):
                    
                    wallet_value = complete_dict[account]

                    print(f"Account {account} is a wallet with value {wallet_value}")
                    file_path = f"{solana_base_path}/solana_wallets/{wallet_value}"

                    keypair = load_keypair_from_file(file_path)
                    if keypair is None:
                        print(f"Wallet for account {account} not found at path {file_path}.")
                        st.error(f"Wallet not found: {file_path}")
                        continue
                    if account in signer_accounts:
                        signer_accounts_keypairs[account] = keypair
                    final_accounts[account] = keypair.pubkey()



                

            required_args = fetch_args(instruction, idl)
            final_args = dict()
            for arg in required_args:

                print(f"Processing argument: {arg}")                                                                                                                                                                                                                                                                                                                                                                                                                                                
                
                array_type, array_length = check_if_array(arg)
                vec_type = check_if_vec(arg)
                if array_type is not None and array_length is not None:



                    array_values = complete_dict[arg["name"]].split()

                    if len(array_values) != array_length:
                        print(f"Error: Expected array of length {array_length}, but got {len(array_values)}")
                        st.error(f"Invalid array length for {arg['name']}")
                        continue

                    valid_values = []
                    for j in range(len(array_values)):
                        converted_value = convert_type(array_type, array_values[j])
                        if converted_value is not None:
                            valid_values.append(converted_value)
                        else:
                            print(f"Invalid input at index {j} in the array. Please try again.")
                            st.error(f"Invalid array value at index {j}")
                            continue

                    final_args[arg['name']] = valid_values
                elif vec_type is not None:
                    vec_values = complete_dict[arg].split()
                    if len(vec_values) == 0:
                        print("vec cannot have zero elements")
                        st.error("Vector cannot have zero elements")
                        continue
                    
                    valid_values = []
                    for j in range(len(vec_values)):
                        converted_value = convert_type(vec_type, vec_values[j])
                        if converted_value is not None:
                            valid_values.append(converted_value)
                        else:
                            print(f"Invalid input at index {j} in the vector. Please try again.")
                            st.error(f"Invalid vector value at index {j}")
                            continue

                    final_args[arg['name']] = valid_values

                else:

                    type = check_type(arg["type"])
                    if type is None:
                        print(f"Unsupported type for arg {arg['name']}")
                        st.error(f"Unsupported type for {arg['name']}")
                        continue

                    if type == "bytes":      
                            aux = complete_dict[arg['name']].encode('utf-8')
                            final_args[arg['name']] = aux
                            
                    else:
                        try:
                            converted_value = convert_type(type, complete_dict[arg['name']])
                            final_args[arg['name']] = converted_value
                        except KeyError as e :
                            print(f"The names on the trace and the names on the contract must be the same , the error is caused by {e} ")
                            

                

            try :
                provider_keypair_path = f"{solana_base_path}/solana_wallets/{complete_dict[complete_dict["provider_wallet"]]}"
                keypair = load_keypair_from_file(provider_keypair_path)
                if keypair is None:
                    print("Provider wallet not found. Transaction cannot be sent.")
                    st.error("Provider wallet not found")
                    continue
            except KeyError :
                print("Provider wallet not found.Insert the field 'provider_wallet' in the json trace")
                st.error("Provider wallet field missing in trace")
                continue
                
            cluster, is_deployed = fetch_cluster(program_name)
            client_for_transaction = create_client(cluster)
            provider_wallet = Wallet(keypair)
            provider = Provider(client_for_transaction, provider_wallet)

            start_slot = (await client.get_slot()).value

            transaction = await build_transaction(program_name, instruction, final_accounts, final_args, 
                                                signer_accounts_keypairs, client_for_transaction, provider)

            end_slot = (await client.get_slot()).value
            elapsed_slots = end_slot - start_slot


            size = measure_transaction_size(transaction)
            fees = await compute_transaction_fees(client_for_transaction, transaction)

            # Calculate rent cost only for accounts that will be created by this transaction
            total_rent_lamports = 0
            accounts_to_create = []
            
            # Store account sizes BEFORE transaction for realloc detection
            account_sizes_before = {}
            
            # Check which PDA accounts don't exist yet (will be created)
            for account_name, account_pubkey in final_accounts.items():
                # Only check PDA accounts (not wallets/signers)
                if not is_wallet(account_name):
                    account_pubkey_str = str(account_pubkey)
                    # Check if already tracked as created in this trace (no rent duplicato)
                    if account_pubkey_str in created_accounts:
                        print(f"Account '{account_name}' already tracked as created in this trace - no rent needed")
                        continue
                    try:
                        account_info_response = await client.get_account_info(account_pubkey)
                        
                        # Store size before transaction (for realloc detection)
                        if account_info_response.value is not None:
                            account_sizes_before[account_pubkey_str] = len(account_info_response.value.data)
                        else:
                            account_sizes_before[account_pubkey_str] = 0
                        
                        if account_info_response.value is None:
                            expected_size = _get_account_size_from_idl(idl, instruction, account_name)
                            if expected_size > 0:
                                rent_response = await client.get_minimum_balance_for_rent_exemption(expected_size)
                                rent_lamports = rent_response.value
                                total_rent_lamports += rent_lamports
                                accounts_to_create.append({
                                    "account_name": account_name,
                                    "account_pubkey": str(account_pubkey),
                                    "expected_size_bytes": expected_size,
                                    "rent_lamports": rent_lamports
                                })
                                created_accounts.add(account_pubkey_str)
                                print(f"Account '{account_name}' will be created - rent: {rent_lamports} lamports ({rent_lamports / 1_000_000_000:.6f} SOL)")
                            else:
                                print(f"Could not determine size for account '{account_name}', skipping rent calculation")
                        else:
                            print(f"Account '{account_name}' already exists on chain - no rent needed")
                    except Exception as e:
                        print(f"Error checking account {account_name}: {e}")

            # Initialize resize tracking variables
            rent_from_resize = 0
            accounts_resized = []
            
            if str(complete_dict["send_transaction"]).lower() == 'true':
                if is_deployed:
                    transaction_hash = await send_transaction(provider, transaction)
                    
                    # Wait for transaction confirmation before proceeding
                    # This ensures account state is updated for next transaction
                    try:
                        confirmation = await client.confirm_transaction(
                            transaction_hash,
                            commitment="confirmed"
                        )
                        if confirmation.value[0].err:
                            print(f"Transaction failed: {confirmation.value[0].err}")
                        else:
                            print(f"Transaction confirmed in slot {confirmation.context.slot}")
                            
                            # Small delay to ensure RPC state is fully updated
                            await asyncio.sleep(0.5)
                            
                            # Check for account resize (realloc) after transaction
                            rent_from_resize = 0
                            accounts_resized = []
                            
                            for account_name, account_pubkey in final_accounts.items():
                                if not is_wallet(account_name):
                                    account_pubkey_str = str(account_pubkey)
                                    try:
                                        account_info_after = await client.get_account_info(account_pubkey)
                                        if account_info_after.value is not None:
                                            size_after = len(account_info_after.value.data)
                                            size_before = account_sizes_before.get(account_pubkey_str, 0)
                                            
                                            if size_after > size_before:
                                                # Account was resized - calculate additional rent
                                                size_increase = size_after - size_before
                                                rent_increase_response = await client.get_minimum_balance_for_rent_exemption(size_after)
                                                rent_before_response = await client.get_minimum_balance_for_rent_exemption(size_before) if size_before > 0 else type('obj', (object,), {'value': 0})()
                                                
                                                additional_rent = rent_increase_response.value - (rent_before_response.value if hasattr(rent_before_response, 'value') else 0)
                                                rent_from_resize += additional_rent
                                                
                                                accounts_resized.append({
                                                    "account_name": account_name,
                                                    "account_pubkey": account_pubkey_str,
                                                    "size_before": size_before,
                                                    "size_after": size_after,
                                                    "size_increase": size_increase,
                                                    "additional_rent_lamports": additional_rent
                                                })
                                                
                                                print(f"Account '{account_name}' was resized: {size_before} → {size_after} bytes (+{size_increase})")
                                                print(f"   Additional rent: {additional_rent} lamports ({additional_rent / 1_000_000_000:.9f} SOL)")
                                    except Exception as e:
                                        print(f"Error checking resize for {account_name}: {e}")
                            
                            total_rent_lamports += rent_from_resize
                            
                    except Exception as e:
                        print(f"Warning: Could not confirm transaction: {e}")
                    
                else:
                    transaction_hash = "program is not deployed"
            else:
                transaction_hash = "transaction not sent (send_transaction=false)"

            total_cost_lamports = fees + total_rent_lamports
            
            # Determine rent breakdown
            rent_from_creation = sum(acc["rent_lamports"] for acc in accounts_to_create)
            
            json_action = { "execution_time_in_slots": elapsed_slots,
                            "sequence_id" : trace_id ,
                            "function_name": instruction ,
                            "transaction_size_bytes": size,
                            "transaction_fees_lamports": fees,
                            "rent_from_account_creation_lamports": rent_from_creation,
                            "rent_from_resize_lamports": rent_from_resize,
                            "total_rent_cost_lamports": total_rent_lamports,
                            "total_cost_lamports": total_cost_lamports,
                            "accounts_created": len(accounts_to_create),
                            "accounts_created_details": accounts_to_create,
                            "accounts_resized": len(accounts_resized),
                            "accounts_resized_details": accounts_resized,
                            "transaction_hash": f"{transaction_hash}"
                            
                        }

            results.append(json_action)

    finally:
        await client.close()

    file_name_without_extension = file_name.removesuffix(".json")
    file_path,final = _write_json(file_name_without_extension, results, network)
    
    # Replace initial message with completion message
    status_placeholder.success(f"Execution completed successfully! Results saved to: `{os.path.basename(file_path)}`")
    return {"success": True, "results_file": final}


# ====================================================
# PRIVATE FUNCTIONS
# ====================================================

def _find_execution_traces():
    """List all JSON trace files available under execution_traces folder."""
    path = f"{anchor_base_path}/execution_traces/"
    if not os.path.exists(path):
        print(f"Error: Folder '{path}' does not exist.")
        return []
    #modifica 1 modified from csv to json file 
    return [f for f in os.listdir(path) if f.lower().endswith('.json')]




def _get_account_size_from_idl(idl, instruction_name, account_name):
    """
    Try to determine the expected size of an account from the IDL.
    
    Args:
        idl: The loaded IDL dictionary
        instruction_name: Name of the instruction being executed
        account_name: Name of the account to check
        
    Returns:
        int: Expected size in bytes, or 0 if cannot be determined
    """
    try:
        # Look for account types in IDL
        if "accounts" in idl:
            for account_type in idl["accounts"]:
                # Check if account name matches (case-insensitive or partial match)
                if account_type["name"].lower() in account_name.lower() or account_name.lower() in account_type["name"].lower():
                    # Calculate size from account fields
                    total_size = 8  # Anchor discriminator (8 bytes)
                    
                    if "type" in account_type and "fields" in account_type["type"]:
                        for field in account_type["type"]["fields"]:
                            field_type = field.get("type", "")
                            
                            # Basic type sizes
                            if field_type == "u8" or field_type == "i8" or field_type == "bool":
                                total_size += 1
                            elif field_type == "u16" or field_type == "i16":
                                total_size += 2
                            elif field_type == "u32" or field_type == "i32":
                                total_size += 4
                            elif field_type == "u64" or field_type == "i64":
                                total_size += 8
                            elif field_type == "u128" or field_type == "i128":
                                total_size += 16
                            elif field_type == "publicKey":
                                total_size += 32
                            elif field_type == "string":
                                # String with default max length
                                total_size += 4 + 100  # 4 bytes length + max 100 chars
                            elif isinstance(field_type, dict):
                                # Handle complex types (vec, array, etc.)
                                if "vec" in field_type:
                                    total_size += 4 + 32  # Vec length + some default space
                                elif "array" in field_type:
                                    total_size += 32  # Default array size
                            else:
                                # Unknown type, add some default space
                                total_size += 8
                    
                    return total_size
        
        # If no match found in accounts section, use a conservative default
        # Most PDAs are at least 128 bytes (discriminator + some data)
        return 128
        
    except Exception as e:
        print(f"Error determining account size from IDL: {e}")
        return 128  # Fallback default size


def _read_json(file_path):
    """Safely read and parse a JSON file; return dict or None on error."""
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except FileNotFoundError:
            print(f"File {file_path} non trovato")
            return None
        except json.JSONDecodeError as e:
            print(f"Errore nel parsing JSON: {e}")
            return None
        except Exception as e:
            print(f"Errore generico: {e}")
            return None 
        with open(file_path, mode='r') as file:
            data = load_json('auction.json')
            return list(json_file)
    else:
        return None

def _write_json(file_name, results , network):
    """Write final results JSON under execution_traces_results and return path+object."""
    folder = f'{anchor_base_path}/execution_traces_results/'
    json_file = os.path.join(folder, f'{file_name}_results.json')

    # Create folder if it doesn't exist
    os.makedirs(folder, exist_ok=True)
    final = {"network" : f"{network}*" ,
             "platform" : "Solana",
            "trace_title" : f"{file_name}_results",
            "actions" : results}

    with open(json_file, "w") as f:
        json.dump(final, f, indent=2)
    
    return json_file ,final





def build_table(data):
    """Render a vertical, readable summary table in Streamlit with downloads."""
    if data is None:
        st.error("No data received from backend")
        return
    
    if "results_file" not in data:
        st.error(f"Invalid data format: {data}")
        return
        
    results = data["results_file"]
    actions = results["actions"]
    
    # --- Stile personalizzato ---
    st.markdown("""
    <style>
        /* Titoli principali */
        h3 {
            font-size: 2rem !important;
        }

        /* Titoli delle metriche */
        .info-title {
            font-size: 1.6rem;
            font-weight: 600;
            color: #cccccc;
            margin-bottom: 0.3rem;
        }

        /* Valori delle metriche (Network, Platform, Trace title) */
        .info-value {
            font-size: 1.2rem;
            font-weight: 400;
            color: #ffffff;
            margin-bottom: 0.8rem;
        }

        /* Tabella verticale */
        .vertical-table {
            background-color: rgba(255, 255, 255, 0.05);
            padding: 1.2rem;
            border-radius: 12px;
            margin-top: 1rem;
            width: 100%;
        }
        .vertical-table-row {
            display: flex;
            justify-content: space-between;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            padding: 0.5rem 0;
        }
        .vertical-table-label {
            color: #aaa;
            font-weight: 600;
        }
        .vertical-table-value {
            color: #fff;
            word-break: break-all;
            text-align: right;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # --- Info generali (su una riga) ---
    st.markdown("### Generic Info")
    cols = st.columns(3)

    with cols[0]:
        st.markdown("<div class='info-title'>Network</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='info-value'>{results['network']}</div>", unsafe_allow_html=True)

    with cols[1]:
        st.markdown("<div class='info-title'>Platform</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='info-value'>{results['platform']}</div>", unsafe_allow_html=True)

    with cols[2]:
        st.markdown("<div class='info-title'>Trace Title</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='info-value'>{results['trace_title']}</div>", unsafe_allow_html=True)
    
    # --- Azioni in formato verticale ---
    st.markdown("### Actions")

    for action in actions:
   
        st.markdown('<div class="vertical-table">', unsafe_allow_html=True)
        for key, value in action.items():
            st.markdown(
                f"""
                <div class="vertical-table-row">
                    <div class="vertical-table-label">{key.replace('_', ' ').title()}</div>
                    <div class="vertical-table-value">{value}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        st.markdown('</div>', unsafe_allow_html=True)

    # --- Pulsanti di Download ---
    st.markdown("### Download Results")
    
    # Prepara i dati per il download
    download_data = {
        "network": results['network'],
        "platform": results['platform'],
        "trace_title": results['trace_title'],
        "actions": actions
    }
    
    # Converti in JSON
    json_data = json.dumps(download_data, indent=2)
    
    # Prepara dati per CSV
    csv_rows = []
    for action in actions:
        row = {
            "Network": results['network'],
            "Platform": results['platform'],
            "Trace Title": results['trace_title']
        }
        row.update(action)
        csv_rows.append(row)
    
    df = pd.DataFrame(csv_rows)
    csv_data = df.to_csv(index=False)
    
    # Due colonne per i pulsanti di download
    col1, col2 = st.columns(2)
    
    with col1:
        st.download_button(
            label="Download as JSON",
            data=json_data,
            file_name=f"{results['trace_title']}_results.json",
            mime="application/json"
        )
    
    with col2:
        st.download_button(
            label="Download as CSV",
            data=csv_data,
            file_name=f"{results['trace_title']}_results.csv",
            mime="text/csv"
        )