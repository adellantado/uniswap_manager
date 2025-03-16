import json

from web3 import Web3

import utils.utils as utils


def get_web3(config: dict) -> Web3:
    is_prod = config["network"].get("prod", True)
    return Web3(Web3.HTTPProvider(config["network"]["rpc"], 
        cache_allowed_requests = not is_prod)
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
    signed_tx = web3.eth.account.sign_transaction(tx, utils.get_private_key(wallet))
    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
    return tx_hash

def sign_and_get_raw_tx(web3: Web3, tx, wallet: str):
    signed_tx = web3.eth.account.sign_transaction(tx, utils.get_private_key(wallet))
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
    