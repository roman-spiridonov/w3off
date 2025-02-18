from dataclasses import dataclass
from hexbytes import HexBytes
import rlp
from eth_typing import HexStr
from eth_utils import keccak, to_bytes, encode_hex, is_hexstr
from rlp.sedes import Binary, big_endian_int, binary, lists
from w3off.w3provider import w3

from web3.datastructures import AttributeDict

from eth_account import Account
from eth_account.typed_transactions import TypedTransaction
from hexbytes import HexBytes


def decodeRawTx2(raw_tx: str):
    print(TypedTransaction.from_bytes(HexBytes(raw_tx)).as_dict())


# https://ethereum.stackexchange.com/questions/83802/how-to-decode-a-raw-transaction-in-python
class Transaction_Type0(rlp.Serializable):
    fields = [
        ("nonce", big_endian_int),
        ("gas_price", big_endian_int),
        ("gas", big_endian_int),
        ("to", Binary.fixed_length(20, allow_empty=True)),
        ("value", big_endian_int),
        ("data", binary),
        ("v", big_endian_int),
        ("r", big_endian_int),
        ("s", big_endian_int),
    ]


class Transaction_Type2(rlp.Serializable):
    fields = [
        ("chain_id", big_endian_int),
        ("nonce", big_endian_int),
        ("max_priority_fee_per_gas", big_endian_int),
        ("max_fee_per_gas", big_endian_int),
        ("gas", big_endian_int),
        ("to", binary),
        ("value", big_endian_int),
        ("data", binary),
        (
            "access_list",
            rlp.sedes.CountableList(rlp.sedes.List([binary, binary])),
        ),  # Access list needs a proper sedes
        ("v", big_endian_int),
        ("r", big_endian_int),
        ("s", big_endian_int),
    ]


def hex_to_bytes(data: str) -> bytes:
    try:
        result = to_bytes(hexstr=HexStr(data))
    except Exception as e:
        print(f"Error converting hex to bytes. Please ensure you enter a hex string. Error: {e}.")
    return result


def decodeRawTx(raw_tx: str):
    if not raw_tx.startswith("0x"):
        raw_tx = "0x" + raw_tx

    raw_tx_bytes = to_bytes(hexstr=raw_tx)
    type = raw_tx_bytes[0]

    if type == 0x02:
        # EIP-1559 transaction (Type 2)
        tx = rlp.decode(raw_tx_bytes[1:], Transaction_Type2, strict=False)
    else:
        # Legacy transaction (Type 0)
        tx = rlp.decode(raw_tx_bytes, Transaction_Type0, strict=False)

    hash_tx = w3.to_hex(keccak(hex_to_bytes(raw_tx)))
    from_ = w3.eth.account.recover_transaction(raw_tx)
    to = w3.to_checksum_address(tx.to) if tx.to else None
    data = w3.to_hex(tx.data)
    r = hex(tx.r)
    s = hex(tx.s)
    chain_id = (tx.v - 35) // 2 if tx.v % 2 else (tx.v - 36) // 2

    if type == 0x02:
        # EIP-1559 transaction (Type 2)
        return {
            "hash": hash_tx,
            "type": 2,  # Indicate EIP-1559 transaction
            "from": from_,
            "to": to,
            "nonce": tx.nonce,
            "gas": tx.gas,
            "maxPriorityFeePerGas": tx.max_priority_fee_per_gas,
            "maxFeePerGas": tx.max_fee_per_gas,
            "value": tx.value,
            "data": data,
            "chainId": tx.chain_id,
            "r": r,
            "s": s,
            "v": tx.v,
            "accessList": tx.access_list,
        }

    else:
        # Legacy transaction (Type 0)
        return {
            "hash": hash_tx,
            "from": from_,
            "to": to,
            "nonce": tx.nonce,
            "gas": tx.gas,
            "gasPrice": tx.gas_price,
            "value": tx.value,
            "data": data,
            "chainId": chain_id,
            "r": r,
            "s": s,
            "v": tx.v,
        }


def prepareDictToPrint(d: AttributeDict | dict):
    """Recursively convert HexBytes in a dictionary to strings."""
    if isinstance(d, dict | AttributeDict):
        return {k: prepareDictToPrint(v) for k, v in d.items()}
    elif isinstance(d, list):
        return [prepareDictToPrint(item) for item in d]
    elif isinstance(d, HexBytes):
        return "0x" + d.hex()  # Convert HexBytes to string
    elif isinstance(d, str):
        if is_hexstr(d) and not d.startswith("0x"):
            return "0x" + d
    return d  # Return the value as is if it's not a dict, list, or HexBytes
