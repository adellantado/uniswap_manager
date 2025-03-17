from __future__ import annotations

from .contract import Contract
import utils.web3_utils as web3_utils
from utils.decorators import to_checksum_address


class WETH9(Contract):
    """
    WETH9 is a class that represents the WETH9 contract.

    Methods:
        deposit(wallet_address: str, amount: int):
            Builds a transaction to deposit the specified amount of ETH into the WETH9 contract from the given wallet address.
    """

    instance: WETH9 = None 

    def __init__(self):
        super().__init__(self.config.erc20_tokens['WETH'], "WETH9")

    @staticmethod
    def get_singleton() -> WETH9:
        if WETH9.instance is None:
            WETH9.instance = WETH9()
        return WETH9.instance

    @to_checksum_address(1)
    def deposit(self, wallet_address: str, amount: int):
        tx = self.contract.functions.deposit().build_transaction({
            "from": wallet_address,
            "nonce": self.get_nonce(wallet_address),
            "gasPrice": web3_utils.get_gas_price(self.web3),
            "gas": 100000,
            "value": amount,
        })
        return tx