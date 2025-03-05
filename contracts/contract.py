from __future__ import annotations
from typing import Any

from web3 import Web3

import utils.web3_utils as web3_utils


class Contract():

    web3: Web3 = None 

    contract_instances: dict[str, Contract] = {}

    def __init__(self, contract_address: str, abi_path: str):
        self.contract_address = Web3.to_checksum_address(contract_address)
        self.abi = web3_utils.load_abi(abi_path)
        self.contract = self.web3.eth.contract(address=self.contract_address, abi=self.abi)
        self._sync_allowed = True
        self._sync_num_of_calls = 0
        self._nonce = None

    def sync(self, num_of_calls: int=1) -> Contract:
        self._sync_num_of_calls = num_of_calls
        return self

    def call_view_func(self, contract_function: str, *args) -> Any:
        cache_key = hash(tuple(args+(contract_function+'_data',)))
        if self._sync_num_of_calls > 0 or not self.__dict__.get(cache_key, None):
            data = self.contract.functions[contract_function](*args).call()
            self.__dict__[cache_key] = web3_utils.map_contract_result(self.abi, contract_function, data)
            self._sync_num_of_calls -= 1
        return self.__dict__[cache_key]

    def set_nonce(self, nonce: int) -> Contract:
        self._nonce = nonce
        return self

    def get_nonce(self, wallet_address: str) -> int:
        return self._nonce if self._nonce else self.web3.eth.get_transaction_count(wallet_address)

    def sign_and_send_tx(self, tx, wallet: str):
        return web3_utils.sign_and_send_tx(self.web3, tx, wallet)

    def get_tx_receipt(self, tx_hash):
        return self.web3.eth.wait_for_transaction_receipt(tx_hash)

