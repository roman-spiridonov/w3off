# from eth_account import Account
# from eth_utils import keccak
import os
import re
from eth_tester import EthereumTester
from web3 import Web3, EthereumTesterProvider

import w3off.config as config
from w3off.cli.helpers import bcolors
from w3off.config import getChainName, getDefault
from w3off.test.ethTesterEnv import setEthTesterEnv


w3 = None  # Instance of web3 (singleton)
eth_tester = None  # Instance of eth_tester (singleton)
t_initial = None  # Snapshot of eth_tester, if one has been initialized (for easy revert in tests)


def initialize_provider():
    global w3, eth_tester
    if config.DEBUG:
        eth_tester = EthereumTester()
        provider = EthereumTesterProvider(eth_tester)
    else:
        # adapter = requests.adapters.HTTPAdapter()
        # session = requests.Session()
        # session.mount('https://', adapter)
        provider = Web3.HTTPProvider(config.web3_provider_url)

    w3 = Web3(provider)
    if config.DEBUG:
        w3.eth_tester = eth_tester


def show_provider_status():
    status = w3.is_connected()
    status_str = f"{bcolors.OKGREEN}{status}{bcolors.ENDC}" if status else f"{bcolors.FAIL}{status}{bcolors.ENDC}"
    web3_provider_str = config.web3_provider_url.split("://")[1].split("/")[0] if "://" in config.web3_provider_url else config.web3_provider_url
    print(f"Connected to **{config.chain_name}** - {web3_provider_str} RPC provider... STATUS: {status_str}")
    return status


def normalize_addresses():
    for chain in config.chains.values():
        for name, contract in chain.get("smart_contracts", {}).items():
            contract["address"] = w3.to_checksum_address(contract["address"])
            if "implementation" in contract:
                contract["implementation"] = w3.to_checksum_address(contract["implementation"])
        for key, value in chain.get("defaults", {}).items():
            if w3.is_address(value):
                chain["defaults"][key] = w3.to_checksum_address(value)


def insert_rpc_placeholder(full_str, matched_str):
    result = os.environ.get(matched_str,"") or input(
        f"Could not find environment variable **{matched_str}** (in {full_str}) . Please enter desired value manually: "
    )
    return result


def update_default_values(chosen_chain: str = None):
    """Updates some default values based on user chain selection"""
    chosen_chain = chosen_chain or getChainName(config.chain_id)
    # DEFAULT VALUES
    config.default_amount = getDefault(chosen_chain, "amount") or config.default_amount
    config.default_maxgas = getDefault(chosen_chain, "maxgas") or config.default_maxgas
    config.gas_leeway_coef = getDefault(chosen_chain, "gas_leeway_coef") or config.gas_leeway_coef

    config.default_pkey_mode = getDefault(chosen_chain, "pkey_mode") or config.default_pkey_mode  # in place
    config.default_keystore_file = os.path.join(*tuple(getDefault(chosen_chain, "keystore_file").split("/"))) or config.default_keystore_file

    config.default_sender = getDefault(chosen_chain, "sender") or config.default_sender
    config.default_destination = getDefault(chosen_chain, "destination") or config.default_destination

    config.smart_contracts_by_name = config.chains[chosen_chain].get("smart_contracts",{})
    for key in config.smart_contracts_by_name:
        config.smart_contracts_by_name[key]["name"] = key
    config.smart_contracts = {v["address"]: {"name": k, **v} for k, v in config.smart_contracts_by_name.items()}

    config.default_erc20 = config.smart_contracts_by_name.get(getDefault(chosen_chain, "erc20"), {}).get("address", False) or config.default_erc20
    config.default_contract = (
        config.smart_contracts_by_name.get(getDefault(chosen_chain, "contract"), {}).get("address", False) or config.default_contract
    )
    config.default_abi = config.smart_contracts.get(config.default_contract, {}).get("abi") or config.default_abi


def change_chain(chosen_chain):
    global w3, eth_tester
    # Use environment variable for API key in provider URL
    status = None
    pattern = r"\{(.*?)\}"
    rpc_string = config.chains[chosen_chain]["rpc_provider"]
    provider_url = re.sub(
        pattern,
        lambda match: f'{insert_rpc_placeholder(rpc_string, f"{match.group(1)}")}',
        rpc_string,
    )
    if config.web3_provider_url.lower() != provider_url.lower():
        if chosen_chain == "debug":
            if not eth_tester:
                eth_tester = EthereumTester()
                # eth_tester.t_initial = eth_tester.take_snapshot()
            w3.provider = EthereumTesterProvider(eth_tester)
            w3.eth_tester = eth_tester
            config.web3_provider_url = "debug"
        else:
            w3.provider = Web3.HTTPProvider(provider_url)

        config.chain_id = w3.eth.chain_id
        config.chain_name = getChainName(config.chain_id)
        config.web3_provider_url = provider_url
        status = show_provider_status()
        update_default_values(chosen_chain)
        if chosen_chain == "debug":
            setEthTesterEnv(w3, w3.eth_tester)

    status = status or w3.is_connected()
    assert chosen_chain == getChainName(
        config.chain_id
    ), "Mismatch between chain name in transaction and the one in the provider after its initialization."
    return status


def estimateBaseFee():
    try:
        base_fee = w3.eth.get_block("latest").get("baseFeePerGas")
    except Exception as e:
        print("Note: could not estimate base fee from the latest block - using gas_price RPC call instead (this is ok)")
        base_fee = w3.eth.gas_price
    return base_fee


# --------------------------
# ----- INITIALIZATION -----
# --------------------------
initialize_provider()
show_provider_status()

if config.DEBUG:
    # Deploy some smart contracts and addresses for use in tests
    # from test.ethTesterContracts import usdt_ethtester, aave_v3_ethtester
    w3 = setEthTesterEnv(w3, eth_tester)
    eth_tester = w3.eth_tester


def resetEthTester():
    global w3
    w3.eth_tester.revert_to_snapshot(w3.eth_tester.t_initial)
