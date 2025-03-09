from __future__ import annotations

from .contract import Contract
from .erc20 import ERC20
from .uniswap_v3_pool import UniswapV3Pool
from utils.decorators import to_checksum_address


class UniswapV3Factory(Contract):

    instance: UniswapV3Factory = None 

    def __init__(self, config: dict):
        super().__init__(config['uniswap']['contracts']['factory'], "UniswapV3Factory")

    @staticmethod
    def get_singleton(config) -> UniswapV3Factory:
        if UniswapV3Factory.instance is None:
            UniswapV3Factory.instance = UniswapV3Factory(config)
        return UniswapV3Factory.instance

    @to_checksum_address(1,2)
    @cache("contracts")
    def get_pool_address(self, token0_address: str, token1_address: str, fee_tier: int) -> str:
        return self.call_view_func('getPool', token0_address, token1_address, fee_tier)

    def get_pool(self, token0_address: str, token1_address: str, fee_tier: int) -> UniswapV3Pool:
        pool_address = self.get_pool_address(
            token0_address, token1_address, fee_tier
        )
        return UniswapV3Pool.get_instance(pool_address)