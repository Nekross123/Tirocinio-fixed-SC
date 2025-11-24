import os
import re
import json
import toml
import sys
import subprocess
import platform
from Solana_module.solana_module.solana_utils import run_command, choose_wallet, choose_cluster
from Solana_module.solana_module.anchor_module.anchor_utils import load_idl

anchor_base_path = os.path.join("Solana_module", "solana_module", "anchor_module")


# -------------------------
# Utility
# -------------------------
def _remove_extension(filename: str) -> str:
    return os.path.splitext(filename)[0]


# =====================================================
# VERSIONE HEADLESS: COMPILAZIONE E DEPLOY TUTTO JSON
# =====================================================
def compile_and_deploy_programs(wallet_name=None, cluster="Devnet", deploy=False, single_program=None):
    """Headless compile -> optional anchorpy init -> optional deploy pipeline.

    Returns a JSON-friendly dict per program with compile/deploy results, IDs,
    and any errors. Supports selecting a single program by filename.
    """

    results = []
    operating_system = platform.system()
    programs_path = os.path.join(anchor_base_path, "anchor_programs")

    allowed = {"Devnet", "Localnet", "Mainnet"}
    if cluster not in allowed:
        return {"success": False, "error": f"Cluster non supportato: {cluster}", "programs": []}

    file_names, programs = _read_rs_files(programs_path, single_program)
    if not file_names:
        if single_program:
            return {"success": False, "error": f"Programma '{single_program}' non trovato", "programs": []}
        else:
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

            if not compiled:
                program_result["errors"].append("Errore durante la compilazione")
                results.append(program_result)
                continue

            try:
                idl_converted = _convert_idl_for_anchorpy(program_name)
                if not idl_converted:
                    program_result["errors"].append("IDL non trovata o conversione fallita")
            except Exception as e:
                program_result["errors"].append(f"IDL conversion error: {str(e)}")

            if program_id:
                try:
                    _initialize_anchorpy(program_name, program_id, operating_system)
                    program_result["anchorpy_initialized"] = True
                except Exception as e:
                    program_result["errors"].append(f"AnchorPy init error: {str(e)}")
            else:
                program_result["errors"].append("Program ID non determinato dopo la build")

            if deploy and program_id:
                deploy_res = _deploy_program(program_name, operating_system, wallet_name, cluster)
                program_result["deployed"] = deploy_res.get("success", False)
                if not deploy_res.get("success", False):
                    err = deploy_res.get("error", "Errore deploy")
                    program_result["errors"].append(err)
                else:
                    program_result["program_id"] = deploy_res.get("program_id")
                    program_result["signature"] = deploy_res.get("signature")
            elif deploy and not program_id:
                program_result["errors"].append("Deploy saltato: program_id assente")
        except Exception as e:
            program_result["errors"].append(str(e))
        results.append(program_result)

    return {"success": True, "programs": results}



# =====================================================
# FUNZIONI PRIVATE BASE
# =====================================================
def _read_rs_files(programs_path, single_program=None):
    """Read .rs files from anchor_programs, optional filtering by one program name."""
    if not os.path.isdir(programs_path):
        return [], []
    
    all_files = [f for f in os.listdir(programs_path) if f.endswith(".rs")]
    
    # Se è specificato un singolo programma, filtra solo quello
    if single_program:
        if single_program in all_files:
            file_names = [single_program]
        else:
            return [], []  # Programma non trovato
    else:
        file_names = all_files
    
    anchor_programs = []
    for file_name in file_names:
        with open(os.path.join(programs_path, file_name), "r", encoding="utf-8") as f:
            anchor_programs.append(f.read())
    return file_names, anchor_programs


def _compile_program(program_name, operating_system, program_code):
    """Initialize, update Cargo.toml, build, and return (success, program_id)."""
    done_init = _perform_anchor_initialization(program_name, operating_system)
    if not done_init:
        return False, None, None, None

    cargo_path = os.path.join(anchor_base_path, ".anchor_files", program_name,
                              "anchor_environment", "programs", "anchor_environment", "Cargo.toml")
    try:
        addInitIfNeeded(cargo_path, program_code)
    except Exception as e:
        return False, None

    success, program_id = _perform_anchor_build(program_name, program_code, operating_system)
    return success, program_id


def _perform_anchor_initialization(program_name, operating_system):
    """Create project folders and run anchor init for the program."""
    target_dir = os.path.join(anchor_base_path, ".anchor_files", program_name)
    commands = [
        f"mkdir -p {target_dir}",
        f"cd {target_dir}",
        "anchor init anchor_environment"
    ]
    run_command(operating_system, " && ".join(commands))
    return True


