import requests
import w3off.config as config
from w3off.config import getChainName
from w3off.w3provider import estimateBaseFee, w3
from w3off.observer.fetchABI import fetchABI, implementationAddress, isContract
from web3.types import TContractFn
from eth_utils import keccak
from w3off.cli.helpers import bcolors

# Flags for currently processed transaction
isSmartContract = True
isProxy = False
implementation = ""
name = "Custom"


def prepTx(
    from_address: str,
    to_address: str,
    value: int = 0,
    f: TContractFn = None,
    param_values: tuple = None,
    type: int = config.tx_type,
):
    """Given parsed contract function and its parameters, construct a transaction for signing."""
    # Normalize addresses
    from_address = w3.to_checksum_address(from_address)
    to_address = w3.to_checksum_address(to_address)

    # Construct transaction params
    nonce = w3.eth.get_transaction_count(from_address)
    gas_price = w3.eth.gas_price  # default calculation

    tx = {}
    low_percentile = 5
    priority_fees_low_estimate = calculateGasPriorityFeePercentile(low_percentile=low_percentile) or 0

    if config.verbose:
        avg_base_fee = calculateGasBaseFeeAverage()
        print(f"=============================== ")
        print(f"Current network gas statistics: ")
        print(f"=============================== ")
        print(f"- current gas price = {round(w3.from_wei(gas_price, 'gwei'),4)} gwei")
        print(f"- avg base fee = {round(w3.from_wei(avg_base_fee, 'gwei'),4)} gwei")
        print(f"- priority fee (lower {low_percentile}% percentile) = {round(w3.from_wei(priority_fees_low_estimate, 'gwei'),4)} gwei")

    if type == 2:
        base_fee = estimateBaseFee()
        # maxPriorityFeePerGas = min(int(gas_price*config.gas_leeway_coef) - base_fee,config.gas_max_priority_fee)
        maxPriorityFeePerGas = int(
            min(
                w3.eth.max_priority_fee,
                priority_fees_low_estimate,
                config.gas_max_priority_fee,
            )
        )
        maxFeePerGas = int((base_fee + maxPriorityFeePerGas) * config.gas_leeway_coef)
        if maxFeePerGas > config.gas_max_fee:
            print(
                f"{bcolors.WARNING}High gas price{bcolors.ENDC}. Estimated maxFeePerGas is {round(w3.from_wei(maxFeePerGas,'gwei'),4)} \
                   and it exceeds your limit in configuration of {round(w3.from_wei(config.gas_max_fee,'gwei'),4)} gwei."
            )

        if config.verbose:
            print(f"================================ ")
            print(f"Your transaction gas parameters: ")
            print(f"================================ ")
            print(f"- type: 2 (EIP-1559)             ")
            print(f"- base fee (MINIMUM EXPENSE)= {round(w3.from_wei(base_fee, 'gwei'),4)} gwei")
            print(f"- max priority fee per gas = {round(w3.from_wei(maxPriorityFeePerGas, 'gwei'),4)} gwei")
            print(f"- max fee per gas for your transaction (UPPER EXPENSE LIMIT) = {round(w3.from_wei(maxFeePerGas, 'gwei'),4)} gwei")
            print(f"=============================== ")

    if f is not None:
        if not isContract(to_address):
            raise ValueError(f"The target address {to_address} should be smart contract address.")
        try:
            gas = f(*param_values).estimate_gas({"from": from_address, "nonce": nonce})
            gas = int(gas * config.gas_leeway_coef)
        except Exception as e:
            print(f"{bcolors.WARNING}WARNING!{bcolors.ENDC} Could not estimate gas by running locally, since the transaction could not execute.")
            print(f"Transaction error message: {e}")
            if handleApprovalIfRequired(from_address, to_address, value, f, param_values, type):
                nonce = nonce + 1
            print(f"Pulling recent gas price data as a gas estimate for the transaction below...")
            gas = calculateGasBasedOnHistory(to_address, f.signature)
            gas = int(gas * config.gas_leeway_coef_pessimistic)  # need slightly more buffer due to historical estimation

        if type == 0:
            # Legacy Transaction (Type 0)
            tx = f(*param_values).build_transaction(
                {
                    "chainId": w3.eth.chain_id,
                    "from": from_address,  # Specify the source address here
                    "gas": gas,
                    "gasPrice": gas_price,  # use gas_price if connected to blockchain
                    "nonce": nonce,
                    "value": 0,
                }
            )
        else:
            # EIP-1559 transaction (Type 2)
            tx = f(*param_values).build_transaction(
                {
                    "type": 2,
                    "chainId": w3.eth.chain_id,
                    "from": from_address,  # Specify the source address here
                    "gas": gas,
                    "maxPriorityFeePerGas": maxPriorityFeePerGas,
                    "maxFeePerGas": maxFeePerGas,
                    "nonce": nonce,
                    "value": 0,  # Value in wei (for token transfer, this is usually 0)
                }
            )

    else:  # Simple transfer
        tx = {
            "chainId": w3.eth.chain_id,
            "from": from_address,
            "to": to_address,
            "data": "0x",
            # 'gas': gas,          # To be calculated below and then added
            "gasPrice": gas_price,
            "nonce": nonce,
            "value": value,
        }
        gas = int(w3.eth.estimate_gas(tx) * config.gas_leeway_coef)
        tx.update({"gas": gas})
        if type == 2:
            # Update to EIP-1559 transaction (Type 2)
            del tx["gasPrice"]
            tx.update(
                {
                    "type": 2,
                    "maxPriorityFeePerGas": maxPriorityFeePerGas,
                    "maxFeePerGas": maxFeePerGas,
                }
            )

    return tx


