import unittest
from web3.datastructures import AttributeDict

from web3 import Web3, EthereumTesterProvider
from eth_abi import encode

from hexbytes import HexBytes

from w3off.helpers.abiHelpers import dataFromCall, encodeABICall, pad_hex
from w3off.helpers.addressHelpers import deployerToSmartContractAddress
from w3off.helpers.txHelpers import decodeRawTx, prepareDictToPrint


class TestAddressHelpers(unittest.TestCase):

    def test_deployerToSmartContractAddress(self):
        usdt_sc = "0xdAC17F958D2ee523a2206206994597C13D831ec7"
        usdt_sc_deployer = "0x36928500Bc1dCd7af6a2B4008875CC336b927D57"  # see https://etherscan.io/tx/0x51a2395087450379f38a866662090d6656e73929d205d8d559f5c8f2c46a2ca1
        self.assertEqual(
            usdt_sc.lower(),
            deployerToSmartContractAddress(address=usdt_sc_deployer, nonce=6),
        )


class TestAbiHelpers(unittest.TestCase):
    def test_encodeabi(self):
        func_sig = "withdraw(uint256)"
        params = [10000000000000000]
        self.assertEqual(
            encodeABICall(func_sig, params),
            "000000000000000000000000000000000000000000000000002386f26fc10000",
        )

    def test_pad_hex(self):
        # Test padding of a typical Ethereum address
        address = "0x1234567890123456789012345678901234567890"
        expected_output = "0000000000000000000000001234567890123456789012345678901234567890"
        self.assertEqual(pad_hex(address), expected_output)

        # Test padding of a short hex value
        short_hex = "0x1a"
        expected_output_short = "000000000000000000000000000000000000000000000000000000000000001a"
        self.assertEqual(pad_hex(short_hex), expected_output_short)

        # Test padding of a full-length hex value (no padding needed)
        full_length_hex = "0x" + "f" * 64  # 64 'f' characters
        expected_output_full = "f" * 64
        self.assertEqual(pad_hex(full_length_hex), expected_output_full)

    def test_withdraw(self):
        # https://github.com/ethereumbook/ethereumbook/blob/develop/06transactions.asciidoc
        w3 = Web3(EthereumTesterProvider())
        func_sig = "withdraw(uint256)"
        params = [10000000000000000]
        self.assertEqual(
            dataFromCall(func_sig, params),
            "2e1a7d4d000000000000000000000000000000000000000000000000002386f26fc10000",
        )

    def test_usdt_transfer(self):
        # Similar output to $ cast calldata "transfer(address,uint256)" 0x5AD1F1Aa106B5Af3A4F9D8B095427Df95607a452 2002220000
        # w3 = Web3(Web3.HTTPProvider('http://localhost:8545'))
        w3 = Web3(EthereumTesterProvider())
        func_sig = "transfer(address,uint256)"
        params = ["0x5AD1F1Aa106B5Af3A4F9D8B095427Df95607a452", int(2002.22 * 10**6)]
        self.assertEqual(
            dataFromCall(func_sig, params),
            "a9059cbb0000000000000000000000005ad1f1aa106b5af3a4f9d8b095427df95607a45200000000000000000000000000000000000000000000000000000000775773e0",
        )


