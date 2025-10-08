import os
import asyncio
import json
import importlib.util
from datetime import datetime
from typing import List, Dict, Any, Tuple

from anchorpy import Provider, Wallet
from solders.pubkey import Pubkey
from based58 import b58encode

from Toolchain.solana_module.solana_utils import (
    create_client,
    load_keypair_from_file,
    solana_base_path,
)
from Toolchain.solana_module.anchor_module.anchor_utils import (
    fetch_required_accounts,
    fetch_signer_accounts,
    fetch_args,
    check_if_array,
    check_type,
    convert_type,
    fetch_cluster,
    anchor_base_path,
    load_idl,
    fetch_program_instructions,
    fetch_initialized_programs,
)
from Toolchain.solana_module.anchor_module.transaction_manager import (
    build_transaction,
    measure_transaction_size,
    compute_transaction_fees,
    send_transaction,
)

# ------------------------------------------------------------------
# Async perchè Streamlit è considerato come "already running loop" e quindi non si può usare asyncio.run()
# ------------------------------------------------------------------
import nest_asyncio
def _run_async(coro):
    """Run an async """
    try:
        # Check if there's already a running loop (Streamlit case)
        loop = asyncio.get_running_loop()
        # If we're here, there's a running loop. We need to use nest_asyncio or create new loop
        nest_asyncio.apply()
        return asyncio.run(coro)
    except RuntimeError:
        # No running loop - just use asyncio.run like in CLI
        return asyncio.run(coro)


# ------------------------------ Fetch  ------------------------------ #

def fetch_programs() -> List[str]:
    return fetch_initialized_programs()


def load_idl_for_program(program: str) -> dict:
    idl_path = os.path.join(
        anchor_base_path,
        ".anchor_files",
        program,
        "anchor_environment",
        "target",
        "idl",
        f"{program}.json",
    )
    if not os.path.exists(idl_path):
        raise FileNotFoundError("IDL file non trovato. Compila prima il programma.")
    return load_idl(idl_path)


def fetch_instructions_for_program(program: str) -> List[str]:
    idl = load_idl_for_program(program)
    return fetch_program_instructions(idl)


def fetch_program_context(program: str, instruction: str) -> Dict[str, Any]:
    idl = load_idl_for_program(program)
    required_accounts = fetch_required_accounts(instruction, idl)
    signer_accounts = fetch_signer_accounts(instruction, idl)
    args_spec = fetch_args(instruction, idl)
    return {
        'idl': idl,
        'required_accounts': required_accounts,
        'signer_accounts': signer_accounts,
        'args_spec': args_spec,
    }


# --------------------------- PDA / Account Helpers ------------------------ #

