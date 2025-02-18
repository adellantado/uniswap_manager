
# Lists Uniswap V3 positions with APY

Ouput Example:

```
Wallet: wallet1
Locked:  77.25509729254254 USDC 0.04489450445888164 WETH
Fees:  1.7803438428622809 USDC 0.0006890496127918755 WETH
Position 921111 (USDC/WETH 0.30%) APY: 51.00%, 13 days, 195.74$ deposit, 3.60$ fee
```

## Usage

1. Edit `config.json`. Add wallet addresses with Uniswap positions under `wallet.addresses` field and Quicknode or Infura url under network.rpc field
2. `pip3 install -r requirements.txt`
3. `python3 main.py`