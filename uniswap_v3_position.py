from __future__ import annotations

import json
import time
from datetime import datetime,timezone
from decimal import Decimal

from web3 import Web3

import web3_utils


class UniswapV3Position:

    def __init__(self, web3: Web3, position_manager_address: str, factory_address: str, 
            position_id: int, owner_address: str):
        self.web3 = web3
        self.POSITION_MANAGER = position_manager_address
        self.FACTORY = factory_address
        self.position_id = position_id
        self.owner = owner_address


    def fetch_data(self, from_block: int) -> UniswapV3Position:
        self.position = self.get_position_contract_data()
        self.creation_date = self.get_deposit_init_date(from_block)
        self.pool_address = self.get_pool_address()
        self.pool_data = self.get_pool_contract_data(self.position['tickLower'], 
            self.position['tickUpper'])
        token0_decimals, symbol0 = self.get_token_info(self.position['token0'])
        token1_decimals, symbol1 = self.get_token_info(self.position['token1'])
        self.token0_decimals = token0_decimals
        self.token1_decimals = token1_decimals
        self.symbol0 = symbol0
        self.symbol1 = symbol1
        return self


    @property
    def name(self) -> str:
        return f"Position {self.position_id} ({self.symbol0}/{self.symbol1} {int(self.position['fee'])/10000:.2f}%)"


    def refresh(self) -> UniswapV3Position:
        self.position = self.get_position_contract_data()
        self.pool_data = self.get_pool_contract_data(self.position['tickLower'], 
            self.position['tickUpper'])
        return self


    def get_position_contract_data(self) -> dict:
        position_manager_abi = web3_utils.load_abi("UniswapV3PositionManager")
        position_manager = self.web3.eth.contract(address=self.POSITION_MANAGER, abi=position_manager_abi)
        position = position_manager.functions.positions(self.position_id).call()
        return web3_utils.map_contract_result(position_manager_abi, 'positions', position)


    def get_deposit_init_date(self, from_block: int, chunk_size: int = 5000) -> datetime:
        latest_block = self.web3.eth.block_number
        all_logs = []
        for start_block in range(from_block, latest_block, chunk_size):
            end_block = min(start_block + chunk_size - 1, latest_block)
            logs = self.web3.eth.get_logs({
                "fromBlock": start_block,
                "toBlock": end_block,
                "address": self.POSITION_MANAGER,
                "topics": [
                    web3_utils.get_topic_keccak_hex("Transfer(address,address,uint256)"),
                    None,
                    web3_utils.get_topic_hex(self.owner.lower()),
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
            print(f"Position {str(self.position_id)} was created on: {creation_date} UTC")
            return creation_date


    def get_total_fees_collected(self) -> tuple[float, float]:
        slot0, tickLow, tickHi, feeGrowthGlobal0, feeGrowthGlobal1 = self.pool_data
        return self._calculate_fees(feeGrowthGlobal0, feeGrowthGlobal1, tickLow['feeGrowthOutside0X128'], 
            tickHi['feeGrowthOutside0X128'], self.position['feeGrowthInside0LastX128'], 
            tickLow['feeGrowthOutside1X128'], tickHi['feeGrowthOutside1X128'], 
            self.position['feeGrowthInside1LastX128'], self.position['liquidity'], self.token0_decimals, 
            self.token1_decimals, self.position['tickLower'], self.position['tickUpper'], slot0['tick'])


    def get_total_locked_amount(self) -> tuple[float, float]:
        slot0, tickLower, tickUpper, feeGrowthGlobal0, feeGrowthGlobal1 = self.pool_data
        # Convert ticks to sqrtPriceX96
        sqrt_price_lower_x96 = 1.0001 ** (self.position['tickLower'] / 2) * (2**96)
        sqrt_price_upper_x96 = 1.0001 ** (self.position['tickUpper'] / 2) * (2**96)
        # Calculate amounts
        amount0, amount1 = self._calculate_amounts(self.position['liquidity'], slot0['sqrtPriceX96'], 
            sqrt_price_upper_x96, sqrt_price_lower_x96)
        token0_amount = amount0/10**self.token0_decimals
        token1_amount = amount1/10**self.token1_decimals
        return token0_amount, token1_amount


    def calculate_position_apy(self) -> tuple[float, int, float, float, str]:
        token0_amount, token1_amount = self.get_total_locked_amount()
        print('Locked: ', token0_amount, self.symbol0, token1_amount, self.symbol1)
        token0_fee, token1_fee = self.get_total_fees_collected()
        print('Fees: ', token0_fee, self.symbol0, token1_fee, self.symbol1)

        price = self.get_pool_price()
        total_amount = token0_amount*price + token1_amount
        total_fees = token0_fee*price + token1_fee

        date_diff = (datetime.now(timezone.utc) - self.creation_date)
        years_portion = 365*24*60*60/date_diff.total_seconds()
        apy = 0
        if total_amount != 0:
            apy = total_fees / total_amount * years_portion * 100
        return apy, date_diff.days, total_amount, total_fees, self.symbol1


    def get_pool_address(self) -> str:
        factory_abi = web3_utils.load_abi("UniswapFactory")
        factory_contract = self.web3.eth.contract(address=self.FACTORY, abi=factory_abi)
        pool_address = factory_contract.functions.getPool(self.position['token0'], 
            self.position['token1'], self.position['fee']).call()
        return pool_address


    def get_pool_contract_data(self, tickLower, tickUpper) -> tuple[dict, dict, dict, float, float]:
        pool_abi = web3_utils.load_abi("UniswapV3Pool")
        pool_contract = self.web3.eth.contract(address=self.pool_address, abi=pool_abi)

        slot0 = pool_contract.functions.slot0().call()
        slot0 = web3_utils.map_contract_result(pool_abi, 'slot0', slot0)

        tickLow = pool_contract.functions.ticks(tickLower).call()
        tickLow = web3_utils.map_contract_result(pool_abi, 'ticks', tickLow)

        tickHi = pool_contract.functions.ticks(tickUpper).call()
        tickHi = web3_utils.map_contract_result(pool_abi, 'ticks', tickHi)

        feeGrowthGlobal0 = pool_contract.functions.feeGrowthGlobal0X128().call()
        feeGrowthGlobal0 = web3_utils.map_contract_result(pool_abi, 'feeGrowthGlobal0X128', feeGrowthGlobal0)

        feeGrowthGlobal1 = pool_contract.functions.feeGrowthGlobal1X128().call()
        feeGrowthGlobal1 = web3_utils.map_contract_result(pool_abi, 'feeGrowthGlobal1X128', feeGrowthGlobal1)

        return slot0, tickLow, tickHi, feeGrowthGlobal0, feeGrowthGlobal1


    def get_pool_price(self) -> float:
        pool_abi = web3_utils.load_abi("UniswapV3Pool")
        pool_contract = self.web3.eth.contract(address=self.pool_address, abi=pool_abi)
        slot0 = pool_contract.functions.slot0().call()
        sqrtPriceX96 = slot0[0]
        price = (sqrtPriceX96 / (2**96))**2
        adjusted_to_token1_price = price / (10 ** (self.token1_decimals - self.token0_decimals))  # Adjust for decimals
        return adjusted_to_token1_price


    def get_token_info(self, token_address: str) -> tuple[int, str]:
        erc20_abi = web3_utils.load_abi("ERC20")
        token_contract = self.web3.eth.contract(address=Web3.to_checksum_address(token_address), abi=erc20_abi)
        decimals_token = token_contract.functions.decimals().call()
        symbol = token_contract.functions.symbol().call()
        return decimals_token, symbol


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


    def _calculate_fees(self, feeGrowthGlobal0, feeGrowthGlobal1, feeGrowth0Low, feeGrowth0Hi, 
            feeGrowthInside0, feeGrowth1Low, feeGrowth1Hi, feeGrowthInside1, liquidity, decimals0, 
            decimals1, tickLower, tickUpper, tickCurrent) -> tuple[float, float]:
        feeGrowthGlobal_0 = Decimal(feeGrowthGlobal0)
        feeGrowthGlobal_1 = Decimal(feeGrowthGlobal1)
        tickLowerFeeGrowthOutside_0 = Decimal(feeGrowth0Low)
        tickLowerFeeGrowthOutside_1 = Decimal(feeGrowth1Low)
        tickUpperFeeGrowthOutside_0 = Decimal(feeGrowth0Hi)
        tickUpperFeeGrowthOutside_1 = Decimal(feeGrowth1Hi)
        tickLowerFeeGrowthBelow_0 = 0
        tickLowerFeeGrowthBelow_1 = 0
        tickUpperFeeGrowthAbove_0 = 0
        tickUpperFeeGrowthAbove_1 = 0
        if tickCurrent >= tickUpper:
            tickUpperFeeGrowthAbove_0 = feeGrowthGlobal_0 - tickUpperFeeGrowthOutside_0
            tickUpperFeeGrowthAbove_1 = feeGrowthGlobal_1 - tickUpperFeeGrowthOutside_1
        else:
            tickUpperFeeGrowthAbove_0 = tickUpperFeeGrowthOutside_0
            tickUpperFeeGrowthAbove_1 = tickUpperFeeGrowthOutside_1
        if tickCurrent >= tickLower:
            tickLowerFeeGrowthBelow_0 = tickLowerFeeGrowthOutside_0
            tickLowerFeeGrowthBelow_1 = tickLowerFeeGrowthOutside_1
        else:
            tickLowerFeeGrowthBelow_0 = feeGrowthGlobal_0 - tickLowerFeeGrowthOutside_0
            tickLowerFeeGrowthBelow_1 = feeGrowthGlobal_1 - tickLowerFeeGrowthOutside_1
        fr_t1_0 = feeGrowthGlobal_0 - tickLowerFeeGrowthBelow_0 - tickUpperFeeGrowthAbove_0
        fr_t1_1 = feeGrowthGlobal_1 - tickLowerFeeGrowthBelow_1 - tickUpperFeeGrowthAbove_1
        feeGrowthInsideLast_0 = Decimal(feeGrowthInside0)
        feeGrowthInsideLast_1 = Decimal(feeGrowthInside1)
        uncollectedFees_0 = liquidity * (fr_t1_0 - feeGrowthInsideLast_0) / 2**128
        uncollectedFees_1 = liquidity * (fr_t1_1 - feeGrowthInsideLast_1) / 2**128
        uncollectedFeesAdjusted_0 = uncollectedFees_0 / Decimal(10**decimals0)
        uncollectedFeesAdjusted_1 = uncollectedFees_1 / Decimal(10**decimals1)
        return float(uncollectedFeesAdjusted_0), float(uncollectedFeesAdjusted_1)


    def __str__(self):
        return self.name

    
    def __getstate__(self):
        state = self.__dict__.copy()
        if state.get('web3', None):
            del state['web3']
        return state


    def __setstate__(self, state):
        self.__dict__.update(state)
