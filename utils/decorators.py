from functools import wraps

from web3 import Web3


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