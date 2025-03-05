import click

from contracts.erc20 import ERC20
from manager.balance_manager import BalanceManager
from manager.uniswap_manager import UniswapManager
import utils.utils as utils
import utils.web3_utils as web3_utils
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
            if address:
                get_balance_rec(address, None, False)
                for token_name, token_address in config['ERC20']['tokens'].items():
                    get_balance_rec(address, token_address, False)
            else:
                for wallet_alias, wallet_address in config['wallet']['addresses'].items():
                    click.echo(f'Wallet: {wallet_alias}')
                    get_balance_rec(wallet_address, None, False)
                    for token_name, token_address in config['ERC20']['tokens'].items():
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
@click.option('--estimate', '-e', is_flag=True, default=False, help="Estimate fee tier")
@click.option('--send', '-s', is_flag=True, default=False, help="Sing and send transactions")
def swap(in_token, out_token, wallet, estimate, send):
    address = utils.get_wallet_address(wallet)
    manager = UniswapManager(utils.get_config())

    in_amount = 0
    if '=' in in_token:
        in_token, in_amount = in_token.split('=')
        in_amount = float(in_amount.strip())
        in_token = in_token.strip()
    if in_token.upper() == 'ETH':
        in_token = 'WETH'
    in_token_address = utils.get_token_address(in_token)

    out_amount = 0
    if '=' in out_token:
        out_token, out_amount = out_token.split('=')
        out_amount = float(out_amount.strip())
        out_token = out_token.strip()
    if out_token.upper() == 'ETH':
        out_token = 'WETH'
    out_token_address = utils.get_token_address(out_token)

    in_erc20 = ERC20.get_instance(in_token_address)
    out_erc20 = ERC20.get_instance(out_token_address)

    in_amount = int(in_amount * 10**in_erc20.get_decimals())
    out_amount = int(out_amount * 10**out_erc20.get_decimals())

    manager.swap(in_erc20, out_erc20, in_amount, out_amount, address, False if estimate else send)


cli.add_command(balance)
cli.add_command(positions)
cli.add_command(price)
cli.add_command(swap)


if __name__ == '__main__':
    cli()