def _perform_anchor_build(program_name, program_code, operating_system):
    """Write lib.rs with detected program_id, run cargo update + anchor build."""

    root_env_dir = os.path.join(anchor_base_path, ".anchor_files", program_name, "anchor_environment")
    lib_path = os.path.join(root_env_dir, "programs", "anchor_environment", "src", "lib.rs")

    # Aggiorna codice con program_id generato da anchor init
    try:
        updated_code, program_id = _update_program_id(lib_path, program_code)
    except Exception:
        updated_code = program_code
        program_id = None

    _write_program_in_lib_rs(lib_path, program_name, updated_code)

    commands = [
        f"cd {root_env_dir}",
        #pay attention to this, bytemuck_derive changes often , avoid a specific version if possible
        "cargo update -p bytemuck_derive", #occhio cambia spesso
        "anchor build"
    ]
    concatenated = " && ".join(commands)
    result = run_command(operating_system, concatenated)
   

    # errore -Znext
    if result and hasattr(result, 'stderr') and result.stderr and '-Znext' in result.stderr:
        try:
            _impose_cargo_lock_version(program_name)
            result = run_command(operating_system, concatenated)
        except Exception:
            pass

    # Se non abbiamo program_id, proviamo ad estrarlo adesso dal file scritto
    if not program_id:
        program_id = _extract_program_id(lib_path)

    # Fallback IDL
    if not program_id:
        idl_path = os.path.join(root_env_dir, "target", "idl", f"{program_name}.json")
        if os.path.exists(idl_path):
            try:
                idl = load_idl(idl_path)
                program_id = idl.get("metadata", {}).get("address")
            except Exception:
                pass

    success = bool(result) and (getattr(result, 'returncode', 0) == 0) and program_id is not None
    return success, program_id


def _write_program_in_lib_rs(lib_path, program_name, program_code):
    """Persist the updated Rust source to lib.rs for the initialized project."""
    os.makedirs(os.path.dirname(lib_path), exist_ok=True)
    with open(lib_path, "w", encoding="utf-8") as f:
        f.write(program_code)


def _extract_program_id(lib_path):
    """Try to regex-extract program_id from lib.rs; return None if not found."""
    if not os.path.exists(lib_path):
        return None
    with open(lib_path, "r", encoding="utf-8") as f:
        content = f.read()
        match = re.search(r'declare_id!\s*\(\s*"([^"]+)"\s*\)\s*;', content)
        return match.group(1) if match else None


# =====================================================
# CARGO.TOML E DIPENDENZE
# =====================================================
def _detect_dependencies_from_code(program_code: str):
    """Heuristically identify Rust deps (pyth, switchboard, spl, mpl, sha3, etc.)."""
    deps = {}
    if 'pyth_sdk_solana' in program_code or 'pyth_sdk_solana::' in program_code:
        deps['pyth-sdk-solana'] = '0.10'
    if 'switchboard_' in program_code:
        deps['switchboard-solana'] = '0.29'
    if any(x in program_code for x in ['spl_token', 'spl_token::', 'Token', 'TokenAccount']):
        deps['spl-token'] = '7.0'
    if 'spl_associated_token_account' in program_code:
        deps['spl-associated-token-account'] = '4.0'
    if 'mpl_token_metadata' in program_code or 'mpl_token_metadata::' in program_code:
        deps['mpl-token-metadata'] = '4.1'
    if 'sha3::' in program_code or 'Keccak256' in program_code or 'use sha3' in program_code:
        deps['sha3'] = '0.10'
    return deps

def _check_for_anchor_spl_usage(program_code: str):
    """Return True if anchor_spl usage indicators are present in the code."""
    indicators = [
        'use anchor_spl', 'anchor_spl::', 'Token,', 'TokenAccount,', 'AssociatedToken',
        'SetAuthority', 'Transfer', 'token::', 'associated_token::'
    ]
    return any(i in program_code for i in indicators)

