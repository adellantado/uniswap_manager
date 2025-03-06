import time
import requests
import json

# Define API URL
url = "https://api.coingecko.com/api/v3/coins/markets"

# Define query parameters
params = {
    "vs_currency": "usd",  # Get prices in USD
    "category": "ethereum-ecosystem",  # ERC-20 tokens
    "order": "market_cap_desc",  # Sort by market cap
    "per_page": 100,  # Number of tokens to retrieve
    "page": 1,
    "sparkline": "false"
}

# Make the API request
response = requests.get(url, params=params)
tokens = response.json()

# Fetch contract addresses for each token
token_addresses = {}   

# for token in tokens:
i = 0
while i < len(tokens):
    token = tokens[i]
    token_id = token["id"]
    token_symbol = token["symbol"].upper()
    token_details_url = f"https://api.coingecko.com/api/v3/coins/{token_id}"

    details_response = requests.get(token_details_url)
    details = details_response.json()

    # Extract contract address (only if available)
    contract_address = details.get("platforms", {}).get("ethereum")

    if contract_address:  # Only add if an Ethereum contract address exists
        token_addresses[token_symbol] = contract_address

    if details_response.status_code != 200:
        print(f"Failed to fetch details for {token_symbol} ({token_id})\nset timeout to 30 seconds and try again...")
        time.sleep(30)
    else:
        with open("coins.txt", "w") as f:
            f.write(json.dumps(token_addresses))
        i += 1
        time.sleep(2)