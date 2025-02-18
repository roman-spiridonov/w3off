#!/usr/bin/env python
import getpass
import json
import os
import sys

from hexbytes import HexBytes

import w3off.signer.vault as vault
import w3off.config as config
import w3off.cli.prompts as cli_prompts
from w3off.cli.helpers import bcolors
from w3off.w3provider import change_chain, w3
from w3off.helpers.txHelpers import decodeRawTx
from eth_account.datastructures import SignedTransaction
from pprint import pprint
from w3off.signer.checkOffline import checkOffline


def signTx(tx):
    assert vault.pkey is not None
    vault.decrypt_pkey()
    raw_tx = w3.eth.account.sign_transaction(tx, vault.pkey)
    del vault.pkey  # remove from memory right after signing
    return raw_tx


def signedTxToDict(signed_tx: SignedTransaction):
    return {
        "raw_transaction": "0x" + signed_tx.raw_transaction.hex(),
        "hash": "0x" + signed_tx.hash.hex(),
        "r": signed_tx.r,
        "s": signed_tx.s,
        "v": signed_tx.v,
    }


def dictToSignedTx(signed_tx_dict: dict):
    return SignedTransaction(
        HexBytes(bytes.fromhex(signed_tx_dict["raw_transaction"].removeprefix("0x"))),
        HexBytes(bytes.fromhex(signed_tx_dict["hash"].removeprefix("0x"))),
        signed_tx_dict["r"],
        signed_tx_dict["s"],
        signed_tx_dict["v"],
    )


def run_signer(tx, **pparams):
    """
    Signs transaction and returns raw transactions. Ensures the operation is done fully offline.
    Ensures private is not exposed to other modules and purged from memory as soon as possible.
    Args:
        ignoreNetworkCheckPrompt (bool): if True, will not prompt user
        pkey (str): private key as a hex string
        keystore_file (str): path to keystore file
        keystore_pwd (str): keystore password

    Returns:
        raw_tx (AttributeDict):
            Dictionary containing 'raw_transaction' key with a hex string, 'txHash' and signature keys 'r', 's', 'v'.
            The output is ready to be consumed by sender module.
    """
    # print('Closing web3 connection if open...')
    # for a in w3provider.session.adapters.values():
    #     a.close()
    #     a.poolmanager.clear()
    #     for proxy in a.proxy_manager.values():
    #         proxy.clear()
    # w3provider.adapter.close()
    # w3provider.session.close()

    print("Proceeding to signing the transaction to generate a signed transaction...")
    print("Checking if you are offline...")
    isOffline = checkOffline()
    while not isOffline:
        print(
            f"{bcolors.WARNING}You are not offline!{bcolors.ENDC} Make sure you disconnect your network (and VPN tunnel, if one is available)."
        )
        if pparams.get("ignoreNetworkCheckPrompt", False) or cli_prompts.userNetworkCheck():
            break
        isOffline = checkOffline()

    if isOffline:
        print(f"{bcolors.OKGREEN}Good!{bcolors.ENDC} You are offline, so we can proceed.")

    print(
        "Note we are only creating a raw transaction string (aka signed transaction). It will not be sent until you explicitly confirm. You can also choose to exit before sending."
    )

    while True:
        print("1 - Enter pkey securely in place")
        print("2 - Load pkey from keystore file")
        chosen_pkey_mode = 1 if pparams.get("pkey", False) or (2 if pparams.get("keystore_file", False) else False) else False
        if chosen_pkey_mode:
            print(f"Your pre-selected choice: **{chosen_pkey_mode}**")
        # print('3 - Restore pkey from seed phrase (and optionally save in an encrypted keystore file)')
        try:
            if not chosen_pkey_mode:
                if os.name == "nt" and not sys.stdin.isatty():
                    chosen_pkey_mode = (
                        getpass.getpass(f"Choose how to obtain private key to sign the transaction(s) (default is {config.default_pkey_mode}): ")
                        or config.default_pkey_mode
                    )
                else:
                    chosen_pkey_mode = (
                        input(f"Choose how to obtain private key to sign the transaction(s) (default is {config.default_pkey_mode}): ")
                        or config.default_pkey_mode
                    )

            if int(chosen_pkey_mode) == 1:
                vault.promptPkey(pparams.get("pkey", None))
                break
            elif int(chosen_pkey_mode) == 2:
                vault.promptKeystoreFile(
                    pparams.get("keystore_file", None),
                    pparams.get("keystore_pwd", None),
                )
                break
            # elseif(int(chosen_pkey_mode) == 3):
            # cli_prompts.promptMnemonic()
        except Exception as e:
            print(f"Invalid entry. Error text: {e}")
            print("Please try again.")
            chosen_pkey_mode = None

    signed_tx = signTx(tx)

    print("Your signed transaction (with signature r, s, v): ")
    pprint(signedTxToDict(signed_tx), sort_dicts=False)

    return signed_tx


def parseTxFromStr(tx_str: str):
    tx_str = tx_str.replace("'", '"')  # replace single quotes with double quotes since the formed is not accepted by json.loads
    try:
        tx = json.loads(tx_str)
    except json.JSONDecodeError as e:
        print(f"Error parsing the transaction, likely you passed invalid JSON: {e}")
        print(f"Restart the program and try again")
        return
    return tx


def main(tx_str: str = None):
    tx_str = cli_prompts.getInitialStdinStr() if tx_str is None else tx_str
    tx = parseTxFromStr(tx_str)
    run_signer(tx)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        from w3off.test.data.txTestUSDTTransfer import txTest

        main(txTest.__str__())
