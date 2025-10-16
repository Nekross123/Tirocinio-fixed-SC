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
  - Interazione con funzioni/ABI, meta-transazioni (stile progetto universitario)
  - Gestione wallet EVM
- Backend Flask (`flask_backend.py`) e UI in Streamlit (`pages/*.py`, `Rosetta_SC.py`)

La repo è organizzata per lavorare bene su Windows con WSL (Ubuntu). Se usi macOS/Linux nativo, cambia poco.


---


##  Avvio applicazione

Apri due terminali (o schede):

1) Backend Flask

2) UI Streamlit


---

##  Come usare le toolchain

### Solana
- Wallet: file JSON in `Solana_module/solana_module/solana_wallets`
- Programmi: sorgenti Rust in `Solana_module/solana_module/anchor_module/anchor_programs`
- Tracce automatiche: JSON in `Solana_module/solana_module/anchor_module/execution_traces`

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
