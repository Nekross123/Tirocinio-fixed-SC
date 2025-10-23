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
    try:
        print(f"🔧 Executing function: {function}")
        print(f"📋 Parameters: {parameters}")
        print(f"💰 Value: {value} wei")
        print(f"👤 From: {account.address}")
        
        # Build transaction using contract function
        transaction = getattr(contract.functions, function)(*parameters).build_transaction({
            "chainId": w3.eth.chain_id,
            "from": account.address,
            "value": value,
            "gasPrice": w3.eth.gas_price
        })

        # Add nonce and gas estimation with fallback
        transaction.update({"nonce": w3.eth.get_transaction_count(account.address)})
        
        # Try to estimate gas, use fallback if it fails
        print(f"🔍 Transaction before gas estimation: {transaction}")
        try:
            estimated_gas = w3.eth.estimate_gas(transaction)
            print(f"✅ Gas estimation successful: {estimated_gas}")
            # Add 20% buffer to the estimated gas
            gas_limit = int(estimated_gas * 1.2)
            transaction.update({'gas': gas_limit})
            print(f"🔧 Using buffered gas limit: {gas_limit}")
        except Exception as gas_error:
            print(f"⚠️ Gas estimation failed: {gas_error}")
            print(f"🔍 Gas error type: {type(gas_error)}")
            # Use a reasonable default gas limit for contract interactions
            default_gas = 500000  # 500k gas should be enough for most operations
            transaction.update({'gas': default_gas})
            print(f"🔧 Using default gas limit: {default_gas}")
            
        print(f"🔍 Final transaction with gas: {transaction}")

        # Sign transaction - handle different web3.py versions
        signed_tx = w3.eth.account.sign_transaction(transaction, account.key)
        
        # Calculate transaction size in bytes
        raw_transaction = getattr(signed_tx, 'rawTransaction', getattr(signed_tx, 'raw_transaction', signed_tx))
        size_in_bytes = len(raw_transaction)
        
        # Send transaction
        print(f"📤 Sending transaction...")
        tx_hash = w3.eth.send_raw_transaction(raw_transaction)
        print(f"🔗 Transaction hash: {tx_hash.hex()}")
        
        # Wait for receipt
        print(f"⏳ Waiting for transaction receipt...")
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        # Convert AttributeDict to regular dict and add size_in_bytes
        receipt_dict = dict(tx_receipt)
        receipt_dict['size_in_bytes'] = size_in_bytes
        
        print(f"✅ Transaction successful! Gas used: {receipt_dict.get('gasUsed')}")
        return receipt_dict
        
    except Exception as e:
        print(f"❌ metaTransaction failed: {str(e)}")
        print(f"🔍 Error type: {type(e).__name__}")
        raise e  # Re-raise the exception with more context