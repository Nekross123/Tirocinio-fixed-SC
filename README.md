# Rosetta_SC

Welcome to Rosetta_SC!
This project brings together three **smart contract toolchains** — **Solana**, **Tezos**, and **Ethereum (EVM)** — into a single interface.
It’s designed to let you **experiment, compile, deploy, and interact** with smart contracts all in one place.

---

## Contents

* **Solana** (`Solana_module/solana_module`)

  * Anchor program compilation and deployment
  * Automatic and interactive data insertion
  * Solana wallet management (Devnet/Testnet/Mainnet)
* **Tezos** (`Tezos_module/` + wrapper in `Tezos_module/tezos_module`)

  * SmartPy compilation, origination, and entrypoint calls
  * CSV-based execution traces
  * Tezos wallet management (Ghostnet)
* **Ethereum (EVM)** (`ethereum_module/`)

  * Compilation via `py-solc-x` and deployment using `web3.py`
  * ABI interaction, meta-transactions
  * EVM wallet management
* **Backend Flask** (`flask_backend.py`) and **Streamlit UI** (`pages/*.py`, `Rosetta_SC.py`)

The repository is optimized for **Windows + WSL (Ubuntu)**.
If you’re using native macOS or Linux, everything works nearly the same.

---

## Prerequisites

Before running the app, make sure you meet the following requirements.
All dependencies must be installed **inside your WSL Ubuntu virtual environment**.

### General

* WSL Ubuntu (recommended 22.04+)
* Python 3.12 with an active virtual environment
* Core Python packages: `streamlit`, `flask`, `python-dotenv`

---

### Solana

To compile and deploy Anchor programs and use the interactive tools:

* Rust toolchain (`rustup` / `cargo`)
* Node.js 18+ and npm
* Solana CLI (configured for Devnet/Testnet/Mainnet)
* Anchor CLI
* Python packages: `anchorpy`, `solders`, `solana`, `toml`
* Wallets in `Solana_module/solana_module/solana_wallets` (JSON keypairs)
* Rust sources in `Solana_module/solana_module/anchor_module/anchor_programs`
* Execution traces in `Solana_module/solana_module/anchor_module/execution_traces` (for automated runs)

Note: For local testing, use `solana-test-validator` or Devnet with airdrop.

---

### Tezos

To compile SmartPy contracts, originate them, and interact on Ghostnet:

* Python package: `pytezos`
* SmartPy CLI (required to compile SmartPy → Michelson)
* Wallet in `Tezos_module/tezos_module/tezos_wallets/wallet.json`
* CSV traces in `Tezos_module/toolchain/execution_traces/*.csv` (for trace execution)

---

### Ethereum (EVM)

For compilation, deployment, and interaction:

* Python packages: `web3`, `py-solc-x`, `eth-account`
* Local node: Ganache CLI or Hardhat node
* (Optional for testnet/mainnet): environment variable `INFURA_PROJECT_ID`
* Recommended compiler: `solc` 0.8.18 via `py-solc-x`
* Contracts in `ethereum_module/hardhat_module/contracts/*.sol`
* Artifacts and deployments in their respective folders
* Wallets in `ethereum_module/ethereum_wallets/*.json`

If any Python dependencies are missing, install them in your venv.
For Solana/Anchor, follow the official CLI installation guides.

---

## Running the Application

Open **two terminal windows (or tabs)** with your venv activated:

1. Start Flask backend:
   `python flask_backend.py`

2. Start Streamlit UI:
   `streamlit run Rosetta_SC.py`

3. Click the link displayed in the terminal to open the web interface.

---

## Using the Toolchains

### Solana

* Add your wallets: `Solana_module/solana_module/solana_wallets/*.json`
* Add your programs: `Solana_module/solana_module/anchor_module/anchor_programs`
* Add trace files: `Solana_module/solana_module/anchor_module/execution_traces/*.json`

Check exact dependencies in:

* `Solana_module/solana_module/requirements.txt`
* `Solana_module/solana_module/anchor_module/requirements.txt`

From the **Solana menu**:

* **Upload** → upload a `.rs` file
* **Compile & Deploy** → compile + deploy to Devnet/Testnet/Mainnet
* **Interactive Data Insertion** → send on-chain instructions with parameters
* **Execution Traces** → run automatic sequences from JSON

---

### Tezos

* Contracts: `Tezos_module/contracts/<ContractName>/<ContractName>.py`
* Wallet: `Tezos_module/tezos_module/tezos_wallets/wallet.json`
* Traces: `Tezos_module/toolchain/execution_traces/*.csv`

From the **Tezos menu**:

* **Compile** → run SmartPy compiler and generate Michelson
* **Deploy** → originate contract on Ghostnet
* **Interact** → call entrypoints with parameters
* **Execute Trace** → run a full CSV-defined sequence

---

### Ethereum

* Contracts: `ethereum_module/hardhat_module/contracts/*.sol`
* Artifacts: `ethereum_module/hardhat_module/artifacts/*.json`
* Deployments: `ethereum_module/hardhat_module/deployments/*.json`
* Wallets: `ethereum_module/ethereum_wallets/*.json`

From the **Ethereum menu**:

* **Manage Wallets** → view addresses and balances
* **Upload new contract** → upload `.sol` files
* **Compile & Deploy** → compile via `py-solc-x` and deploy to localhost/Sepolia/Goerli/Mainnet
* **Interactive** → call contract functions (view or transaction)

---

Enjoy experimenting with multi-chain smart contracts in one unified environment 🚀
