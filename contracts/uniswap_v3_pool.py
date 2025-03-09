from __future__ import annotations
import enum

from .contract import Contract
from .erc20 import ERC20
from utils.decorators import cache
import utils.web3_utils as web3_utils


class UniswapV3Pool(Contract):

    def __init__(self, contract_address: str):
        super().__init__(contract_address, "UniswapV3Pool")

    @staticmethod
    def get_instance(contract_address: str) -> UniswapV3Pool:
        contract_address = UniswapV3Pool.web3.to_checksum_address(contract_address)
        if contract_address not in UniswapV3Pool.contract_instances:
            UniswapV3Pool.contract_instances[contract_address] = UniswapV3Pool(contract_address)
        return UniswapV3Pool.contract_instances[contract_address]

    def get_pool_price(self, token1_adjusted: bool = False) -> float:
        sqrtPriceX96 = self.get_slot0()['sqrtPriceX96']
        price = (sqrtPriceX96 / (2**96))**2
        if not token1_adjusted:
            return price
        adjusted_to_token1_price = price / (
            10 ** (self.get_token1().get_decimals() - self.get_token0().get_decimals()) # Adjust for decimals
        )
        return adjusted_to_token1_price

    def get_slot0(self) -> dict:
        return self.call_view_func('slot0')

    def get_ticks(self, tick: int) -> dict:
        return self.call_view_func('ticks', tick)
        
    def get_feeGrowthGlobal0X128(self) -> int:
        return self.call_view_func('feeGrowthGlobal0X128')

    def get_feeGrowthGlobal1X128(self) -> int:
        return self.call_view_func('feeGrowthGlobal1X128')

    @cache("contracts")
    def get_token0_address(self) -> str:
        return self.call_view_func('token0')

    @cache("contracts")
    def get_token1_address(self) -> str:
        return self.call_view_func('token1')

    @cache("contracts")
    def get_fee_tier(self) -> int:
        return self.call_view_func('fee')

    def get_token0(self) -> ERC20:
        return ERC20.get_instance(self.get_token0_address())

    def get_token1(self) -> ERC20:
        return ERC20.get_instance(self.get_token1_address())


@enum.unique
class PoolFee(enum.IntEnum):
    FEE_TIER_100 = 100
    FEE_TIER_500 = 500
    FEE_TIER_3000 = 3000
    FEE_TIER_10000 = 10000


@enum.unique
class PoolTickSpacing(enum.IntEnum):
    FEE_TIER_100 = 1
    FEE_TIER_500 = 10
    FEE_TIER_3000 = 60
    FEE_TIER_10000 = 200