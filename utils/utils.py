import subprocess
import getpass
import os
import requests
import json
from pathlib import Path

import click
from web3 import Web3

from entity.config import Config


def get_coin_price_usd(symbol: str) -> str:
    if symbol.upper() == "WETH":
        symbol = "ETH"
    elif symbol.upper() in ["USDT", "USDC"]:
        return 1
    return requests.get(f"https://api.binance.com/api/v3/avgPrice?symbol={symbol.upper()}USDT").json()["price"]

def get_gas_price(etherscan_key: str) -> tuple[int, int, int]:
    url = f"https://api.etherscan.io/api?module=gastracker&action=gasoracle&apikey={etherscan_key}"
    response = requests.get(url).json()
    safe_gas = response["result"]["SafeGasPrice"]
    propose_gas = response["result"]["ProposeGasPrice"]
    fast_gas = response["result"]["FastGasPrice"]
    return safe_gas, propose_gas, fast_gas

def get_config() -> Config:
    return Config.get_singleton()

def get_wallet_address(wallet: str):
    for alias, address in Config.get_singleton().wallet_addresses.items():
        if wallet.lower() == alias.lower() or wallet.lower() == address.lower():
            return address
    return wallet

def get_token_address(token: str):
    for alias, address in Config.get_singleton().erc20_tokens.items():
        if token.lower() == alias.lower() or token.lower() == address.lower():
            return address
    return token

def get_private_key_by_path(key_path: str, ask_passphare_directly: bool = False):
    if not os.path.isfile(key_path):
        raise Exception(f"Error: File '{key_path}' does not exist.")
    extension = Path(key_path).suffix
    is_gpg = extension == ".gpg" or extension == ".asc"
    if not is_gpg:
        with open(key_path, "r") as f:
            return f.read().strip()
    else:
        if ask_passphare_directly:
            passphrase = getpass.getpass(prompt='Enter GPG password to decode private key: ')
        result = subprocess.run(
            [
                'gpg', '--passphrase', passphrase, '--batch', '--yes', '--decrypt', key_path
            ] 
                if ask_passphare_directly else 
            [
                'gpg', '--decrypt', key_path
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise Exception(f"Decryption failed: {result.stderr.strip()}")
        return result.stdout.strip()

def get_private_key(wallet: str):
    for alias, address in Config.get_singleton().wallet_addresses.items():
        if wallet.lower() == alias.lower() or wallet.lower() == address.lower():
            return get_private_key_by_path(Config.get_singleton().private_keys[alias])
    return None

def print(message: str, type: str = None):
    if not bool(Config.get_singleton().is_styles_active):
        click.secho(message)
        return
    is_bright = bool(Config.get_singleton().is_styles_bright)
    colors = {
        "info": "blue",
        "warning": "yellow",
        "error": "red",
        "success": "green",
    }
    color = colors.get(type, None)
    color = "bright_"+color if (is_bright and color) else color
    if color:
        click.secho(message, fg=color)
    else:
        click.secho(message)

def get_web3() -> Web3:
    config = Config.get_singleton()
    return Web3(Web3.HTTPProvider(config.rpc_url, 
        cache_allowed_requests = not config.is_prod)
    )

def load_abi(abi_name: str) -> dict:
    with open(f"abi/{abi_name}.json") as f:
        abi_json = json.load(f)
    return abi_json

def map_contract_result(json_abi: dict, func_name: str, result) -> dict:
    if type(result) is not tuple and type(result) is not list:
        return result
    field_names = []
    for item in json_abi:
        if item['type'] == 'function' and item['name'] == func_name:
            field_names = [output["name"] for output in item['outputs'] if output["name"]]
    if not field_names:
        return result
    mapped_result = dict(zip(field_names, result)) if field_names else {}
    return mapped_result

def get_topic_keccak_hex(topic: str) -> str:
    return Web3.keccak(text=topic).to_0x_hex()

def get_topic_hex(hex_str: str) -> str:
    return '0x'+hex_str[2:].rjust(64, '0')

def sign_and_send_tx(web3: Web3, tx, wallet: str):
    signed_tx = web3.eth.account.sign_transaction(tx, get_private_key(wallet))
    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
    return tx_hash

def sign_and_get_raw_tx(web3: Web3, tx, wallet: str):
    signed_tx = web3.eth.account.sign_transaction(tx, get_private_key(wallet))
    return signed_tx.raw_transaction.hex()

def estimate_tx_gas(web3: Web3, tx) -> int:
    gas_estimate = web3.eth.estimate_gas(tx)
    return gas_estimate

def get_tx_deadline(web3: Web3):
    return web3.eth.get_block("latest")["timestamp"] + 600 # 10-minute deadline

def get_gas_price(web3: Web3):
    gas_fee = web3.eth.fee_history(1, "latest")
    base_fee = gas_fee['baseFeePerGas'][-1]
    return base_fee

def get_eth_balance(web3: Web3, address: str) -> float:
    return web3.eth.get_balance(web3.to_checksum_address(address))

def raise_address_not_valid(web3: Web3, address: str) -> bool:
    if not web3.is_address(address):
        raise Exception(f"Invalid address: {address}")