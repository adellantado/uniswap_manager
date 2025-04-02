from __future__ import annotations
from typing import Callable, cast
import logging

from contracts.contract import Contract, BatchStruct
import utils.utils as utils


logger = logging.getLogger(__name__)


class Batch():

    def __init__(self):
        self.batch = Contract.web3.batch_requests()
        self.output = []

    def add(self, func: Callable[..., object], *args):
        contract = func.__self__
        if not isinstance(contract, Contract):
            raise ValueError("Contract object is required")
        item = BatchStruct()
        contract.batch_or_get_cache(item)
        res = func(*args)
        # check if the result is not in cache
        is_empty_cached_result = isinstance(res, BatchStruct)
        if is_empty_cached_result:
            logger.debug("Batch add function %s", item.func_name)
            self.batch.add(item.func_obj)
        else:
            item.result = res
        self.output.append(item)

    # TODO:
    # 3.fix for @cache decorator
    def execute(self, return_items: bool = False):
        queue = list(filter(lambda item: item.result is None, self.output))
        if queue:
            logger.debug("Batch started")
            res = self.batch.execute()
            for i, data in enumerate(res):
                item = cast(BatchStruct, queue[i])
                item.result = utils.map_contract_result(item.contract.abi, item.func_name, data)
                # add to contract's cache
                cache_key = hash(tuple(item.args+(item.func_name+'_data',)))
                item.contract.__dict__[cache_key] = item.result
                item.contract._sync_num_of_calls -= 1
        if return_items:
            return self.output
        return list(map(lambda item: item.result, self.output))
    
    def clear(self):
        self.batch.clear()
        self.output = []
        logger.debug("Batch is cleared")

    def __enter__(self) -> Batch:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.clear()