def parseERC20Info(f: TContractFn = None, param_values: tuple = None):
    token_info = {}
    for i, param in enumerate(f.abi["inputs"]):
        if param["type"] == "address" and ("asset" in param["name"] or config.smart_contracts.get(param_values[i], {}).get("type") == "ERC20") and (not token_info):
            try:
                token_info = config.smart_contracts.get(param_values[i])
            except Exception as e:
                print(f"Could not obtain ERC20 token info for {param_values[i]} locally.")
                print("Fetching token info online...")
                fetchERC20Info(param_values[i])

            token_info["address"] = param_values[i]
        if param["type"][:4] == "uint" and ("amount" in param["name"].lower()) and ("amount" not in token_info):
            token_info["amount"] = param_values[i]
            token_info["amount_index"] = i
    return token_info


def fetchERC20Info(token_address, abi=None):
    abi = abi or fetchABI(token_address)
    contract = w3.eth.contract(address=token_address, abi=abi)
    name = contract.functions.name().call()
    decimals = contract.functions.decimals().call()
    symbol = contract.functions.symbol().call()
    config.smart_contracts[token_address] = {
        "name": name,
        "decimals": decimals,
        "symbol": symbol,
        "address": token_address,
        "abi": abi,
        "type": "ERC20",
    }
    return config.smart_contracts[token_address]


def fetchApprovedAmount(from_address, spender_address, token_info, abi=None):
    abi = abi or fetchABI(implementationAddress(token_info["address"]))
    contract = w3.eth.contract(address=token_info["address"], abi=abi)

    decimals = contract.functions.decimals.call()
    token_info["decimals"] = decimals
    token_info["abi"] = abi

    allowance = contract.functions.allowance(from_address, spender_address).call()
    return allowance


def handleApprovalIfRequired(
    from_address: str,
    to_address: str,
    value: int = 0,
    f: TContractFn = None,
    param_values: tuple = None,
    type: int = config.tx_type,
):
    """Returns True if approval transaction was handled."""
    approvedAmount = None  # no approval needed
    if config.smart_contracts.get(to_address, {}).get("type", False) == "ERC20":
        # No need to check for approval if target smart contract is the token itself
        return False

    token_info = parseERC20Info(f, param_values)
    if token_info:
        approvedAmount = fetchApprovedAmount(from_address, to_address, token_info)
    else:
        print("No ERC20 token detected in the parameters of transaction. If you think this is not right, check `chains.yaml` to see if your expected token is listed in smart contracts list.")
        return False
    if approvedAmount < token_info.get("amount", -1):  # Not enough allowance
        print(f"{bcolors.WARNING}Approval to spend coins needed{bcolors.ENDC}. You need to issue approval to spend at least {token_info['amount'] // 10**token_info['decimals']} of {token_info['name']} first. Your current allowance is {approvedAmount}.")
        print(f"We proceed to approval transaction creation. Please launch this dialog again , if needed, for your initially desired transaction once you complete the approval tx.")
        erc20_contract = w3.eth.contract(address=token_info["address"], abi=token_info["abi"])
        tx_approval = prepTx(
            from_address,
            token_info["address"],
            0,
            erc20_contract.functions.approve,
            (to_address, token_info.get("amount")),
            type,
        )
        print("Your approval transaction is ready (RUN FIRST): ")
        print(tx_approval)
        return True
    else:
        print(f"You have enough token allowance to proceed. Your current allowance for smart contract {to_address} is {approvedAmount}.")
    return False


def calculateGasBasedOnHistory(contract_address, f_signature):
    assert config.ethscan_api_key, "Please sign up on etherscan and save your API key to environment variable named ETHSCAN_API_KEY to use this application."
    response = requests.post(
        f"https://api.etherscan.io/v2/api?chainId={w3.eth.chain_id}&module=account&action=txlist&address={contract_address}&startblock=0&endblock=99999999&page=1&offset=10000&sort=asc&apikey={config.ethscan_api_key}"
    )
    response_json = response.json()
    f_name_encoded = "0x" + keccak(text=f_signature).hex()[:8]
    transactions = filter(lambda tx: tx.get("methodId") == f_name_encoded, response_json["result"])

    gas_prices = []
    gas_used = []
    i = 0
    for i, tx in enumerate(transactions):
        gas_prices.append(int(tx["gasPrice"]))
        gas_used.append(int(tx["gasUsed"]))
        if i > 50:
            break

    average_gas_price = sum(gas_prices) / len(gas_prices)
    average_gas_used = int(sum(gas_used) / len(gas_used)) + 1

    # return w3.from_wei(average_gas_price, 'gwei')
    return average_gas_used


def calculateGasBaseFeeAverage(n_blocks: int = 5):
    fee_history = w3.eth.fee_history(n_blocks, "latest", [10, 90])
    base_fee = sum(fee_history["baseFeePerGas"]) / len(fee_history["baseFeePerGas"])
    return base_fee


def calculateGasPriorityFeePercentile(n_blocks: int = 1, low_percentile: int = 10):
    fee_history = w3.eth.fee_history(n_blocks, "latest", [low_percentile, 90])
    if fee_history["reward"]:
        priority_fees_low = [low_reward for low_reward in fee_history["reward"][0]]
        priority_fees_low_estimate = sum(priority_fees_low) / len(priority_fees_low)
    else:
        priority_fees_low = []
        priority_fees_low_estimate = 0
    return priority_fees_low_estimate
