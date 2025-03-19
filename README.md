# 🪙 BUM - CLI helper in managing Ethereum and Uniswap 🦄 assets 


## Usage ⬇️

1. Edit `config.json`. 
- Add wallet addresses with Uniswap positions under `wallet.addresses` field. 
- Add private key paths under `wallet.keys` field. 
- Quicknode or Infura url under `network.rpc` field.

2. `python3 -m venv .venv`
3. `source venv/bin/activate`
4. `pip install --editable .`


## Commands ⬇️

```
  add-liquidity     Add liquidity to a Uniswap V3 pool
  balance           Prints balance of ETH/ERC20 token for addresses in the config
  close-position    Close Uniswap V3 position
  collect-fees      Collect fees from Uniswap V3 position
  net               Prints network info
  open-position     Open Uniswap V3 position
  positions         Prints Uniswap V3 positions for addresses in the config
  price             Prints Binance price of a given coin in USD
  remove-liquidity  Decrease liquidity from Uniswap V3 position
  send              Send ETH/ERC20 tokens to another wallet
  send-raw-tx       Send raw transaction
  swap              Swap ERC20 tokens using Uniswap V3.
```

### 1. Wallet balance 👛

```
Usage: bum balance [OPTIONS]

  Prints balance of ETH/ERC20 token for addresses in the config

Options:
  -w, --wallet TEXT  Ethereum wallet address/alias to get balance for
  --erc20 TEXT       ERC20 token address/name to get balance for
  -a, --all          Balance of all known tokens from the config. Overlaps --erc20 option
  --help             Show this message and exit.
```
Example:
>bum balance -a

>Wallet: test_addr<br>
0.99989471688899 ETH, 1877.79 USD<br>
0.0 WETH, 0.00 USD<br>
1897.925291 USDC, 1897.93 USD<br>
100.0 USDT, 100.00 USD

### 2. Price 💲

```
Usage: bum price [OPTIONS] [SYMBOL]

  Prints Binance price of a given coin in USD

Options:
  --help  Show this message and exit.
```
Example:
>bum price ETH

>1936.80961179 USD

### 3. Print uniswap positions 🖨

```
Usage: bum positions [OPTIONS]

  Prints Uniswap V3 positions for addresses in the config

Options:
  --help  Show this message and exit.
```
Example:
>bum positions

>Wallet: test_addr
>
>Locked:  77.25509729254254 USDC 0.04489450445888164 WETH <br>
Fees:  1.7803438428622809 USDC 0.0006890496127918755 WETH <br>
Position 921111 (USDC/WETH 0.30%) APY: 51.00%, 13 days, 195.74$ deposit, 3.60$ fee

### 4. Swap tokens 💱
```
Usage: bum swap [OPTIONS] IN_TOKEN OUT_TOKEN WALLET

  Swap ERC20 tokens using Uniswap V3. Use format `swap WETH=0.1 USDC
  <wallet_alias>`, `swap USDT ETH=0.01 <wallet_address>`

Options:
  -e, --estimate  Estimate fee tier
  -s, --send      Sing and send transactions
  -r, --raw       Sing and return raw transaction
  --help          Show this message and exit.
```
Example:
>bum swap ETH=1.2 USDC test_addr -e

>Pool 0.01% output amount = 2318.718975 USDC with gas 93138 units<br>
>Pool 0.05% output amount = 2317.416884 USDC with gas 84856 units<br>
>Pool 0.3% output amount = 2307.662359 USDC with gas 84910 units<br>
>Pool 1.0% output amount = 2267.983816 USDC with gas 122395 units<br>
>Transactions: 3<br>
>1.  Wrap 1.2 ETH to WETH:<br>
>45038 units for 1.13 Gwei -> 50847.96 Gwei, 0.10$<br>
>2.  Approve spender to spend 1.2 WETH:<br>
>46052 units for 1.13 Gwei -> 51992.77 Gwei, 0.10$<br>
>3.  Swap 1.2 WETH to USDC:<br>
>93138 units for 1.13 Gwei -> 105152.92 Gwei, 0.20$

