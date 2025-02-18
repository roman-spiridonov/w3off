from w3off.test.ethTesterContracts import aave_v3_ethtester, usdt_ethtester
from web3 import Web3
from eth_tester import EthereumTester
from eth_utils import keccak, to_bytes

import w3off.config as config
from w3off.config import getChainName


def setEthTesterEnv(w3: Web3, eth_tester: EthereumTester):
    """Deploy smart contracts on EthereumTestProvider"""
    assert w3.provider.ethereum_tester
    assert w3.eth_tester
    # usdt_addr = t.add_account(keccak(text='usdt').hex())
    # aave_v3_addr = t.add_account(keccak(text='aave_v3').hex())

    print("----------------------")
    print("YOU ARE IN DEBUG MODE!")
    print("----------------------")
    print(f"Full list of pre-populated test addresses: {w3.eth.accounts}")

    config.cache.setdefault("abi", {})[usdt_ethtester["contract_address"]] = usdt_ethtester["abi"]
    config.cache.setdefault("abi", {})[aave_v3_ethtester["contract_address"]] = aave_v3_ethtester["abi"]
    config.cache.setdefault("abi", {})[aave_v3_ethtester["implementation_address"]] = aave_v3_ethtester["abi"]

    w3.eth.default_account = w3.eth.accounts[0]  # contract owner

    print(f"Smart contracts are deployed using private key belonging to this address on EthereumTester: {w3.eth.default_account}")
    print(f"Deploying smart contracts for testing...")

    sender_account = eth_tester.add_account("f8f8a2f43c8376ccb0871305060d7b27b0554d2cc72bccf41b2705608452f315")
    sender_account_index = w3.eth.accounts.index(sender_account)
    print(f"-> Your default sender address is {sender_account}. ")
    print(f"Sending ETH balance to the specified sender address...")
    assert sender_account_index == 10, "New sender account should be created and added to the end of `w3.eth.accounts` list"
    amount_to_send = w3.eth.get_balance(w3.eth.accounts[0]) // 10
    w3.eth.send_transaction({"from": w3.eth.accounts[0], "to": sender_account, "value": amount_to_send})
    assert w3.eth.get_balance(sender_account) == amount_to_send, "Could not fill balance!"

    # USDT
    print(f"-> USDT")
    USDT = w3.eth.contract(abi=usdt_ethtester["abi"], bytecode=usdt_ethtester["creation_bytecode"])
    usdt_total_supply = 100000000000
    # Deploy contract
    usdt_tx_hash = USDT.constructor(usdt_total_supply, "USD Tether Test", "USDT", 6).transact()
    usdt_tx_receipt = w3.eth.wait_for_transaction_receipt(usdt_tx_hash)
    print(f"Contract USDT at address: {usdt_tx_receipt.contractAddress} with total supply of {usdt_total_supply//10**6} USDT")
    usdt_ethtester["contract_address"] = usdt_tx_receipt.contractAddress
    usdt = w3.eth.contract(address=usdt_tx_receipt.contractAddress, abi=usdt_ethtester["abi"])
    assert usdt.functions.totalSupply().call() == usdt_total_supply, "Checking totalSupply of USDT coints"
    assert usdt.functions.decimals().call() == 6, "Checking number decimals on USDT contract should be 6"
    # Distribute USDT to test addresses
    amount_to_disribute = 10000 * 10**6
    print(f"Transferring {amount_to_disribute // (10 ** 6)} USDT to all test addresses...")
    for recipient in w3.eth.accounts:
        if recipient == usdt_tx_receipt.contractAddress:  # Skip sending to self
            continue
        tx_hash = usdt.functions.transfer(recipient, amount_to_disribute).transact()
        if recipient == sender_account:
            print(f"Transferred {amount_to_disribute // (10 ** 6)} USDT to your default address - Transaction hash: {tx_hash.hex()}")

    assert (
        usdt.functions.balanceOf("0xd41c057fd1c78805AAC12B0A94a405c0461A6FBb").call() // 10**6 == 10000
    ), "All the test wallets should receive 10000 USDT"

    # Aave v3
    # Aave v3 has complex logic spread between multiple smart contracts. For testing purposes, we need to either mock functions.* calls or use local hardfork
    print(f"-> Aave v3")
    AAVE_V3 = w3.eth.contract(abi=aave_v3_ethtester["abi"], bytecode=aave_v3_ethtester["creation_bytecode"])
    aave_v3_tx_hash = AAVE_V3.constructor("0x2f39d218133AFaB8F2B819B1066c7E434Ad94E9e").transact()
    aave_v3_tx_receipt = w3.eth.wait_for_transaction_receipt(aave_v3_tx_hash)
    aave_v3_ethtester["contract_address"] = aave_v3_tx_receipt.contractAddress

    print(f"Contract AAVE v3 at address (dummy functions only): {aave_v3_tx_receipt.contractAddress}")
    aave_v3 = w3.eth.contract(address=aave_v3_tx_receipt.contractAddress, abi=aave_v3_ethtester["abi"])

    # Updating config variables for Ethereum Tester environment
    curr_chain = getChainName(w3.eth.chain_id)
    assert curr_chain == "debug"

    # Need to update these separately since we know the address only after deployment of the contract
    config.chains[curr_chain]["smart_contracts"].setdefault("USDT", {})["address"] = usdt_ethtester["contract_address"]
    config.chains[curr_chain]["smart_contracts"].setdefault("AAVE_V3", {})["address"] = aave_v3_ethtester["contract_address"]
    config.chains[curr_chain].setdefault("defaults", {})["erc20"] = "USDT"
    config.chains[curr_chain].setdefault("defaults", {})["contract"] = "USDT"

    # update_default_values(curr_chain, config)
    config.default_sender = w3.eth.accounts[10]
    config.default_destination = w3.eth.accounts[1]
    assert config.default_abi == usdt_ethtester["abi"]
    assert config.default_erc20 == usdt_ethtester["contract_address"]
    assert config.default_contract == usdt_ethtester["contract_address"]

    eth_tester.t_initial = eth_tester.take_snapshot()
    assert w3.eth_tester.t_initial is not None
    return w3


if __name__ == "__main__":
    from w3off.w3provider import w3, eth_tester
