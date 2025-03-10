import click

from contracts.erc20 import ERC20
from manager.balance_manager import BalanceManager
from manager.uniswap_manager import UniswapManager, UniswapManagerError
import utils.utils as utils
import utils.web3_utils as web3_utils
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
    manager = BalanceManager(config)

    @to_checksum_address(0,1)
    def get_balance_rec(address, erc20, all):
        if all:
            erc20_tokens_to_check = config['wallet']['erc20']['active']
            if address:
                get_balance_rec(address, None, False)
                for token_name in erc20_tokens_to_check:
                    token_address = utils.get_token_address(token_name)
                    get_balance_rec(address, token_address, False)
            else:
                for wallet_alias, wallet_address in config['wallet']['addresses'].items():
                    click.echo(f'Wallet: {wallet_alias}')
                    get_balance_rec(wallet_address, None, False)
                    for token_name in erc20_tokens_to_check:
                        token_address = utils.get_token_address(token_name)
                        get_balance_rec(wallet_address, token_address, False)
            return
        if address and erc20:
            amount, decimals, symbol = manager.get_token_balance(address, erc20)
            price = float(utils.get_coin_price_usd(symbol))
            click.echo(f'{str(amount/10**decimals)} {symbol}, {(amount/10**decimals) * price:.2f} USD')
        elif address:
            amount = manager.get_eth_balance(address)
            eth_price = float(utils.get_coin_price_usd('ETH'))
            click.echo(f'{str(amount)} ETH, {amount * eth_price:.2f} USD')
        elif erc20: 
            for wallet_alias, wallet_address in config['wallet']['addresses'].items():
                click.echo(f'Wallet: {wallet_alias}')
                get_balance_rec(wallet_address, erc20, all)
        else:
            for wallet_alias, wallet_address in config['wallet']['addresses'].items():
                click.echo(f'Wallet: {wallet_alias}')
                get_balance_rec(wallet_address, None, all)

    if wallet:
        # check wallet address alias from config
        address = utils.get_wallet_address(wallet)
    else:
        address = wallet
    if erc20:
        # check token name from config
        erc20 = erc20.upper()
        if erc20 in config['ERC20']['tokens']:
            erc20 = config['ERC20']['tokens'][erc20]
    get_balance_rec(address, erc20, all)


@click.command(help="Prints Uniswap V3 positions for addresses in the config")
def positions():
    config = utils.get_config()
    manager = UniswapManager(config)
    manager.print_positions()

@click.command(help="Prints Binance price of a given coin in USD")
@click.argument('symbol', default='ETH')
def price(symbol):
    config = utils.get_config()
    price = utils.get_coin_price_usd(symbol.upper())
    click.echo(f"{price} USD")

@click.command(help="Swap ERC20 tokens using Uniswap V3. Use format `swap WETH=0.1 USDC <wallet_alias>`, `swap USDT ETH=0.01 <wallet_address>`")
@click.argument('in_token')
@click.argument('out_token')
@click.argument('wallet')
@click.option('--estimate', '-e', is_flag=True, default=False, help="Estimate transactions")
@click.option('--send', '-s', is_flag=True, default=False, help="Sing and send transactions")
def swap(in_token, out_token, wallet, estimate, send):
    wallet_address = utils.get_wallet_address(wallet)
    try:
        manager = UniswapManager(utils.get_config())
        _, in_erc20, _, in_native_amount = cli_utils.split_token_amount(in_token)
        _, out_erc20, _, out_native_amount = cli_utils.split_token_amount(out_token)
        manager.swap(in_erc20, out_erc20, in_native_amount, out_native_amount, wallet_address, 
            False if estimate else send
        )
    except UniswapManagerError as e:
        click.echo(str(e))
        exit(1)

@click.command("open-position", help="Open position")
@click.argument('token1')
@click.argument('token2')
@click.argument('fee_tier')
@click.argument('wallet')
@click.option('--estimate', '-e', is_flag=True, default=False, help="Estimate transactions")
@click.option('--send', '-s', is_flag=True, default=False, help="Sing and send transactions")
def open_position(token1, token2, fee_tier, wallet, estimate, send):
    wallet_address = utils.get_wallet_address(wallet)
    try:
        manager = UniswapManager(utils.get_config())
        _, token1_erc20, _, token1_native_amount = cli_utils.split_token_amount(token1)
        _, token2_erc20, _, token2_native_amount = cli_utils.split_token_amount(token2)
        manager.open_position(token1_erc20, token2_erc20, token1_native_amount, token2_native_amount, 
            int(fee_tier), wallet_address, False if estimate else send
        )
    except UniswapManagerError as e:
        click.echo(str(e))
        exit(1)

@click.command(help="Prints network info")
def net():
    config = utils.get_config()
    web3 = web3_utils.get_web3(config)
    click.echo(f"Connection: {'🟢 Connected' if web3.is_connected() else '🔴 No connection'}")
    click.echo(f"Gas price: {web3.from_wei(web3.eth.gas_price, 'gwei'):.2f} Gwei")
    click.echo(f"Chain ID: {web3.eth.chain_id}")
    click.echo(f"Web3 version: {web3.api}")
    click.echo(f"Client version: {web3.client_version}")

cli.add_command(net)
cli.add_command(balance)
cli.add_command(positions)
cli.add_command(price)
cli.add_command(swap)
cli.add_command(open_position)


if __name__ == '__main__':
    cli()