### 5. Open position 🏦
```
Usage: bum open-position [OPTIONS] TOKEN1 TOKEN2 FEE_TIER WALLET

  Open position

Options:
  -e, --estimate  Estimate transactions
  -s, --send      Sing and send transactions
  -r, --raw       Sing and return raw transaction
  --help          Show this message and exit.
```

### 6. Show network info  ℹ️
```
Usage: bum net [OPTIONS]

  Prints network info

Options:
  --help  Show this message and exit.
```
Example:
>bum net

>Connection: 🟢 Connected<br>
>Gas price: 2.13 Gwei<br>
>Chain ID: 1<br>
>Web3 version: 7.8.0<br>
>Client version: anvil/v1.0.0

### 7. Send crypto 🚚
```
Usage: bum send [OPTIONS] TOKEN WALLET_FROM WALLET_TO

  Send ETH/ERC20 tokens to another wallet e.g.(bum send ETH=0.1 <wallet_alias>
  <wallet_address>)

Options:
  -e, --estimate  Estimate transactions
  -s, --send      Sing and send transactions
  -r, --raw       Sing and return raw transaction
  --help          Show this message and exit.
```
Example:
>bum send USDC=100.23 test_addr 0x70997970C51812dc3A010C7d01b50e0d17dc79C8 -s

>Transaction hash: b416fcd675b9cdb2e1fd2718b0cc85f8eb289595e741bc6aaba83eeb8de8e3eb

### 8. Close position 🗑
```
Usage: bum close-position [OPTIONS] POSITION_ID

  Close Uniswap V3 position

Options:
  -e, --estimate  Estimate transactions
  -s, --send      Sing and send transactions
  -r, --raw       Sing and return raw transaction
  --help          Show this message and exit.
```

### 9. Add liquidity 📥
```
Usage: bum add-liquidity [OPTIONS] TOKEN1 TOKEN2 POSITION_ID WALLET

  Add liquidity to a Uniswap V3 pool

Options:
  -e, --estimate  Estimate transactions
  -s, --send      Sing and send transactions
  -r, --raw       Sing and return raw transaction
  --help          Show this message and exit.
```

### 10. Collect fees 📤
```
Usage: bum collect-fees [OPTIONS] POSITION_ID

  Collect fees from Uniswap V3 position

Options:
  -e, --estimate  Estimate transactions
  -s, --send      Sing and send transactions
  -r, --raw       Sing and return raw transaction
  --help          Show this message and exit.
```

### 11. Remove liquidity ➖
```
Usage: bum remove-liquidity [OPTIONS] POSITION_ID

  Decrease liquidity from Uniswap V3 position

Options:
  -percent, -p TEXT  Percentage of liquidity to remove, from 1 to 100
                     [required]
  -e, --estimate     Estimate transactions
  -s, --send         Sing and send transactions
  -r, --raw          Sing and return raw transaction
  --help             Show this message and exit.
```

### 12. Send raw transaction 🎯
```
Usage: bum send-raw-tx [OPTIONS] TX

  Send raw transaction

Options:
  --help  Show this message and exit.
```
Example:
>bum send-raw-tx f86d82037d844ce4f0628252089470997970c51812dc3a010c7d01b50e0d17dc79c8880de0b6b3a7640000801ca0745c07257970392e9a2ab20298a372a36bc57a7d2a75209a2d74609a10b8fe92a0449a4cf94d594a205a85e524f3513f4c6c323be60843de3f6459d2f3cf16da1a

>Transaction hash: b19535a0944219629addb2b29d5a9dfcb9c31c4c64cc1f6e867a1b27dab52696

## Encoding private keys ⬇️

> [!TIP]
> Good practice is to encode private keys with `gpg` and provide `config.json` with paths of encoded keys `.gpg` or `.asc` extensions. 

example:

```
"keys": {
  "lpacc": "keys/private_key1.gpg",
  "eth1": "keys/private_key2.asc"
}
```

By providing keys with these extensions in the `config.json` the script will call local `gpg` with pass phrase promting to allow any signing activity.   
You can encode your keys with GPA, Kleopatra or similar apps.
