from __future__ import annotations
import json


class Config():

    instance = None

    def __init__(self):
        with open("config/config.json", "r") as f:
            self.config = json.load(f)

    @staticmethod
    def get_singleton() -> Config:
        if Config.instance is None:
            Config.instance = Config()
        return Config.instance

    def to_dict(self) -> dict:
        return self.config

    # Network

    @property
    def is_prod(self) -> bool:
        return self.config["network"].get("prod", True)
    
    @property
    def rpc_url(self) -> str:
        """
        RPC provider URL (QuickNode, Infura, etc.).

        Returns:
            str: The RPC URL specified in the network configuration.
        """
        return self.config["network"]["rpc"]
    
    @property
    def history_from_block(self) -> int:
        return self.config["network"]["from_block"]
    
    # Tokens

    @property
    def erc20_tokens(self) -> dict:
        """
        Tokens recognized by the app, allows to manipulate with names instead of addresses.
        Fill with the tokens you want to use in the app.

        Returns:
            dict: A dictionary containing the ERC20 tokens configuration.
        """
        return self.config['ERC20']['tokens']
    
    # Contracts

    @property
    def uniswap_contracts(self) -> dict:
        return self.config['uniswap']['contracts']
    
    @property
    def uniswap_v3_position_manager(self) -> str:
        return self.config['uniswap']['contracts']['position_manager']
    
    @property
    def uniswap_v3_factory(self) -> str:
        return self.config['uniswap']['contracts']['factory']

    @property
    def uniswap_v3_router(self) -> str:
        return self.config['uniswap']['contracts']['router']
    
    @property
    def uniswap_v3_quoter(self) -> str:
        return self.config['uniswap']['contracts']['quoter']
    
    # Wallet
    
    @property
    def wallet_addresses(self) -> dict:
        """
        Dictinary wallet_alias -> wallet_address. Replace with your own wallet addresses.
        Allows to manipulate with aliases instead of addresses.

        Returns:
            dict: A dictionary containing wallet addresses.
        """
        return self.config["wallet"]["addresses"]
    
    @property
    def private_keys(self) -> dict:
        """
        Add private keys file paths to the wallets. Use encoded keys with local GPG encryption.
        Add file paths with .asc / .gpg extensions. 

        Returns:
            dict: A dictionary containing the private keys from the wallet configuration.
        """
        return self.config["wallet"]["keys"]
    
    @property
    def balance_visible_tokens(self) -> list:
        """
        This list of tokens get used for 'balance' command with --all key.

        Returns:
            list: A list of active ERC20 tokens.
        """
        return self.config["wallet"]["erc20"]["active"]
    
    # Styles

    @property
    def is_styles_active(self) -> bool:
        return self.config["styles"]["active"]
    
    @property
    def is_styles_bright(self) -> bool:
        return self.config["styles"]["bright"]