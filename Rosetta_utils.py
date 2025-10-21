import streamlit as st
import pandas as pd
import json
from io import StringIO
import os
import re
import asyncio
from solders.pubkey import Pubkey
from anchorpy import Wallet, Provider


from Solana_module.solana_module.anchor_module.anchor_utils import anchor_base_path






def upload_trace_file():
    """UI component for uploading execution trace files via drag & drop."""
    
    st.subheader("📤 Upload Execution Trace")
    
    uploaded_file = st.file_uploader(
        "Drag and drop your execution trace JSON file here",
        type=['json'],
        help="Upload a JSON file containing the execution trace"
    )
    
    if uploaded_file is not None:
        try:
            # Read and validate JSON
            file_content = uploaded_file.read()
            json_data = json.loads(file_content)
            
            # Validate required fields
            required_fields = ["trace_title", "trace_execution"]
            missing_fields = [field for field in required_fields if field not in json_data]
            
            if missing_fields:
                st.error(f"❌ Invalid trace file. Missing required fields: {', '.join(missing_fields)}")
                return
            config_list = []

            for configuration in json_data['configuration']:
                
                use = json_data['configuration'][configuration].get("use", "False")

                if use.lower() == 'true':
                    config_list.append(configuration.lower())


               
            if "solana" in config_list :
                # Save to execution_traces folder
                traces_folder = f"{anchor_base_path}/execution_traces/"
                os.makedirs(traces_folder, exist_ok=True)

                file_path = os.path.join(traces_folder, uploaded_file.name)

                # Save the file
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, indent=2)

            if "tezos" in config_list :
                print("add tezos path")
            if "cardano" in config_list :
                print("add cardano path")
            if "evm" in config_list :
                print("add evm path")
               
            st.info(f"📁 Saved to: `execution_traces/{uploaded_file.name}`")
            st.success(f"✅ Trace file `{uploaded_file.name}` uploaded successfully , you can find and choose the list of toolchains below:")
            showLinks(config_list)
            
                
        except json.JSONDecodeError:
            st.error("❌ Invalid JSON file. Please upload a valid JSON trace file.")
        except Exception as e:
            st.error(f"❌ Error uploading file: {str(e)}")

def showLinks(config_list):
    """Show links to relevant toolchain pages based on configuration."""
    col1, = st.columns(1)
    with col1:
        if "solana" in config_list :
            st.page_link("pages/Solana.py", label="🌞 Solana Toolchain")
        if "tezos" in config_list :
            st.page_link("pages/Tezos.py", label="🔷 Tezos Toolchain")
        if "evm" in config_list :
            st.page_link("pages/Ethereum.py", label="⚡ Ethereum Toolchain")
        if "cardano" in config_list :
            st.page_link("pages/Cardano.py", label="🧩 Cardano Toolchain")



