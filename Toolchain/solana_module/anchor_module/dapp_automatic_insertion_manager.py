import streamlit as st
import os
import re
import json
import asyncio
from solders.pubkey import Pubkey
from anchorpy import Wallet, Provider
from solana_module.anchor_module.transaction_manager import build_transaction, measure_transaction_size, \
    compute_transaction_fees, send_transaction
from solana_module.solana_utils import load_keypair_from_file, solana_base_path, create_client, selection_menu
from solana_module.anchor_module.anchor_utils import anchor_base_path, fetch_initialized_programs, \
    fetch_program_instructions, fetch_required_accounts, fetch_signer_accounts, fetch_args, check_type, convert_type, \
    fetch_cluster, load_idl, check_if_array , check_if_vec , bind_actors , is_pda  , generate_pda_automatically , find_sol_arg , \
    get_network_from_client , find_args

from spl.token.async_client import AsyncToken
from spl.token.constants import ASSOCIATED_TOKEN_PROGRAM_ID
from solders.pubkey import Pubkey as SoldersPubkey
from solana.rpc.async_api import AsyncClient

# ====================================================
# PUBLIC FUNCTIONS
# ====================================================

async def run_execution_trace(file_name):
    # Fetch initialized programs

    st.info(f"Running execution trace {file_name}...")

    initialized_programs = fetch_initialized_programs()
    if len(initialized_programs) == 0:
        print("No program has been initialized yet.")
        return

    results = []


    if file_name is None:
        return



    json_file = _read_json(f"{anchor_base_path}/execution_traces/{file_name}")
    actors = bind_actors(file_name)
   

    # Create async client outside the loop
    client = AsyncClient("https://api.devnet.solana.com")
    #search fotr the network
    network = get_network_from_client(client)
    progrma_name = json_file["trace_title"]

    try:
        # For each execution trace
        for trace in json_file["trace_execution"]:

            args = find_args(trace)

            st.info(f"Processing execution trace with ID {trace['sequence_id']} with args {args}...") 
            sol_args = find_sol_arg(trace)

            
            complete_dict = generate_pda_automatically(actors ,progrma_name , sol_args , args)
            
            

            
            

            # Get execution trace ID
            trace_id = trace["sequence_id"]
            print(f"Working on execution trace with ID {trace_id}...")

            # Manage program
            program_name = json_file["trace_title"]


            # Manage instruction

            idl_file_path = f'{anchor_base_path}/.anchor_files/{program_name}/anchor_environment/target/idl/{program_name}.json'
            idl = load_idl(idl_file_path)
            instructions = fetch_program_instructions(idl)
            instruction = trace["function_name"]

            if instruction not in instructions:
                print(f"Instruction {instruction} not found for the program {program_name} (execution trace {trace_id}).")

            # Manage accounts
            

            required_accounts = fetch_required_accounts(instruction, idl)
            signer_accounts = fetch_signer_accounts(instruction, idl)
            final_accounts = dict()
            signer_accounts_keypairs = dict()
            

            #manage timer 
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

                

            


            # Initialize remaining accounts list
            remaining_accounts = []
            from solders.instruction import AccountMeta
            
            for account in required_accounts:
                # If it is a wallet
                st.info("Checkpoint 2 reached")

                if not is_pda(complete_dict[account]):
                    
                    
                    file_path = f"{solana_base_path}/solana_wallets/{complete_dict[account]}"


                    keypair = load_keypair_from_file(file_path)
                    if keypair is None:
                        print(f"Wallet for account {account} not found at path {file_path}.")


                        return
                    if account in signer_accounts:
                        signer_accounts_keypairs[account] = keypair
                    final_accounts[account] = keypair.pubkey()


                # If it is a PDA
                elif is_pda(complete_dict[account]):
                    
                    try:
                        pda_key = Pubkey.from_string(complete_dict[account])
                        final_accounts[account] = pda_key
                    except Exception as e:
                        print(f"Invalid PDA key format for account {account}: {extracted_key}. Error: {e}")
                        return
                # If it is a Token Account (manual input)
                #elif execution_trace[i].startswith("T:"):
                #    extracted_key = execution_trace[i].removeprefix('T:')
                #    try:
                #        token_account_key = Pubkey.from_string(extracted_key)
                #        final_accounts[account] = token_account_key
                #        print(f"Token account {account} added with address: {token_account_key}")
                #    except Exception as e:
                #        print(f"Invalid token account key format for account {account}: {extracted_key}. Error: {e}")
                #        return
                else:
                    print("work on errors")
                    return
                

            # Manage args
            required_args = fetch_args(instruction, idl)
            final_args = dict()
            for arg in required_args:
                st.info("Checkpoint 3 reached")

                
               
                # Manage arrays
                array_type, array_length = check_if_array(arg)
                vec_type = check_if_vec(arg)
                if array_type is not None and array_length is not None:



                    array_values = complete_dict[arg["name"]].split()

                    # Check if array has correct length
                    if len(array_values) != array_length:
                        print(f"Error: Expected array of length {array_length}, but got {len(array_values)}")
                        return

                    # Convert array elements basing on the type
                    valid_values = []
                    for j in range(len(array_values)):
                        converted_value = convert_type(array_type, array_values[j])
                        if converted_value is not None:
                            valid_values.append(converted_value)
                        else:
                            print(f"Invalid input at index {j} in the array. Please try again.")
                            return

                    final_args[arg['name']] = valid_values
                #vectors handling
                elif vec_type is not None:
                    vec_values = complete_dict[arg].split()
                    #check if vec has more than zero 
                    if len(vec_values) == 0:
                        print("vec cannot have zero elements")
                        return
                    
                    # Convert vec elements basing on the type
                    valid_values = []
                    for j in range(len(vec_values)):
                        converted_value = convert_type(vec_type, vec_values[j])
                        if converted_value is not None:
                            valid_values.append(converted_value)
                        else:
                            print(f"Invalid input at index {j} in the vector. Please try again.")
                            return

                    final_args[arg['name']] = valid_values

                # Manage classical args
                else:

                    type = check_type(arg["type"])
                    if type is None:
                        print(f"Unsupported type for arg {arg['name']}")
                        return

                    if type == "bytes":      
                            aux = complete_dict[arg['name']].encode('utf-8')
                            final_args[arg['name']] = aux
                            
                    else:
                        try:
                            converted_value = convert_type(type, complete_dict[arg['name']])
                            final_args[arg['name']] = converted_value
                        except KeyError as e :
                            print(f"The names on the trace and the names on the contract must be the same , the error is caused by {e} ")
                            

                

            # Manage provider
            try :
                provider_keypair_path = f"{solana_base_path}/solana_wallets/{complete_dict[complete_dict["provider_wallet"]]}"
                keypair = load_keypair_from_file(provider_keypair_path)
                if keypair is None:
                    print("Provider wallet not found. Transaction cannot be sent.")
            except KeyError :
                print("Provider wallet not found.Insert the field 'provider_wallet' in the json trace")
                return
                
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

            # json building


            
            if str(complete_dict["send_transaction"]).lower() == 'true':
                if is_deployed:
                    transaction_hash = await send_transaction(provider, transaction)
                    
                else:
                    transaction_hash = "program is not deployed"

            json_action = {"sequence_id" : trace_id ,
                            "function_name": instruction ,
                            "transaction_size_bytes": size,
                            "transaction_fees_lamports": fees,
                            "transaction_hash": f"{transaction_hash}",
                            "execution_time_in_slots": elapsed_slots
                        }

            # Append results
            results.append(json_action)
            print(f"Execution trace {trace["sequence_id"]} results computed!")

    finally:
        await client.close()

    # json writing
    file_name_without_extension = file_name.removesuffix(".json")
    file_path = _write_json(file_name_without_extension, results , network)
    print(f"Results written successfully to {file_path}")


# ====================================================
# PRIVATE FUNCTIONS
# ====================================================

def _find_execution_traces():
    path = f"{anchor_base_path}/execution_traces/"
    if not os.path.exists(path):
        print(f"Error: Folder '{path}' does not exist.")
        return []
    #modifica 1 modified from csv to json file 
    return [f for f in os.listdir(path) if f.lower().endswith('.json')]




def _read_json(file_path):
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
    
    return json_file