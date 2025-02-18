from w3off.w3provider import w3

name = "ERC20"


def prepERC20Transfer(
    sender_address: str,
    receiver_address: str,
    contract_address: str,
    abi: str,
    amount: int | float,
):
    # Normalize addresses
    sender_address = w3.to_checksum_address(sender_address)
    receiver_address = w3.to_checksum_address(receiver_address)
    contract_address = w3.to_checksum_address(contract_address)

    # Create contract object
    contract = w3.eth.contract(address=contract_address, abi=abi)
    decimals = contract.functions.decimals.call()

    nonce = w3.eth.get_transaction_count(sender_address)
    gas_price = w3.eth.gas_price
    amount = int(amount * 10**decimals)
    gas = contract.functions.transfer(receiver_address, amount).estimate_gas({"chainId": w3.eth.chain_id, "from": sender_address, "nonce": nonce})

    # Build the transaction to call the `transfer` function
    tx = contract.functions.transfer(receiver_address, amount).build_transaction(
        {
            "chainId": w3.eth.chain_id,
            "gas": gas,
            "gasPrice": gas_price,  # use gas_price if connected to blockchain
            "nonce": nonce,
        }
    )
    return tx
