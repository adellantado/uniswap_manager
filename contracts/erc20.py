
from __future__ import annotations

from .contract import Contract
import utils.web3_utils as web3_utils
from utils.decorators import to_checksum_address


class ERC20(Contract):

    def __init__(self, token_address: str):
        super().__init__(token_address, "ERC20")

    @staticmethod
    def get_instance(token_address: str) -> ERC20:
        token_address = ERC20.web3.to_checksum_address(token_address)
        if token_address not in ERC20.contract_instances:
            ERC20.contract_instances[token_address] = ERC20(token_address)
        return ERC20.contract_instances[token_address]

    @to_checksum_address(1,2)
    def get_allowance(self, owner_address: str, spender_address: str) -> int:
        return self.call_view_func('allowance', owner_address, spender_address)

    @to_checksum_address(1)
    def get_balance(self, wallet_address: str) -> int:
        return self.call_view_func('balanceOf', wallet_address)

    def get_decimals(self) -> int:
        return self.call_view_func('decimals')

    def get_symbol(self) -> str:
        return self.call_view_func('symbol')

    @to_checksum_address(1,2)
    def approve(self, wallet_address: str, spender_address: str, amount: int):
        tx = self.contract.functions.approve(spender_address, amount).build_transaction({
            "nonce": self.get_nonce(wallet_address),
            "gasPrice": web3_utils.get_gas_price(self.web3),
            "gas": 100000,
        })
        return tx
    