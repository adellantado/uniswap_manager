from __future__ import annotations
import math
from web3 import Web3

from .contract import Contract
from .uniswap_v3_pool import UniswapV3Pool, PoolFee, PoolTickSpacing
from .erc20 import ERC20
import utils.web3_utils as web3_utils
from utils.decorators import to_checksum_address



class UniswapV3PositionManager(Contract):

    instance: UniswapV3PositionManager = None 

    def __init__(self, config: dict):
        self.config = config
        super().__init__(config['uniswap']['contracts']['position_manager'], "UniswapV3PositionManager")

    @staticmethod
    def get_singleton(config: dict) -> UniswapV3PositionManager:
        if UniswapV3PositionManager.instance is None:
            UniswapV3PositionManager.instance = UniswapV3PositionManager(config)
        return UniswapV3PositionManager.instance

    def get_position_data(self, position_id: int) -> dict:
        return self.call_view_func('positions', position_id)

    @to_checksum_address(1)
    def get_all_position_last_index(self, wallet_address: str) -> int:
        return self.call_view_func('balanceOf', wallet_address)

    @to_checksum_address(1)
    def get_token_id_by_index(self, wallet_address: str, index: int) -> int:
        return self.call_view_func('tokenOfOwnerByIndex', wallet_address, index)

    def get_position_ids(self, wallet_address: str) -> list[int]:
        position_ids = []
        for i in range(self.get_all_position_last_index(wallet_address)):
            position_ids.append(self.get_token_id_by_index(wallet_address, i))
        return position_ids

    @to_checksum_address(1)
    def collect_all(self, wallet_address: str, position_id: int):
        tx = self.contract.functions.collect({
            "tokenId": position_id,
            "recipient": wallet_address,
            "amount0Max": 2**128 - 1,  # Max possible collection
            "amount1Max": 2**128 - 1   # Max possible collection
        }).build_transaction({
            "from": wallet_address,
            "nonce": self.get_nonce(wallet_address),
            "gasPrice": web3_utils.get_gas_price(self.web3),
            "gas": 200000,
        })
        # tx_hash = web3_utils.sign_and_send_tx(web3, tx)
        # receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        # print("Transaction confirmed in block:", receipt["blockNumber"])
        # for log in receipt.logs:
        #     if log.address.lower() == config['uniswap']['contracts']['position_manager'].lower():
        #         print("Collected Fees Log:", log)


    @to_checksum_address(3)
    def decrease_liquidity(self, position_id: int, liquidity: int, wallet_address: str):
        tx = self.contract.functions.decreaseLiquidity({
            "tokenId": position_id,
            "liquidity": liquidity,
            "amount0Min": 0,  # Set minimums to avoid slippage
            "amount1Min": 0,
            "deadline": web3.eth.get_block("latest")["timestamp"] + 600  # 10-minute deadline
        }).build_transaction({
            "from": wallet_address,
            "nonce": self.get_nonce(wallet_address),
            "gasPrice": web3_utils.get_gas_price(self.web3),
            "gas": 250000,
        })

    @to_checksum_address(4)
    def increase_liquidity(self, position_id: int, 
            amount0_desired: int, amount1_desired: int, wallet_address: str):
        tx = self.contract.functions.increaseLiquidity({
            "tokenId": position_id,
            "amount0Desired": amount0_desired,
            "amount1Desired": amount1_desired,
            "amount0Min": 0,  # Set minimums to avoid slippage
            "amount1Min": 0,
            "deadline": web3.eth.get_block("latest")["timestamp"] + 600  # 10-minute deadline
        }).build_transaction({
            "from": wallet_address,
            "nonce": self.get_nonce(wallet_address),
            "gasPrice": web3_utils.get_gas_price(self.web3),
            "gas": 250000,
        })

    @to_checksum_address(6)
    def open_position_for_pool(self, pool: UniswapV3Pool, 
            amount0_desired: int, amount1_desired: int, 
            amount0_min: int, amount1_min: int,
            wallet_address: str, deviation_percent: int=15):
        tick_lower, tick_upper = self.get_ticks(pool, deviation_percent)
        tx = self.open_position(
            pool.token0.contract_address, pool.token1.contract_address, 
            pool.get_fee_tier(),
            amount0_desired, amount1_desired, amount0_min, amount1_min,
            tick_lower, tick_upper, wallet_address
        )
        return tx

    @to_checksum_address(1,2,10)
    def open_position(self, token0_address: str, token1_address: str, fee_tier: int, 
            amount0_desired: int, amount1_desired: int, 
            amount0_min: int, amount1_min: int,
            tick_lower: int, tick_upper: int, 
            wallet_address: str):
        tx = self.contract.functions.mint({
            "token0": token0_address,
            "token1": token1_address,
            "fee": fee_tier,
            "tickLower": tick_lower,
            "tickUpper": tick_upper,
            "amount0Desired": amount0_desired,
            "amount1Desired": amount1_desired,
            "amount0Min": amount0_min,
            "amount1Min": amount1_min,
            "recipient": wallet_address,
            "deadline": web3_utils.get_tx_deadline(),
        }).build_transaction({
            "from": wallet_address,
            "nonce": self.get_nonce(wallet_address),
            "gasPrice": web3_utils.get_gas_price(self.web3),
            "gas": 500000,
        })
        return tx


    def get_ticks(self, pool: UniswapV3Pool, deviation_percent: int):
        fee_tier = pool.get_fee_tier()
        tick_spacing = PoolTickSpacing[PoolFee(fee_tier).name].value
        price = pool.get_pool_price()
        price_lower = price * (1 - deviation_percent/100)
        price_upper = price * (1 + deviation_percent/100)
        # Convert Price to Tick
        tick_lower = int(math.log(price_lower, 1.0001))
        tick_upper = int(math.log(price_upper, 1.0001))
        # Adjust tick to nearest valid multiple of tick spacing
        tick_lower = tick_lower - (tick_lower % tick_spacing)
        tick_upper = tick_upper - (tick_upper % tick_spacing)
        return tick_lower, tick_upper