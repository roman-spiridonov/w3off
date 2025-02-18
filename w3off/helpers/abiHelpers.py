from web3 import Web3
from eth_abi import encode
from eth_utils import (
    keccak,
    to_bytes,
    function_signature_to_4byte_selector,
    filter_abi_by_type,
)
from eth_abi import abi
from w3off.w3provider import w3
import json

# from eth_keys import keys


def encodeABICall(func_signature, param_values):
    """Encode ABI function call to data attribute by padding all function parameters."""
    _, param_types = func_signature.split("(")
    param_types = param_types[:-1].split(",")
    encoded_params = ""
    for param, param_type in zip(param_values, param_types):
        if param_type == "address":
            encoded_params += pad_hex(param)
        elif param_type == "uint256":
            hex_param = hex(int(param))
            encoded_params += pad_hex(hex_param)
        # TODO: add other supported attribute types, as well as dynamic
    return encoded_params


def decodeABICall(abi_string: str, func_params_sig: str, data: str):
    param_values = decodeABIParams(func_params_sig, data)
    func_name = decodeABIMethod(abi_string, data)
    return (func_name, *param_values)


def decodeABIParams(func_params_sig: str, data: str):
    return abi.decode(func_params_sig, bytes.fromhex(data[10:]))  # 2 to remove '0x' and 8 to remove func signature


def decodeABIMethod(abi_string: str, data: str):
    abi_obj = json.loads(abi_string)
    func_selector = data[:10]  # Get the first 10 characters
    for func in abi_obj:
        func_signature = f"{func['name']}({','.join([input['type'] for input in func['inputs']])})"
        selector = function_signature_to_4byte_selector(func_signature)
        if selector.hex() == func_selector[2:]:  # Compare hex values without '0x'
            func_name = func["name"]
            break

    if not func_name:
        raise ValueError("Could not find function name in provided ABI. Check ABI parameter passed to decodeABICall() function.")

    return func_name


def pad_hex(value):
    """Pad a hexadecimal string to 32 bytes (64 hex characters). Padding means actually making the resulting hex be that of 32 bytes."""
    return value[2:].rjust(64, "0")


def dataFromCall(func_signature, func_parameters):
    """
    Construct the `data` attribute for an Ethereum transaction. Does not support dynamic parameters (with dynamic length) at this point.

    Args:
    func_signature (str): The function signature, e.g., "transfer(address,uint256)"
    func_parameters (list): The parameters to pass to the function, e.g., ["0x1234567890123456789012345678901234567890", 1000]

    Returns:
    str: The encoded `data` attribute for the transaction.
    """
    # Ensure that the first parameter (if address) is checksummed to avoid errors
    if "address" in func_signature.split("(")[1].split(",")[0]:  # TODO may need smarter address determination, not always first param?
        func_parameters[0] = Web3.to_checksum_address(func_parameters[0])

    # ABI encode the function call
    function_selector = w3.keccak(text=func_signature)[:4]  # First 4 bytes
    # using web3 library function instead of encodeabi in this module
    encoded_parameters = encode(
        types=func_signature.split("(")[1][:-1].split(","), args=func_parameters
    )  # Function parameters, padded by 32 bytes, or 64 hex-chars
    # Concatenate function selector and encoded parameters
    data = function_selector.hex() + encoded_parameters.hex()
    return data
