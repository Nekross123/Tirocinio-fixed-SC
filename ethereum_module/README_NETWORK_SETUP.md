# Ethereum Network Setup Guide

## Problemi Risolti

### 1. INFURA_PROJECT_ID Configuration
**Problema precedente**: Il codice usava `os.getenv('INFURA_PROJECT_ID', '')` che restituiva stringa vuota se non configurato, causando URL non validi.

**Soluzione**: Ora il sistema:
- Controlla se l'ID è presente prima di costruire gli URL
- Mostra errori chiari se manca per reti pubbliche
- Fornisce istruzioni per ottenerlo e configurarlo

### 2. Network Hardcoding
**Problema precedente**: Molte funzioni avevano `network="localhost"` hardcoded come default.

**Soluzione**: Implementato sistema di rete globale:
- `DEFAULT_NETWORK` globale configurabile
- Funzioni usano `network=None` e fallback al default
- Possibilità di cambiare rete per tutta l'applicazione

## Come Configurare

### Per Localhost (Ganache/Hardhat)
```python
from ethereum_module.ethereum_utils import setup_ethereum_environment

# Default è già localhost
setup_ethereum_environment()
```

### Per Reti Pubbliche (Sepolia, Goerli, Mainnet)

1. **Ottieni un Infura Project ID**:
   - Vai su https://infura.io/
   - Crea un account gratuito
   - Crea un nuovo progetto
   - Copia il Project ID

2. **Configura la variabile d'ambiente**:
   ```bash
   export INFURA_PROJECT_ID=your_project_id_here
   ```

3. **Usa nel codice**:
   ```python
   from ethereum_module.ethereum_utils import setup_ethereum_environment, set_default_network
   
   # Imposta rete di default
   set_default_network('sepolia')
   
   # Verifica configurazione
   setup_ethereum_environment()
   ```

## Funzioni Aggiornate

### Nuove Funzioni
- `set_default_network(network)`: Imposta rete di default
- `get_default_network()`: Ottieni rete corrente
- `setup_ethereum_environment()`: Verifica configurazione completa
- `verify_network_connection()`: Testa connessione

### Funzioni Modificate
Tutte le funzioni ora usano `network=None` e fallback al default:
- `create_web3_instance()`
- `get_wallet_balance()`
- `estimate_gas_price()`
- `send_eth_transaction()`
- `wait_for_transaction_receipt()`

## Esempio Completo

```python
from ethereum_module.ethereum_utils import (
    setup_ethereum_environment, 
    set_default_network,
    get_wallet_balance,
    create_ethereum_wallet
)

# Configurazione iniziale
set_default_network('sepolia')  # o 'localhost', 'goerli', 'mainnet'

# Verifica ambiente
if setup_ethereum_environment():
    print("✓ Ambiente configurato correttamente")
    
    # Ora tutte le funzioni useranno 'sepolia' come default
    balance = get_wallet_balance('path/to/wallet.json')  # usa sepolia
    
    # O specifica rete esplicitamente
    balance = get_wallet_balance('path/to/wallet.json', network='localhost')
else:
    print("✗ Problemi di configurazione")
```

## Cos'è Infura?

**Infura** è un servizio che fornisce accesso ai nodi Ethereum senza dover gestire un nodo completo:

- **Gratuito** fino a 100.000 richieste/giorno
- **Reti supportate**: Mainnet, Sepolia, Goerli, Polygon, etc.
- **Alternative**: Alchemy, QuickNode, Moralis
- **Senza Infura**: Devi gestire un nodo Ethereum completo (richiede ~500GB+ di storage)

## Reti Disponibili

- **localhost**: Ganache o Hardhat locale (no Infura needed)
- **sepolia**: Testnet Ethereum (richiede Infura)
- **goerli**: Testnet Ethereum deprecata (richiede Infura) 
- **mainnet**: Rete principale Ethereum (richiede Infura + ETH reali)