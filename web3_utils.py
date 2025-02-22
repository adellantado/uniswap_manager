import json

from web3 import Web3


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