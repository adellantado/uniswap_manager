from web3 import Web3

from contracts.contract import Contract
from contracts.erc20 import ERC20
import utils.web3_utils as web3_utils


class BalanceManager:
    """
    A class to manage and retrieve balances of ETH and ERC20 tokens using web3.
    Attributes:
        config (dict): Configuration dictionary containing web3 settings.
        web3 (Web3): An instance of Web3 initialized with the provided configuration.
    Methods:
        get_eth_balance(wallet_address: str) -> float:
            Retrieves the ETH balance of the specified wallet address.
        get_token_balance(wallet_address: str, token_address: str) -> float:
            Retrieves the balance, decimals, and symbol of the specified ERC20 token for the given wallet address.
    """

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