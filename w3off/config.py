import glob
import json
import os

from yaml import load

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

# Enable debug mode to use eth_tester instead of connection to an actual RPC mode
DEBUG = False

# Chains contain chain IDs and some predefined smart contracts on these chains
chains = {}  # populated via yaml_loader.py
# If user provided config in ~/.w3off/chains.yaml, use it, otherwise use the one in root folder
chains_file_path = os.path.join(os.path.expanduser("~"), ".w3off", "chains.yaml")
if os.path.exists(chains_file_path):
    chains_uses_home_path = True
    print(f'Loading chains.yaml configuration from ~/.w3off...')
else:
    chains_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),"chains.yaml")
    chains_uses_home_path = False
    print(f'Loading chains.yaml from your installed package directory...')
stream = open(chains_file_path)
chains = load(stream, Loader)
stream.close()
assert chains["eth"]["smart_contracts"]["USDT"]["type"] == "ERC20", "To ensure configuraiton is working, please provide USDT smart contract details on ETH MainNet as part of chains.yaml file"

chain_name = "eth" if not DEBUG else "debug"
# chain_id = 1 if not DEBUG else 131277322940537 # current chain id
chain_id = chains[chain_name]["id"]

# Replace smart contract addresses with debug addresses if DEBUG mode is enabled
for chain in chains.values():
    for name, contract in chain.get("smart_contracts", {}).items():
        if DEBUG and "debug_overrides" in contract and "address" in contract["debug_overrides"]:
            contract["address"] = contract["debug_overrides"]["address"]
            del contract["debug_overrides"]
        if contract:
            contract["name"] = name

# Application cache (global)
cache = {}
if chains_uses_home_path:
    cache_file_path = os.path.join(os.path.expanduser("~"), ".w3off", "cache.json")
    cache_prompt_path_str = '~/.w3off'
else:
    cache_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),"cache.json")
    cache_prompt_path_str = 'your installed package directory'

try:
    with open(cache_file_path) as json_file:
        cache = json.load(json_file)
    print(f'Loading cache.json from {cache_prompt_path_str}...')
except:
    print(f'No cache.json file available at {cache_prompt_path_str}. The file will be auto-generated after the first successful run.')
    cache = {}

# DEFAULT VALUES FOR API URLs
# Choose network browser
ethscan_api_key = os.environ.get("ETHSCAN_API_KEY","")
# Choose one of the following node providers below:
web3_provider_url = chains[chain_name]["rpc_provider"]
# web3_provider_url = f"https://mainnet.infura.io/v3/{os.environ['INFURA_API_KEY']}" if not DEBUG else "debug"
# web3_provider_url = "https://rpc.ankr.com/eth" if not DEBUG else "EthereumTester (LOCAL)"
# web3_provider_url = "https://ethereum-rpc.publicnode.com" if not DEBUG else "EthereumTester (LOCAL)"
# web3_provider_url = "https://eth.llamarpc.com" if not DEBUG else "EthereumTester (LOCAL)"
# web3_provider_url = f"https://polished-spring-needle.quiknode.pro/{os.environ['QUICKNODE_API_KEY']}"  # Alternative provider


# Add ABIs to the previously loaded YAML ration from test/data/*.abi
def load_predefined_abis(smart_contracts):
    """Loads ABIs from test/data/*.abi to `smart_contracts` dictionary."""
    _nPredefinedSmartContracts = len(smart_contracts)
    if _nPredefinedSmartContracts == 0:
        return
    for file_path in glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), "test", "data", "*.abi")):
        file_name = os.path.splitext(os.path.basename(file_path))[0]
        name_to_addr = {value["name"].lower(): addr for addr, value in smart_contracts.items()}
        # Loads ABI strings from test/data/*.abi for ETH and DEBUG chains only
        with open(file_path) as file:
            addr = name_to_addr.get(file_name)
            if addr and "abi" not in smart_contracts[addr]:
                smart_contracts[addr].update({"abi": file.read()})


load_predefined_abis(chains["eth"]["smart_contracts"])
load_predefined_abis(chains["debug"]["smart_contracts"])
# for chain in chains.values():
#     load_predefined_abis(chain.get('smart_contracts',{}))

# Allows to use smart_contracts_by_name['0x...'] , i.e. uses comfortable indexing
# smart_contracts_by_name = {k: v.get('smart_contracts',{}) for k, v in chains.items()}
# smart_contracts = { chain_name: { v['address']: {'name': k, **v } for k, v in chain_obj.items()} for chain_name, chain_obj in smart_contracts_by_name.items() }
smart_contracts_by_name = chains["eth"]["smart_contracts"]
for key in smart_contracts_by_name:
    smart_contracts_by_name[key]["name"] = key
smart_contracts = {v["address"]: {"name": k, **v} for k, v in smart_contracts_by_name.items()}

