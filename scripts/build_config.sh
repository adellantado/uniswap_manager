#!/bin/bash
export $(cat ../.env)
sed -i -e "s@<RPC_URL>@$RPC_URL@" \
    -i -e "s@<LPACC_ADDRESS>@$LPACC_ADDRESS@" \
    -i -e "s@<ETH1_ADDRESS>@$ETH1_ADDRESS@" \
    -i -e "s@<LPACC_KEY>@$LPACC_KEY@" \
    -i -e "s@<ETH1_KEY>@$ETH1_KEY@" ../config/config.json

