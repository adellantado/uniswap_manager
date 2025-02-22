import requests
import pickle
import os

from web3 import Web3

import web3_utils
from uniswap_v3_position import UniswapV3Position


class UniswapManager():

    def __init__(self, config: dict):
        self.config = config
        self.POSITION_MANAGER = config["uniswap"]["contracts"]["position_manager"]
        self.FACTORY = config["uniswap"]["contracts"]["factory"]
        self.web3 = Web3(Web3.HTTPProvider(self.config["network"]["rpc"]))


    def fetch_positions(self):
        for title, address in self.config["wallet"]["addresses"].items():
            print(f"Wallet: {title}")
            self.print_all_deposits(Web3.to_checksum_address(address))


    def get_all_wallet_positions(self, owner_address: str) -> list[int]:
        token_ids = []
        position_manager_abi = web3_utils.load_abi("UniswapV3PositionManager")
        position_manager = self.web3.eth.contract(address=self.POSITION_MANAGER, abi=position_manager_abi)
        balance = position_manager.functions.balanceOf(owner_address).call()
        for i in range(balance):
            # Get token ID at index
            token_id = position_manager.functions.tokenOfOwnerByIndex(owner_address, i).call()
            token_ids.append(token_id)
        return token_ids


    def print_all_deposits(self, address: str):
        position_ids = self.get_all_wallet_positions(address)
        positions = {}
        resave_file = False
        if os.path.exists("positions.pkl"):
            with open("positions.pkl", "rb") as f:
                positions = pickle.load(f)
        for position_id in position_ids:
            position: UniswapV3Position = positions.get(position_id, None)
            if not position:
                position = UniswapV3Position(self.web3, self.POSITION_MANAGER, self.FACTORY, 
                    position_id, address).fetch_data(self.config["network"]["from_block"])
                positions[position_id] = position
                resave_file = True
            else:
                position.web3 = self.web3
                position.refresh()
            apy, position_days, total_amount, total_fees, symbol = position.calculate_position_apy()
            token_price = float(self.get_coin_price_usd(symbol))
            total_amount = total_amount * token_price
            total_fees = total_fees * token_price
            print(f"{position.name} APY: {apy:.2f}%, {position_days} days, {total_amount:.2f}$ deposit, {total_fees:.2f}$ fees")
            print("---------------------------------------")
        if resave_file:
            with open("positions.pkl", "wb") as f:
                pickle.dump(positions, f)


    def get_coin_price_usd(self, symbol: str) -> str:
        if symbol.upper() == "WETH":
            symbol = "ETH"
        return requests.get(f"https://api.binance.com/api/v3/avgPrice?symbol={symbol.upper()}USDT").json()["price"]