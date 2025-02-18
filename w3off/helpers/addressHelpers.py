import re
from rlp import encode
from eth_utils import keccak, to_bytes

# from eth_keys import keys


def isHexStr(s):
    if not isinstance(s, str):
        return False
    return bool(re.match(r"^(0x)?[0-9a-fA-F]+$", s))


def deployerToSmartContractAddress(address: str, nonce: int):
    if address[:2] != "0x":
        address = "0x" + address
    assert len(address) == 42  # eth address should contains 40 symbols
    bytes_address = to_bytes(hexstr=address)
    scAddress = "0x" + keccak(encode([bytes_address, nonce])).hex()[24:]
    return scAddress


# def pubKeyToAddress(pubkey: str):
#     return keccak(to_bytes(pubkey)).hex()[24:]

# def pkeyToPubKey(pkey: str):
#     return keys.PrivateKey(pkey).public_key