def addInitIfNeeded(cargo_path, program_code):
    """Ensure anchor-lang init-if-needed and add detected deps/features to Cargo.toml."""
    try:
        if not os.path.exists(cargo_path):
            return False
        cargo_config = toml.load(cargo_path)
        cargo_config.setdefault('dependencies', {})

        needs_anchor_spl = _check_for_anchor_spl_usage(program_code)

        # anchor-lang
        anchor_dep = cargo_config['dependencies'].get('anchor-lang')
        if anchor_dep:
            if isinstance(anchor_dep, dict):
                feats = anchor_dep.setdefault('features', [])
                if 'init-if-needed' not in feats:
                    feats.append('init-if-needed')
            else:
                cargo_config['dependencies']['anchor-lang'] = {
                    'version': anchor_dep,
                    'features': ['init-if-needed']
                }
        else:
            cargo_config['dependencies']['anchor-lang'] = {
                'version': '0.32.1', 
                'features': ['init-if-needed']
            }

        if needs_anchor_spl and 'anchor-spl' not in cargo_config['dependencies']:
            cargo_config['dependencies']['anchor-spl'] = '0.32.1'

        # Additional detected deps
        detected = _detect_dependencies_from_code(program_code)
        for k, v in detected.items():
            if k not in cargo_config['dependencies']:
                cargo_config['dependencies'][k] = v

        # Force spl-token if token-like usage
        token_indicators = ['Token', 'TokenAccount', 'Mint', 'transfer', 'mint_to', 'burn', 'freeze_account',
                            'thaw_account', 'set_authority', 'spl_token::', 'token::']
        if any(t in program_code for t in token_indicators) and 'spl-token' not in cargo_config['dependencies']:
            cargo_config['dependencies']['spl-token'] = '7.0'
        # Features section
        cargo_config.setdefault('features', {})
        if needs_anchor_spl:
            idl_build = cargo_config['features'].get('idl-build')
            if not isinstance(idl_build, list):
                idl_build = [] if idl_build is None else list(idl_build)
            if 'anchor-lang/idl-build' not in idl_build:
                idl_build.append('anchor-lang/idl-build')
            if 'anchor-spl/idl-build' not in idl_build:
                idl_build.append('anchor-spl/idl-build')
            cargo_config['features']['idl-build'] = idl_build
        else:
            idl_build = cargo_config['features'].get('idl-build')
            if not isinstance(idl_build, list):
                idl_build = [] if idl_build is None else list(idl_build)
            if 'anchor-lang/idl-build' not in idl_build:
                idl_build.append('anchor-lang/idl-build')
            cargo_config['features']['idl-build'] = idl_build

        # Ensure standard features exist
        required_features = ['default', 'cpi', 'no-entrypoint', 'no-idl', 'no-log-ix-name']
        for feat in required_features:
            if feat not in cargo_config['features']:
                if feat == 'cpi':
                    cargo_config['features'][feat] = ['no-entrypoint']
                else:
                    cargo_config['features'][feat] = []

        # lib section
        cargo_config.setdefault('lib', {})
        cargo_config['lib'].setdefault('crate-type', ['cdylib', 'lib'])
        if 'name' not in cargo_config['lib']:
            pkg_name = cargo_config.get('package', {}).get('name', 'anchor_environment')
            cargo_config['lib']['name'] = pkg_name

        with open(cargo_path, 'w', encoding='utf-8') as f:
            toml.dump(cargo_config, f)
        return True
    except Exception:
        return False

def _update_program_id(lib_rs_path, program_code):
    """Replace declare_id!(...) with the program_id from the generated lib.rs."""
    """Legge il program id generato da anchor init e lo inserisce nel nuovo sorgente."""
    if not os.path.exists(lib_rs_path):
        raise FileNotFoundError("lib.rs non trovato per aggiornare il program id")
    with open(lib_rs_path, 'r', encoding='utf-8') as f:
        content = f.read()
    match = re.search(r'declare_id!\s*\(\s*"([^"]+)"\s*\)\s*;', content)
    if not match:
        raise ValueError("Program ID non trovato nel lib.rs generato")
    new_program_id = match.group(1)
    updated = re.sub(r'declare_id!\s*\(\s*"([^"]+)"\s*\)\s*;', f'declare_id!("{new_program_id}");', program_code)
    return updated, new_program_id

def _impose_cargo_lock_version(program_name):
    """Force Cargo.lock lines to version = 3 to mitigate -Znext errors."""
    file_path = os.path.join(anchor_base_path, '.anchor_files', program_name, 'anchor_environment', 'Cargo.lock')
    if not os.path.exists(file_path):
        return
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        with open(file_path, 'w', encoding='utf-8') as f:
            for line in lines:
                line = re.sub(r'^version = \d+', 'version = 3', line)
                f.write(line)
    except Exception:
        pass


# =====================================================
# ANCHORPY INIT
# =====================================================
def _initialize_anchorpy(program_name, program_id,operating_system):
    """Generate Python client code with anchorpy client-gen."""
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
    """Convert Anchor v31-style IDL to v29 format expected by AnchorPy."""
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
    """Convert snake_case to camelCase for IDL account names."""
    import re
    return re.sub(r'_([a-z])', lambda m: m.group(1).upper(), snake_str)



# =====================================================
# DEPLOY PROGRAMMI
# =====================================================
def _deploy_program(program_name, operating_system, wallet_name=None, cluster="Devnet"):
    """Deploy an Anchor program after updating Anchor.toml with wallet/cluster."""
    if not wallet_name:
        wallet_name = choose_wallet()

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
    """Extract Program Id and Signature from anchor deploy output (regex-based)."""
    pid = re.search(r"Program Id: (\S+)", output)
    sig = re.search(r"Signature: (\S+)", output)
    return pid.group(1) if pid else None, sig.group(1) if sig else None