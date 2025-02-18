import unittest

import w3off.config as config
from w3off.config import getChainName
from w3off.w3provider import change_chain, w3
from w3off.sender.w3sender import parseRawTxFromStr, sendRawTx, waitForReceipt
from w3off.helpers.txHelpers import decodeRawTx
from w3off.helpers.abiHelpers import decodeABICall
from w3off.test.data.txTestUSDTTransfer import txTestRaw
from w3off.test.ethTesterEnv import setEthTesterEnv
import eth_utils
from eth_abi import abi

from w3off.test.ethTesterContracts import usdt_ethtester, aave_v3_ethtester
from w3off.test.data.txTestUSDTTransfer import txTestRaw


class Test_Sender(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not config.DEBUG:
            cls.initial_chain = config.chain_name
            status = change_chain("debug")
            assert status == True
            # setEthTesterEnv(w3, w3.eth_tester)

    def setUp(self):
        from w3off.w3provider import resetEthTester

        resetEthTester()

    @classmethod
    def tearDownClass(cls):
        if not config.DEBUG:
            if cls.initial_chain != "eth":
                change_chain(cls.initial_chain)
                del cls.initial_chain

    def test_send(self):
        tx = decodeRawTx(txTestRaw["raw_transaction"])
        usdt_abi = config.smart_contracts_by_name["USDT"]["abi"]
        usdt = w3.eth.contract(address=config.default_erc20, abi=usdt_abi)

        func_name, to_address, amount = decodeABICall(usdt_abi, ["address", "uint256"], tx["data"])
        to_address = w3.to_checksum_address(to_address)
        self.assertEqual(func_name, "transfer")

        from_balance_1 = usdt.functions.balanceOf(tx["from"]).call()
        to_balance_1 = usdt.functions.balanceOf(to_address).call()

        nonce = w3.eth.get_transaction_count(tx["from"])
        gas = usdt.functions.transfer(to_address, amount).estimate_gas({"from": tx["from"], "nonce": nonce})
        self.assertGreater(gas, 0)

        txHash = sendRawTx(txTestRaw["raw_transaction"])
        self.assertTrue(txHash.hex())
        txReceipt = waitForReceipt(txHash)
        from_balance_2 = usdt.functions.balanceOf(tx["from"]).call()
        to_balance_2 = usdt.functions.balanceOf(to_address).call()

        self.assertGreater(txReceipt["cumulativeGasUsed"], 0)
        self.assertEqual(txReceipt["to"], tx["to"])
        self.assertEqual(txReceipt["from"], tx["from"])
        self.assertEqual(to_balance_2, to_balance_1 + amount)
        self.assertEqual(from_balance_2, from_balance_1 - amount)

    def test_sendRawTx_accepts_string(self):
        txHash = sendRawTx(txTestRaw["raw_transaction"])
        self.assertTrue(txHash)

    def test_parseRawTxFromStr(self):
        self.assertEqual(parseRawTxFromStr(txTestRaw.__str__()), txTestRaw["raw_transaction"])
        self.assertEqual(
            parseRawTxFromStr(txTestRaw["raw_transaction"]),
            txTestRaw["raw_transaction"],
        )


if __name__ == "__main__":
    unittest.main()
