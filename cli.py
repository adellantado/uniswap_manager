from web3.exceptions import ContractLogicError
import click

from contracts.erc20 import ERC20
from manager.balance_manager import BalanceManager
from manager.uniswap_manager import UniswapManager, UniswapManagerError
import utils.utils as utils
import utils.cli_utils as cli_utils
from utils.decorators import to_checksum_address


@click.group()
def cli():
    pass

@click.command(help="Prints balance of ETH/ERC20 token for addresses in the config")
@click.option('--wallet', '-w', help="Ethereum wallet address/alias to get balance for")
@click.option('--erc20', help="ERC20 token address/name to get balance for")
@click.option('--all', '-a', is_flag=True, default=False, help="Balance of all known tokens from the config. Overlaps --erc20")
def balance(wallet, erc20, all):
    config = utils.get_config()
    manager = BalanceManager()

    @to_checksum_address(0,1)
    def get_balance_rec(address, erc20, all):
        if all:
            if address:
                get_balance_rec(address, None, False)
                for token_name in config.balance_visible_tokens:
                    token_address = utils.get_token_address(token_name)
                    get_balance_rec(address, token_address, False)
            else:
                for wallet_alias, wallet_address in config.wallet_addresses.items():
                    click.echo(f'Wallet: {wallet_alias}')
                    get_balance_rec(wallet_address, None, False)
                    for token_name in config.balance_visible_tokens:
                        token_address = utils.get_token_address(token_name)
                        get_balance_rec(wallet_address, token_address, False)
            return
        if address and erc20:
            amount, decimals, symbol = manager.get_token_balance(address, erc20)
            price = float(utils.get_coin_price_usd(symbol))
            click.echo(f'{str(amount/10**decimals)} {symbol}, {(amount/10**decimals) * price:.2f} USD')
        elif address:
            amount = manager.get_eth_balance(address, True)
            eth_price = float(utils.get_coin_price_usd('ETH'))
            click.echo(f'{str(amount)} ETH, {amount * eth_price:.2f} USD')
        elif erc20: 
            for wallet_alias, wallet_address in config.wallet_addresses.items():
                click.echo(f'Wallet: {wallet_alias}')
                get_balance_rec(wallet_address, erc20, all)
        else:
            for wallet_alias, wallet_address in config.wallet_addresses.items():
                click.echo(f'Wallet: {wallet_alias}')
                get_balance_rec(wallet_address, None, all)

    if wallet:
        # check wallet address alias from config
        address = utils.get_wallet_address(wallet)
        utils.raise_address_not_valid(manager.web3, address)
    else:
        address = wallet
    if erc20:
        # check token name from config
        erc20 = erc20.upper()
        if erc20 in config.erc20_tokens:
            erc20 = config.erc20_tokens[erc20]
    get_balance_rec(address, erc20, all)


@click.command(help="Prints Uniswap V3 positions for addresses in the config")
def positions():
    manager = UniswapManager()
    manager.print_positions()

@click.command(help="Prints Binance price of a given coin in USD")
@click.argument('symbol', default='ETH')
def price(symbol):
    price = utils.get_coin_price_usd(symbol.upper())
    click.echo(f"{price} USD")

@click.command(help="Swap ERC20 tokens using Uniswap V3. Use format `swap WETH=0.1 USDC <wallet_alias>`, `swap USDT ETH=0.01 <wallet_address>`")
@click.argument('in_token')
@click.argument('out_token')
@click.argument('wallet')
@click.option('--estimate', '-e', is_flag=True, default=False, help="Estimate transactions")
@click.option('--send', '-s', is_flag=True, default=False, help="Sing and send transactions")
@click.option('--raw', '-r', is_flag=True, default=False, help="Sing and return raw transaction")
def swap(in_token, out_token, wallet, estimate, send, raw):
    wallet_address = utils.get_wallet_address(wallet)
    manager = UniswapManager()
    utils.raise_address_not_valid(manager.web3, wallet_address)
    try:
        _, in_erc20, _, in_native_amount = cli_utils.split_token_amount(in_token)
        _, out_erc20, _, out_native_amount = cli_utils.split_token_amount(out_token)
        if in_native_amount == 0 and out_native_amount == 0:
            utils.print("Amount can't be 0 for both tokens", "error")
            exit(1)
        in_token_name, _ = cli_utils.split_coin_name_and_amount(in_token)
        use_eth = in_token_name == 'ETH'
        manager.swap(in_erc20, out_erc20, in_native_amount, out_native_amount, wallet_address, 
            use_eth, False if estimate else send, raw
        )
    except UniswapManagerError as e:
        click.echo(str(e))
        exit(1)

