from Solana_module.solana_module.anchor_module.dapp_automatic_insertion_manager import  fetch_initialized_programs , build_table
from Rosetta_utils import upload_trace_file
from flask import Flask, request, jsonify
import streamlit as st
import pandas as pd
import os
import sys
import requests
import json
import asyncio
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), "Solana_module"))

# ==============================
# Import moduli Solana
# ==============================

import Solana_module.solana_module.anchor_module.compiler_and_deployer_adpp as toolchain
from  Solana_module.solana_module.solana_utils import load_keypair_from_file, create_client
import  Solana_module.solana_module.anchor_module.dapp_automatic_insertion_manager as trace_manager


TRACES_PATH = os.path.join( "Solana_module","solana_module", "anchor_module", "execution_traces")





# ==============================
# Configurazione pagina
# ==============================
st.set_page_config(
    page_title="Rosetta SC - Home",
    page_icon="🌹",
    layout="wide"
)

# ==============================
# Sidebar
# ==============================


# ==============================
# Titolo e descrizione
# ==============================s
st.title("🌹 Welcome to Rosetta Smart Contract")
st.markdown("""
This application let you manage easily your **Smart Contract toolchains**.
### Quick Start Guide:
1. On the left you have the **sidebar**, select the toolchain you want to use:
   - **Solana** per lavorare con smart contract Solana.
   - **Tezos** per lavorare con smart contract Tezos.
3. After deploying a program, you can use the **Automatic Data Insertion** feature , which is present in each toolchain, to test it with predefined execution traces.
    The results will be printe below after the execution.
""")
upload_trace_file()
# ==============================
# Footer
# ==============================
st.markdown("---")
st.write("© 2025 - Rosetta SC")
