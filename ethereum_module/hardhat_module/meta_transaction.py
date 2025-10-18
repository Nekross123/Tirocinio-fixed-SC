# MIT License
#
# Copyright (c) 2025  Palumbo Lorenzo, Piras Mauro - Università degli Studi di Cagliari
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
        Transaction receipt
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
    
    # Send transaction - handle different web3.py versions
    raw_transaction = getattr(signed_tx, 'rawTransaction', getattr(signed_tx, 'raw_transaction', signed_tx))
    tx_hash = w3.eth.send_raw_transaction(raw_transaction)
    
    # Wait for receipt
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    return tx_receipt