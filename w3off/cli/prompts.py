import os
import sys

import w3off.config as config
from w3off.config import getChainName
from w3off.cli.helpers import bcolors
from w3off.helpers.txHelpers import decodeRawTx
from w3off.w3provider import change_chain, estimateBaseFee, w3


def promptConfirm(confirmation_str: str = "Do you confirm?"):
    while True:
        try:
            if os.name == "nt" and not sys.stdin.isatty():
                import msvcrt

                print(confirmation_str + " [Y/N]: ")
                response = msvcrt.getwch()
            else:
                response = input(confirmation_str + " [Y/N]: ")
            response = response.lower()
            if response == "y":
                return True
            elif response == "n":
                return False
        except KeyboardInterrupt:
            exit(0)
        except:
            print("Please try again.")


def inputShortcut(array_of_choices: list):
    while True:
        try:
            chosen_index = int(input("Your choice (e.g. 1): ") or 1)
            choice = array_of_choices[chosen_index - 1]
            if chosen_index < 1:
                raise IndexError
            return choice
        except KeyboardInterrupt as e:
            print(f"Exiting the application...")
            exit(0)
        except IndexError as e:
            print(f"Your value is out of bounds. Error: {e}")
            print(f"Please enter correct index between 1 and {len(array_of_choices)}: ")
        except Exception as e:
            print(f"Your input value is incorrect. Error: {e}")
            print(f"Make sure to enter appropriate numerical index of a shortcut (e.g. 1) or leave empty. Please try again.")


def keyPress():
    if os.name == "nt" and not sys.stdin.isatty():
        import msvcrt

        print("Press any key to continue or [Q] to abort...")
        key_pressed = msvcrt.getwch()
        if key_pressed == chr(27) or key_pressed == "q" or key_pressed == "Q":
            exit(0)

    else:
        input("Press <Enter> to continue...")


def getInitialStdinStr():
    if not sys.stdin.isatty():
        input_str = sys.stdin.read()
        if os.name != "nt":
            os.ttyname(0)
    else:
        print("No tx input detected. Please enter the transaction data (JSON or string) manually: ")
        input_str = input()

    return input_str


# TODO: merge confirmTxPrice into one function
def confirmTxPrice(gas_price: int, gas: int, current_gas_price: int):
    """Estimate for Type 0 (legacy) transactions. All inputs are in wei."""
    if current_gas_price - gas_price / current_gas_price < -(config.gas_leeway_coef - 1):
        print(f"WARNING: Your estimated gas price is less than current gas price by more than {int((config.gas_leeway_coef - 1)*100)}% !!!")
    elif abs(current_gas_price - gas_price) / current_gas_price > (config.gas_leeway_coef_pessimistic - 1):
        print(
            f"WARNING: Note the current gas price deviates from the value in transaction by over {int((config.gas_leeway_coef_pessimistic - 1)*100)}% !!!"
        )
    gas_price_eth = w3.from_wei(gas_price, "ether")
    cost_estimate = ("%.12f" % (gas_price_eth * gas)).rstrip("0").rstrip(".")
    print(f"Transaction price is estimated to be {round(gas_price_eth * 10**9, 4)} gwei x {gas} gas = {cost_estimate} ETH.")

    return promptConfirm()


def confirmTxPrice_Type2(
    base_fee: int,
    gas_max_priority_fee: int,
    gas_max_fee: int,
    gas: int,
    current_gas_price: int,
):
    """Estimate for Type 2 transactions. All inputs are in wei."""
    if current_gas_price - (base_fee + gas_max_priority_fee) / current_gas_price < -(config.gas_leeway_coef - 1):
        print(f"WARNING: Your estimated gas price is less than current gas price by more than {int((config.gas_leeway_coef - 1)*100)}% !!!")
    elif abs(current_gas_price - (base_fee + gas_max_priority_fee)) / current_gas_price > (config.gas_leeway_coef_pessimistic - 1):
        print(
            f"WARNING: Note the current gas price deviates from the value in transaction by over {int((config.gas_leeway_coef_pessimistic - 1)*100)}% !!!"
        )

    cost_estimate = (base_fee + gas_max_priority_fee) * gas
    cost_estimate_eth = ("%.12f" % w3.from_wei(cost_estimate, "ether")).rstrip("0").rstrip(".")
    print(f"Transaction price is estimated to be ({round((base_fee + gas_max_priority_fee) / 10**9, 4)}) gwei x {gas} gas = {cost_estimate_eth} ETH.")
    cost_upper_limit = gas_max_fee * gas
    cost_upper_limit_eth = ("%.12f" % w3.from_wei(cost_upper_limit, "ether")).rstrip("0").rstrip(".")
    print(f"UPPER limit on price {round(gas_max_fee / 10**9, 4)} gwei x {gas} gas = {cost_upper_limit_eth} ETH.")
    return promptConfirm()


def confirmSendRawTx(signed_tx: str):
    """Returns True if user accepted."""
    print("Raw transaction: ", signed_tx)
    print("Decoding raw transaction...")
    tx = decodeRawTx(signed_tx)
    print("You are about to send the following raw transaction: ")
    print(tx)
    chain_id = tx["chainId"] or 1
    # chosen_chain = next((k for k, v in config.chains.items() if v['id'] == chain_id), None)
    chosen_chain = getChainName(chain_id)
    print(f"Note: This transaction is intended for the **{chosen_chain.upper()}** blockchain.")
    if getChainName(w3.eth.chain_id) != chosen_chain:
        if config.DEBUG:
            print(f"{bcolors.WARNING}You are in DEBUG mode, but connecting to a real chain.{bcolors.ENDC}")
            if not promptConfirm("Are you sure you want to proceed?"):
                print("Exiting the application...")
                exit(0)
        change_chain(chosen_chain)
    assert chain_id == w3.eth.chain_id, "Mismatch between chain_id in transaction and the one in the provider after its initizaliation."

    current_gas_price = w3.eth.gas_price
    print(f"Current network gas price: {round(current_gas_price / 10**9, 4)} gwei")

    if ("type" not in tx and "gasPrice" in tx) or tx["type"] == 0:
        return confirmTxPrice(tx["gasPrice"], tx["gas"], current_gas_price)
    else:
        return confirmTxPrice_Type2(
            estimateBaseFee(),
            tx["maxPriorityFeePerGas"],
            tx["maxFeePerGas"],
            tx["gas"],
            current_gas_price,
        )


def userNetworkCheck():
    """Asks user to check network, but ignores in DEBUG mode. Returns True if consumer can ignore, and False otherwise."""
    if config.chain_id == config.chains.get("debug", {}).get("id", 0):
        print("You are connected to a DEBUG blockchain, so we will skip the network check after you press a key .")
        keyPress()
        return True
    if config.DEBUG:
        print("You are in DEBUG mode, so we will skip the network check after you press a key.")
        keyPress()
        return True
    keyPress()
    return False
