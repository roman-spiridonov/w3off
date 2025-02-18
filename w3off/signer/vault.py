import datetime
import sys
from w3off.cli.prompts import promptConfirm
import w3off.cli.helpers as cli_helpers
import w3off.config as config
from w3off.w3provider import w3
import json
import os
import hashlib
import getpass

from eth_keyfile import create_keyfile_json

# from eth_account import Account
# from mnemonic import Mnemonic
# import binascii
# from bip_utils import Bip39SeedGenerator, Bip44, Bip44Coins

from Crypto.Random import get_random_bytes
from Crypto.Protocol.KDF import PBKDF2  # brute force protection
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

# We use global variables to ensure these values are initialized only once and stored only in one pace (singleton)
pkey = None  # App-level user pkey, stored always encrypted and cleared after used once

# AES Encryption settings are valid only for one user session
_salt = get_random_bytes(32)
_pwd = os.urandom(16)
_key = PBKDF2(_pwd, _salt, dkLen=32)
_iv = None


def encrypt_pkey():
    global pkey
    pkey, _, _ = encrypt_str(pkey)


def decrypt_pkey():
    global pkey
    pkey = decrypt_str(pkey)


def generate_salt(length=32):
    """Generate a random salt."""
    return os.urandom(length)


def hash(string, salt):
    """Hash the string with the given salt using PBKDF2 and HMAC-SHA256."""
    # Use PBKDF2 with HMAC-SHA256
    return hashlib.pbkdf2_hmac("sha256", string.encode("utf-8"), salt, 1000000)


def encrypt_str(string, encoding="utf-8"):
    global _salt, _pwd, _key, _iv

    cipher = AES.new(_key, AES.MODE_CBC)

    ciphered_data = cipher.encrypt(pad(string.encode(encoding), AES.block_size))
    _iv = cipher.iv
    return (ciphered_data, _key, _iv)


def decrypt_str(ciphered_data, key=None, iv=None, encoding="utf-8"):
    global _key, _iv
    key = key or _key
    iv = iv or _iv
    cipher_read = AES.new(key, AES.MODE_CBC, iv=iv)
    original = unpad(cipher_read.decrypt(ciphered_data), AES.block_size)
    return original.decode(encoding)


# Function to load and decrypt an Ethereum keystore file
def get_pkey_from_keystore(keystore: str, pwd: str):
    global pkey
    # Decrypt the private key from keystore and encrypt as a string in memory
    pkey = w3.eth.account.decrypt(keystore, pwd).hex()
    pkey, _, _ = encrypt_str(pkey)
    del pwd
    del keystore


def get_pkey_from_prompt(pkey_str=None):
    global pkey
    pkey, _, _ = encrypt_str(
        pkey_str
        or getpass.getpass(
            "Enter private key (it will not be displayed as you type, never persisted, encrypted and deleted from memory right after usage): "
        )
    )


def convert_pkey_to_keystore(pwd):
    global pkey
    try:
        decrypt_pkey()
        keystore = create_keyfile_json(
            private_key=bytes.fromhex(pkey.removeprefix("0x")),
            password=pwd.encode("utf-8"),
            iterations=100000,
        )
        # keystore = w3.eth.account.from_key(private_key=bytes.fromhex(pkey), kdf="pbkdf2", password=pwd.encode('utf-8'), iterations=100000)
        encrypt_pkey()
    except Exception as e:
        print(f"Something went wrong: {e}")
        raise Exception
    return keystore


def promptPkey(pkey_str=None):
    """Securely ask for the password to decrypt (e.g. the keystore file)."""
    if pkey_str:
        get_pkey_from_prompt(pkey_str=pkey_str)
        return

    while True:
        try:
            get_pkey_from_prompt()
            break
        except Exception as e:
            print(f"Error occured: {e}")
            print(e.__traceback__)
            print("Please try again.")

    if not config.signer_suggest_keystore:
        return

    print("It is not recommended to enter the private key manually each time. We are going to generate an encrypted keystore file so you can use it in future transactions.")
    if promptConfirm():
        while True:
            pwd = getpass.getpass("Enter strong password to encrypt your keystore file: ")
            pwd2 = getpass.getpass("Confirm by typing again: ")
            if pwd != pwd2:
                print("Your entries do not match. Please try again.")
            else:
                break
        try:
            keystore = convert_pkey_to_keystore(pwd)
        except Exception as e:
            print(f"Proceeding without generating a keystore file.")
            return
        now = datetime.datetime.now(datetime.timezone.utc)
        filename = f"UTC--{now.strftime('%Y-%m-%dT%H-%M-%SZ')}--{keystore['address']}.json"
        while True:
            try:
                path = os.path.normpath(
                    input("Please specify preferred path for saving the keystore file (by default, it will be saved in current folder with unique filename): ")
                    or ""
                )
                break
            except Exception as e:
                print("Your input is incorrect. Please try again")
        try:
            print(f"Attempting to save the keystore file to {os.path.join(path,filename)}...")
            with open(os.path.join(path, filename), "w") as f:
                f.write(json.dumps(keystore))
        except Exception as e:
            print(f"Error occured when saving the file: {e}, {e.__traceback__}")
            print(f"Proceeding without generating a keystore file.")


