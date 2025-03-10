import pickle
import os
import math

from web3 import Web3
from web3.exceptions import ContractLogicError

from entity.uniswap_v3_position import UniswapV3Position
from entity.pickle_cache import PickleCache
from contracts.uniswap_v3_position_manager import UniswapV3PositionManager
from contracts.uniswap_v3_router import UniswapV3Router
from contracts.uniswap_v3_pool import UniswapV3Pool, PoolFee
from contracts.uniswap_v3_factory import UniswapV3Factory
from contracts.erc20 import ERC20
from contracts.weth9 import WETH9
from contracts.contract import Contract
import utils.web3_utils as web3_utils
import utils.utils as utils
from .balance_manager import BalanceManager


class UniswapManager:
    """
    A class to manage Uniswap V3 positions and swaps.
    Attributes:
        config (dict): Configuration dictionary containing network and wallet information.
        web3 (Web3): Web3 instance for interacting with the Ethereum blockchain.
        position_manager (UniswapV3PositionManager): Singleton instance of UniswapV3PositionManager.
    Methods:
        get_list_of_positions() -> dict[str, dict[int, UniswapV3Position]]:
            Retrieves a list of positions for all configured wallets.
        print_positions():
            Prints the details of all positions for all configured wallets.
        swap(in_erc20: ERC20, out_erc20: ERC20, in_token_amount: int, out_token_amount: int, 
             wallet_address: str, send=False):
            Executes a token swap on Uniswap V3.
        open_position(token0: ERC20, token1: ERC20, amount0: int, amount1: int, fee: int, 
                      wallet_address: str, send=False):
            Opens a new liquidity position on Uniswap V3.
    """

    def __init__(self, config: dict):
        self.config = config
        self.web3 = web3_utils.get_web3(config)
        Contract.web3 = self.web3
        self.position_manager = UniswapV3PositionManager.get_singleton(config)

    def get_list_of_positions(self) -> dict[str, dict[int, UniswapV3Position]]:
        all_positions = {}
        # caching positions
        resave_file = False
        cache = PickleCache.get_instance("positions")
        if cache.has("positions"):
            all_positions = cache.get("positions")
        # end caching positions
        for wallet_alias, wallet_address in self.config['wallet']['addresses'].items():
            wallet_address = str(self.web3.to_checksum_address(wallet_address))
            if wallet_address not in all_positions.keys():
                all_positions[wallet_address] = {}
            position_ids = self.position_manager.get_position_ids(wallet_address)
            for position_id in position_ids:
                if position_id not in all_positions[wallet_address].keys():
                    position = UniswapV3Position.get_instance(
                        self.position_manager, position_id, wallet_address
                    )
                    position.get_deposit_init_date(self.config['network']['from_block'])
                    all_positions[wallet_address][position_id] = position
                    resave_file = True
                else:
                    position = all_positions[wallet_address][position_id]
                    position.web3 = self.web3
                    position.position_manager = self.position_manager
                    position_data = position.position_data
                    position.pool = (UniswapV3Factory.get_singleton(self.config)
                        .get_pool(position_data['token0'], position_data['token1'], 
                            position_data['fee']
                        )
                    )
                position.refresh()
        # cache positions
        if resave_file:
            cache.set("positions", all_positions)
        # end caching positions
        return all_positions

    def print_positions(self):
        all_positions = self.get_list_of_positions()
        for wallet_address, positions in all_positions.items():
            wallet_title = wallet_address
            for wallet_name, wa in self.config['wallet']['addresses'].items():
                if wallet_address.lower() == wa.lower():
                    wallet_title = wallet_name
                    break
            print(f"Wallet: {wallet_title}\n👇👇👇")
            if not positions:
                print("No positions found")
            for position_id, position in positions.items():
                apy, position_days, total_amount, total_fees, symbol = position.calculate_position_apy()
                token_price = float(utils.get_coin_price_usd(symbol))
                total_amount = total_amount * token_price
                total_fees = total_fees * token_price
                low_price, high_price = position.get_price_range()
                print(f"{'⚪️' if position.is_closed() else '🟢' if position.is_active() else '🔴'} "
                    f"price range {1/low_price:.2f} {position.get_token0().get_symbol()} - "
                    f"{1/high_price:.2f} {position.get_token1().get_symbol()}, "
                    f"opened at {position.creation_date}"
                )
                token0_amount, token1_amount = position.get_total_locked_amount()
                print('Locked: ', token0_amount, position.get_token0().get_symbol(), 
                    token1_amount, position.get_token1().get_symbol()
                )
                token0_fee, token1_fee = position.get_total_fees_collected()
                print('Fees: ', token0_fee, position.get_token0().get_symbol(),
                    token1_fee, position.get_token1().get_symbol()
                )
                print(f"{position.name} APY: {apy:.2f}%, {position_days} days," 
                    f"{total_amount:.2f}$ deposit, {total_fees:.2f}$ fees"
                )
                print("---------------------------------------")

    def swap(self, in_erc20: ERC20, out_erc20: ERC20, in_token_amount: int, out_token_amount: int, 
            wallet_address: str, send = False):
        if in_erc20 == out_erc20:
            raise UniswapManagerError("Tokens must be different")
        wallet_address = str(self.web3.to_checksum_address(wallet_address))
        txs = []
        nonce = in_erc20.get_nonce(wallet_address)
        if out_token_amount == 0:
            out_min_mode = False
        else:
            out_min_mode = True

        # estimate prices and select fee tier
        fee_tier = PoolFee.FEE_TIER_100.value
        lowest_price = 0
        for tier in PoolFee:
            pool = UniswapV3Factory.get_singleton(self.config).get_pool(
                in_erc20.contract_address, out_erc20.contract_address, tier
            )
            price_to_token_1 = pool.get_pool_price(True)
            if pool.get_token0_address().lower() == in_erc20.contract_address.lower():
                price_to_token_1 = 1/price_to_token_1
            price_full = price_to_token_1+price_to_token_1*tier/1000000
            if lowest_price == 0 or price_full < lowest_price:
                lowest_price = price_full
                fee_tier = tier.value
            if not send:
                print('Pool', tier/10000, '% token price = ', price_to_token_1, in_erc20.get_symbol(), 'with fees', price_full, in_erc20.get_symbol())

        if in_token_amount == 0:
            in_token_amount = math.ceil(price_full*out_token_amount * 10 ** (in_erc20.get_decimals()-out_erc20.get_decimals()))

        if out_token_amount == 0:
            out_token_amount = math.ceil(in_token_amount / price_full * 10 ** (out_erc20.get_decimals()-in_erc20.get_decimals()))
            print('Out token amount', out_token_amount, out_erc20.get_symbol())

        # check balance
        balance_manager = BalanceManager(self.config)
        in_balance, in_decimals, in_symbol = balance_manager.get_token_balance(wallet_address, in_erc20.contract_address)
        if in_balance < in_token_amount:
            if in_symbol == "WETH":
                # deposit WETH
                weth_amount = in_token_amount - in_balance
                deposit_weth_tx = WETH9.get_singleton(self.config).set_nonce(nonce).deposit(wallet_address, weth_amount)
                txs.append({"tx": deposit_weth_tx, "action": f"Wrap {weth_amount/10**18} ETH to WETH"})
                nonce += 1
            else:
                raise UniswapManagerError(f"Insufficient balance: {in_balance} {in_symbol}")

        # check allowance
        router = UniswapV3Router.get_singleton(self.config)
        in_tokens_allowed = in_erc20.get_allowance(wallet_address, router.contract_address)
        print('Allowance', in_tokens_allowed, in_erc20.get_symbol())
        if in_tokens_allowed < in_token_amount:
            # approve in token for router
            allow_tx = in_erc20.set_nonce(nonce).approve(wallet_address, router.contract_address, in_token_amount)
            txs.append({"tx": allow_tx, "action": f"Approve uniswap router to spend {in_token_amount/10**in_erc20.get_decimals()} {in_erc20.get_symbol()}"})
            nonce += 1

        if out_min_mode:
            swap_tx = router.set_nonce(nonce).swap_out_min(in_erc20.contract_address, out_erc20.contract_address, in_token_amount, out_token_amount, 
                fee_tier, wallet_address)
        else:
            swap_tx = router.set_nonce(nonce).swap_in_max(in_erc20.contract_address, out_erc20.contract_address, in_token_amount, out_token_amount, 
                fee_tier, wallet_address)
        txs.append({"tx": swap_tx, "action": f"Swap {in_token_amount/10**in_erc20.get_decimals()} {in_erc20.get_symbol()} to {out_erc20.get_symbol()}"})

        print(f"Transactions: {len(txs)}")

        if send:
            
            for i, tx in enumerate(txs):
                print(f"{i+1}.  {tx['action']}")
                tx_hash = in_erc20.sign_and_send_tx(tx['tx'], wallet_address)
                receipt = in_erc20.get_tx_receipt(tx_hash)
                print(receipt)
        else:
            gas_price = web3_utils.get_gas_price(self.web3)
            eth_price = float(utils.get_coin_price_usd('ETH'))
            for i, tx in enumerate(txs):
                try:
                    print(f"{i+1}.  {tx['action']}:")
                    gas_units = web3_utils.estimate_tx_gas(self.web3, tx['tx'])
                    print('Gas price', self.web3.from_wei(gas_price, 'gwei'), 'Gwei', 
                        'Gas=', self.web3.from_wei(gas_price*gas_units, 'gwei'), 'Gwei', 
                        f"{gas_price*gas_units*eth_price/10**18:.2f}", '$'
                    )
                except ContractLogicError as e:
                    print("error: can't estimate gas")

    def open_position(self, token0: ERC20, token1: ERC20, amount0: int, amount1: int, fee: int, 
            wallet_address: str, send = False):
        if token0 == token1:
            raise UniswapManagerError("Tokens must be different")
        if fee not in [item.value for item in PoolFee]:
            raise UniswapManagerError(f"Invalid fee tier: {fee}")
        wallet_address = str(self.web3.to_checksum_address(wallet_address))
        txs = []

        nonce = token0.get_nonce(wallet_address)
        # check balance
        balance_manager = BalanceManager(self.config)
        token0_balance, _, _ = balance_manager.get_token_balance(wallet_address, token0.contract_address)
        if token0_balance < amount0:
            if token0.get_symbol() == "WETH":
                # deposit WETH
                weth_amount = amount0 - token0_balance
                deposit_weth_tx = WETH9.get_singleton(self.config).set_nonce(nonce).deposit(wallet_address, weth_amount)
                txs.append({"tx": deposit_weth_tx, "action": f"Wrap {weth_amount/10**18} ETH to WETH"})
                nonce += 1
            else:
                raise UniswapManagerError(f"Insufficient balance: {token0_balance} {token0.get_symbol()}")
        token1_balance, _, _ = balance_manager.get_token_balance(wallet_address, token1.contract_address)
        if token1_balance < amount1:
            if token1.get_symbol() == "WETH":
                # deposit WETH
                weth_amount = amount1 - token1_balance
                deposit_weth_tx = WETH9.get_singleton(self.config).set_nonce(nonce).deposit(wallet_address, weth_amount)
                txs.append({"tx": deposit_weth_tx, "action": f"Wrap {weth_amount/10**18} ETH to WETH"})
                nonce += 1
            else:
                raise UniswapManagerError(f"Insufficient balance: {token1_balance} {token1.get_symbol()}")

        # check allowance
        position_manager = UniswapV3PositionManager.get_singleton(self.config)
        token0_allowed = token0.get_allowance(wallet_address, position_manager.contract_address)
        print('Allowance', token0_allowed, token0.get_symbol())
        if token0_allowed < amount0:
            allow_tx = token0.set_nonce(nonce).approve(wallet_address, position_manager.contract_address, amount0)
            txs.append({"tx": allow_tx, "action": f"Approve uniswap position manager to spend {amount0/10**token0.get_decimals()} {token0.get_symbol()}"})
            nonce += 1
        token1_allowed = token1.get_allowance(wallet_address, position_manager.contract_address)
        print('Allowance', token1_allowed, token1.get_symbol())
        if token1_allowed < amount1:
            allow_tx = token1.set_nonce(nonce).approve(wallet_address, position_manager.contract_address, amount1)
            txs.append({"tx": allow_tx, "action": f"Approve uniswap position manager to spend {amount1/10**token1.get_decimals()} {token1.get_symbol()}"})
            nonce += 1

        price_deviation_percents = 15
        position_id = position_manager.get_position_id(token0.contract_address, token1.contract_address, fee, wallet_address)
        if position_id is None:
            # create new position
            pool = UniswapV3Factory.get_singleton(self.config).get_pool(token0.contract_address, token1.contract_address, fee)
            tick_lower, tick_upper = position_manager.get_ticks(pool, price_deviation_percents)
            open_tx = position_manager.set_nonce(nonce).open_position(token0.contract_address, token1.contract_address, fee,
                amount0, amount1, 0, 0, tick_lower, tick_upper, wallet_address
            )
            txs.append({"tx": open_tx, "action": f"Create position"})
            nonce += 1
        else:
            raise UniswapManagerError(f"Position already exists: {position_id}")

        print(f"Transactions: {len(txs)}")

        if send:
            for i, tx in enumerate(txs):
                print(f"{i+1}.  {tx['action']}")
                tx_hash = token0.sign_and_send_tx(tx['tx'], wallet_address)
                receipt = token0.get_tx_receipt(tx_hash)
                # print(receipt)
        else:
            gas_price = web3_utils.get_gas_price(self.web3)
            eth_price = float(utils.get_coin_price_usd('ETH'))
            for i, tx in enumerate(txs):
                try:
                    print(f"{i+1}.  {tx['action']}:")
                    gas_units = web3_utils.estimate_tx_gas(self.web3, tx['tx'])
                    print('Gas price', self.web3.from_wei(gas_price, 'gwei'), 'Gwei', 
                        'Gas=', self.web3.from_wei(gas_price*gas_units, 'gwei'), 'Gwei', 
                        f"{gas_price*gas_units*eth_price/10**18:.2f}", '$'
                    )
                except ContractLogicError as e:
                    print("error: can't estimate gas")



class UniswapManagerError(Exception):
    pass