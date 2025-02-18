#!/usr/bin/env python
import w3off.cli.prompts as cli_prompts
from w3off.observer.w3observer import run_observer
from w3off.sender.w3sender import run_sender
from w3off.signer.w3signer import run_signer
from w3off.w3provider import estimateBaseFee, w3


def main():
    # Check stability & prerequisites

    # ---------------------------------------------------------
    # 1. Prepare Tx (Orchestrator)
    tx = run_observer()

    # Confirm tx price is good for the user
    if ("type" not in tx and "gasPrice" in tx) or tx.get("type", -1) == 0:
        isConfirmed = cli_prompts.confirmTxPrice(tx["gasPrice"], tx["gas"], w3.eth.gas_price)
    else:
        isConfirmed = cli_prompts.confirmTxPrice_Type2(
            estimateBaseFee(),
            tx["maxPriorityFeePerGas"],
            tx["maxFeePerGas"],
            tx["gas"],
            w3.eth.gas_price,
        )
    if tx and not isConfirmed:
        print("Stopped the transaction creation. Please restart the program and try again.")
        return

    # ---------------------------------------------------------
    # 2. Sign transaction offline (tx) -> SIGNER -> (raw_tx)
    signed_tx = run_signer(tx)

    # ---------------------------------------------------------
    # 3. Send raw transaction (raw_tx) -> SENDER -> (events)
    txReceipt = run_sender("0x" + signed_tx["raw_transaction"].hex(), ignoreTxConfirmation=True)


if __name__ == "__main__":
    main()
