"""
This module contains end to end transaction tests , i.e. running some test transactions through the whole pipeline and checking expected results.
"""

import json
import os
from pprint import pprint
import unittest
from unittest.mock import patch
from web3.datastructures import AttributeDict
from eth_account.datastructures import SignedTransaction

import w3off.config as config
from w3off.helpers.txHelpers import decodeRawTx
from w3off.observer.w3observer import run_observer
from w3off.sender.w3sender import run_sender
from w3off.signer.w3signer import run_signer, signedTxToDict
import w3off.test.data.txTestUSDTTransfer as t
import w3off.test.data.txTestEthTransfer as ts
from w3off.w3provider import change_chain, w3


class Test_w3off(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.verbose = config.verbose
        config.verbose = False
        if not config.DEBUG:
            cls.initial_chain = config.chain_name
            status = change_chain("debug")
            assert status == True

    @classmethod
    def tearDownClass(cls):
        config.verbose = cls.verbose

    def setUp(self):
        self.type = config.tx_type
        self.gas0 = t.txTest.pop("gas")  # gas consumed amounts can vary even on eth_tester
        self.gas2 = t.txTest_type2.pop("gas")  # gas consumed amounts can vary even on eth_tester
        self.gass = ts.txTest.pop("gas")  # gas consumed amounts can vary even on eth_tester
        from w3off.w3provider import resetEthTester

        resetEthTester()

    def tearDown(self):
        config.tx_type = self.type
        t.txTest.update({"gas": self.gas0})
        t.txTest_type2.update({"gas": self.gas2})
        ts.txTest.update({"gas": self.gass})

    def run_e2e_usdt_tx(self, isExplicitType: bool = False, type: int = 0):
        tx_test = t.txTest if type == 0 else t.txTest_type2
        config.tx_type = type

        usdt_abi = config.smart_contracts_by_name["USDT"]["abi"]
        usdt = w3.eth.contract(address=config.smart_contracts_by_name["USDT"]["address"], abi=usdt_abi)
        destination = "0xE57bFE9F44b819898F47BF37E5AF72a0783e1141"
        from_balance_1 = usdt.functions.balanceOf(tx_test["from"]).call()
        to_balance_1 = usdt.functions.balanceOf(destination).call()

        kwargs_observer = {
            "chain": "debug",
            "tx_shortcut": "custom",
            "sender": tx_test["from"],
            "contract": tx_test["to"],
            "func_choice": "transfer",
            "func_params": (destination, 1000000),
        }

        if isExplicitType:
            kwargs_observer.update({"type": type})

        tx = run_observer(**kwargs_observer)
        tx_gas = tx.pop("gas")
        self.assertIsInstance(tx, dict)
        self.assertDictEqual(tx, tx_test)
        tx.update({"gas": tx_gas})

        kwargs_signer = {
            "ignoreNetworkCheckPrompt": True,
            "pkey": "f8f8a2f43c8376ccb0871305060d7b27b0554d2cc72bccf41b2705608452f315",
        }
        raw_tx = run_signer(tx, **kwargs_signer)
        self.assertIsInstance(raw_tx, SignedTransaction)
        raw_tx_dict = signedTxToDict(raw_tx)
        tx_restored = decodeRawTx(raw_tx_dict["raw_transaction"])
        tx_restored.pop("hash") and tx_restored.pop("r") and tx_restored.pop("s") and tx_restored.pop("v") and tx_restored.pop("accessList", True)
        self.assertDictEqual(tx_restored, tx)

        kwargs_sender = {"ignoreNetworkCheckPrompt": True, "ignoreTxConfirmation": True}
        txReceipt = run_sender(raw_tx_dict["raw_transaction"], **kwargs_sender)
        self.assertIsInstance(txReceipt, dict)
        self.assertEqual(txReceipt["transactionHash"], raw_tx_dict["hash"])
        self.assertEqual(txReceipt["status"], 1)
        # index_sender = next( (i for i in range(1, len(w3.eth.accounts)) if w3.eth.accounts[i] == kwargs_observer['sender']) )
        # index_destination = next( (i for i in range(1, len(w3.eth.accounts)) if w3.eth.accounts[i] == kwargs_observer['sender']) )

        from_balance_2 = usdt.functions.balanceOf(tx_test["from"]).call()
        to_balance_2 = usdt.functions.balanceOf(destination).call()

        self.assertEqual(from_balance_2, from_balance_1 - 1000000)
        self.assertEqual(to_balance_2, to_balance_1 + 1000000)

    def test_e2e_usdt_tx_type0_implicit(self):
        self.run_e2e_usdt_tx(isExplicitType=False)

    def test_e2e_usdt_tx_type0_explicit(self):
        self.run_e2e_usdt_tx(isExplicitType=True)

    def test_e2e_usdt_tx_type2_implicit(self):
        self.run_e2e_usdt_tx(isExplicitType=False, type=2)

    def test_e2e_usdt_tx_type2_explicit(self):
        self.run_e2e_usdt_tx(isExplicitType=True, type=2)

    def test_simple_eth_transfer(self):
        tx_test = ts.txTest
        kwargs_observer = {
            "chain": "debug",
            "tx_shortcut": "custom",
            "sender": tx_test["from"],
            "contract": tx_test["to"],
            "value": tx_test["value"],
        }

        from_balance_1 = w3.eth.get_balance(ts.txTest["from"])
        to_balance_1 = w3.eth.get_balance(ts.txTest["to"])

        tx = run_observer(**kwargs_observer)

        tx_gas = tx.pop("gas")
        self.assertIsInstance(tx, dict)
        self.assertDictEqual(tx, tx_test)
        tx.update({"gas": tx_gas})

        kwargs_signer = {
            "ignoreNetworkCheckPrompt": True,
            "pkey": "f8f8a2f43c8376ccb0871305060d7b27b0554d2cc72bccf41b2705608452f315",
        }
        raw_tx = run_signer(tx, **kwargs_signer)
        self.assertIsInstance(raw_tx, SignedTransaction)
        raw_tx_dict = signedTxToDict(raw_tx)
        tx_restored = decodeRawTx(raw_tx_dict["raw_transaction"])
        tx_restored.pop("hash", True) and tx_restored.pop("r", True) and tx_restored.pop("s", True) and tx_restored.pop("v", True)
        tx_restored.pop("accessList", True)
        self.assertDictEqual(tx_restored, tx)

        kwargs_sender = {"ignoreNetworkCheckPrompt": True, "ignoreTxConfirmation": True}
        txReceipt = run_sender(raw_tx_dict["raw_transaction"], **kwargs_sender)
        self.assertEqual(txReceipt["status"], 1)

        txCost = txReceipt["cumulativeGasUsed"] * txReceipt["effectiveGasPrice"]
        from_balance_2 = w3.eth.get_balance(tx_test["from"])
        to_balance_2 = w3.eth.get_balance(tx_test["to"])

        self.assertEqual(from_balance_2, from_balance_1 - tx_test["value"] - txCost)
        self.assertEqual(to_balance_2, to_balance_1 + tx_test["value"])


if __name__ == "__main__":
    unittest.main()