class TestTxHelpers(unittest.TestCase):
    def test_decodeRawTxLegacy1(self):
        raw_tx = "0xf8a910850684ee180082e48694a0b86991c6218b36c1d19d4a2e9eb0ce3606eb4880b844a9059cbb000000000000000000000000b8b59a7bc828e6074a4dd00fa422ee6b92703f9200000000000000000000000000000000000000000000000000000000010366401ba0e2a4093875682ac6a1da94cdcc0a783fe61a7273d98e1ebfe77ace9cab91a120a00f553e48f3496b7329a7c0008b3531dd29490c517ad28b0e6c1fba03b79a1dee"  # noqa
        res = decodeRawTx(raw_tx)
        expected = {
            "chainId": -4,
            "data": "0xa9059cbb000000000000000000000000b8b59a7bc828e6074a4dd00fa422ee6b92703f920000000000000000000000000000000000000000000000000000000001036640",
            "from": "0xD8cE57B469962b6Ea944d28b741312Fb7E78cfaF",
            "gas": 58502,
            "gasPrice": 28000000000,
            "hash": "0xb808400bd5a1dd9c37960c515d2493c380b829c5a592e499ed0d5d9913a6a446",
            "nonce": 16,
            "r": "0xe2a4093875682ac6a1da94cdcc0a783fe61a7273d98e1ebfe77ace9cab91a120",
            "s": "0xf553e48f3496b7329a7c0008b3531dd29490c517ad28b0e6c1fba03b79a1dee",
            "to": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            "v": 27,
            "value": 0,
        }
        self.assertDictEqual(res, expected)

    def test_decodeRawTxLegacy2(self):
        import w3off.test.data.txTestAaveSupply as t

        res = decodeRawTx(t.txTestRaw["raw_transaction"])
        res.pop("r") and res.pop("s") and res.pop("v") and res.pop("hash")
        self.assertEqual(res, t.txTest)

    def test_decodeRawTxType2(self):
        original_hexstr = "0x02f8ef822105048275308356578f8305542b94a238dd80c259a72e81d7e4664a9801593f98d1c580b884617ba037000000000000000000000000833589fcd6edb6e08f4c7c32d4f71b54bda029130000000000000000000000000000000000000000000000000000000005f5e1000000000000000000000000005970f919a4e1c57d32d2160425ad7b4cb3a43d4a0000000000000000000000000000000000000000000000000000000000000000c080a0e9bc4a3a293f1245215ec8f2e1354deba8b7f6c06618ce3ab330801050079e72a0102d14d09474d89948c69c308809897618351aee7eeb923cfeaf9ef3e55a9ede"  # Example transaction hash
        tx = decodeRawTx(original_hexstr)
        self.assertEqual(tx["maxFeePerGas"], 5658511)
        self.assertEqual(tx["maxPriorityFeePerGas"], 30000)
        self.assertEqual(tx["type"], 2)
        self.assertTrue("accessList" in tx)
        self.assertFalse("gasPrice" in tx)

        import w3off.test.data.txTestUSDTTransfer as t

        original_hexstr2 = t.txTestRaw_type2["raw_transaction"]
        tx2 = decodeRawTx(original_hexstr2)
        self.assertEqual(tx2["maxFeePerGas"], 174957127)
        self.assertEqual(tx2["maxPriorityFeePerGas"], 0)
        self.assertEqual(tx2["to"], "0x2946259E0334f33A064106302415aD3391BeD384")
        self.assertEqual(tx2["type"], 2)
        self.assertFalse("gasPrice" in tx2)

        original_hexstr3 = "0x02f86c867765623370798080840a6da24782da97942946259e0334f33a064106302415ad3391bed3848080c080a077fbb67de7b070d8056dbd7f222256ccb2fa7d2e2a162f2f15e1febc4b7149bfa0794b6563d48d98943350eb89a0f7198ee065f0cb0c082446b973f821a3558c7d"
        tx3 = decodeRawTx(original_hexstr3)
        self.assertEqual(tx3["maxFeePerGas"], 174957127)
        self.assertEqual(tx3["maxPriorityFeePerGas"], 0)
        self.assertEqual(tx3["to"], "0x2946259E0334f33A064106302415aD3391BeD384")
        self.assertEqual(tx3["type"], 2)
        self.assertFalse("gasPrice" in tx3)

    def test_convert_hexbytes_to_str(self):
        nested_dict = {
            "data": HexBytes(b"\x00\x01\x02"),
            "info": {
                "value": HexBytes(b"\x03\x04"),
                "description": "Sample data",
                "more_data": [HexBytes(b"\x05\x06"), "text"],
            },
        }

        normalized_dict = prepareDictToPrint(nested_dict)
        expected_result = {
            "data": "0x000102",
            "info": {
                "value": "0x0304",
                "description": "Sample data",
                "more_data": ["0x0506", "text"],
            },
        }
        self.assertDictEqual(normalized_dict, expected_result)

        attr_dict = AttributeDict(nested_dict)
        self.assertDictEqual(prepareDictToPrint(attr_dict), expected_result)


if __name__ == "__main__":
    unittest.main()
