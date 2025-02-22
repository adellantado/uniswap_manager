import json

from uniswap_manager import UniswapManager


if __name__ == "__main__":
    with open("config.json", "r") as f:
        config = json.load(f)
    manager = UniswapManager(config)
    manager.fetch_positions()