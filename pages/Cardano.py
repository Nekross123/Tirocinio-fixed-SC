import json
import os
import binascii
import subprocess
from pathlib import Path
import streamlit as st
from Cardano_module.cardano_module.cardano_utils import cardano_base_path

CONTRACTS_DIR = Path.cwd() / "uploads" / "plutus"
CONTRACTS_DIR.mkdir(parents=True, exist_ok=True)

TRACES_DIR = Path(cardano_base_path).expanduser().resolve() / "execution_traces"
TRACES_DIR.mkdir(parents=True, exist_ok=True)

PROTO_DIR = Path.cwd()

# Header
st.set_page_config(page_title="Cardano DApp", page_icon="🔶", layout="wide")
st.title("🔶 Cardano Toolchain")

# Menu
st.sidebar.header("Menu")
mode = st.sidebar.radio(
    "Select an operation",
    ["Upload Raw Contract", "Calculate Fee and Size"],
    index=0
)

# Helpers
def detect_cardano_cli() -> str | None:
    exe = "cardano-cli.exe" if os.name == "nt" else "cardano-cli"
    from shutil import which
    return which(exe)

def list_uploaded_contracts():
    """Return a sorted list of (display_name, absolute_path) for saved .plutus.json files."""
    files = sorted(CONTRACTS_DIR.glob("*.json"))
    return [(f.name, f) for f in files]

def list_uploaded_traces():
    """Return a sorted list of saved traces."""
    files = sorted(TRACES_DIR.glob("*.json"))
    return [(f.name, f) for f in files]

def extract_plutus_cbor_hex(plutus_json_str: str) -> str:
    # Extract cborHex from common .plutus.json possible configurations.
    data = json.loads(plutus_json_str)
    candidates = []

    if isinstance(data, dict):
        # flat
        if isinstance(data.get("cborHex"), str):
            candidates.append(data["cborHex"])
        # nested
        if isinstance(data.get("plutusScript"), dict):
            ch = data["plutusScript"].get("cborHex")
            if isinstance(ch, str):
                candidates.append(ch)
        # Aiken bundle-like
        vals = data.get("validators")
        if isinstance(vals, list):
            for v in vals:
                if isinstance(v, dict):
                    if isinstance(v.get("cborHex"), str):
                        candidates.append(v["cborHex"])
                    cc = v.get("compiledCode")
                    if isinstance(cc, dict) and isinstance(cc.get("cborHex"), str):
                        candidates.append(cc["cborHex"])

    for c in candidates:
        c = c.strip()
        if c:
            return c
    raise ValueError("Could not find 'cborHex' in the uploaded .plutus.json.")

def hex_size_bytes(hex_str: str) -> int:
    hex_str = hex_str.strip().lower()
    if hex_str.startswith("0x"):
        hex_str = hex_str[2:]
    try:
        return len(binascii.unhexlify(hex_str))
    except binascii.Error as e:
        raise ValueError(f"Invalid cborHex (not hex?): {e}")


def view_validator_size():
    st.header("Upload Raw Contract")
    plutus_file = st.file_uploader("Upload Validator (.plutus.json)", type=["json"], accept_multiple_files=False)

    if "plutus_info" not in st.session_state:
        st.session_state.plutus_info = None

    if plutus_file and st.button("Upload Validator"):
        try:
            pjson = plutus_file.getvalue().decode("utf-8")
            (CONTRACTS_DIR / plutus_file.name).write_text(pjson, encoding="utf-8")
            cbor_hex = extract_plutus_cbor_hex(pjson)
            script_bytes = hex_size_bytes(cbor_hex)
            st.session_state.plutus_info = {
                "file": plutus_file.name,
                "script_bytes": script_bytes
            }
            st.success("Validator uploaded successfully.")
            m1, = st.columns(1)
            with m1:
                st.metric("Script size (bytes)", f"{script_bytes}")
            with st.expander("Details"):
                st.json(st.session_state.plutus_info)
        except Exception as e:
            st.error(f"Error during analysis: {e}")

