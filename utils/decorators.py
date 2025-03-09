from functools import wraps
import hashlib

from web3 import Web3

from entity.cachable import Cachable
from entity.pickle_cache import PickleCache


def to_checksum_address(*arg_nums):
    def inner_to_checksum_address(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            new_args = []
            # Process positional arguments
            for i, arg in enumerate(args):
                if isinstance(arg, str) and i in arg_nums:
                    new_args.append(Web3.to_checksum_address(arg))
                else:
                    new_args.append(arg)
            # Process keyword arguments
            new_kwargs = {
                k: (Web3.to_checksum_address(v) if "address" in k.lower() and isinstance(v, str) else v)
                for k, v in kwargs.items()
            }
            return func(*new_args, **new_kwargs)
        return wrapper
    return inner_to_checksum_address

def cache(name: str):
    def inner_cache(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            hashed_args = [func.__name__]
            hashed_args += [arg.get_hash() if isinstance(arg, Cachable) else str(arg) 
                for arg in list(args)+list(kwargs.values())]
            hash_key = hashlib.sha256("".join(hashed_args).encode()).hexdigest()
            pickle_cache = PickleCache.get_instance(name)
            if pickle_cache.has(hash_key):
                return pickle_cache.get(hash_key)
            result = func(*args, **kwargs)
            pickle_cache.set(hash_key, result)
            return result
        return wrapper
    return inner_cache