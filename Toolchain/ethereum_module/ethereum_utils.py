# MIT License
#
# Copyright (c) 2025 Manuel Boi - Università degli Studi di Cagliari
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import os
import json
import subprocess
import platform
from web3 import Web3
from eth_account import Account
import secrets

ethereum_base_path = os.path.join("Toolchain", "ethereum_module")


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


def create_web3_instance(network="localhost"):
    """Create a Web3 instance for the specified network."""
    network_configs = {
        "localhost": "http://127.0.0.1:8545",
        "sepolia": f"https://sepolia.infura.io/v3/{os.getenv('INFURA_PROJECT_ID', '')}",
        "goerli": f"https://goerli.infura.io/v3/{os.getenv('INFURA_PROJECT_ID', '')}",
        "mainnet": f"https://mainnet.infura.io/v3/{os.getenv('INFURA_PROJECT_ID', '')}"
    }
    
    rpc_url = network_configs.get(network, network_configs["localhost"])
    return Web3(Web3.HTTPProvider(rpc_url))


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


def get_wallet_balance(wallet_file, network="localhost"):
    """Get the ETH balance of a wallet."""
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


def estimate_gas_price(network="localhost"):
    """Estimate current gas price for the network."""
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


def send_eth_transaction(from_wallet_file, to_address, amount_eth, network="localhost"):
    """Send ETH from one wallet to another."""
    wallet_data = load_wallet_from_file(from_wallet_file)
    if not wallet_data:
        return None
    
    w3 = create_web3_instance(network)
    if not w3.is_connected():
        print("Failed to connect to network")
        return None
    
    try:
        account = Account.from_key(wallet_data["private_key"])
        
        # Get nonce
        nonce = w3.eth.get_transaction_count(account.address)
        
        # Build transaction
        transaction = {
            'nonce': nonce,
            'to': to_address,
            'value': w3.to_wei(amount_eth, 'ether'),
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


def wait_for_transaction_receipt(tx_hash, network="localhost", timeout=120):
    """Wait for transaction to be mined and return receipt."""
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