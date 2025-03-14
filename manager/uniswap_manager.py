import math

from web3.exceptions import ContractLogicError

from entity.uniswap_v3_position import UniswapV3Position
from entity.pickle_cache import PickleCache
from contracts.uniswap_v3_position_manager import UniswapV3PositionManager
from contracts.uniswap_v3_router import UniswapV3Router
from contracts.uniswap_v3_pool import PoolFee
from contracts.uniswap_v3_factory import UniswapV3Factory
from contracts.uniswap_v3_quoter_v2 import UniswapV3QuoterV2
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

    def get_list_of_positions(self, refresh_data: bool = True) -> dict[str, dict[int, UniswapV3Position]]:
        all_positions = {}
        # caching positions
        resave_file = False
        cache = PickleCache.get_instance("positions")
        if cache.has("positions"):
            all_positions = cache.get("positions")
        # end caching positions
        for wallet_alias, wallet_address in self.config["wallet"]["addresses"].items():
            wallet_address = str(self.web3.to_checksum_address(wallet_address))
            position_ids = self.position_manager.get_position_ids(wallet_address)
            positions_per_address = {}
            for position_id in position_ids:
                if position_id not in all_positions[wallet_address].keys():
                    position = UniswapV3Position.get_instance(
                        self.position_manager, position_id, wallet_address
                    )
                    position.get_deposit_init_date(self.config["network"]["from_block"])
                    resave_file = True
                else:
                    position = all_positions[wallet_address][position_id]
                    position.web3 = self.web3
                    position.position_manager = self.position_manager
                    position_data = position.position_data
                    position.pool = UniswapV3Factory.get_singleton(
                        self.config
                    ).get_pool(
                        position_data["token0"],
                        position_data["token1"],
                        position_data["fee"],
                    )
                if refresh_data:
                    position.refresh()
                positions_per_address[position_id] = position
            all_positions[wallet_address] = positions_per_address
        # cache positions
        if resave_file:
            cache.set("positions", all_positions)
        # end caching positions
        return all_positions

    def print_positions(self):
        all_positions = self.get_list_of_positions()
        for wallet_address, positions in all_positions.items():
            wallet_title = wallet_address
            for wallet_name, wa in self.config["wallet"]["addresses"].items():
                if wallet_address.lower() == wa.lower():
                    wallet_title = wallet_name
                    break
            print(f"Wallet: {wallet_title}\n👇👇👇")
            if not positions:
                print("No positions found")
            for position_id, position in positions.items():
                apy, position_days, total_amount, total_fees, symbol = (
                    position.calculate_position_apy()
                )
                token_price = float(utils.get_coin_price_usd(symbol))
                total_amount = total_amount * token_price
                total_fees = total_fees * token_price
                low_price, high_price = position.get_price_range()
                print(
                    f"{'⚪️' if position.is_closed() else '🟢' if position.is_active() else '🔴'} "
                    f"price range {1/low_price:.2f} {position.get_token0().get_symbol()} - "
                    f"{1/high_price:.2f} {position.get_token1().get_symbol()}, "
                    f"opened at {position.creation_date}"
                )
                token0_amount, token1_amount = position.get_total_locked_amount()
                print(
                    "Locked: ",
                    token0_amount,
                    position.get_token0().get_symbol(),
                    token1_amount,
                    position.get_token1().get_symbol(),
                )
                token0_fee, token1_fee = position.get_total_fees_collected()
                print(
                    "Fees: ",
                    token0_fee,
                    position.get_token0().get_symbol(),
                    token1_fee,
                    position.get_token1().get_symbol(),
                )
                print(
                    f"{position.name} APY: {apy:.2f}%, {position_days} days,"
                    f"{total_amount:.2f}$ deposit, {total_fees:.2f}$ fees"
                )
                print("---------------------------------------")

    def swap(
        self,
        in_erc20: ERC20,
        out_erc20: ERC20,
        in_token_amount: int,
        out_token_amount: int,
        wallet_address: str,
        send=False,
    ):
        if in_erc20 == out_erc20:
            raise UniswapManagerError("Tokens must be different")
        wallet_address = str(self.web3.to_checksum_address(wallet_address))
        txs = []
        nonce = in_erc20.get_nonce(wallet_address)
        if out_token_amount == 0:
            find_in_mode = False
        else:
            find_in_mode = True
        # estimate prices and select fee tier
        fee_tier = PoolFee.FEE_TIER_100.value
        # lowest_price = 0
        best_quote = None
        quoter = UniswapV3QuoterV2(self.config)
        for tier in PoolFee:
            pool = UniswapV3Factory.get_singleton(self.config).get_pool(
                in_erc20.contract_address, out_erc20.contract_address, tier
            )

            if find_in_mode:
                quote = quoter.quote_exact_output(pool, out_erc20, out_token_amount)
                amount_key = 'amountIn'
            else:
                quote = quoter.quote_exact_input(pool, in_erc20, in_token_amount)
                amount_key = 'amountOut'

            if best_quote is None:
                best_quote = quote
                fee_tier = tier.value
            elif find_in_mode and (quote[amount_key] < best_quote[amount_key]):
                print(f"Pool {tier / 10000}% {'input' if find_in_mode else 'output'} amount = {quote[amount_key]}")
                best_quote = quote
                fee_tier = tier.value
            elif not find_in_mode and (quote[amount_key] > best_quote[amount_key]):
                best_quote = quote
                fee_tier = tier.value

            if not send:
                print(
                    f"Pool {tier / 10000}% {'input' if find_in_mode else 'output'} "
                    f"amount = {quote[amount_key]/10**(in_erc20.get_decimals() if find_in_mode else out_erc20.get_decimals())} "
                    f"{in_erc20.get_symbol() if find_in_mode else out_erc20.get_symbol()} "
                    f"with gas {quote['gasEstimate']} units",
                )
        if find_in_mode:
            in_token_amount = best_quote[amount_key]
        else:
            out_token_amount = best_quote[amount_key]
        # check balance
        balance_manager = BalanceManager(self.config)
        deposit_weth_tx = self.check_balance_and_deposit_token(
            balance_manager, in_erc20, wallet_address, in_token_amount, nonce
        )
        if deposit_weth_tx is not None:
            txs.append(deposit_weth_tx)
            nonce += 1
        # check allowance
        router = UniswapV3Router.get_singleton(self.config)
        allow_tx = self.check_allowance_and_approve(
            router, in_erc20, in_token_amount, wallet_address, nonce
        )
        if allow_tx is not None:
            txs.append(allow_tx)
            nonce += 1
        # swap
        swap_tx = None
        if send:
            if find_in_mode:
                swap_tx = router.set_nonce(nonce).swap_out_min(
                    in_erc20.contract_address,
                    out_erc20.contract_address,
                    in_token_amount,
                    out_token_amount,
                    fee_tier,
                    wallet_address,
                )
            else:
                swap_tx = router.set_nonce(nonce).swap_in_max(
                    in_erc20.contract_address,
                    out_erc20.contract_address,
                    in_token_amount,
                    out_token_amount,
                    fee_tier,
                    wallet_address,
                )
        txs.append(
            {
                "tx": swap_tx,
                "action": f"Swap {in_token_amount/10**in_erc20.get_decimals()} {in_erc20.get_symbol()} to {out_erc20.get_symbol()}",
                "gas": best_quote["gasEstimate"]
            }
        )
        print(f"Transactions: {len(txs)}")
        if send:
            self.send_txs(txs, router, wallet_address)
        else:
            self.estimate_txs(txs)

    def open_position(
        self,
        token0: ERC20,
        token1: ERC20,
        amount0: int,
        amount1: int,
        fee: int,
        wallet_address: str,
        send=False,
    ):
        if token0 == token1:
            raise UniswapManagerError("Tokens must be different")
        if fee not in [item.value for item in PoolFee]:
            raise UniswapManagerError(f"Invalid fee tier: {fee}")
        wallet_address = str(self.web3.to_checksum_address(wallet_address))
        txs = []
        nonce = token0.get_nonce(wallet_address)
        # check balance
        balance_manager = BalanceManager(self.config)
        deposit_weth_tx = self.check_balance_and_deposit_token(
            balance_manager, token0, wallet_address, amount0, nonce
        )
        if deposit_weth_tx is not None:
            txs.append(deposit_weth_tx)
            nonce += 1
        deposit_weth_tx = self.check_balance_and_deposit_token(
            balance_manager, token1, wallet_address, amount1, nonce
        )
        if deposit_weth_tx is not None:
            txs.append(deposit_weth_tx)
            nonce += 1
        # check allowance
        position_manager = UniswapV3PositionManager.get_singleton(self.config)
        allow_tx = self.check_allowance_and_approve(
            position_manager, token0, amount0, wallet_address, nonce
        )
        if allow_tx is not None:
            txs.append(allow_tx)
            nonce += 1
        allow_tx = self.check_allowance_and_approve(
            position_manager, token1, amount1, wallet_address, nonce
        )
        if allow_tx is not None:
            txs.append(allow_tx)
            nonce += 1
        # create new position
        price_deviation_percents = 15
        position_id = position_manager.get_position_id(
            token0.contract_address, token1.contract_address, fee, wallet_address
        )
        if position_id is None:
            pool = UniswapV3Factory.get_singleton(self.config).get_pool(
                token0.contract_address, token1.contract_address, fee
            )
            tick_lower, tick_upper = position_manager.get_ticks(
                pool, price_deviation_percents
            )
            open_tx = position_manager.set_nonce(nonce).open_position(
                token0.contract_address,
                token1.contract_address,
                fee,
                amount0,
                amount1,
                0,
                0,
                tick_lower,
                tick_upper,
                wallet_address,
            )
            txs.append({"tx": open_tx, "action": f"Create position"})
            nonce += 1
        else:
            raise UniswapManagerError(f"Position already exists: {position_id}")
        print(f"Transactions: {len(txs)}")
        if send:
            self.send_txs(txs, position_manager, wallet_address)
        else:
            self.estimate_txs(txs)

    def close_position(self, position_id: int, send=False):
        current_position = None
        wallet_address = None
        positions = self.get_list_of_positions(refresh_data=False)
        for wallet, wallet_positions in positions.items():
            if position_id in wallet_positions.keys():
                current_position = wallet_positions[position_id]
                wallet_address = str(self.web3.to_checksum_address(wallet))
                break
        if current_position is None:
            raise UniswapManagerError(
                f"Position with id={str(position_id)} doesn't exist"
            )
        position_manager = UniswapV3PositionManager.get_singleton(self.config)
        liquidity = int(current_position.refresh().position_data['liquidity'])
        if liquidity == 0:
            raise UniswapManagerError(
                f"Position with id={str(position_id)} already closed"
            )
        nonce = position_manager.get_nonce(wallet_address)
        dec_liq_tx = position_manager.set_nonce(nonce).decrease_liquidity(position_id, liquidity, wallet_address)
        txs = [{"tx": dec_liq_tx, "action": f"Remove liquidity for position {str(position_id)}"}]
        nonce += 1
        collect_tx = position_manager.set_nonce(nonce).collect_all(wallet_address, position_id)
        txs.append({"tx": collect_tx, "action": f"Collect liquidity for position {str(position_id)}"})
        nonce += 1
        collect_tx = position_manager.set_nonce(nonce).burn(position_id, wallet_address)
        txs.append({"tx": collect_tx, "action": f"Burn position {str(position_id)} completely"})
        print(f"Transactions: {len(txs)}")
        if send:
            self.send_txs(txs, position_manager, wallet_address)
        else:
            self.estimate_txs(txs)

    def add_liqudity(
        self,
        token0: ERC20,
        token1: ERC20,
        amount0: int,
        amount1: int,
        position_id: int,
        wallet_address: str,
        send=False,
    ):
        if token0 == token1:
            raise UniswapManagerError("Tokens must be different")
        current_position = None
        positions = self.get_list_of_positions(refresh_data=False)
        for wallet, wallet_positions in positions.items():
            if position_id in wallet_positions.keys():
                current_position = wallet_positions[position_id]
                break
        if current_position is None:
            raise UniswapManagerError(
                f"Position with id={str(position_id)} doesn't exist"
            )
        if [token0, token1] != [
            current_position.get_token0(),
            current_position.get_token1(),
        ]:
            raise UniswapManagerError(
                f"Tokens for position {str(position_id)} are "
                f"{current_position.get_token0().get_symbol()} and {current_position.get_token1().get_symbol()}, "
                f"but you set {token0.get_symbol()} and {token1.get_symbol()}"
            )
        wallet_address = str(self.web3.to_checksum_address(wallet_address))
        txs = []
        nonce = token0.get_nonce(wallet_address)
        # check balance
        balance_manager = BalanceManager(self.config)
        deposit_weth_tx = self.check_balance_and_deposit_token(
            balance_manager, token0, wallet_address, amount0, nonce
        )
        if deposit_weth_tx is not None:
            txs.append(deposit_weth_tx)
            nonce += 1
        deposit_weth_tx = self.check_balance_and_deposit_token(
            balance_manager, token1, wallet_address, amount1, nonce
        )
        if deposit_weth_tx is not None:
            txs.append(deposit_weth_tx)
            nonce += 1
        # check allowance
        position_manager = UniswapV3PositionManager.get_singleton(self.config)
        allow_tx = self.check_allowance_and_approve(
            position_manager, token0, amount0, wallet_address, nonce
        )
        if allow_tx is not None:
            txs.append(allow_tx)
            nonce += 1
        allow_tx = self.check_allowance_and_approve(
            position_manager, token1, amount1, wallet_address, nonce
        )
        if allow_tx is not None:
            txs.append(allow_tx)
            nonce += 1
        # add liquidity to the position
        inc_liq_tx = position_manager.set_nonce(nonce).increase_liquidity(position_id, amount0, amount1, wallet_address)
        txs.append({"tx": inc_liq_tx, "action": f"Increse liquidity for position {position_id}"})
        nonce += 1
        print(f"Transactions: {len(txs)}")
        if send:
            self.send_txs(txs, position_manager, wallet_address)
        else:
            self.estimate_txs(txs)

    def collect_position_fees(self, position_id: int, send=False):
        current_position = None
        wallet_address = None
        positions = self.get_list_of_positions(refresh_data=False)
        for wallet, wallet_positions in positions.items():
            if position_id in wallet_positions.keys():
                current_position = wallet_positions[position_id]
                wallet_address = str(self.web3.to_checksum_address(wallet))
                break
        if current_position is None:
            raise UniswapManagerError(
                f"Position with id={str(position_id)} doesn't exist"
            )
        position_manager = UniswapV3PositionManager.get_singleton(self.config)
        collect_tx = position_manager.collect_all(wallet_address, position_id)
        txs = [{"tx": collect_tx, "action": f"Collect liquidity for position {str(position_id)}"}]
        print(f"Transactions: {len(txs)}")
        if send:
            self.send_txs(txs, position_manager, wallet_address)
        else:
            self.estimate_txs(txs)

    def check_balance_and_deposit_token(
        self,
        balance_manager: BalanceManager,
        token: ERC20,
        wallet_address: str,
        token_amount: int,
        nonce: int,
    ) -> dict | None:
        in_balance, in_decimals, in_symbol = balance_manager.get_token_balance(
            wallet_address, token.contract_address
        )
        if in_balance < token_amount:
            if in_symbol == "WETH":
                # deposit WETH
                weth_amount = token_amount - in_balance
                deposit_weth_tx = (
                    WETH9.get_singleton(self.config)
                    .set_nonce(nonce)
                    .deposit(wallet_address, weth_amount)
                )
                return {
                    "tx": deposit_weth_tx,
                    "action": f"Wrap {weth_amount/10**18} ETH to WETH",
                }
            else:
                raise UniswapManagerError(
                    f"Insufficient balance: {in_balance} {in_symbol}"
                )
        return None

    def check_allowance_and_approve(
        self,
        spender: Contract,
        token: ERC20,
        amount: int,
        wallet_address: str,
        nonce: int,
    ):
        tokens_allowed = token.get_allowance(wallet_address, spender.contract_address)
        if tokens_allowed < amount:
            # approve token for spender
            allow_tx = token.set_nonce(nonce).approve(
                wallet_address, spender.contract_address, amount
            )
            return {
                "tx": allow_tx,
                "action": f"Approve spender to spend {amount/10**token.get_decimals()} {token.get_symbol()}",
            }

    def estimate_txs(self, txs: list[dict]):
        gas_price = web3_utils.get_gas_price(self.web3)
        eth_price = float(utils.get_coin_price_usd("ETH"))
        price = self.web3.from_wei(gas_price,"gwei")
        for i, tx in enumerate(txs):
            try:
                print(f"{i+1}.  {tx['action']}:")
                if 'gas' in tx:
                    gas_units = tx['gas']
                else:
                    gas_units = web3_utils.estimate_tx_gas(self.web3, tx["tx"])
                costs = self.web3.from_wei(gas_price * gas_units, "gwei")
                print(
                    f"{str(gas_units)} units for {price:.2f} Gwei -> "
                    f"{costs:.2f} Gwei, "
                    f"{gas_price*gas_units * eth_price / 10**18:.2f}$"
                )
            except ContractLogicError as e:
                print("error: can't estimate gas")

    def send_txs(self, txs: list[dict], contract: Contract, wallet_address: str):
        for i, tx in enumerate(txs):
            print(f"{i+1}.  {tx['action']}")
            tx_hash = contract.sign_and_send_tx(tx["tx"], wallet_address)
            receipt = contract.get_tx_receipt(tx_hash)
            print(receipt)

    def quote_for_in_token(self, in_erc20: ERC20, out_erc20: ERC20, amount_in: int, fee_tier: int) -> dict:
        quoter = UniswapV3QuoterV2(self.config)
        pool = UniswapV3Factory.get_singleton(self.config).get_pool(
            in_erc20.contract_address, out_erc20.contract_address, fee_tier
        )
        res = quoter.quote_exact_input(pool, in_erc20, amount_in)
        print(res)
        return res

    def quote_for_out_token(self, in_erc20: ERC20, out_erc20: ERC20, amount_out: int, fee_tier: int) -> dict:
        quoter = UniswapV3QuoterV2(self.config)
        pool = UniswapV3Factory.get_singleton(self.config).get_pool(
            in_erc20.contract_address, out_erc20.contract_address, fee_tier
        )
        res = quoter.quote_exact_output(pool, out_erc20, amount_out)
        return res
    
class UniswapManagerError(Exception):
    pass
