# This function simplifies the interaction with smart contracts
# Following the same pattern used in the course materials

def metaTransaction(w3, account, contract, value, function, *parameters):
    """
    Simplified smart contract interaction function.
    
    Args:
        w3: Web3 instance
        account: Account object with private key
        contract: Contract instance
        value: ETH value to send (in wei)
        function: Function name to call
        *parameters: Function parameters
    
    Returns:
        Dictionary with transaction receipt and size_in_bytes
    """
    # Build transaction using contract function
    transaction = getattr(contract.functions, function)(*parameters).build_transaction({
        "chainId": w3.eth.chain_id,
        "from": account.address,
        "value": value,
        "gasPrice": w3.eth.gas_price
    })

    # Add nonce and gas estimation
    transaction.update({"nonce": w3.eth.get_transaction_count(account.address)})
    transaction.update({'gas': w3.eth.estimate_gas(transaction)})

    # Sign transaction - handle different web3.py versions
    signed_tx = w3.eth.account.sign_transaction(transaction, account.key)
    
    # Calculate transaction size in bytes
    raw_transaction = getattr(signed_tx, 'rawTransaction', getattr(signed_tx, 'raw_transaction', signed_tx))
    size_in_bytes = len(raw_transaction)
    
    # Send transaction
    tx_hash = w3.eth.send_raw_transaction(raw_transaction)
    
    # Wait for receipt
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    
    # Add size_in_bytes to receipt
    tx_receipt['size_in_bytes'] = size_in_bytes
    
    return tx_receipt