import requests
import json


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

def get_config() -> dict:
    with open("config/fork.config.json", "r") as f:
        config = json.load(f)
    return config

def get_wallet_address(wallet: str):
    config = get_config()
    for alias, address in config['wallet']['addresses'].items():
        if wallet.lower() == alias.lower() or wallet.lower() == address.lower():
            return address
    return wallet

def get_token_address(token: str):
    config = get_config()
    for alias, address in config['ERC20']['tokens'].items():
        if token.lower() == alias.lower() or token.lower() == address.lower():
            return address
    return token

def get_private_key_by_path(key_path: str):
    with open(key_path, "r") as f:
        return f.read().strip()

def get_private_key(wallet: str):
    config = get_config()
    for alias, address in config['wallet']['addresses'].items():
        if wallet.lower() == alias.lower() or wallet.lower() == address.lower():
            return get_private_key_by_path(config['wallet']['keys'][alias])
    return None