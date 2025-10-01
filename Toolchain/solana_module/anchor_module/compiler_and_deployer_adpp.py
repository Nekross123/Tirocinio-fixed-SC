
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
import re
import json
import toml
import sys
import subprocess
import platform
from solana_module.solana_utils import run_command, choose_wallet, choose_cluster
from solana_module.anchor_module.anchor_utils import load_idl

anchor_base_path = os.path.join("solana_module", "anchor_module")


# -------------------------
# Utility
# -------------------------
def _remove_extension(filename: str) -> str:
    return os.path.splitext(filename)[0]


# =====================================================
# VERSIONE HEADLESS: COMPILAZIONE E DEPLOY TUTTO JSON
# =====================================================
def compile_and_deploy_programs(wallet_name=None, cluster="devnet", deploy=False):
    results = []
    operating_system = platform.system()
    programs_path = os.path.join(anchor_base_path, "anchor_programs")

    file_names, programs = _read_rs_files(programs_path)
    if not file_names:
        return {"success": False, "error": "Nessun programma trovato", "programs": []}

    for file_name, program_code in zip(file_names, programs):
        program_name = _remove_extension(file_name)
        program_result = {
            "program": program_name,
            "compiled": False,
            "deployed": False,
            "program_id": None,
            "signature": None,
            "anchorpy_initialized": False,
            "errors": []
        }

        try:
            compiled, program_id = _compile_program(program_name, operating_system, program_code)
            program_result["compiled"] = compiled
            program_result["program_id"] = program_id

            if compiled:
                # **Converti IDL prima di inizializzare AnchorPy**
                try:
                    _convert_idl_for_anchorpy(program_name)
                except Exception as e:
                    program_result["errors"].append(f"IDL conversion error: {str(e)}")

                # Poi inizializza AnchorPy
                try:
                    _initialize_anchorpy(program_name, program_id, operating_system)
                    program_result["anchorpy_initialized"] = True
                except Exception as e:
                    program_result["errors"].append(f"AnchorPy init error: {str(e)}")
            else:
                program_result["errors"].append("Errore durante la compilazione")
                results.append(program_result)
                continue

            if deploy:
                deploy_res = _deploy_program(program_name, operating_system, wallet_name, cluster)
                program_result["deployed"] = deploy_res.get("success", False)
                if not deploy_res.get("success", False):
                    err = deploy_res.get("error", "Errore deploy")
                    program_result["errors"].append(err)
                else:
                    program_result["program_id"] = deploy_res.get("program_id")
                    program_result["signature"] = deploy_res.get("signature")

        except Exception as e:
            program_result["errors"].append(str(e))

        results.append(program_result)

    return {"success": True, "programs": results}


# =====================================================
# FUNZIONI PRIVATE BASE
# =====================================================
def _read_rs_files(programs_path):
    if not os.path.isdir(programs_path):
        return [], []
    file_names = [f for f in os.listdir(programs_path) if f.endswith(".rs")]
    anchor_programs = []
    for file_name in file_names:
        with open(os.path.join(programs_path, file_name), "r", encoding="utf-8") as f:
            anchor_programs.append(f.read())
    return file_names, anchor_programs


def _compile_program(program_name, operating_system, program_code):
    done_init = _perform_anchor_initialization(program_name, operating_system)
    if not done_init:
        return False, None

    cargo_path = os.path.join(anchor_base_path, ".anchor_files", program_name,
                              "anchor_environment", "programs", "anchor_environment", "Cargo.toml")
    addInitIfNeeded(cargo_path, program_code)

    done_build, program_id = _perform_anchor_build(program_name, program_code, operating_system)
    return done_build, program_id


def _perform_anchor_initialization(program_name, operating_system):
    target_dir = os.path.join(anchor_base_path, ".anchor_files", program_name)
    commands = [
        f"mkdir -p {target_dir}",
        f"cd {target_dir}",
        "anchor init anchor_environment"
    ]
    run_command(operating_system, " && ".join(commands))
    return True


