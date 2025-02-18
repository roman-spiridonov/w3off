#!/usr/bin/env python
import itertools

import w3off.config as config
from w3off.config import getChainName
from w3off.cli.prompts import inputShortcut
from w3off.w3provider import change_chain, w3

from w3off.observer.cache import persist_cache
from w3off.observer.fetchABI import fetchABI, isContract, listFunctions
from w3off.observer.shortcuts.erc20Tx import prepERC20Transfer
from w3off.observer.shortcuts.customTx import prepTx
from w3off.observer.shortcuts import available_shortcuts


def run_simple_eth_transfer(source, to_address, **pparams):
    print("You have entered a simple ETH address, so creating simple ETH tarnsfer transaction...")
    type = pparams.get("type", config.tx_type)
    value = pparams.get("value") or None
    if not value:
        while True:
            try:
                value = input("Enter amount of ETH to transfer: ")
                value = w3.to_wei(value, "ether")
                break
            except Exception as e:
                print(f"Invalid entry: {e}. Please try again.")

    tx = prepTx(source, to_address, value, None, None, type)
    return tx


def run_smart_contract_tx(source, to_address, **pparams):
    print("You have entered a smart contract address...")
    funcs = listFunctions(to_address)

    # Put READ functions first, then WRITE
    order = {"pure": 0, "view": 1, "nonpayable": 2, "payable": 3}
    funcs = sorted(funcs, key=lambda f: order.get(f.abi["stateMutability"], 999))

    from w3off.observer.fetchABI import isProxy, implementationAddr

    if isProxy:
        print(f"Note that you have selected a smart contract which is a **proxy** pointing to **{implementationAddr}**")

    # Print list of functions, but only if function was not pre-selected in input pparams
    if not pparams.get("func_choice", False):
        flag = None
        i = 1
        for f in funcs:
            if flag is None:
                print("--- READ functions ---")
                flag = "READ"
            if (f.abi["stateMutability"] not in ("pure", "view")) and flag != "WRITE":
                print("----------------------")
                print("--- WRITE functions ---")
                flag = "WRITE"
            # TODO: support tuples (e.g. uniswap)
            param_string = ", ".join([f"{item['name']}[{item['type']}]" for item in f.abi["inputs"]])
            if len(f.abi["inputs"]) == 0:
                param_string = ""
            print(
                i,
                " - ",
                f.name,
                "( ",
                param_string,
                " )",
                " - ",
                f.abi["stateMutability"],
            )
            i += 1
        print("----------------------")

    # Select function and then enter parameter values for the selected function
    while True:
        # INPUT FUNCTION NAME
        func_choice = None
        while func_choice is None:
            func_choice = pparams.get("func_choice", False) or input(
                "Choose function you want to execute (you can either numerical index or function name): "
            )
            try:
                func_choice = int(func_choice)
                chosen_func = funcs[func_choice - 1]
            except Exception as e1:
                try:
                    matched_funcs = list(i for i, f in enumerate(funcs) if f.name == func_choice)
                    if not matched_funcs:
                        raise ValueError("There are not matching entries for your choice.")
                    chosen_func = funcs[matched_funcs[0]]

                    # Sometimes, two functions are matched. In this case, choose funciton with more parameters.
                    # Typically, function with less parameters would require a raw byte input, which is less preferred for the end user.
                    if len(matched_funcs) > 1:
                        chosen_func2 = funcs[matched_funcs[1]]
                        if len(chosen_func2.abi["inputs"]) > len(chosen_func.abi["inputs"]):
                            chosen_func = chosen_func2

                except Exception as e2:
                    print(f"Your entry is incorrect. Here is the excpetion thrown: {e2}")
                    func_choice = None

        print(f"You have chosen **{chosen_func.name}** function")

        # INPUT FUNCTION PARAMETERS
        chosen_params = []
        param_index = 0
        for params in chosen_func.abi["inputs"]:
            if params["type"] == "address":
                guess = (config.default_erc20 if ("asset" in params["name"].lower()) else (source if ("behalf" in params["name"].lower() or "receiver" in params["name"].lower()) else config.default_destination))
            elif params["type"][:4] == "uint":
                guess = config.default_amount if ("amount" in params["name"].lower()) or ("value" in params["name"]) else 0
            else:
                guess = "<<not defined>>"

            if pparams.get("func_params", False):
                v = pparams.get("func_params")[param_index]
            else:
                v = input(f"{params['name']} [{params['type']}] (default: {guess}) = ") or guess

            if params["type"] == "address":
                v = w3.to_checksum_address(v)
            if params["type"][:4] == "uint":  # TODO: handle other types
                v = int(v)
            chosen_params.append(v)
            param_index += 1

        chosen_params = tuple(chosen_params)

        if chosen_func.abi["stateMutability"] in ("view", "pure"):
            print("Since this function is READ, it can be just executed without a transaction. Executing... See result below.")
            if len(chosen_params) == 0:
                print(chosen_func.call())
            else:
                print(chosen_func(*chosen_params).call())
        else:
            break

    type = pparams.get("type", config.tx_type)
    tx = prepTx(source, to_address, 0, chosen_func, chosen_params, type)
    return tx


