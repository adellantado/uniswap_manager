from __future__ import annotations

from .contract import Contract
import utils.web3_utils as web3_utils
from utils.decorators import to_checksum_address


class WETH9(Contract):

    instance: WETH9 = None 

    def __init__(self, config: dict):
        super().__init__(config['ERC20']['tokens']['WETH'], "WETH9")

    @staticmethod
    def get_singleton(config: dict) -> WETH9:
        if WETH9.instance is None:
            WETH9.instance = WETH9(config)
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