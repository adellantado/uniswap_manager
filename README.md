# BUM - CLI helper in managing Ethereum and Uniswap assets


## Usage

1. Edit `config.json`. 
- Add wallet addresses with Uniswap positions under `wallet.addresses` field. 
- Add private key paths under `wallet.keys` field. 
- Quicknode or Infura url under `network.rpc` field.

2. `python3 -m venv .venv`
3. `source venv/bin/activate`
4. `pip install --editable .`


## Commands

### 1. Wallet balance

```
Usage: bum balance [OPTIONS]

  Prints balance of ETH/ERC20 token for addresses in the config

Options:
  -w, --wallet TEXT  Ethereum wallet address/alias to get balance for
  --erc20 TEXT       ERC20 token address/name to get balance for
  -a, --all          Balance of all known tokens from the config. Overlaps --erc20 option
  --help             Show this message and exit.
```

### 2. Price

```
Usage: bum price [OPTIONS] [SYMBOL]

  Prints Binance price of a given coin in USD

Options:
  --help  Show this message and exit.
```

### 3. Print uniswap positions

```
Usage: bum positions [OPTIONS]

  Prints Uniswap V3 positions for addresses in the config

Options:
  --help  Show this message and exit.
```

```
Ouput Example:

Wallet: wallet1
Locked:  77.25509729254254 USDC 0.04489450445888164 WETH
Fees:  1.7803438428622809 USDC 0.0006890496127918755 WETH
Position 921111 (USDC/WETH 0.30%) APY: 51.00%, 13 days, 195.74$ deposit, 3.60$ fee
```

### 4. Swap tokens
```
Usage: bum swap [OPTIONS] IN_TOKEN OUT_TOKEN WALLET

  Swap ERC20 tokens using Uniswap V3. Use format `swap WETH=0.1 USDC
  <wallet_alias>`, `swap USDT ETH=0.01 <wallet_address>`

Options:
  -e, --estimate  Estimate fee tier
  -s, --send      Sing and send transactions
  --help          Show this message and exit.
```