if DEBUG:
    assert chains["eth"]["smart_contracts"]["USDT"]["address"] == "0x2946259E0334f33A064106302415aD3391BeD384"
    assert len(smart_contracts["0x2946259E0334f33A064106302415aD3391BeD384"]["abi"]) > 0
    assert smart_contracts["0xD24260C102B5D128cbEFA0F655E5be3c2370677C"]["implementation"] == "0xeF434E4573b90b6ECd4a00f4888381e4D0CC5Ccd"
    assert smart_contracts["0xD24260C102B5D128cbEFA0F655E5be3c2370677C"]["proxy"]
    assert len(smart_contracts["0xD24260C102B5D128cbEFA0F655E5be3c2370677C"]["abi"]) > 0
else:
    assert smart_contracts["0xdAC17F958D2ee523a2206206994597C13D831ec7"]["type"] == "ERC20"
    assert smart_contracts["0xdAC17F958D2ee523a2206206994597C13D831ec7"]["decimals"] == 6
    assert smart_contracts["0xdAC17F958D2ee523a2206206994597C13D831ec7"]["name"] == "USDT"

assert smart_contracts_by_name["USDT"]["name"] == "USDT"
assert smart_contracts_by_name["USDT"]["type"] == "ERC20"
assert len(smart_contracts_by_name["USDT"]["abi"]) > 0
assert len(smart_contracts_by_name["USDC"]["abi"]) > 0
# assert 'abi' not in chains['base']['smart_contracts']['USDC']

# DEFAULT VALUES
default_amount = chains["eth"]["defaults"]["amount"] or 1500000000

# gas parameters
tx_type = chains["eth"]["defaults"]["tx_type"] or 0
default_maxgas = chains["eth"]["defaults"]["maxgas"] or 2000000
gas_leeway_coef = chains["eth"]["defaults"]["gas_leeway_coef"] or 1.1
gas_leeway_coef_pessimistic = chains["eth"]["defaults"]["gas_leeway_coef_pessimistic"] or 1.3
gas_max_priority_fee = chains["eth"]["defaults"]["gas_max_priority_fee"] or 2
gas_max_fee = chains["eth"]["defaults"]["gas_max_fee"] or 10
# converting from gwei
gas_max_priority_fee = gas_max_priority_fee * 10**9
gas_max_fee = gas_max_fee * 10**9

default_pkey_mode = chains["eth"]["defaults"]["pkey_mode"] or 1  # in place
default_keystore_file = (
    os.path.join(*tuple(chains["eth"]["defaults"]["keystore_file"].split("/"))) 
    or os.path.join(os.path.dirname(os.path.abspath(__file__)),"data", "keystore-test.json")
)
# default_keystore_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),"data","keystore-test2.json")  # 0x6f9bcfc0edb4057cda665e36d03b7d58e5926b04 | Vintage0!
default_keystore_address = "0x406617a94b991143d92dc3ff53ca29bce1a407c3"
default_keystore_pwd = "MyTestPassword$123"
default_mnemonic_size = 24

default_sender = chains["eth"]["defaults"]["sender"] or "0x001d3F1ef827552Ae1114027BD3ECF1f086bA0F9"
# DEBUG ADDRESS 0x001d3f1ef827552ae1114027bd3ecf1f086ba0f9
# pkey f8f8a2f43c8376ccb0871305060d7b27b0554d2cc72bccf41b2705608452f315 -- test/keystore-default.json, test/keystore-test.json
# Keccak256(K) = 2a5bc342ed616b5ba5732269001d3f1ef827552ae1114027bd3ecf1f086ba0f9
default_destination = chains["eth"]["defaults"]["sender"] or default_sender

default_erc20 = (
    smart_contracts_by_name.get(chains["eth"]["defaults"]["erc20"], {}).get("address", False)
    or chains["eth"]["defaults"]["erc20"]
    or "0xdAC17F958D2ee523a2206206994597C13D831ec7"
)
default_contract = (
    smart_contracts_by_name.get(chains["eth"]["defaults"]["contract"], {}).get("address", False)
    or chains["eth"]["defaults"]["contract"]
    or default_erc20
)
default_abi = smart_contracts[default_contract]["abi"]

signer_suggest_keystore = chains["eth"]["defaults"]["signer_suggest_keystore"] or True
verbose = chains["eth"]["defaults"]["verbose"] or True


def getDefault(chosen_chain: str, key: str):
    global chains
    return chains.get(chosen_chain, {}).get("defaults", {}).get(key, "")


def getChainName(custom_chain_id: int = None):
    """Return current chain name chain_id"""
    global chain_id
    if custom_chain_id is None:
        custom_chain_id = chain_id
    return next((k for k, v in chains.items() if v["id"] == custom_chain_id), None)
