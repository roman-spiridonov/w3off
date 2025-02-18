import json
import w3off.config as config
from w3off.w3provider import w3


def checkABICache(contract_address):
    # Current cache logic is only uses smart contract address as an index
    # This should be fine for now since smart contracts will have different addresses on different chains in most cases, or otherwise share the same abi

    # ERC-20 and Smart contracts from w3off.config for current chain
    if config.smart_contracts.get(contract_address, {}).get("abi"):
        return config.smart_contracts[w3.to_checksum_address(contract_address)]["abi"]

    # application cache
    if config.cache.setdefault("abi", {}).get(contract_address):
        return config.cache.get("abi").get(contract_address)

    return None


def setABICache(contract_address, abi):
    if "abi" not in config.cache:
        config.cache["abi"] = {}

    config.cache["abi"][w3.to_checksum_address(contract_address)] = abi
    return abi


def checkImplementationCache(contract_address):
    # application cache
    if config.cache.setdefault("implementation", {}).get(contract_address):
        return config.cache.get("implementation").get(contract_address)
    return None


def setImplementationCache(contract_address, response_json):
    config.cache.setdefault("implementation", {})[w3.to_checksum_address(contract_address)] = response_json
    return response_json


def persist_cache():
    with open(config.cache_file_path, "w") as json_file:
        json.dump(config.cache, json_file, indent=2)
