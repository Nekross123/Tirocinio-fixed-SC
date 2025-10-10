# MIT License
#
# Copyright (c) 2025 Manuel Boi - Università degli Studi di Cagliari
# Based on Prof. Andrea Pinna's approach from bcschool2023

from web3 import Web3, EthereumTesterProvider
import json
import os
from Toolchain.ethereum_module.ethereum_utils import ethereum_base_path

def create_account():
    """Create a new Ethereum account - following prof's approach."""
    w3 = Web3(EthereumTesterProvider)
    account = w3.eth.account.create()
    return {
        "address": account.address,
        "private_key": account.key.hex(),
        "account_obj": account
    }

def save_encrypted_account(private_key, password, filename):
    """
    Save account with password encryption - following prof's saveAccount.py approach.
    """
    w3 = Web3(EthereumTesterProvider)
    
    # Encrypt the private key
    account_data = w3.eth.account.encrypt(private_key, password)
    
    # Save to wallets directory
    wallets_dir = os.path.join(ethereum_base_path, "ethereum_wallets")
    os.makedirs(wallets_dir, exist_ok=True)
    
    file_path = os.path.join(wallets_dir, f"{filename}.json")
    
    with open(file_path, "w") as file:
        json.dump(account_data, file, indent=2)
    
    return file_path

def load_encrypted_account(filename, password):
    """
    Load encrypted account - following prof's pattern.
    """
    wallets_dir = os.path.join(ethereum_base_path, "ethereum_wallets")
    file_path = os.path.join(wallets_dir, filename)
    
    if not filename.endswith('.json'):
        file_path += '.json'
    
    try:
        with open(file_path, "r") as file:
            data = json.load(file)
        
        # Decrypt using Web3
        w3 = Web3(EthereumTesterProvider)
        recovered_pk = w3.eth.account.decrypt(data, password)
        account = w3.eth.account.from_key(recovered_pk)
        
        return account
    except Exception as e:
        print(f"Error loading encrypted account: {e}")
        return None

def create_and_save_wallet(wallet_name, password="1234"):
    """
    Convenience function to create and save a wallet with encryption.
    """
    # Create account
    account_info = create_account()
    
    # Save encrypted
    file_path = save_encrypted_account(
        account_info["private_key"], 
        password, 
        wallet_name
    )
    
    print(f"Wallet created and saved: {file_path}")
    print(f"Address: {account_info['address']}")
    
    return account_info