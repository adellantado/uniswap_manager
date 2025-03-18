from __future__ import annotations
import math

from .contract import Contract
import utils.utils as utils
from utils.decorators import to_checksum_address


class UniswapV3Router(Contract):
    """
    UniswapV3Router is a class that interacts with the Uniswap V3 Router contract to perform token swaps.

    Methods:
        swap_out_min(in_token_address, out_token_address, in_token_amount, out_token_amount_min, fee_tier, wallet_address):
            Creates a transaction to swap a minimum amount of output tokens for a given input token amount.
        
        swap_in_max(in_token_address, out_token_address, in_token_amount_min, out_token_amount, fee_tier, wallet_address):
            Creates a transaction to swap a maximum amount of input tokens for a given output token amount.
    """

    instance: UniswapV3Router = None 

    def __init__(self):
        super().__init__(self.config.uniswap_v3_router, "UniswapV3SwapRouter")

    @staticmethod
    def get_singleton() -> UniswapV3Router:
        if UniswapV3Router.instance is None:
            UniswapV3Router.instance = UniswapV3Router()
        return UniswapV3Router.instance

    @to_checksum_address(1,2,6)
    def swap_out_min(self, in_token_address: str, out_token_address: str, in_token_amount: int, out_token_amount_min: int, 
            fee_tier: int, wallet_address: str, pass_value_for_in_token: bool = False):
        details = {
            "from": wallet_address,
            "nonce": self.get_nonce(wallet_address),
            "gasPrice": utils.get_gas_price(self.web3),
            "gas": 200000,
        }
        if pass_value_for_in_token:
            details["value"] = in_token_amount
        tx = self.contract.functions.exactInputSingle({
            "tokenIn":  self.web3.to_checksum_address(in_token_address),
            "tokenOut": self.web3.to_checksum_address(out_token_address),
            "fee": fee_tier,
            "recipient": wallet_address,
            "deadline": utils.get_tx_deadline(self.web3),
            "amountIn": in_token_amount,
            "amountOutMinimum": out_token_amount_min,
            "sqrtPriceLimitX96": 0  # No price limit
        }).build_transaction(details)
        return tx

    @to_checksum_address(1,2,6)
    def swap_in_max(self, in_token_address: str, out_token_address: str, in_token_amount_min: int, out_token_amount: int, 
            fee_tier: int, wallet_address: str, pass_value_for_in_token: bool = False):
        details = {
            "from": wallet_address,
            "nonce": self.get_nonce(wallet_address),
            "gasPrice": utils.get_gas_price(self.web3),
            "gas": 200000,
        }
        if pass_value_for_in_token:
            details["value"] = in_token_amount_min
        tx = self.contract.functions.exactOutputSingle({
            "tokenIn":  self.web3.to_checksum_address(in_token_address),
            "tokenOut": self.web3.to_checksum_address(out_token_address),
            "fee": fee_tier,
            "recipient": wallet_address,
            "deadline": utils.get_tx_deadline(self.web3),
            "amountOut": out_token_amount,
            "amountInMaximum": in_token_amount_min,
            "sqrtPriceLimitX96": 0  # No price limit
        }).build_transaction(details)
        return tx
    