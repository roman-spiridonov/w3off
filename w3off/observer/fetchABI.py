import requests
import w3off.config as config
from w3off.observer.cache import (
    checkABICache,
    checkImplementationCache,
    persist_cache,
    setABICache,
    setImplementationCache,
)
from w3off.w3provider import w3

# Flags for currently processed transaction
isProxy = False
sourceAddr = ""
implementationAddr = ""


def fetchABI(contract_address):
    """
    Fetches ABI as a string for a smart contract deployed at address `address`

    Returns:
    str: ABI string ready to be passed to other web3 contract functions
    """
    contract_address = w3.to_checksum_address(contract_address)

    abi = checkABICache(contract_address)
    if abi is not None:
        return abi

    assert config.ethscan_api_key, "Please sign up on etherscan and save your API key to environment variable named ETHSCAN_API_KEY to use this application."
    url = f"https://api.etherscan.io/v2/api?chainid={w3.eth.chain_id}&module=contract&action=getabi&address={contract_address}&apikey={config.ethscan_api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        abi = setABICache(contract_address, response.json()["result"])
        return abi
    else:
        return None


def listFunctions(contract_address: str, abi: str = None):
    contract_address = w3.to_checksum_address(contract_address)

    if not isContract(contract_address):
        raise ValueError(f"The target address {contract_address} should be smart contract address.")

    abi = checkABICache(contract_address)

    if abi is None:
        contract_address_impl = implementationAddress(contract_address)
        abi = fetchABI(contract_address_impl)
        setABICache(contract_address_impl, abi)
        if contract_address != contract_address_impl:  # if proxy address
            setABICache(contract_address, abi)

    contract = w3.eth.contract(address=contract_address, abi=abi)

    return list([i for i in contract.functions if i.abi["type"] == "function"])


def implementationAddress(address):
    global isProxy, implementationAddr, sourceAddr
    address = w3.to_checksum_address(address)
    response_json = checkImplementationCache(address)
    if not response_json:
        assert config.ethscan_api_key, "Please sign up on etherscan and save your API key to environment variable named ETHSCAN_API_KEY to use this application."
        response = requests.post(
            f"https://api.etherscan.io/v2/api?chainid={w3.eth.chain_id}&module=contract&action=getsourcecode&address={address}&apikey={config.ethscan_api_key}"
        )
        response_json = response.json()
        setImplementationCache(address, response_json)

    # initial_abi = response_json['result'][0]['ABI']
    sourceAddr = address
    isProxy = response_json["result"][0]["Proxy"] == "1"
    if not isProxy:
        # setABICache(address, initial_abi)
        return address
    implementationAddr = response_json["result"][0]["Implementation"]
    return w3.to_checksum_address(implementationAddr)


def isContract(address):
    # Get the code at the address!
    address = w3.to_checksum_address(address)
    code = w3.eth.get_code(address)
    # Check if the code is empty
    return code.hex() != ""  # Returns True if it's a contract


def fetchMissingABIs(contract_obj):
    """Obtain ABI from cache values or fetch it from the blockchain."""
    assert contract_obj["address"], "Pass contract object which contains address and potentially misses ABI"

    try:
        if contract_obj["abi"].len() > 0:
            pass
    except:
        contract_obj["abi"] = fetchABI(contract_obj["address"])