def promptKeystoreFile(keystore_file_path: str = None, keystore_pwd: str = None):
    # from pyreadline3 import Readline
    # readline = Readline()
    # readline.set_completer_delims('\t\n `~!@#$%^&*()-=+[{]}\\|;:\'",<>/?')
    # readline.parse_and_bind("tab: complete")
    # def complete(text, state):
    #     return (glob.glob(os.path.expanduser(text)+'*')+[None])[state]
    # readline.set_completer(complete)

    while True:
        try:
            if not keystore_file_path:
                if os.name == "nt" and not sys.stdin.isatty():
                    # If stdin is replaced (e.g. piped), nothing except getpass seems to work for interactive prompting
                    try:
                        keystore_file_path = (
                            getpass.getpass(f"Enter full or relative path to your keystore file (the path will not be displayed) (default is {config.default_keystore_file}): ")
                            or config.default_keystore_file
                        )
                    except Exception as e:
                        print(f"Could not prompt you for directory path due to this error: {e}")
                        print(f"Aborting...")
                        exit(0)
                else:
                    keystore_file_path = (
                        input(f"Enter full or relative path to your keystore file (default is {config.default_keystore_file}): ")
                        or config.default_keystore_file
                    )

            normalized_path = cli_helpers.normalize_path(keystore_file_path)
            # Load the keystore file
            with open(normalized_path) as keyfile:
                keystore = json.load(keyfile)

            if keystore:
                break
            else:
                print("Could not load the keystore data from file (the file is empty?) Try again.")
                print(f"Please check the path to file you entered: {keystore_file_path}")

        except Exception as e:
            print("Error occured (see trace below). Please try again.")
            print(type(e), e, e.__traceback__)
            keystore_file_path = None

    while True:
        try:
            if not keystore_pwd:
                keystore_pwd = (
                    getpass.getpass("Enter password to decrypt the keystore (will not be displayed nor stored): ") 
                    or config.default_keystore_pwd
                )
            get_pkey_from_keystore(keystore, keystore_pwd)
            del keystore
            del keystore_pwd
            break
        except Exception as e:
            print("Error occured (incorrect password?). Please try again.")
            print(type(e), e, e.__traceback__)
            keystore_pwd = None


# TODO: finish the mnemonic feature
# def promptMnemonic():
#     mnemonic_size = input(f'How many words are in your mnemonic phrase (e.g. {config.default_mnemonic_size}): ')
#     print('Enter the mnemonic word by word. The words are not displayed for security purposes.')
#     mnemonic_phr = []
#     mnemonic_str = ""
#     for i in range(1, mnemonic_size):
#         mnemonic_phr.append ( getpass.getpass(f'{i} - ') )

#     for i in range(1, mnemonic_size):
#         mnemonic_str += mnemonic_phr[i]
#         del mnemonic_phr[i]  # clean from memory
#     del mnemonic_phr

#     mnemo = Mnemonic("english")
#     if not mnemo.check(mnemonic_str):
#         raise ValueError("Invalid mnemonic phrase.")

#     seed = mnemo.to_seed(mnemonic_str)
#     seed_bytes = binascii.unhexlify(seed)

#     # Create BIP32 context from seed
#     bip44_mst = Bip44.FromSeed(seed_bytes, Bip44Coins.ETHEREUM)

#     # Step 3: Derive the BIP84 path (m/84'/0'/0')
#     bip84_ctx = bip44_mst.DerivePath("m/84'/0'/0'")
