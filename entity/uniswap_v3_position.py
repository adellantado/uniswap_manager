from __future__ import annotations
from datetime import datetime,timezone
from decimal import Decimal

from web3 import Web3

from contracts.uniswap_v3_position_manager import UniswapV3PositionManager
from contracts.uniswap_v3_pool import UniswapV3Pool
from contracts.uniswap_v3_factory import UniswapV3Factory
from contracts.erc20 import ERC20
import utils.web3_utils as web3_utils 


class UniswapV3Position():
    """
    Represents a position in Uniswap V3.
    Attributes:
        position_manager (UniswapV3PositionManager): The position manager instance.
        web3 (Web3): The Web3 instance.
        position_id (int): The ID of the position.
        wallet_address (str): The wallet address associated with the position.
        position_data (dict): The data related to the position.
        pool (UniswapV3Pool): The pool associated with the position.
        creation_date (datetime): The creation date of the position.
    Methods:
        name:
            Returns the name of the position.
        refresh():
            Refreshes the position data.
        get_token0():
            Returns the token0 of the pool.
        get_token1():
            Returns the token1 of the pool.
        get_deposit_init_date(from_block, chunk_size=5000):
            Returns the initial deposit date of the position.
        get_total_fees_collected():
            Returns the total fees collected by the position.
        get_total_locked_amount():
            Returns the total locked amount in the position.
        calculate_position_apy():
            Calculates the APY of the position.
        is_closed():
            Checks if the position is closed.
        is_active():
            Checks if the position is active.
        get_price_range():
            Returns the price range of the position.
        _calculate_amounts(liquidity, sqrt_price_x96, sqrt_price_upper_x96, sqrt_price_lower_x96):
            Calculates the amounts of token0 and token1.
        _calculate_fees(fee_growth_global0, fee_growth_global1, fee_growth0_low, fee_growth0_high, 
                        fee_growth1_low, fee_growth1_high, fee_growth_inside0, fee_growth_inside1, 
                        liquidity, decimals0, decimals1, tick_lower, tick_upper, tick_current):
    """

    def __init__(self, position_id: int, wallet_address: str, 
            position_data: dict, position_manager: UniswapV3PositionManager,
            pool: UniswapV3Pool = None):
        self.position_manager = position_manager
        self.web3 = position_manager.web3
        self.position_id = position_id
        self.wallet_address = self.web3.to_checksum_address(wallet_address)
        self.position_data = position_data
        self.pool = pool
        self.creation_date = None

    @staticmethod
    def get_instance(position_manager: UniswapV3PositionManager,
            position_id: int, wallet_address: str) -> UniswapV3Position:
        position_data = position_manager.get_position_data(position_id)
        pool = UniswapV3Factory.get_singleton().get_pool(
            position_data['token0'], position_data['token1'], position_data['fee']
        )
        return UniswapV3Position(position_id, wallet_address,
            position_data, position_manager, pool
        )


    @property
    def name(self) -> str:
        return (f"Position {self.position_id} "
            f"({self.pool.get_token0().get_symbol()}/{self.pool.get_token1().get_symbol()} "
            f"{int(self.position_data['fee'])/10000:.2f}%)"
        )

    def refresh(self) -> UniswapV3Position:
        self.position_data = self.position_manager.sync().get_position_data(
            self.position_id
        )
        self.pool.sync(5)
        self.pool.get_slot0()
        self.pool.get_ticks(self.position_data['tickLower'])
        self.pool.get_ticks(self.position_data['tickUpper'])
        self.pool.get_feeGrowthGlobal0X128()
        self.pool.get_feeGrowthGlobal1X128()
        return self

    def get_token0(self) -> ERC20:
        return self.pool.get_token0()

    def get_token1(self) -> ERC20:
        return self.pool.get_token1()


    def get_deposit_init_date(self, from_block: int, chunk_size: int = 5000) -> datetime:
        if self.creation_date:
            return self.creation_date
        latest_block = self.web3.eth.block_number
        all_logs = []
        for start_block in range(from_block, latest_block, chunk_size):
            end_block = min(start_block + chunk_size - 1, latest_block)
            logs = self.web3.eth.get_logs({
                "fromBlock": start_block,
                "toBlock": end_block,
                "address": self.position_manager.contract_address,
                "topics": [
                    web3_utils.get_topic_keccak_hex("Transfer(address,address,uint256)"),
                    None,
                    web3_utils.get_topic_hex(self.wallet_address.lower()),
                    web3_utils.get_topic_hex(Web3.to_hex(self.position_id))
                ]
            })
            if logs:
                all_logs += logs
        if all_logs:
            block_number = all_logs[0]["blockNumber"]
            block = self.web3.eth.get_block(block_number)
            timestamp = block["timestamp"]
            creation_date = datetime.utcfromtimestamp(timestamp).replace(tzinfo=timezone.utc)
            self.creation_date = creation_date
            return creation_date

    def get_total_fees_collected(self) -> tuple[float, float]:
        slot0 = self.pool.get_slot0()
        tick_low = self.pool.get_ticks(self.position_data['tickLower'])
        tick_high = self.pool.get_ticks(self.position_data['tickUpper'])
        fee_growth_global0 = self.pool.get_feeGrowthGlobal0X128()
        fee_growth_global1 = self.pool.get_feeGrowthGlobal1X128()
        return self._calculate_fees(fee_growth_global0, fee_growth_global1, 
            tick_low['feeGrowthOutside0X128'], tick_high['feeGrowthOutside0X128'], 
            tick_low['feeGrowthOutside1X128'], tick_high['feeGrowthOutside1X128'], 
            self.position_data['feeGrowthInside0LastX128'], self.position_data['feeGrowthInside1LastX128'], 
            self.position_data['liquidity'],
            self.pool.get_token0().get_decimals(), self.pool.get_token1().get_decimals(), 
            self.position_data['tickLower'], self.position_data['tickUpper'], slot0['tick'])

    def get_total_locked_amount(self) -> tuple[float, float]:
        slot0 = self.pool.get_slot0()
        # Convert ticks to sqrtPriceX96
        sqrt_price_lower_x96 = 1.0001 ** (self.position_data['tickLower'] / 2) * (2**96)
        sqrt_price_upper_x96 = 1.0001 ** (self.position_data['tickUpper'] / 2) * (2**96)
        # Calculate amounts
        amount0, amount1 = self._calculate_amounts(self.position_data['liquidity'], 
            slot0['sqrtPriceX96'], sqrt_price_upper_x96, sqrt_price_lower_x96
        )
        token0_amount = amount0/10**self.pool.get_token0().get_decimals()
        token1_amount = amount1/10**self.pool.get_token1().get_decimals()
        return token0_amount, token1_amount

    def calculate_position_apy(self) -> tuple[float, int, float, float, str]:
        token0_amount, token1_amount = self.get_total_locked_amount()
        token0_fee, token1_fee = self.get_total_fees_collected()

        price = self.pool.get_pool_price(True)
        total_amount = token0_amount*price + token1_amount
        total_fees = token0_fee*price + token1_fee

        years_portion = 0
        total_days = 0
        if self.creation_date:
            date_diff = (datetime.now(timezone.utc) - self.creation_date)
            years_portion = 365*24*60*60/date_diff.total_seconds()
            total_days = date_diff.days
        apy = 0
        if total_amount != 0:
            apy = total_fees / total_amount * years_portion * 100
        return apy, total_days, total_amount, total_fees, self.pool.get_token1().get_symbol()

    def is_closed(self) -> bool:
        return self.position_data['liquidity'] == 0

    def is_active(self) -> bool:
        if not self.position_data['liquidity'] > 0:
            return False
        to_token1_price = self.pool.get_pool_price(True)
        to_token1_price_lower, to_token1_price_upper = self.get_price_range()
        return to_token1_price_lower < to_token1_price < to_token1_price_upper

    def get_price_range(self) -> tuple[float, float]:
        price_lower = 1.0001 ** int(self.position_data['tickLower'])
        price_upper = 1.0001 ** int(self.position_data['tickUpper'])
        decimals_diff = self.pool.get_token1().get_decimals() - self.pool.get_token0().get_decimals()
        adjusted_to_token1_price_lower = price_lower / (10 ** decimals_diff)
        adjusted_to_token1_price_upper = price_upper / (10 ** decimals_diff)
        return adjusted_to_token1_price_lower, adjusted_to_token1_price_upper

    def _calculate_amounts(self, liquidity, sqrt_price_x96, sqrt_price_upper_x96, 
            sqrt_price_lower_x96) -> tuple[float, float]:
        liquidity = Decimal(liquidity)
        sqrt_price = Decimal(sqrt_price_x96) / (2**96)
        sqrt_price_upper = Decimal(sqrt_price_upper_x96) / (2**96)
        sqrt_price_lower = Decimal(sqrt_price_lower_x96) / (2**96)
        if sqrt_price <= sqrt_price_lower:  
            # All in token0
            amount0 = liquidity * (sqrt_price_upper - sqrt_price_lower) / (sqrt_price_upper * sqrt_price_lower)
            amount1 = 0
        elif sqrt_price >= sqrt_price_upper:  
            # All in token1
            amount0 = 0
            amount1 = liquidity * (sqrt_price_upper - sqrt_price_lower)
        else:  
            # Mixed
            amount0 = liquidity * (sqrt_price_upper - sqrt_price) / (sqrt_price_upper * sqrt_price)
            amount1 = liquidity * (sqrt_price - sqrt_price_lower)
        return float(amount0), float(amount1)

    def _calculate_fees(self, 
            fee_growth_global0, fee_growth_global1, 
            fee_growth0_low, fee_growth0_high,
            fee_growth1_low, fee_growth1_high, 
            fee_growth_inside0, fee_growth_inside1, 
            liquidity, decimals0, decimals1, 
            tick_lower, tick_upper, tick_current) -> tuple[float, float]:
        fee_growth_global0 = Decimal(fee_growth_global0)
        fee_growth_global1 = Decimal(fee_growth_global1)
        tick_lower_fee_growth_outside_0 = Decimal(fee_growth0_low)
        tick_lower_fee_growth_outside_1 = Decimal(fee_growth1_low)
        tick_upper_fee_growth_outside_0 = Decimal(fee_growth0_high)
        tick_upper_fee_growth_outside_1 = Decimal(fee_growth1_high)
        tick_lower_fee_growth_below_0 = 0
        tick_lower_fee_growth_below_1 = 0
        tick_upper_fee_growth_above_0 = 0
        tick_upper_fee_growth_above_1 = 0
        if tick_current >= tick_upper:
            tick_upper_fee_growth_above_0 = fee_growth_global0 - tick_upper_fee_growth_outside_0
            tick_upper_fee_growth_above_1 = fee_growth_global1 - tick_upper_fee_growth_outside_1
        else:
            tick_upper_fee_growth_above_0 = tick_upper_fee_growth_outside_0
            tick_upper_fee_growth_above_1 = tick_upper_fee_growth_outside_1
        if tick_current >= tick_lower:
            tick_lower_fee_growth_below_0 = tick_lower_fee_growth_outside_0
            tick_lower_fee_growth_below_1 = tick_lower_fee_growth_outside_1
        else:
            tick_lower_fee_growth_below_0 = fee_growth_global0 - tick_lower_fee_growth_outside_0
            tick_lower_fee_growth_below_1 = fee_growth_global1 - tick_lower_fee_growth_outside_1
        fr_t1_0 = fee_growth_global0 - tick_lower_fee_growth_below_0 - tick_upper_fee_growth_above_0
        fr_t1_1 = fee_growth_global1 - tick_lower_fee_growth_below_1 - tick_upper_fee_growth_above_1
        fee_growth_inside_last_0 = Decimal(fee_growth_inside0)
        fee_growth_inside_last_1 = Decimal(fee_growth_inside1)
        uncollected_fees_0 = liquidity * (fr_t1_0 - fee_growth_inside_last_0) / 2**128
        uncollected_fees_1 = liquidity * (fr_t1_1 - fee_growth_inside_last_1) / 2**128
        uncollected_fees_adjusted_0 = uncollected_fees_0 / Decimal(10**decimals0)
        uncollected_fees_adjusted_1 = uncollected_fees_1 / Decimal(10**decimals1)
        return float(uncollected_fees_adjusted_0), float(uncollected_fees_adjusted_1)


    def __str__(self):
        return self.name

    
    def __getstate__(self):
        state = self.__dict__.copy()
        if state.get('web3', None):
            del state['web3']
        if state.get('position_manager', None):
            del state['position_manager']
        if state.get('pool', None):
            del state['pool']
        return state


    def __setstate__(self, state):
        self.__dict__.update(state)