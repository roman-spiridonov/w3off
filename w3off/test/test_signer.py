import json
import os
from pprint import pprint
import unittest
from unittest.mock import patch

from w3off.signer import vault
from w3off.signer.vault import (
    decrypt_pkey,
    decrypt_str,
    encrypt_pkey,
    encrypt_str,
    get_pkey_from_keystore,
    get_pkey_from_prompt,
)
from w3off.signer.w3signer import dictToSignedTx, signTx, signedTxToDict


class Test_Signer(unittest.TestCase):
    def test_signTx(self):
        import w3off.test.data.txTestAaveSupply as t

        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "keystore-test.json")) as f:
            keystore = json.load(f)
        vault.get_pkey_from_keystore(keystore, "MyTestPassword$123")
        rawTx = signTx(t.txTest2)
        # pprint(signedTxToDict(rawTx), sort_dicts=False)
        self.assertEqual(
            "0x" + rawTx.raw_transaction.hex(),
            "0xf8ea808504f01476c983042b1b9487870bca3f3fd6335c3f4ce8392d69350b4fa4e280b884617ba037000000000000000000000000dac17f958d2ee523a2206206994597c13d831ec70000000000000000000000000000000000000000000000000000000059682f00000000000000000000000000406617a94b991143d92dc3ff53ca29bce1a407c3000000000000000000000000000000000000000000000000000000000000000025a0c3fb8f3c971a21b7aa6d4aacf37aca5f3ec082e9c54590abc305b715ca52acbfa059d1e72aae1dd02fa7969fabb2169c51f1ef3a6e9b6fd78879e624953c4460fe",
        )

    def test_signedTxConversions(self):
        signed_tx_dict = {
            "raw_transaction": "0xf8ea808504f01476c983042b1b9487870bca3f3fd6335c3f4ce8392d69350b4fa4e280b884617ba037000000000000000000000000dac17f958d2ee523a2206206994597c13d831ec70000000000000000000000000000000000000000000000000000000059682f00000000000000000000000000406617a94b991143d92dc3ff53ca29bce1a407c3000000000000000000000000000000000000000000000000000000000000000025a0c3fb8f3c971a21b7aa6d4aacf37aca5f3ec082e9c54590abc305b715ca52acbfa059d1e72aae1dd02fa7969fabb2169c51f1ef3a6e9b6fd78879e624953c4460fe",
            "hash": "0xf2144271adf506f9833d4e82f73268deba888812e503a26f6f1329a14133e21a",
            "r": 88645472670233617282602266849466166697456468340814178123446291138299080912063,
            "s": 40626710014509862731286299872380817283294316217860379617702627590077424099582,
            "v": 37,
        }
        signed_tx = dictToSignedTx(signed_tx_dict)
        self.assertDictEqual(signed_tx_dict, signedTxToDict(signed_tx))


class Test_Vault(unittest.TestCase):
    def test_encrypt_decrypt(self):
        message = "hello"
        message_enc, key, iv = encrypt_str(message)
        self.assertEqual(decrypt_str(message_enc, key, iv), message)

        message2 = "7f3cd07e543c0bc589f754fab8022da6d032745c44865250971ca46a2493a669"
        message_enc, key, iv = encrypt_str(message2)
        self.assertEqual(decrypt_str(message_enc, key, iv), message2)

    def test_pkey_from_keystore(self):
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "keystore-test2.json")) as f:
            keystore2 = json.load(f)
        vault.get_pkey_from_keystore(keystore2, "Vintage0!")
        decrypt_pkey()
        self.assertEqual(
            vault.pkey,
            "59f2a4b1397784e76ee2fb7ca5ee305d5a2c4f4c565c82e84cdda88e3ef98b52",
        )
        pkey_saved = vault.pkey
        encrypt_pkey()
        decrypt_pkey()
        self.assertEqual(vault.pkey, pkey_saved)

        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "keystore-default.json")) as f:
            keystore2 = json.load(f)
        vault.get_pkey_from_keystore(keystore2, "test")
        decrypt_pkey()
        self.assertEqual(
            vault.pkey,
            "f8f8a2f43c8376ccb0871305060d7b27b0554d2cc72bccf41b2705608452f315",
        )

    @patch("getpass.getpass")
    def test_pkey_from_prompt(self, mock_getpass):
        global pkey
        pkey_input = "7f3cd07e543c0bc589f754fab8022da6d032745c44865250971ca46a2493a669"
        mock_getpass.return_value = pkey_input
        get_pkey_from_prompt()
        decrypt_pkey()
        self.assertEqual(vault.pkey, pkey_input)


if __name__ == "__main__":
    unittest.main()
