import streamlit as st

# ==============================
# Configurazione pagina
# ==============================
st.set_page_config(
    page_title="Rosetta SC - Home",
    page_icon="🌹",
    layout="wide"
)

# ==============================
# Titolo e descrizione
# ==============================
st.title("🌹 Benvenuto in Rosetta Smart Contract")

st.markdown("""
Questa applicazione ti permette di gestire facilmente le tue **toolchain per Smart Contract**.

### Come iniziare:
1. Sulla sinistra, nella **sidebar**, seleziona la toolchain desiderata:
   - **Solana** per lavorare con smart contract Solana.
   - **Tezos** per lavorare con smart contract Tezos.
2. Ogni toolchain ha le proprie funzionalità:

""")

# ==============================
# Footer
# ==============================
st.markdown("---")
st.write("© 2025 - Rosetta SC")
