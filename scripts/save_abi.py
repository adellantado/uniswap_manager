import requests
import json
import os
from dotenv import load_dotenv
import sys

def etherscan_get_abi(contract_address, api_key):
    """
    Get contract ABI from Etherscan API.
    
    :param contract_address: Ethereum contract address
    :param api_key: Etherscan API key
    :return: Contract ABI (list)
    """
    url = f'https://api.etherscan.io/v2/api?chainid=1&module=contract&action=getabi&address={contract_address}&apikey={api_key}'
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        return data['result']
    else:
        print(f"❌ Error: {response.json()}")


load_dotenv('../.env')
address = sys.argv[2]
res = etherscan_get_abi(address, os.getenv('ETHERSCAN_TOKEN'))
with open(f'../abi/{sys.argv[1]}.json', 'w') as f:
    json.dump(json.loads(res), f, indent=4)
print(f"ABI saved to abi/{sys.argv[1]}.json")