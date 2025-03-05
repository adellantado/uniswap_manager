from web3 import Web3

from contracts.contract import Contract
from contracts.erc20 import ERC20
import utils.web3_utils as web3_utils


class BalanceManager:

    def __init__(self, config: dict):
        self.config = config
        self.web3 = web3_utils.get_web3(config)
        Contract.web3 = self.web3

    def get_eth_balance(self, wallet_address: str) -> float:
        return web3_utils.get_eth_balance(self.web3, wallet_address) / 10**18
    
    def get_token_balance(self, wallet_address: str, token_address: str) -> float:
        contract = ERC20.get_instance(token_address)
        balance = contract.get_balance(wallet_address)
        decimals = contract.get_decimals()
        symbol = contract.get_symbol()
        return balance, decimals, symbol