def _perform_anchor_build(program_name, program_code, operating_system):
    lib_path = os.path.join(anchor_base_path, ".anchor_files", program_name,
                            "anchor_environment", "programs", "anchor_environment", "src", "lib.rs")
    _write_program_in_lib_rs(lib_path, program_name, program_code)

    env_dir = os.path.dirname(lib_path)
    commands = [
        f"cd {env_dir}",
        "cargo update -p bytemuck_derive@1.9.3",
        "anchor build"
    ]
    run_command(operating_system, " && ".join(commands))

    program_id = _extract_program_id(lib_path)
    if not program_id:
        idl_path = os.path.join(anchor_base_path, ".anchor_files", program_name,
                                "anchor_environment", "target", "idl", f"{program_name}.json")
        if os.path.exists(idl_path):
            try:
                idl = load_idl(idl_path)
                program_id = idl.get("metadata", {}).get("address")
            except Exception:
                pass
    return True, program_id


def _write_program_in_lib_rs(lib_path, program_name, program_code):
    os.makedirs(os.path.dirname(lib_path), exist_ok=True)
    with open(lib_path, "w", encoding="utf-8") as f:
        f.write(program_code)


def _extract_program_id(lib_path):
    if not os.path.exists(lib_path):
        return None
    with open(lib_path, "r", encoding="utf-8") as f:
        content = f.read()
        match = re.search(r'declare_id!\s*\(\s*"([^"]+)"\s*\)\s*;', content)
        return match.group(1) if match else None


# =====================================================
# CARGO.TOML E DIPENDENZE
# =====================================================
def addInitIfNeeded(cargo_path, program_code):
    try:
        if not os.path.exists(cargo_path):
            return False
        cargo_config = toml.load(cargo_path)
        cargo_config.setdefault('dependencies', {})

        # anchor-lang
        if 'anchor-lang' in cargo_config['dependencies']:
            dep = cargo_config['dependencies']['anchor-lang']
            if isinstance(dep, dict):
                dep.setdefault('features', [])
                if 'init-if-needed' not in dep['features']:
                    dep['features'].append('init-if-needed')
            else:
                cargo_config['dependencies']['anchor-lang'] = {"version": dep, "features": ['init-if-needed']}
        else:
            cargo_config['dependencies']['anchor-lang'] = {"version": "0.31.1", "features": ['init-if-needed']}

        # anchor-spl
        if any(x in program_code for x in ['use anchor_spl', 'anchor_spl::']) and 'anchor-spl' not in cargo_config['dependencies']:
            cargo_config['dependencies']['anchor-spl'] = "0.31.1"

        # altre dipendenze comuni
        deps = {
            "pyth-sdk-solana": "0.10" if 'pyth_sdk_solana' in program_code else None,
            "switchboard-solana": "0.29" if 'switchboard_' in program_code else None,
            "spl-token": "7.0" if any(x in program_code for x in ['spl_token', 'Token', 'TokenAccount']) else None,
            "spl-associated-token-account": "4.0" if 'spl_associated_token_account' in program_code else None,
            "mpl-token-metadata": "4.1" if 'mpl_token_metadata' in program_code else None
        }
        for k, v in deps.items():
            if v and k not in cargo_config['dependencies']:
                cargo_config['dependencies'][k] = v

        with open(cargo_path, "w", encoding="utf-8") as f:
            toml.dump(cargo_config, f)
        return True
    except Exception:
        return False


# =====================================================
# ANCHORPY INIT
# =====================================================
def _initialize_anchorpy(program_name, program_id,operating_system):
    idl_path = os.path.join(
        anchor_base_path, ".anchor_files", program_name,
        "anchor_environment", "target", "idl", f"{program_name}.json"
    )
    output_dir = os.path.join(
        anchor_base_path, ".anchor_files", program_name, "anchorpy_files"
    )
    os.makedirs(output_dir, exist_ok=True)

    cmd = ["anchorpy", "client-gen", idl_path, output_dir, "--program-id", program_id]

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"AnchorPy init error: {e}")


