# Ethereum Toolchain Setup

## Prerequisites

To use the Ethereum toolchain, you need to install the following dependencies:

### Python Dependencies

```bash
pip install web3 py-solc-x eth-account
```

### Solidity Compiler

The py-solc-x package will automatically download and install the Solidity compiler when needed.

### Optional: Hardhat (for advanced compilation)

If you want to use Hardhat for compilation (optional feature):

```bash
npm install -g hardhat
```

## Network Configuration

### Local Development (Default) - **REQUIRED FOR TESTING**

The toolchain uses `http://127.0.0.1:8545` as the default local network.

**⚠️ IMPORTANT: You MUST run a local Ethereum node for testing!**

#### Option 1: Ganache CLI (Recommended)

Install Ganache CLI:
```bash
npm install -g ganache-cli
```

Start Ganache with deterministic accounts:
```bash
ganache-cli --host 127.0.0.1 --port 8545 --accounts 10 --deterministic
```

This will provide:
- 10 test accounts with 100 ETH each
- Deterministic addresses (same every time)
- Local blockchain on port 8545

#### Option 2: Hardhat Node

```bash
npx hardhat node
```

### Important Notes for Local Testing

1. **Always start Ganache BEFORE testing** the Ethereum toolchain
2. **Keep Ganache running** during development and testing
3. **Use the provided test accounts** - the first account is pre-configured in `test_wallet.json`
4. **Network will reset** when you restart Ganache (deployed contracts will be lost)

### Testnet/Mainnet

For testnets and mainnet, you need to set up an Infura project:

1. Create an account at https://infura.io/
2. Create a new project
3. Set the environment variable:
   ```bash
   export INFURA_PROJECT_ID="your_project_id_here"
   ```

## Wallet Management

Wallets are stored as JSON files in `ethereum_module/ethereum_wallets/`.

Each wallet file contains:
- `address`: The Ethereum address
- `private_key`: The private key (keep secure!)
- `public_key`: The public key

## Contract Deployment

Contracts are deployed and their information is stored in:
- `deployments/`: Deployment information with ABI
- `artifacts/`: Compiled contract artifacts

## Usage

### Quick Start Guide

1. **Start Ganache** (REQUIRED):
   ```bash
   ganache-cli --host 127.0.0.1 --port 8545 --accounts 10 --deterministic
   ```
   Keep this terminal open!

2. **Start Backend** (in another terminal):
   ```bash
   cd /path/to/ROSETTASC
   source venv/bin/activate  # Activate virtual environment
   python flask_backend.py
   ```

3. **Start Frontend** (in another terminal):
   ```bash
   cd /path/to/ROSETTASC
   source venv/bin/activate  # Activate virtual environment
   streamlit run Rosetta_SC.py
   ```

4. **Use the Ethereum toolchain**:
   - **Upload Contracts**: Use the frontend to upload .sol files
   - **Compile & Deploy**: Select "localhost" network and wallet for deployment
   - **Interact**: Use the interactive interface to call contract functions

### Troubleshooting

If you get "Error reading wallet" or "Could not connect to network":
1. Check if Ganache is running: `curl -X POST -H "Content-Type: application/json" --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' http://127.0.0.1:8545`
2. Restart Ganache if needed
3. Make sure you're using "localhost" network in the frontend

## Example Contracts

A sample `SimpleStorage.sol` contract is included for testing.

## Default Test Account

When using Ganache with `--deterministic` flag, the first account is:
- **Address**: `0x90F8bf6A479f320ead074411a4B0e7944Ea8c9C1`
- **Private Key**: `0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d`
- **Balance**: 100 ETH

This account is pre-configured in `test_wallet.json` for immediate testing.

## Security Notes

- **For LOCAL TESTING ONLY**: The provided test wallet contains Ganache's deterministic keys
- Never use test keys on real networks (testnets/mainnet)
- Never share private keys for real accounts
- Use testnets for development before mainnet
- Be careful with mainnet deployments (real money involved)
- Always test contracts thoroughly before mainnet deployment

## Common Commands Reference

```bash
# Start Ganache
ganache-cli --host 127.0.0.1 --port 8545 --accounts 10 --deterministic

# Check if Ganache is running
curl -X POST -H "Content-Type: application/json" --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' http://127.0.0.1:8545

# Stop Ganache
# Press Ctrl+C in the Ganache terminal

# Install dependencies (in virtual environment)
pip install web3 py-solc-x eth-account
```