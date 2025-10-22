import os
import json
import subprocess
import platform
from web3 import Web3
from eth_account import Account
import secrets

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Load .env from project root
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    load_dotenv(env_path)
except ImportError:
    print("⚠️  python-dotenv not installed. Install with: pip install python-dotenv")
except Exception as e:
    print(f"⚠️  Could not load .env file: {e}")

# Base path now points to this package at repo root
ethereum_base_path = os.path.join("ethereum_module")

# Global default network - can be changed by set_default_network()
DEFAULT_NETWORK = "localhost"


def set_default_network(network):
    """Set the default network for all operations."""
    global DEFAULT_NETWORK
    valid_networks = ["localhost", "sepolia", "goerli", "mainnet"]
    if network not in valid_networks:
        raise ValueError(f"Network must be one of: {valid_networks}")
    DEFAULT_NETWORK = network
    print(f"Default network set to: {network}")


def get_default_network():
    """Get the current default network."""
    return DEFAULT_NETWORK


def setup_ethereum_environment(network=None, check_connection=True):
    """Setup and verify Ethereum environment."""
    if network:
        set_default_network(network)
    
    current_network = get_default_network()
    print(f"Current default network: {current_network}")
    
    # Check if Infura is needed and configured
    if current_network in ["sepolia", "goerli", "mainnet"]:
        infura_id = os.getenv('INFURA_PROJECT_ID')
        if not infura_id:
            print("⚠️  Warning: INFURA_PROJECT_ID not set!")
            print("   Get a free project ID from https://infura.io/")
            print("   Then set it with: export INFURA_PROJECT_ID=your_project_id")
            return False
        else:
            print(f"✓ Infura Project ID configured: {infura_id[:8]}...")
    
    if check_connection:
        return verify_network_connection(current_network)
    
    return True


def run_command(operating_system, command_str):
    """Execute shell commands based on the operating system."""
    try:
        if operating_system == "Windows":
            result = subprocess.run(
                ["cmd", "/c"] + command_str.split(),
                capture_output=True,
                text=True
            )
        else:  # Linux/macOS
            result = subprocess.run(
                command_str,
                shell=True,
                capture_output=True,
                text=True
            )
        return result
    except Exception as e:
        print(f"Error executing command: {e}")
        return None


def create_web3_instance(network=None):
    """Create a Web3 instance for the specified network."""
    if network is None:
        network = DEFAULT_NETWORK
        
    # Check if Infura Project ID is available for public networks
    infura_project_id = os.getenv('INFURA_PROJECT_ID')
    
    # Public RPC endpoints as fallback
    fallback_rpcs = {
        "sepolia": "https://rpc2.sepolia.org",  # Public Sepolia RPC
        "goerli": "https://goerli.blockpi.network/v1/rpc/public",
        "mainnet": "https://cloudflare-eth.com"
    }
    
    network_configs = {
        "localhost": "http://127.0.0.1:8545",
        "sepolia": f"https://sepolia.infura.io/v3/{infura_project_id}" if infura_project_id else fallback_rpcs["sepolia"],
        "goerli": f"https://goerli.infura.io/v3/{infura_project_id}" if infura_project_id else fallback_rpcs["goerli"],
        "mainnet": f"https://mainnet.infura.io/v3/{infura_project_id}" if infura_project_id else fallback_rpcs["mainnet"]
    }
    
    rpc_url = network_configs.get(network)
    
    # Handle case where no RPC is available
    if rpc_url is None:
        # Fallback to localhost for unknown networks
        rpc_url = network_configs["localhost"]
        print(f"Unknown network '{network}', falling back to localhost")
    
    # Show warning if using fallback RPC
    if not infura_project_id and network in fallback_rpcs:
        print(f"⚠️  Using public RPC for {network}. For better reliability, set INFURA_PROJECT_ID")
    
    return Web3(Web3.HTTPProvider(rpc_url))


def verify_network_connection(network=None):
    """Verify if the network connection is working."""
    if network is None:
        network = DEFAULT_NETWORK
        
    try:
        w3 = create_web3_instance(network)
        if w3.is_connected():
            block_number = w3.eth.block_number
            print(f"✓ Connected to {network} network (Block: {block_number})")
            return True
        else:
            print(f"✗ Failed to connect to {network} network")
            return False
    except Exception as e:
        print(f"✗ Error connecting to {network}: {e}")
        return False


def create_ethereum_wallet(wallet_name=None):
    """Create a new Ethereum wallet and save it to file."""
    if not wallet_name:
        wallet_name = input("Enter wallet name (without .json): ")
    
    # Generate a new private key
    private_key = secrets.token_hex(32)
    account = Account.from_key(private_key)
    
    # Create wallet data structure
    wallet_data = {
        "address": account.address,
        "private_key": private_key,
        "public_key": account._key_obj.public_key.to_hex()
    }
    
    # Save to file
    wallets_dir = os.path.join(ethereum_base_path, "ethereum_wallets")
    os.makedirs(wallets_dir, exist_ok=True)
    
    wallet_file = os.path.join(wallets_dir, f"{wallet_name}.json")
    with open(wallet_file, 'w', encoding='utf-8') as f:
        json.dump(wallet_data, f, indent=2)
    
    print(f"Wallet created and saved to {wallet_file}")
    print(f"Address: {account.address}")
    return wallet_file


