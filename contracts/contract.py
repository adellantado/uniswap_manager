from __future__ import annotations
from dataclasses import dataclass
from typing import Any

from web3 import Web3

import utils.utils as utils
from entity.cachable import Cachable
from entity.config import Config


@dataclass
class BatchStruct():
    contract: Contract = None
    func_name: str = None
    args: list = None
    result: Any = None
    func_obj: Any = None


class Contract(Cachable):
    """
    Contract class for interacting with Ethereum smart contracts using Web3.py.

    Attributes:
        web3 (Web3): An instance of Web3.
        contract_instances (dict[str, Contract]): A dictionary to store contract instances.

    Methods:
        __init__(contract_address: str, abi_path: str):
            Initializes the Contract instance with the given contract address and ABI path.
        
        sync(num_of_calls: int=1) -> Contract:
            Sets the number of calls to sync and returns the Contract instance.
        
        call_view_func(contract_function: str, *args) -> Any:
            Calls a view function on the contract and caches the result.
        
        set_nonce(nonce: int) -> Contract:
            Sets the nonce for transactions and returns the Contract instance.
        
        get_nonce(wallet_address: str) -> int:
            Gets the nonce for the given wallet address.
        
        sign_and_send_tx(tx, wallet: str):
            Signs and sends a transaction using the given wallet.
        
        get_tx_receipt(tx_hash):
            Gets the transaction receipt for the given transaction hash.
        
        get_hash():
            Returns the contract address as the hash.
    """

    web3: Web3 = None 

    config: Config = Config.get_singleton()

    contract_instances: dict[str, Contract] = {}

    def __init__(self, contract_address: str, abi_path: str):
        self.contract_address = Web3.to_checksum_address(contract_address)
        self.abi = utils.load_abi(abi_path)
        self.contract = self.web3.eth.contract(address=self.contract_address, abi=self.abi)
        self._sync_allowed = True
        self._sync_num_of_calls = 0
        self._nonce = None
        self._batch = None

    def sync(self, num_of_calls: int=1) -> Contract:
        self._sync_num_of_calls = num_of_calls
        return self

    def call_view_func(self, contract_function: str, *args) -> Any:
        cache_key = hash(tuple(args+(contract_function+'_data',)))
        if self._batch:
            self._batch.func_name = contract_function
            self._batch.args = args
            self._batch.contract = self
        if self._sync_num_of_calls > 0 or not self.__dict__.get(cache_key, None):
            contract_function_obj = self.contract.functions[contract_function](*args)
            if self._batch:
                batch = self._batch
                self._batch.func_obj = contract_function_obj
                self._batch = None
                # returns BatchStruct if we need to process the result later
                return batch
            data = contract_function_obj.call()
            self.__dict__[cache_key] = utils.map_contract_result(self.abi, contract_function, data)
            self._sync_num_of_calls -= 1
        result = self.__dict__[cache_key]
        if self._batch:
            self._batch.result = result
            self._batch = None
        return result
    
    def batch_or_get_cache(self, batch: BatchStruct) -> Contract:
        self._batch = batch
        return self

    def set_nonce(self, nonce: int) -> Contract:
        self._nonce = nonce
        return self

    def get_nonce(self, wallet_address: str) -> int:
        return self._nonce if self._nonce else self.web3.eth.get_transaction_count(wallet_address)

    def sign_and_send_tx(self, tx, wallet: str):
        return utils.sign_and_send_tx(self.web3, tx, wallet)

    def get_tx_receipt(self, tx_hash):
        return self.web3.eth.wait_for_transaction_receipt(tx_hash)

    def __eq__(self, other: Contract):
        return self.contract_address == other.contract_address

    def get_hash(self):
        return self.contract_address