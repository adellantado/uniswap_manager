from functools import wraps
import hashlib

from web3 import Web3

from entity.cachable import Cachable
from entity.pickle_cache import PickleCache


def to_checksum_address(*arg_nums):
    """
    A decorator to convert specified string arguments to their checksum address format using Web3.

    Args:
        *arg_nums (int): Variable length argument list specifying the positions of the arguments 
                         that need to be converted to checksum addresses.

    Returns:
        function: A wrapper function that processes the specified arguments and keyword arguments 
                  to convert them to checksum addresses before calling the original function.

    Example:
        @to_checksum_address(0, 2)
        def example_function(arg1, arg2, arg3):
            pass

        In this example, arg1 and arg3 will be converted to checksum addresses if they are strings.
    """
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
                k: (
                    Web3.to_checksum_address(v)
                    if "address" in k.lower() and isinstance(v, str)
                    else v
                )
                for k, v in kwargs.items()
            }
            return func(*new_args, **new_kwargs)

        return wrapper

    return inner_to_checksum_address


def cache(name: str):
    """
    A decorator that caches the result of a function using a specified cache name.

    Args:
        name (str): The name of the cache to use.

    Returns:
        function: The decorated function with caching enabled.

    The decorator uses a hash of the function name and its arguments to create a unique key for each function call.
    If the result of the function call is already cached, it returns the cached result.
    Otherwise, it calls the function, caches the result, and then returns the result.

    Example:
        @cache('my_cache')
        def my_function(arg1, arg2):
            # function implementation
            pass
    """
    def inner_cache(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            hashed_args = [func.__name__]
            hashed_args += [
                arg.get_hash() if isinstance(arg, Cachable) else str(arg)
                for arg in list(args) + list(kwargs.values())
            ]
            hash_key = hashlib.sha256("".join(hashed_args).encode()).hexdigest()
            pickle_cache = PickleCache.get_instance(name)
            if pickle_cache.has(hash_key):
                return pickle_cache.get(hash_key)
            result = func(*args, **kwargs)
            pickle_cache.set(hash_key, result)
            return result

        return wrapper

    return inner_cache
