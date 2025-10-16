# MIT License
#
# Copyright (c) 2025 Manuel Boi - Università degli Studi di Cagliari
# Based on Prof. Andrea Pinna's approach from bcschool2023

"""
Ethereum Account Management Module

This module provides comprehensive functionality for managing Ethereum accounts including:
- Creating new Ethereum accounts with private/public key pairs
- Encrypting and saving accounts to JSON keystore files
- Loading and decrypting existing encrypted account files
- Managing wallet files in the ethereum_wallets directory

The implementation follows Prof. Andrea Pinna's approach from bcschool2023 for 
account management and encryption standards.
"""

# Web3.py library for Ethereum blockchain interaction
from web3 import Web3, EthereumTesterProvider
# JSON library for handling keystore file format
import json
# OS library for file system operations
import os
# Import the base path configuration for the ethereum module
from ethereum_module.ethereum_utils import ethereum_base_path

def create_account():

    # Initialize Web3 instance with EthereumTesterProvider for account operations
    # EthereumTesterProvider is used for local account generation without needing a real network
    w3 = Web3(EthereumTesterProvider)
    
    # Generate a new account with random private key using Web3's secure random generation
    account = w3.eth.account.create()
    
    # Return account information in a structured dictionary format
    return {
        "address": account.address,        # Public Ethereum address (0x format)
        "private_key": account.key.hex(),  # Private key in hexadecimal string format
        "account_obj": account             # Full Web3 Account object for advanced operations
    }

def save_encrypted_account(private_key, password, filename):
    """
    Save an Ethereum account's private key in an encrypted JSON keystore file.
    
    This function encrypts a private key using a password and saves it in the standard
    Ethereum keystore format. The encrypted file can be used with various Ethereum
    wallets and tools.
    
    Args:
        private_key (str): The private key in hexadecimal format to encrypt
        password (str): The password used for encryption (should be strong)
        filename (str): The name for the keystore file (without .json extension)
    
    Returns:
        str: The full file path where the encrypted keystore was saved
    
    Example:
        file_path = save_encrypted_account("0x123abc...", "myPassword123", "my_wallet")
        print(f"Wallet saved to: {file_path}")
    """
    # Initialize Web3 instance for encryption operations
    w3 = Web3(EthereumTesterProvider)
    
    # Encrypt the private key using Web3's built-in encryption
    # This creates a JSON keystore format compatible with standard Ethereum wallets
    account_data = w3.eth.account.encrypt(private_key, password)
    
    # Create the wallets directory path within the ethereum module
    wallets_dir = os.path.join(ethereum_base_path, "ethereum_wallets")
    # Ensure the directory exists, create it if it doesn't (exist_ok=True prevents errors)
    os.makedirs(wallets_dir, exist_ok=True)
    
    # Construct the full file path with .json extension
    file_path = os.path.join(wallets_dir, f"{filename}.json")
    
    # Write the encrypted account data to the JSON file
    # indent=2 makes the JSON file human-readable with proper formatting
    with open(file_path, "w") as file:
        json.dump(account_data, file, indent=2)
    
    # Return the path where the file was saved for confirmation
    return file_path

def load_encrypted_account(filename, password):
    """
    Load and decrypt an Ethereum account from an encrypted JSON keystore file.
    
    This function reads an encrypted keystore file and decrypts it using the provided
    password to recover the original Ethereum account. 
    
    Args:
        filename (str): The name of the keystore file (with or without .json extension)
        password (str): The password used to decrypt the keystore file
    
    Returns:
        Account: Web3 Account object if successful, None if decryption fails
    
    Example:
        account = load_encrypted_account("my_wallet.json", "myPassword123")
        if account:
            print(f"Loaded account: {account.address}")
        else:
            print("Failed to load account - check password")
    """
    # Construct the path to the wallets directory
    wallets_dir = os.path.join(ethereum_base_path, "ethereum_wallets")
    file_path = os.path.join(wallets_dir, filename)
    
    # Ensure the filename has .json extension for consistency
    if not filename.endswith('.json'):
        file_path += '.json'
    
    try:
        # Read the encrypted keystore file
        with open(file_path, "r") as file:
            data = json.load(file)
        
        # Initialize Web3 instance for decryption operations
        w3 = Web3(EthereumTesterProvider)
        
        # Decrypt the keystore using the provided password
        # This recovers the original private key from the encrypted data
        recovered_pk = w3.eth.account.decrypt(data, password)
        
        # Create a Web3 Account object from the recovered private key
        account = w3.eth.account.from_key(recovered_pk)
        
        return account
        
    except Exception as e:
        # Handle any errors during file reading or decryption
        # Common causes: wrong password, corrupted file, file not found
        print(f"Error loading encrypted account: {e}")
        return None

def create_and_save_wallet(wallet_name, password="1234"):
    """
    Convenience function to create a new Ethereum wallet and save it encrypted.
    
    This is a high-level function that combines account creation and encrypted storage
    in a single operation. It's designed for quick wallet generation during development
    or testing scenarios.
    
    Args:
        wallet_name (str): The name for the wallet file (without .json extension)
        password (str, optional): Password for encryption. Defaults to "1234"
                                 Note: Use strong passwords in production!
    
    Returns:
        dict: The account information including address, private_key, and account_obj
    
    Side Effects:
        - Creates a new encrypted keystore file in ethereum_wallets directory
        - Prints confirmation message with file path and address
    
    Example:
        wallet_info = create_and_save_wallet("test_wallet", "strongPassword123")
        # Output: "Wallet created and saved: /path/to/ethereum_wallets/test_wallet.json"
        #         "Address: 0x742d35Cc6688C4c4B3cD3C7..."
    """
    # Step 1: Create a new Ethereum account with random private key
    account_info = create_account()
    
    # Step 2: Save the account's private key in an encrypted keystore file
    file_path = save_encrypted_account(
        account_info["private_key"],  # The generated private key
        password,                     # Encryption password
        wallet_name                   # Name for the keystore file
    )
    
    # Step 3: Provide user feedback about the successful wallet creation
    print(f"Wallet created and saved: {file_path}")
    print(f"Address: {account_info['address']}")
    
    # Return the account information for immediate use if needed
    return account_info