def run_erc20_transfer(source, **pparams):
    erc20_contracts = [
        {"i": i, **v} for i, v in zip(itertools.count(start=1, step=1), config.smart_contracts_by_name.values()) if v.get("type", "") == "ERC20"
    ]
    print(
        "\n".join(
            [f"{contract['i']} - {contract['name']} [ {contract['address']} ] ({contract['decimals'] or 6} decimals)" for contract in erc20_contracts]
        )
    )
    print("Choose ERC20 token for transfer (default is USDT): ")
    chosen_contract = inputShortcut(erc20_contracts)

    print(f"Please enter below the parameters for **transfer()** function.")
    default_amount = config.default_amount // 10 ** chosen_contract["decimals"]
    amount = input(f"Enter amount of transfer in {chosen_contract['name']} (e.g. {default_amount}): ") or default_amount
    destination = input(f"Input recepient of your transfer (TO) (e.g. {config.default_destination}): ") or config.default_destination

    tx = prepERC20Transfer(
        source,
        destination,
        chosen_contract["address"],
        chosen_contract.get("abi", False) or fetchABI(chosen_contract["address"]),
        float(amount),
    )
    return tx


def prep_autocomplete_from_kwargs(**kwargs):
    pparams = kwargs.copy()
    return pparams


def run_observer(**kwargs):
    """
    Create a transaction object based on provided parameters.
    This function uses argument names similar to those defined in `chain.yml`, but without the "default_" prefix.

    Args:
        chain (str): Chain name (e.g. 'base').
        tx_shortcut (str): Transaction shortcut: 'custom' for custom transaction, 'erc20', etc. (see full list in observer.shortcuts)
        sender (str): Address of the sender (FROM).
        destination (str): Address of the recipient (TO) for token transfers.
        contract (str): Smart contract address which is the target of the transaction, or the target address in case of a simple ETH transfer.
        type (int): Transaction type: 0 for legacy, 2 for EIP-1559.
        func_choice (str | int): Function choice, specified either as a name (str) or an index (int).
        func_params (tuple): Tuple of function parameters. Each parameter can be a string, int, etc.

    Returns:
        tx (dict): A transaction object ready to be consumed by a signer.
    """
    # pparams are exact user inputs to be inserted instead of input() prompts, while kwargs are consistent with config and intended for user
    # intended usage: pparams['tx_shortcut'] or inpuShortcut(...), while kwargs are human readable
    pparams = {}
    if kwargs:
        pparams = prep_autocomplete_from_kwargs(**kwargs)

    print("Choose desired blockchain for transaction: ")
    # include eth_tester provider regardless of the mode selected
    supported_chains = [key for key in config.chains.keys() if config.chains[key].get("debug", False) in {config.DEBUG, True}]

    print(
        "\n".join(
            [
                f"{v[0]} - {v[1].upper()} (chain_id: {config.chains[v[1]]['id']}) "
                f"{'-- [TEST NETWORK] ' if config.chains[v[1]].get('test',False) else ''}"
                f"{'-- [LOCAL NETWORK] ' if config.chains[v[1]].get('debug') else ''}"
                for v in enumerate(supported_chains, start=1)
            ]
        )
    )

    chosen_chain = pparams.get("chain", False) or inputShortcut(supported_chains)
    print(f"You have chosen {chosen_chain.upper()} blockchain.")
    chain_id = config.chains[chosen_chain]["id"]

    if config.chain_id != chain_id:
        change_chain(chosen_chain)

    print("Choose your desired transaction shortcut (default value is 1):")
    for i, shortcut in enumerate(available_shortcuts, start=1):
        print(f"{i} - {shortcut}")

    chosen_shortcut = pparams.get("tx_shortcut", False) or inputShortcut(available_shortcuts)
    print(f"You have chosen {chosen_shortcut} transaction.")

    source = pparams.get("sender", False) or input(f"Input sender address (FROM) (e.g. {config.default_sender}): ") or config.default_sender

    tx = {}

    if chosen_shortcut.lower() == "custom":
        # print('For desination address, remember to use ERC20 smart contract (e.g. USDT) address for coins transfer (you will specify receiver in parameters of transfer(...) function)')
        to_address = (
            pparams.get("contract", False)
            or input(f"Enter smart contract or destination address (e.g. {config.default_contract}): ")
            or config.default_contract
        )

        # PRINT FUNCTIONS
        if not isContract(to_address):
            tx = run_simple_eth_transfer(source, to_address, **pparams)

        else:
            tx = run_smart_contract_tx(source, to_address, **pparams)

    elif chosen_shortcut.lower() == "erc20":  # ERC20
        tx = run_erc20_transfer(source, **pparams)

    else:
        pass

    print("Your transaction is ready: ")
    print(tx)
    # Save cache on disk
    if not config.DEBUG:
        persist_cache()

    return tx


def main():
    # TODO: add parsing of sys.argv parameters if passed. Do not redirect stdin due to interactive mode required cross-platform.
    run_observer()


if __name__ == "__main__":
    main()
