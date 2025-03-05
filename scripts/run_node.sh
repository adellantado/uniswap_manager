#!/bin/bash
export $(cat ../.env)
anvil --fork-url $FORK_RPC