@click.command("open-position", help="Open Uniswap V3 position")
@click.argument('token1')
@click.argument('token2')
@click.argument('fee_tier')
@click.argument('wallet')
@click.option('--estimate', '-e', is_flag=True, default=False, help="Estimate transactions")
@click.option('--send', '-s', is_flag=True, default=False, help="Sing and send transactions")
@click.option('--raw', '-r', is_flag=True, default=False, help="Sing and return raw transaction")
def open_position(token1, token2, fee_tier, wallet, estimate, send, raw):
    wallet_address = utils.get_wallet_address(wallet)
    manager = UniswapManager()
    utils.raise_address_not_valid(manager.web3, wallet_address)
    try:
        _, token1_erc20, _, token1_native_amount = cli_utils.split_token_amount(token1)
        _, token2_erc20, _, token2_native_amount = cli_utils.split_token_amount(token2)
        token1_name, _ = cli_utils.split_coin_name_and_amount(token1)
        token2_name, _ = cli_utils.split_coin_name_and_amount(token2)
        use_eth = token1_name == 'ETH' or token2_name == 'ETH'
        manager.open_position(token1_erc20, token2_erc20, token1_native_amount, token2_native_amount, 
            int(fee_tier), wallet_address, use_eth, False if estimate else send, raw
        )
    except UniswapManagerError as e:
        click.echo(str(e))
        exit(1)

@click.command("add-liquidity", help="Add liquidity to a Uniswap V3 pool")
@click.argument('token1')
@click.argument('token2')
@click.argument('position_id')
@click.argument('wallet')
@click.option('--estimate', '-e', is_flag=True, default=False, help="Estimate transactions")
@click.option('--send', '-s', is_flag=True, default=False, help="Sing and send transactions")
@click.option('--raw', '-r', is_flag=True, default=False, help="Sing and return raw transaction")
def add_liquidity(token1, token2, position_id, wallet, estimate, send, raw):
    wallet_address = utils.get_wallet_address(wallet)
    manager = UniswapManager()
    utils.raise_address_not_valid(manager.web3, wallet_address)
    try:
        _, token1_erc20, _, token1_native_amount = utils.split_token_amount(token1)
        _, token2_erc20, _, token2_native_amount = utils.split_token_amount(token2)
        token1_name, _ = cli_utils.split_coin_name_and_amount(token1)
        token2_name, _ = cli_utils.split_coin_name_and_amount(token2)
        use_eth = token1_name == 'ETH' or token2_name == 'ETH'
        manager.add_liqudity(token1_erc20, token2_erc20, token1_native_amount, token2_native_amount, 
            int(position_id), wallet_address, use_eth, False if estimate else send, raw
        )
    except UniswapManagerError as e:
        click.echo(str(e))
        exit(1)

@click.command("close-position", help="Close Uniswap V3 position")
@click.argument('position_id')
@click.option('--estimate', '-e', is_flag=True, default=False, help="Estimate transactions")
@click.option('--send', '-s', is_flag=True, default=False, help="Sing and send transactions")
@click.option('--raw', '-r', is_flag=True, default=False, help="Sing and return raw transaction")
def close_position(position_id, estimate, send, raw):
    try:
        manager = UniswapManager()
        manager.close_position(int(position_id), False if estimate else send, raw) 
    except UniswapManagerError as e:
        click.echo(str(e))
        exit(1)

