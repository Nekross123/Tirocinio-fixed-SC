# This function simplifies the interaction with smart contracts
# Following the same pattern used in the course materials

def metaTransaction(w3, account, contract, value, function, *parameters):
    
    try:        
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
            gas_limit = int(estimated_gas * 1.2)
            transaction.update({'gas': gas_limit})
        except Exception as gas_error:
            default_gas = 500000  # 500k gas should be enough for most operations
            transaction.update({'gas': default_gas})
            

        # Sign transaction - handle different web3.py versions
        signed_tx = w3.eth.account.sign_transaction(transaction, account.key)
        
        # Calculate transaction size in bytes
        raw_transaction = getattr(signed_tx, 'rawTransaction', getattr(signed_tx, 'raw_transaction', signed_tx))
        size_in_bytes = len(raw_transaction)
        
        # Send transaction
        tx_hash = w3.eth.send_raw_transaction(raw_transaction)
        
        # Wait for receipt
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        # Convert AttributeDict to regular dict and add size_in_bytes
        receipt_dict = dict(tx_receipt)
        receipt_dict['size_in_bytes'] = size_in_bytes
        
        return receipt_dict
        
    except Exception as e:
        raise e  # Re-raise the exception with more context