def load_wallet_from_file(wallet_file_path):
    """Load wallet data from a JSON file."""
    try:
        with open(wallet_file_path, 'r', encoding='utf-8') as f:
            wallet_data = json.load(f)
        return wallet_data
    except Exception as e:
        print(f"Error loading wallet: {e}")
        return None


def get_wallet_balance(wallet_file, network=None):
    """Get the ETH balance of a wallet."""
    if network is None:
        network = DEFAULT_NETWORK
        
    wallet_data = load_wallet_from_file(wallet_file)
    if not wallet_data:
        return None
    
    w3 = create_web3_instance(network)
    if not w3.is_connected():
        return None
    
    try:
        balance_wei = w3.eth.get_balance(wallet_data["address"])
        balance_eth = w3.from_wei(balance_wei, 'ether')
        return float(balance_eth)
    except Exception as e:
        print(f"Error getting balance: {e}")
        return None


def get_wallet_address(wallet_file):
    """Get the address from a wallet file."""
    wallet_data = load_wallet_from_file(wallet_file)
    if wallet_data:
        return wallet_data.get("address")
    return None


def estimate_gas_price(network=None):
    """Estimate current gas price for the network."""
    if network is None:
        network = DEFAULT_NETWORK
        
    w3 = create_web3_instance(network)
    if not w3.is_connected():
        return None
    
    try:
        gas_price = w3.eth.gas_price
        return w3.from_wei(gas_price, 'gwei')
    except Exception as e:
        print(f"Error estimating gas price: {e}")
        return None


def choose_wallet():
    """Interactive wallet selection."""
    wallets_dir = os.path.join(ethereum_base_path, "ethereum_wallets")
    if not os.path.exists(wallets_dir):
        print("No wallets directory found.")
        return None
    
    wallet_files = [f for f in os.listdir(wallets_dir) if f.endswith('.json')]
    if not wallet_files:
        print("No wallet files found.")
        return None
    
    print("Available wallets:")
    for i, wallet_file in enumerate(wallet_files, 1):
        print(f"{i}. {wallet_file}")
    
    try:
        choice = int(input("Choose wallet (number): ")) - 1
        if 0 <= choice < len(wallet_files):
            return wallet_files[choice]
        else:
            print("Invalid choice.")
            return None
    except ValueError:
        print("Invalid input.")
        return None


def choose_network():
    """Interactive network selection."""
    networks = ["localhost", "sepolia", "goerli", "mainnet"]
    
    print("Available networks:")
    for i, network in enumerate(networks, 1):
        print(f"{i}. {network}")
    
    try:
        choice = int(input("Choose network (number): ")) - 1
        if 0 <= choice < len(networks):
            return networks[choice]
        else:
            print("Invalid choice.")
            return "localhost"
    except ValueError:
        print("Invalid input.")
        return "localhost"


def send_eth_transaction(from_wallet_file, to_address, amount_eth, network=None):
    """Send ETH from one wallet to another."""
    if network is None:
        network = DEFAULT_NETWORK
        
    wallet_data = load_wallet_from_file(from_wallet_file)
    if not wallet_data:
        return None
    
    w3 = create_web3_instance(network)
    if not w3.is_connected():
        print("Failed to connect to network")
        return None
    
    try:
        account = Account.from_key(wallet_data["private_key"])
        
        # Get nonce: numero sequenziale delle transazioni inviate da questo indirizzo
        # Se l'indirizzo ha fatto 5 transazioni, nonce sarà 5 (per la 6° transazione)
        nonce = w3.eth.get_transaction_count(account.address)
        
        # Build transaction
        transaction = {
            'nonce': nonce,
            'to': to_address,
            'value': w3.to_wei(amount_eth, 'ether'),
            #least amount of gas for a standard ETH transfer
            'gas': 21000,
            'gasPrice': w3.eth.gas_price,
        }
        
        # Sign transaction
        signed_txn = w3.eth.account.sign_transaction(transaction, wallet_data["private_key"])
        
        # Send transaction - handle different web3.py versions
        raw_transaction = getattr(signed_txn, 'rawTransaction', getattr(signed_txn, 'raw_transaction', signed_txn))
        tx_hash = w3.eth.send_raw_transaction(raw_transaction)
        
        return tx_hash.hex()
        
    except Exception as e:
        print(f"Error sending transaction: {e}")
        return None


def wait_for_transaction_receipt(tx_hash, network=None, timeout=120):
    """Wait for transaction to be mined and return receipt."""
    if network is None:
        network = DEFAULT_NETWORK
        
    w3 = create_web3_instance(network)
    if not w3.is_connected():
        return None
    
    try:
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)
        return receipt
    except Exception as e:
        print(f"Error waiting for transaction: {e}")
        return None


def format_eth_address(address):
    """Format Ethereum address with checksum."""
    return Web3.to_checksum_address(address) if address else None