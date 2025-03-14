from .contract import Contract
from .erc20 import ERC20
from .uniswap_v3_pool import UniswapV3Pool


class UniswapV3QuoterV2(Contract):

    def __init__(self, config: dict):
        super().__init__(config['uniswap']['contracts']['quoter'], "UniswapV3QuoterV2")

    def quote_exact_input(self, pool: UniswapV3Pool, in_token: ERC20, in_token_amount: int) -> dict:
        if in_token == pool.get_token0():
            token_address_0 = pool.get_token0_address()
            token_address_1 = pool.get_token1_address()
        else:
            token_address_0 = pool.get_token1_address()
            token_address_1 = pool.get_token0_address()
        path = (
            bytes.fromhex(token_address_0[2:]) +
            pool.get_fee_tier().to_bytes(3, byteorder='big') +
            bytes.fromhex(token_address_1[2:])
        )
        return self.call_view_func("quoteExactInput", path, in_token_amount)

    def quote_exact_output(self, pool: UniswapV3Pool, out_token: ERC20, out_token_amount: int) -> dict:
        if out_token == pool.get_token0():
            token_address_0 = pool.get_token0_address()
            token_address_1 = pool.get_token1_address()
        else:
            token_address_0 = pool.get_token1_address()
            token_address_1 = pool.get_token0_address()
        path = (
            bytes.fromhex(token_address_0[2:]) +
            pool.get_fee_tier().to_bytes(3, byteorder='big') +
            bytes.fromhex(token_address_1[2:])
        )
        return self.call_view_func("quoteExactOutput", path, out_token_amount)

    
