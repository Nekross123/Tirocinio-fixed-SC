# Rosetta_SC

Benvenuto/a in Rosetta_SC! Questo progetto raccoglie (in un unico posto) tre toolchain per smart contract che puoi usare da un'unica interfaccia: Solana, Tezos ed Ethereum (EVM). È pensato per sperimentare, compilare, fare deploy e interagire con contratti senza dover saltare tra mille repo diversi.


## Cosa c'è dentro

- Solana (cartella `Solana_module/solana_module`)
  - Compilazione e deploy di programmi Anchor
  - Inserimento dati automatico e interattivo
  - Gestione wallet Solana (Devnet/Testnet/Mainnet)
- Tezos (cartella `Tezos_module/` + wrapper in `Tezos_module/tezos_module`)
  - Compilazione SmartPy, origination, chiamata entrypoint
  - Esecuzione tracce da CSV
  - Gestione wallet Tezos (Ghostnet)
- Ethereum (cartella `ethereum_module/`)
  - Compilazione con `py-solc-x` e deploy via web3.py
  - Interazione con funzioni/ABI, meta-transazioni 
  - Gestione wallet EVM
- Backend Flask (`flask_backend.py`) e UI in Streamlit (`pages/*.py`, `Rosetta_SC.py`)

La repo è organizzata per lavorare bene su Windows con WSL (Ubuntu). Se usi macOS/Linux nativo, cambia poco.


---

## Prerequisiti per toolchain

Prima di avviare l’app, assicurati di avere questi requisiti. Le dipendenze vanno installate in WSL (Ubuntu) dentro il virtual environment del progetto.

### Generali
- WSL Ubuntu (consigliato 22.04+)
- Python 3.12 e un venv attivo 
- Pacchetti Python minimi: `streamlit`, `flask`, `python-dotenv`

### Solana
Per compilare e fare deploy dei programmi Anchor e usare le funzioni di interazione:
- Rust toolchain (rustup/cargo)
- Node.js 18+ e npm
- Solana CLI (configurata su Devnet/Testnet/Mainnet)
- Anchor CLI
- Pacchetti Python: `anchorpy`, `solders`, `solana`, `toml`
- Wallet in `Solana_module/solana_module/solana_wallets` (chiavi JSON)
- Sorgenti Rust in `Solana_module/solana_module/anchor_module/anchor_programs`
- Tracce in `Solana_module/solana_module/anchor_module/execution_traces` (se usi l’esecuzione automatica)

Note: per test locali puoi usare `solana-test-validator` o Devnet con airdrop.

### Tezos
Per compilare SmartPy, fare origination e interagire su Ghostnet:
- Pacchetti Python: `pytezos`
- SmartPy CLI installata (necessaria per la compilazione SmartPy → Michelson)
- Wallet in `Tezos_module/tezos_module/tezos_wallets/wallet.json`
- Tracce CSV in `Tezos_module/toolchain/execution_traces/*.csv` (per Execute Trace)

### Ethereum (EVM)
Per compilare con py-solc-x, fare deploy e interagire:
- Pacchetti Python: `web3`, `py-solc-x`, `eth-account`
- Nodo locale per i test: Ganache CLI oppure Hardhat node
- (Opzionale per testnet/mainnet) account/endpoint: variabile `INFURA_PROJECT_ID`
- Consigliato preinstallare `solc` 0.8.18 tramite `py-solc-x`
- Contratti in `ethereum_module/hardhat_module/contracts/*.sol`, artifacts e deployments nelle relative cartelle
- Wallet in `ethereum_module/ethereum_wallets/*.json`

Se mancano dipendenze Python, installale nel venv del progetto. Per Solana/Anchor segui la documentazione ufficiale di Anchor e Solana CLI per l’installazione.

---


##  Avvio applicazione

Apri due terminali (o schede) con il venv attivo:

1) Backend Flask (python flask_backend.py)

2) UI Streamlit (streamlit run Rosetta_SC.py)

3) premi sul link nel terminale per aprire l'interfaccia web

---

##  Come usare le toolchain

### Solana
- Inseri qui i tuoi Wallet: file JSON in `Solana_module/solana_module/solana_wallets`
- Inseri qui i tuoi Programmi Rust(SC): sorgenti Rust in `Solana_module/solana_module/anchor_module/anchor_programs`
- Inseri qui le tue Tracce automatiche: JSON in `Solana_module/solana_module/anchor_module/execution_traces`

ATTENZIONE: per versioni e dipendenze esatte, vedi i file requirements nelle cartelle della toolchain:
- `Solana_module/solana_module/requirements.txt`
- `Solana_module/solana_module/anchor_module/requirements.txt`

Dal menu “Solana”:
- Upload → carichi un `.rs`
- Compile & Deploy → compila + deploy (Devnet/Testnet/Mainnet)
- Interactive Data Insertion → invio istruzioni con parametri
- Execution Traces → esecuzione automatica da file JSON

### Tezos
- Contratti: `Tezos_module/contracts/<NomeContratto>/<NomeContratto>.py`
- Wallet: `Tezos_module/tezos_module/tezos_wallets/wallet.json`
- Tracce: `Tezos_module/toolchain/execution_traces/*.csv`

Dal menu “Tezos”:
- Compile → esegue SmartPy e genera Michelson
- Deploy → origination su Ghostnet
- Interact → chiama entrypoint con parametri
- Execute Trace → esecuzione CSV (wrapper di comandi esistenti)

### Ethereum
- Contratti: `ethereum_module/hardhat_module/contracts/*.sol`
- Artifacts: `ethereum_module/hardhat_module/artifacts/*.json`
- Deployments: `ethereum_module/hardhat_module/deployments/*.json`
- Wallet: `ethereum_module/ethereum_wallets/*.json`

Dal menu “Ethereum”:
- Manage Wallets → mostra address e balance
- Upload new contract → carica `.sol`
- Compile & Deploy → compila con `py-solc-x` e deploy su localhost/Sepolia/Goerli/Mainnet
- Interactive → chiama funzioni del contratto (view/tx)
