#!/usr/bin/env python
import json
from pprint import pprint
import sys

from hexbytes import HexBytes
import w3off.cli.prompts as cli_prompts
import w3off.config as config
from w3off.config import getChainName
from w3off.cli.helpers import bcolors
from w3off.helpers.txHelpers import prepareDictToPrint
from w3off.signer.checkOffline import checkOffline

from w3off.w3provider import w3

def sendRawTx(signed_tx: str):
    # raw_tx_str = signed_tx if isinstance(signed_tx, str) else signed_tx.get('raw_transaction')
    txHash = w3.eth.send_raw_transaction(signed_tx)
    return txHash


def waitForReceipt(txHash: HexBytes):
    txReceipt = w3.eth.wait_for_transaction_receipt(txHash)
    return txReceipt


def parseRawTxFromStr(raw_tx_str: str):
    raw_tx_str = raw_tx_str.replace("'", '"')  # replace single quotes with double quotes since the formed is not accepted by json.loads
    try:
        raw_tx = json.loads(raw_tx_str)
        raw_tx = raw_tx["raw_transaction"]
    except json.JSONDecodeError as e:
        # already contains encoded tx as a string
        raw_tx = raw_tx_str
    except Exception as e:
        print(
            f'Error parsing the transaction (does your transaction object contain "raw_transaction" key which contains encoded transaction string?): {e}'
        )
        print(f"Restart the program and try again")
        return
    return raw_tx


def run_sender(signed_tx, **kwargs):
    """
    Sends transaction and returns its receipt (unless timeout happened).
    Args:
        ignoreNetworkCheckPrompt (bool): if True, will not prompt user
        ignoreTxConfirmation (bool): if True, will not decode tx and prompt user to confirm
    Returns:
        txReceipt (dict): Dictionary containing logs about transaction with 'transactionHash' key.
    """

    if not signed_tx.startswith("0x"):
        signed_tx = "0x" + signed_tx

    if config.chain_name != "debug":
        print("Checking if you are online now that we proceed to sending the transaction...")
        while checkOffline():
            print(f"{bcolors.UNDERLINE}You are offline!{bcolors.ENDC} Make sure you connect back to the Internet.")
            if kwargs.get("ignoreNetworkCheckPrompt", False) or cli_prompts.userNetworkCheck():
                break

    if (not kwargs.get("ignoreTxConfirmation", False)) and (not cli_prompts.confirmSendRawTx(signed_tx)):
        print("Stopped the transaction sending. Please restart the program and try again.")
        return

    print("Sending the raw transaction...")
    txHash = sendRawTx(signed_tx)
    print(f"Transaction has been sent: {'0x' + txHash.hex()}")
    if not config.DEBUG:
        print(f"You check tx hash using the block scanner on the {getChainName(w3.eth.chain_id)} chain.")
        try:
            print(f"{config.chains[getChainName(w3.eth.chain_id)]['tx_url']}/tx/{'0x' + txHash.hex()}")
        except Exception as e:
            print("Could not build the URL to the transaction (it was likely not specified in chains.yml settings).")

    print(f"Waiting for confirmation...")
    txReceipt = w3.eth.wait_for_transaction_receipt(txHash)
    print(f"{bcolors.OKGREEN}Transaction has been confirmed!{bcolors.ENDC} See receipt below: ")
    txReceipt = prepareDictToPrint(txReceipt)
    txReceipt.pop("logs")
    pprint(txReceipt)
    return txReceipt


def main(raw_tx_str: str = None):
    raw_tx_str = cli_prompts.getInitialStdinStr() if raw_tx_str is None else raw_tx_str
    signed_tx = parseRawTxFromStr(raw_tx_str)
    run_sender(signed_tx)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        from w3off.test.data.txTestAaveSupply import txTestRaw, txTestRaw2

        raw_tx = txTestRaw['raw_transaction']
        # raw_tx = txTestRaw2["raw_transaction"]
        main(raw_tx)
