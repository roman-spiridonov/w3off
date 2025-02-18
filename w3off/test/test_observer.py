import unittest
from unittest import mock
from unittest.mock import patch, MagicMock, Mock
import w3off.config as config
from w3off.config import getChainName
from w3off.observer.fetchABI import fetchABI, implementationAddress, listFunctions, isContract
from w3off.signer.checkOffline import checkOffline
from w3off.w3provider import change_chain, w3
from w3off.test.ethTesterContracts import aave_v3_ethtester, usdt_ethtester


class Test_fetchABI(unittest.TestCase):
    """Test caching and ABI fetching."""

    @classmethod
    def setUpClass(cls):
        cls.initial_chain = config.chain_name
        cls.initial_smart_contracts = config.smart_contracts
        cls.initial_cache = config.cache
        cls.usdt_abi = '[{"constant":true,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"_upgradedAddress","type":"address"}],"name":"deprecate","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":false,"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"deprecated","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"_evilUser","type":"address"}],"name":"addBlackList","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"totalSupply","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"_from","type":"address"},{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transferFrom","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"upgradedAddress","outputs":[{"name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"name":"","type":"address"}],"name":"balances","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"maximumFee","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"_totalSupply","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[],"name":"unpause","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[{"name":"_maker","type":"address"}],"name":"getBlackListStatus","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"name":"","type":"address"},{"name":"","type":"address"}],"name":"allowed","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"paused","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"name":"who","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[],"name":"pause","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"getOwner","outputs":[{"name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"owner","outputs":[{"name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":false,"inputs":[{"name":"newBasisPoints","type":"uint256"},{"name":"newMaxFee","type":"uint256"}],"name":"setParams","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":false,"inputs":[{"name":"amount","type":"uint256"}],"name":"issue","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":false,"inputs":[{"name":"amount","type":"uint256"}],"name":"redeem","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[{"name":"_owner","type":"address"},{"name":"_spender","type":"address"}],"name":"allowance","outputs":[{"name":"remaining","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"basisPointsRate","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"name":"","type":"address"}],"name":"isBlackListed","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"_clearedUser","type":"address"}],"name":"removeBlackList","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"MAX_UINT","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"newOwner","type":"address"}],"name":"transferOwnership","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":false,"inputs":[{"name":"_blackListedUser","type":"address"}],"name":"destroyBlackFunds","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"inputs":[{"name":"_initialSupply","type":"uint256"},{"name":"_name","type":"string"},{"name":"_symbol","type":"string"},{"name":"_decimals","type":"uint256"}],"payable":false,"stateMutability":"nonpayable","type":"constructor"},{"anonymous":false,"inputs":[{"indexed":false,"name":"amount","type":"uint256"}],"name":"Issue","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"name":"amount","type":"uint256"}],"name":"Redeem","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"name":"newAddress","type":"address"}],"name":"Deprecate","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"name":"feeBasisPoints","type":"uint256"},{"indexed":false,"name":"maxFee","type":"uint256"}],"name":"Params","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"name":"_blackListedUser","type":"address"},{"indexed":false,"name":"_balance","type":"uint256"}],"name":"DestroyedBlackFunds","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"name":"_user","type":"address"}],"name":"AddedBlackList","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"name":"_user","type":"address"}],"name":"RemovedBlackList","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"owner","type":"address"},{"indexed":true,"name":"spender","type":"address"},{"indexed":false,"name":"value","type":"uint256"}],"name":"Approval","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"from","type":"address"},{"indexed":true,"name":"to","type":"address"},{"indexed":false,"name":"value","type":"uint256"}],"name":"Transfer","type":"event"},{"anonymous":false,"inputs":[],"name":"Pause","type":"event"},{"anonymous":false,"inputs":[],"name":"Unpause","type":"event"}]'
        config.smart_contracts = {}
        config.cache = {"abi": {
            usdt_ethtester["contract_address"]: cls.usdt_abi
        }}
        cls.online_mode = w3.is_connected() and cls.initial_chain != "debug"
        cls.target_chain = "debug" if cls.online_mode else "eth"
        if cls.online_mode and cls.initial_chain != "eth":
            change_chain("eth")

    @classmethod
    def tearDownClass(cls):
        if cls.initial_chain != cls.target_chain and cls.online_mode:
            change_chain(cls.initial_chain)
        del cls.initial_chain
        config.smart_contracts = cls.initial_smart_contracts
        config.cache = cls.initial_cache

    def test_usdt(self):
        if not self.online_mode:
            print(f"Skipped << {self.__str__().replace('__main__.','')} >> due to the fact that you are offline.")
            return
        abi = fetchABI(usdt_ethtester["contract_address"])
        self.assertEqual(abi,self.usdt_abi)

    @patch("w3off.observer.fetchABI.implementationAddress")
    @patch("w3off.observer.fetchABI.fetchABI")
    @patch("w3off.observer.fetchABI.isContract")
    def test_listFunctions(self, mock_isContract, mock_fetchABI, mock_implementationAddress):
        AAVE_V3_addr = "0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2"
        AAVE_V3_implementation = "0xeF434E4573b90b6ECd4a00f4888381e4D0CC5Ccd"
        self.assertNotIn(AAVE_V3_addr, config.cache["abi"])
        self.assertNotIn(AAVE_V3_implementation, config.cache["abi"])
        mock_implementationAddress.side_effect = lambda addr: (
            "0xeF434E4573b90b6ECd4a00f4888381e4D0CC5Ccd" if addr == "0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2" else ""
        )
        mock_fetchABI.side_effect = lambda addr: (aave_v3_ethtester["abi"] if addr == "0xeF434E4573b90b6ECd4a00f4888381e4D0CC5Ccd" else "")
        mock_isContract.side_effect = lambda addr: (
            True if (addr == "0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2" or addr == "0xeF434E4573b90b6ECd4a00f4888381e4D0CC5Ccd") else False
        )
        funcs = listFunctions(AAVE_V3_addr)
        self.assertIn(AAVE_V3_addr, config.cache["abi"])
        self.assertIn(AAVE_V3_implementation, config.cache["abi"])

        self.assertIsNotNone(funcs[0].abi)
        self.assertEqual(funcs[0].abi["type"], "function")


if __name__ == "__main__":
    unittest.main()
