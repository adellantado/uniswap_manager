from web3 import Web3
from web3.exceptions import ContractLogicError  

from contracts.contract import Contract
from contracts.erc20 import ERC20
import utils.web3_utils as web3_utils
import utils.utils as utils
from utils.decorators import to_checksum_address


class BalanceManager:
    """
    A class to manage and retrieve balances of ETH and ERC20 tokens using web3.
    Attributes:
        web3 (Web3): An instance of Web3 initialized with the provided configuration.
    Methods:
        get_eth_balance(wallet_address: str) -> float:
            Retrieves the ETH balance of the specified wallet address.
        get_token_balance(wallet_address: str, token_address: str) -> float:
            Retrieves the balance, decimals, and symbol of the specified ERC20 token for the given wallet address.
    """

    def __init__(self):
        self.web3 = web3_utils.get_web3()
        Contract.web3 = self.web3

    def get_eth_balance(self, wallet_address: str, readable = False) -> float:
        if readable:
            return web3_utils.get_eth_balance(self.web3, wallet_address) / 10**18
        return web3_utils.get_eth_balance(self.web3, wallet_address)
    
    def get_token_balance(self, wallet_address: str, token_address: str) -> float:
        contract = ERC20.get_instance(token_address)
        balance = contract.get_balance(wallet_address)
        decimals = contract.get_decimals()
        symbol = contract.get_symbol()
        return balance, decimals, symbol
    
    @to_checksum_address(1,2)
    def send_eth(self, wallet_address: str, receiver_address: str, amount: float, send: bool = False, raw: bool = False):
        tx = {
            "to": receiver_address,
            "value": int(amount*10**18),
            "gas": 21000,
            "nonce": self.web3.eth.get_transaction_count(wallet_address),
            "gasPrice": web3_utils.get_gas_price(self.web3),
        }
        if raw:
            raw_tx = web3_utils.sign_and_get_raw_tx(self.web3, tx, wallet_address)
            utils.print(f"Transfer {amount} ETH to {receiver_address}")
            utils.print(f"Singed raw transaction:\n{raw_tx}", "info")
        elif send:
            tx_hash = web3_utils.sign_and_send_tx(self.web3, tx, wallet_address)
            utils.print(f"Transaction hash: {tx_hash.hex()}", "success")
        else:
            gas_price = web3_utils.get_gas_price(self.web3)
            eth_price = float(utils.get_coin_price_usd("ETH"))
            try:
                utils.print(f"Transfer {amount} ETH to {receiver_address}")
                gas_units = web3_utils.estimate_tx_gas(self.web3, tx)
                price = self.web3.from_wei(gas_price,"gwei")
                costs = self.web3.from_wei(gas_price * gas_units, "gwei")
                utils.print(
                    f"{str(gas_units)} units for {str(price)} Gwei -> ",
                    f"{str(costs)} Gwei, ",
                    f"{gas_price*gas_units * eth_price / 10**18:.2f}$"
                )
            except ContractLogicError as e:
                utils.print("error: can't estimate gas", "warning") 
    
    def send_token(self, wallet_address: str, receiver_address: str, token: ERC20, amount: int, send: bool = False, raw: bool = False):
        tx = token.transfer(wallet_address, receiver_address, amount)
        if raw:
            raw_tx = web3_utils.sign_and_get_raw_tx(self.web3, tx, wallet_address)
            utils.print(f"Transfer {amount} {token.get_symbol()} to {receiver_address}")
            utils.print(f"Singed raw transaction:\n{raw_tx}", "info")
        elif send:
            tx_hash = web3_utils.sign_and_send_tx(self.web3, tx, wallet_address)
            utils.print(f"Transaction hash: {tx_hash.hex()}", "success")
        else:
            gas_price = web3_utils.get_gas_price(self.web3)
            eth_price = float(utils.get_coin_price_usd("ETH"))
            price = self.web3.from_wei(gas_price,"gwei")
            try:
                utils.print(f"Transfer {amount} {token.get_symbol()} to {receiver_address}")
                gas_units = web3_utils.estimate_tx_gas(self.web3, tx)
                costs = self.web3.from_wei(gas_price * gas_units, "gwei")
                utils.print(
                    f"{str(gas_units)} units for {price:.2f} Gwei -> "
                    f"{costs:.2f} Gwei, "
                    f"{gas_price*gas_units * eth_price / 10**18:.2f}$"
                )
            except ContractLogicError as e:
                utils.print("error: can't estimate gas", "warning") 