@click.command("collect-fees", help="Collect fees from Uniswap V3 position")
@click.argument('position_id')
@click.option('--estimate', '-e', is_flag=True, default=False, help="Estimate transactions")
@click.option('--send', '-s', is_flag=True, default=False, help="Sing and send transactions")
@click.option('--raw', '-r', is_flag=True, default=False, help="Sing and return raw transaction")
def collect_fees(position_id, estimate, send, raw):
    try:
        manager = UniswapManager()
        manager.collect_position_fees(int(position_id), False if estimate else send, raw)
    except UniswapManagerError as e:
        click.echo(str(e))
        exit(1)

@click.command(help="Prints network info")
def net():
    web3 = utils.get_web3()
    click.echo(f"Connection: {'🟢 Connected' if web3.is_connected() else '🔴 No connection'}")
    click.echo(f"Gas price: {web3.from_wei(web3.eth.gas_price, 'gwei'):.2f} Gwei")
    click.echo(f"Chain ID: {web3.eth.chain_id}")
    click.echo(f"Web3 version: {web3.api}")
    click.echo(f"Client version: {web3.client_version}")

@click.command(help="Send ETH/ERC20 tokens to another wallet e.g.(bum send ETH=0.1 <wallet_alias> <wallet_address>)")
@click.argument('token')
@click.argument('wallet_from')
@click.argument('wallet_to')
@click.option('--estimate', '-e', is_flag=True, default=False, help="Estimate transactions")
@click.option('--send', '-s', is_flag=True, default=False, help="Sing and send transactions")
@click.option('--raw', '-r', is_flag=True, default=False, help="Sing and return raw transaction")
def send(token, wallet_from, wallet_to, estimate, send, raw):
    wallet_from_address = utils.get_wallet_address(wallet_from)
    wallet_to_address = utils.get_wallet_address(wallet_to)
    manager = BalanceManager()
    utils.raise_address_not_valid(manager.web3, wallet_from_address)
    utils.raise_address_not_valid(manager.web3, wallet_to_address)
    try:
        if token[:3].upper() == 'ETH':
            _, amount = cli_utils.split_coin_name_and_amount(token)
            if amount == 0:
                utils.print("Amount can't be 0", "error")
                exit(1)
            balance = manager.get_eth_balance(wallet_from_address, True)
            if balance < amount:
                utils.print(f"Insufficient balance. Available: {balance} ETH", "error")
                exit(1)
            manager.send_eth(wallet_from_address, wallet_to_address, amount, False if estimate else send, raw)
        else:
            _, erc20, _, native_amount = utils.split_token_amount(token)
            if native_amount == 0:
                utils.print("Amount can't be 0", "error")
                exit(1)
            balance, decimals, symbol = manager.get_token_balance(wallet_from_address, erc20.contract_address)
            if balance < native_amount:
                utils.print(f"Insufficient balance. Available: {balance/10**decimals:.2f} {symbol}", "error")
                exit(1)
            manager.send_token(wallet_from_address, wallet_to_address, erc20, native_amount, False if estimate else send, raw)
    except ContractLogicError as e:
        click.echo(str(e))
        exit(1)

@click.command("send-raw-tx", help="Send raw transaction")
@click.argument('tx')
def send_raw_tx(tx):
    web3 = utils.get_web3()
    tx_hash = web3.eth.send_raw_transaction(tx)
    utils.print(f"Transaction hash: {tx_hash.hex()}", "success")

cli.add_command(net)
cli.add_command(balance)
cli.add_command(positions)
cli.add_command(price)
cli.add_command(swap)
cli.add_command(open_position)
cli.add_command(close_position)
cli.add_command(add_liquidity)
cli.add_command(collect_fees)
cli.add_command(send)
cli.add_command(send_raw_tx)


if __name__ == '__main__':
    cli()