def _program_id(program: str):
    module_path = os.path.join(
        anchor_base_path,
        '.anchor_files',
        program,
        'anchorpy_files',
        'program_id.py'
    )
    if not os.path.exists(module_path):
        raise FileNotFoundError("program_id.py non trovato. Hai deployato il programma?")
    spec = importlib.util.spec_from_file_location('program_id', module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore
    return module.PROGRAM_ID


def _generate_pda_from_seeds(program: str, seeds_spec: List[Dict[str, Any]]) -> Pubkey:
    seeds_bytes = []
    for s in seeds_spec:
        mode = s['mode']
        if mode == 'Wallet':
            wf = s.get('wallet')
            if wf in (None, '--'):
                raise ValueError('Seed wallet mancante')
            kp = load_keypair_from_file(os.path.join(solana_base_path, 'solana_wallets', wf))
            seeds_bytes.append(bytes(kp.pubkey()))
        elif mode == 'Random':
            seeds_bytes.append(os.urandom(32))
        elif mode == 'Manual':
            mv = s.get('manual', '')
            if not mv:
                raise ValueError('Seed manuale vuoto')
            seeds_bytes.append(mv.encode())
        else:
            raise ValueError(f"Modalità seed sconosciuta: {mode}")
    program_id = _program_id(program)
    return Pubkey.find_program_address(seeds_bytes, program_id)[0]


def build_accounts(program: str, account_inputs: List[Dict[str, Any]], signer_accounts: List[str]):
    accounts_dict = {}
    signer_keypairs = {}
    wallets_dir = os.path.join(solana_base_path, 'solana_wallets')

    for entry in account_inputs:
        acc_name = entry['name']
        method = entry['method']
        if method == 'Wallet':
            wf = entry.get('wallet')
            if wf in (None, '--'):
                raise ValueError(f"Wallet mancante per account {acc_name}")
            kp = load_keypair_from_file(os.path.join(wallets_dir, wf))
            accounts_dict[acc_name] = kp.pubkey()
            if acc_name in signer_accounts:
                signer_keypairs[acc_name] = kp
        elif method == 'PDA Manuale':
            pkey = (entry.get('pda_manual') or '').strip()
            if len(pkey) != 44:
                raise ValueError(f"PDA manuale non valida per {acc_name}")
            accounts_dict[acc_name] = Pubkey.from_string(pkey)
        elif method == 'PDA Random':
            rnd = os.urandom(32)
            b58 = b58encode(rnd).decode('utf-8')
            accounts_dict[acc_name] = Pubkey.from_string(b58)
        elif method == 'PDA Seeds':
            seeds_spec = entry.get('seeds', [])
            pda_key = _generate_pda_from_seeds(program, seeds_spec)
            accounts_dict[acc_name] = pda_key
        else:
            raise ValueError(f"Metodo account sconosciuto: {method}")
    return accounts_dict, signer_keypairs


def build_payees(payee_wallets: List[str]):
    wallets_dir = os.path.join(solana_base_path, 'solana_wallets')
    remaining_accounts = []
    seen = set()
    for w in payee_wallets:
        if w in (None, '', '--'):
            continue
        if w in seen:
            raise ValueError("Payee duplicato")
        seen.add(w)
        kp = load_keypair_from_file(os.path.join(wallets_dir, w))
        remaining_accounts.append({
            'pubkey': kp.pubkey(),
            'is_signer': False,
            'is_writable': False,
        })
    return remaining_accounts


# ------------------------------ Args parsing ------------------------------ #

def parse_args(args_spec: List[Dict[str, Any]], raw_arg_values: Dict[str, Any], instruction: str, remaining_accounts: List[Dict[str, Any]]):
    final_args = {}
    for spec in args_spec:
        name = spec['name']
        raw = raw_arg_values.get(name)
        array_type, array_length = check_if_array(spec)
        if array_type is not None:
            # array or vec
            if array_length is not None:
                if not raw:
                    raise ValueError(f"Argomento {name} mancante")
                parts = raw.split()
                if len(parts) != array_length:
                    raise ValueError(f"Array {name} deve avere {array_length} elementi")
                conv = []
                for p in parts:
                    cv = convert_type(array_type, p)
                    if cv is None:
                        raise ValueError(f"Valore non valido {p} in {name}")
                    conv.append(cv)
                final_args[name] = conv
            else:  # vec
                if raw in (None, ''):
                    final_args[name] = []
                else:
                    conv = []
                    for p in raw.split():
                        cv = convert_type(array_type, p)
                        if cv is None:
                            raise ValueError(f"Valore non valido {p} in {name}")
                        conv.append(cv)
                    final_args[name] = conv
                if name == 'shares_amounts' and instruction == 'initialize':
                    if len(final_args[name]) != len(remaining_accounts):
                        raise ValueError("shares_amounts deve avere tanti elementi quanti i payees")
        else:
            kind = check_type(spec['type'])
            if kind == 'integer':
                if raw in (None, ''):
                    raise ValueError(f"Argomento {name} mancante")
                cv = convert_type('integer', raw)
                if cv is None:
                    raise ValueError(f"Intero non valido per {name}")
                final_args[name] = cv
            elif kind == 'boolean':
                if raw not in ('true','false'):
                    raise ValueError(f"Boolean {name} non selezionato")
                final_args[name] = True if raw == 'true' else False
            elif kind == 'floating point number':
                if raw in (None, ''):
                    raise ValueError(f"Argomento {name} mancante")
                cv = convert_type('floating point number', raw)
                if cv is None:
                    raise ValueError(f"Float non valido per {name}")
                final_args[name] = cv
            elif kind == 'string':
                if raw is None:
                    raise ValueError(f"Argomento {name} mancante")
                final_args[name] = raw
            else:
                raise ValueError(f"Tipo non supportato: {kind}")
    return final_args


# ------------------ Save Transaction Result ------------------ #

def save_transaction_result(program: str,
                            instruction: str,
                            accounts: Dict[str, Any],
                            args: Dict[str, Any],
                            provider_wallet: str,
                            tx_hash: str,
                            tx_size: int,
                            tx_fees: int,
                            cluster: str) -> str:
    """Save transaction result to execution_traces_results folder."""
    results_folder = os.path.join(anchor_base_path, 'execution_traces_results')
    os.makedirs(results_folder, exist_ok=True)
    
    file_name = f"{program}_results.json"
    file_path = os.path.join(results_folder, file_name)
    
    # Format cluster with asterisk like automatic mode
    network_formatted = f"{cluster.lower()}*"
    
    result_data = {
        "network": network_formatted,
        "platform": "Solana",
        "trace_title": f"{program}_results",
        "actions": [
            {
                "sequence_id": "1",
                "function_name": instruction,
                "transaction_size_bytes": tx_size,
                "transaction_fees_lamports": tx_fees,
                "transaction_hash": tx_hash,
                "execution_time_in_slots": None
            }
        ]
    }
    
    with open(file_path, 'w') as f:
        json.dump(result_data, f, indent=2)
    
    return file_name

# ------------------ Build & (Optional) Send Transaction ------------------ #

async def _build_and_send_internal(program: str,
                                   instruction: str,
                                   accounts: Dict[str, Any],
                                   args: Dict[str, Any],
                                   signer_keypairs: Dict[str, Any],
                                   remaining_accounts: List[Dict[str, Any]],
                                   provider_wallet_file: str,
                                   send_now: bool,
                                   cluster: str,
                                   is_deployed: bool) -> Dict[str, Any]:
    """Internal async function that creates client/provider and performs all async operations."""
    provider_kp = load_keypair_from_file(os.path.join(solana_base_path, 'solana_wallets', provider_wallet_file))
    
    # Create client and provider INSIDE the async context
    client = create_client(cluster)
    provider_obj = Provider(client, Wallet(provider_kp))
    
    
    try:
        # Build transaction
        tx = await build_transaction(
            program,
            instruction,
            accounts,
            args,
            signer_keypairs,
            client,
            provider_obj,
            remaining_accounts if instruction == 'initialize' else None
        )
        
        # Measure size (sync operation)
        size = measure_transaction_size(tx)
        
        # Compute fees
        fees = await compute_transaction_fees(client, tx)
        
        # Send if requested
        tx_hash = None
        if send_now and is_deployed:
            tx_hash = await send_transaction(provider_obj, tx)
        
        return {
            'size': size,
            'fees': fees,
            'hash': str(tx_hash) if tx_hash else None,
            'sent': bool(tx_hash),
            'cluster': cluster,
            'is_deployed': is_deployed,
        }
    finally:
        # Clean up client connection
        await client.close()

def build_and_optionally_send_transaction(program: str,
                                          instruction: str,
                                          accounts: Dict[str, Any],
                                          args: Dict[str, Any],
                                          signer_keypairs: Dict[str, Any],
                                          remaining_accounts: List[Dict[str, Any]],
                                          provider_wallet_file: str,
                                          send_now: bool) -> Dict[str, Any]:
    """Synchronous wrapper that runs the entire async workflow in one go."""
    if provider_wallet_file in (None, '--'):
        raise ValueError("Seleziona provider wallet")
    
    cluster, is_deployed = fetch_cluster(program)
    
    # Run everything in a single async context to ensure client/provider stay valid
    result = _run_async(_build_and_send_internal(
        program,
        instruction,
        accounts,
        args,
        signer_keypairs,
        remaining_accounts,
        provider_wallet_file,
        send_now,
        cluster,
        is_deployed
    ))
    
    # Save to JSON if transaction was sent
    if result['sent']:
        try:
            saved_file = save_transaction_result(
                program,
                instruction,
                accounts,
                args,
                provider_wallet_file,
                result['hash'],
                result['size'],
                result['fees'],
                cluster
            )
            result['saved_file'] = saved_file
        except Exception as e:
            # Don't fail the whole operation if saving fails
            result['saved_file'] = None
            result['save_error'] = str(e)
    
    return result


# Backwards compatibility exports (minimal)
choose_program_to_run = fetch_programs  # legacy name used elsewhere

def _choose_instruction(program: str):  # legacy wrapper
    return fetch_instructions_for_program(program)