# =====================================================
# CONVERSIONE IDL V31 -> V29
# =====================================================
def _convert_idl_for_anchorpy(program_name):
    import os, re, json
    idl_file_path = os.path.join(
        anchor_base_path, ".anchor_files", program_name,
        "anchor_environment", "target", "idl", f"{program_name}.json"
    )

    if not os.path.exists(idl_file_path):
        print(f"IDL file not found for {program_name}")
        return False

    idl_31 = load_idl(idl_file_path)


    idl_29 = {
        "version": idl_31.get("metadata", {}).get("version", "0.1.0"),
        "name": idl_31.get("metadata", {}).get("name", program_name),
        "instructions": [],
        "accounts": [],
        "errors": idl_31.get("errors", []),
        "types": []
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

    for instruction in idl_31.get("instructions", []):
        converted_instruction = {
            "name": instruction.get("name", "unknown"),
            "accounts": [],
            "args": fix_defined_types(instruction.get("args", []))
        }
        for account in instruction.get("accounts", []):
            converted_account = {
                "name": _snake_to_camel(account.get("name", "unknown")),
                "isMut": account.get("writable", False),
                "isSigner": account.get("signer", False)
            }
            converted_instruction["accounts"].append(converted_account)
        idl_29["instructions"].append(converted_instruction)

    type_definitions = {t.get("name"): t.get("type") for t in idl_31.get("types", [])}
    for account in idl_31.get("accounts", []):
        account_name = account.get("name", "unknown")
        account_type = type_definitions.get(account_name, {})
        fixed_type = fix_defined_types(account_type)
        if isinstance(fixed_type, dict) and "fields" in fixed_type:
            fixed_type["fields"] = fix_defined_types(fixed_type["fields"])
        idl_29["accounts"].append({
            "name": account_name,
            "type": fixed_type
        })

    for t in idl_31.get("types", []):
        fixed_type = fix_defined_types(t.get("type", {}))
        idl_29["types"].append({
            "name": t.get("name", "unknown"),
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
                        {"name": "Variant1"},
                        {"name": "Variant2"}
                    ]
                }
            })

    # salva IDL corretto
    with open(idl_file_path, "w", encoding="utf-8") as f:
        json.dump(idl_29, f, indent=2)

    return True


def _snake_to_camel(snake_str):
    import re
    return re.sub(r'_([a-z])', lambda m: m.group(1).upper(), snake_str)



# =====================================================
# DEPLOY PROGRAMMI
# =====================================================
def _deploy_program(program_name, operating_system, wallet_name=None, cluster="devnet"):
    if not wallet_name:
        wallet_name = choose_wallet()
    cluster = choose_cluster() if cluster is None else cluster

    anchor_toml = os.path.join(anchor_base_path, ".anchor_files", program_name, "anchor_environment", "Anchor.toml")
    if not os.path.exists(anchor_toml):
        return {"success": False, "error": f"Anchor.toml non trovato per {program_name}"}

    config = toml.load(anchor_toml)
    config['provider']['wallet'] = f"../../../../solana_wallets/{wallet_name}"
    config['provider']['cluster'] = cluster
    with open(anchor_toml, "w", encoding="utf-8") as f:
        toml.dump(config, f)

    commands = [
        f"cd {os.path.join(anchor_base_path, '.anchor_files', program_name, 'anchor_environment')}",
        "anchor deploy"
    ]
    res = run_command(operating_system, " && ".join(commands))
    output = res.stdout if res else ""
    error_output = res.stderr if res else ""

    program_id, signature = _parse_deploy_output(output)
    success = True if program_id else False

    return {
        "success": success,
        "program_id": program_id,
        "signature": signature,
        "error": None if success else (error_output or "Deploy failed"),
        "stdout": output,
        "stderr": error_output
    }


def _parse_deploy_output(output):
    pid = re.search(r"Program Id: (\S+)", output)
    sig = re.search(r"Signature: (\S+)", output)
    return pid.group(1) if pid else None, sig.group(1) if sig else None
