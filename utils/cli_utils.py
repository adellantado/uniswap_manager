import utils.utils as utils
from contracts.erc20 import ERC20
from contracts.contract import Contract


def split_token_amount(token: str) -> tuple[str, Contract, float, int]:
    """
    Splits a token string into its components and converts the amount to the native token amount.

    Args:
        token (str): The token string in the format 'TOKEN=amount'. If no amount is provided, defaults to 0.

    Returns:
        tuple[str, Contract, float, int]: A tuple containing:
            - The token symbol (str)
            - The ERC20 contract instance (Contract)
            - The amount as a float (float)
            - The native token amount as an integer (int)
    """
    token, amount = split_coin_name_and_amount(token)
    if token.upper() == 'ETH':
        token = 'WETH'
    token_address = utils.get_token_address(token)
    erc20 = ERC20.get_instance(token_address)
    native_amount = int(amount * 10**erc20.get_decimals())
    return token, erc20, amount, native_amount

def split_coin_name_and_amount(coins: str) -> tuple[str, float]:
    amount = 0
    if '=' in coins:
        coins, amount = coins.split('=')
        amount = float(amount.strip())
        coins = coins.strip().upper()
    return coins, amount