def view_calculate_fee_cli():
    st.header("Calculate Min Fee — cardano-cli")
    cli_path = detect_cardano_cli()
    st.write(f"`cardano-cli` detected: {cli_path if cli_path else 'not in PATH'}")

    cA, cB = st.columns(2)
    with cA:
        proto_file = st.file_uploader("Protocol parameters (protocol-parameters.json)", type=["json"], accept_multiple_files=False)
    with cB:
        uploaded_scripts = list_uploaded_contracts()
        if not uploaded_scripts:
            st.warning("Missing Validators. Go to 'Upload Raw Contract' and upload one or more .plutus.json.")
            return
        script_names = [name for name, _ in uploaded_scripts]
        script_choice = st.selectbox("Select the validator (.plutus.json)", script_names, index=0)
        script_file = dict(uploaded_scripts)[script_choice]

    uploaded_traces = list_uploaded_traces()
    if not uploaded_traces:
        st.warning("Missing Traces. Go to 'Rosetta SC' and upload one or more .json traces.")
        return
    trace_names = [name for name, _ in uploaded_traces]
    trace_choice = st.selectbox("Select the trace", trace_names, index=0)
    trace_file = dict(uploaded_traces)[trace_choice]

    st.caption("You can manually add tx and witness information (if they're not already present in trace files)")
    r1, r2, r3 = st.columns(3)
    with r1:
        out_count = st.number_input("tx-out count", min_value=0, value=2, step=1)
    with r2:
        witness_count = st.number_input("witness count", min_value=0, value=1, step=1, help="Sum of key + script witnesses (not Byron).")
    with r3:
        byron_witness_count = st.number_input("Byron witness count", min_value=0, value=0, step=1)

    if st.button("Calculate with cardano-cli"):
        results = []

        if not cli_path:
            st.error("`cardano-cli` not found in PATH.")
            return
        
        if proto_file:
            try:
                file_content = proto_file.read()
                proto_data = json.loads(file_content)

                proto_path = os.path.join(PROTO_DIR, proto_file.name)
                # Save the file
                with open(proto_path, 'w', encoding='utf-8') as f:
                    json.dump(proto_data, f, indent=2)
            except Exception as e:
                st.error(f"Error during protocol file parsing: {e}")
        else:
            st.error("Upload protocol parameters.")
            return

        try:
            DEFAULT_TX_IN = "0000000000000000000000000000000000000000000000000000000000000000#0"
            DEFAULT_ADDR  = "addr_test1vr8rgrxvlgg0wh3d05yhg53lw3n80fj7m8p0j2mj6r0hkyc4x98sf+0"

            raw_file = Path.cwd() / "tmp_tx.body"

            print(trace_file)
            trace_json = json.load(open(trace_file))

            for id, _ in enumerate(trace_json.get("trace_execution")):
                card = trace_json.get("trace_execution", [{}])[id].get("cardano", {})
                tx_in = card.get("in_utxo", DEFAULT_TX_IN) or DEFAULT_TX_IN
                tx_out_1 = card.get("out_addr_1", DEFAULT_ADDR) or DEFAULT_ADDR
                tx_out_2 = card.get("out_addr_2", DEFAULT_ADDR) or DEFAULT_ADDR

                datum_str = trace_json["trace_execution"][id]["cardano"]["datum"]
                redeemer_str = trace_json["trace_execution"][id]["cardano"]["redeemer"]
                
                build_cmd = [
                    cli_path,
                    "conway", "transaction", "build-raw",
                    "--fee", "0",
                    "--tx-in", str(tx_in),
                    "--tx-out", str(tx_out_1),
                    "--tx-out", str(tx_out_2),
                    "--tx-in-script-file", str(script_file),
                    "--tx-in-datum-value", str(datum_str).replace("'", "\""),
                    "--tx-in-redeemer-value", str(redeemer_str).replace("'", "\"") ,
                    "--tx-in-execution-units", "(0,0)",
                    "--out-file", str(raw_file)
                ]
                build_res = subprocess.run(build_cmd, capture_output=True, text=True, check=True)
                

                tx_size_bytes = raw_file.stat().st_size

                out_count = card.get("out_count", out_count) or out_count
                witness_count = card.get("witness_count", witness_count) or witness_count
                byron_witness_count = card.get("byron_witness_count", byron_witness_count) or byron_witness_count

                fee_cmd = [
                    cli_path,
                    "conway", "transaction", "calculate-min-fee",
                    "--tx-body-file", str(raw_file),
                    "--protocol-params-file", str(proto_path),
                    "--tx-in-count", str(len(trace_json["trace_execution"][id]["actors"])),
                    "--tx-out-count", str(out_count),
                    "--witness-count", str(witness_count),
                    "--byron-witness-count", str(byron_witness_count),
                    "--mainnet"
                ]
                fee_res = subprocess.run(fee_cmd, capture_output=True, text=True, check=True)
                cli_fee_str = fee_res.stdout.strip()
                results.append([id, tx_size_bytes, cli_fee_str])

            st.subheader("Results")

            for res in results:
                st.text(f"Sequence ID {res[0]}")
                m1, m2 = st.columns(2)
                with m1:
                    st.metric("Tx body size (bytes)", f"{res[1]}")
                with m2:
                    st.metric("Min fee (cardano-cli)", res[2])

                with st.expander("Executed Command:"):
                    st.code(" ".join(fee_cmd), language="bash")
                    st.code(fee_res.stdout, language="text")

        except subprocess.CalledProcessError as e:
            st.error(f"cardano-cli error: {e.stderr or e.stdout or str(e)}")
        except Exception as e:
            st.error(f"Errore: {e}")

# Router
if mode == "Upload Raw Contract":
    view_validator_size()
elif mode == "Calculate Fee and Size":
    view_calculate_fee_cli()

# Footer
st.markdown("---")
st.write("© 2025 - Cardano")
