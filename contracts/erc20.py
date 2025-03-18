
from __future__ import annotations

from .contract import Contract
import utils.utils as utils
from utils.decorators import to_checksum_address, cache


class ERC20(Contract):
    """
    ERC20 class for interacting with ERC20 token contracts.

    Methods:
        get_instance(token_address: str) -> ERC20:
            Returns an instance of the ERC20 contract for the given token address.

        get_allowance(owner_address: str, spender_address: str) -> int:
            Returns the allowance of the spender for the owner's tokens.

        get_balance(wallet_address: str) -> int:
            Returns the balance of the given wallet address.

        get_decimals() -> int:
            Returns the number of decimals used by the token.

        get_symbol() -> str:
            Returns the symbol of the token.

        approve(wallet_address: str, spender_address: str, amount: int):
            Approves the spender to spend the specified amount of tokens from the wallet address.

        transfer(wallet_address: str, to_address: str, amount: int):
            Sends the specified amount of tokens from the wallet address to the recipient address.
    """

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

    @cache("contracts")
    def get_decimals(self) -> int:
        return self.call_view_func('decimals')

    @cache("contracts")
    def get_symbol(self) -> str:
        return self.call_view_func('symbol')

    @to_checksum_address(1,2)
    def approve(self, wallet_address: str, spender_address: str, amount: int):
        tx = self.contract.functions.approve(spender_address, amount).build_transaction({
            "nonce": self.get_nonce(wallet_address),
            "gasPrice": utils.get_gas_price(self.web3),
            "gas": 100000,
        })
        return tx
    
    @to_checksum_address(1,2)
    def transfer(self, wallet_address: str, to_address: str, amount: int):
        tx = self.contract.functions.transfer(to_address, amount).build_transaction({
            "nonce": self.get_nonce(wallet_address),
            "gasPrice": utils.get_gas_price(self.web3),
            "gas": 100000,
        })
        return tx