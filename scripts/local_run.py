################################################
# imports
################################################

import pandas as pd
import os
import yaml
from terra_sdk.client.lcd import LCDClient
from terra_sdk.core.wasm import MsgStoreCode, MsgInstantiateContract, MsgExecuteContract
from terra_sdk.core.fee import Fee
from terra_sdk.core.bank.msgs import MsgSend
from terra_sdk.key.mnemonic import MnemonicKey
from terra_sdk.client.lcd.api.tx import CreateTxOptions
from terra_sdk.client.localterra import LocalTerra
from terra_sdk.core.coins import Coins, Coin
import base64
import json
import pendulum
import subprocess
import argparse

################################################
# parse configs
################################################

contracts_df = pd.read_csv("/repos/metadata69/contracts.tsv", sep="\t")

################################################
# terra objects
################################################

terra = LocalTerra()

wallet1 = terra.wallets["test1"]
wallet2 = terra.wallets["test2"]
wallet3 = terra.wallets["test3"]
wallet4 = terra.wallets["test4"]

worker_wallet = terra.wallets["test7"]


################################################
# deploy func
################################################

def deploy_local_wasm(file_path, wallet, terra):
  with open(file_path, "rb") as fp:
    file_bytes = base64.b64encode(fp.read()).decode()
    store_code_msg = MsgStoreCode(wallet.key.acc_address, file_bytes)
    store_code_tx = wallet.create_and_sign_tx(CreateTxOptions(msgs=[store_code_msg], fee=Fee(6900000, "1000000uluna")))
    store_code_result = terra.tx.broadcast(store_code_tx)

  #persist code_id
  deployed_code_id = store_code_result.logs[0].events_by_type["store_code"]["code_id"][0]

  return deployed_code_id

def init_contract(code_id, init_msg, wallet, terra):

  #invoke contract instantiate
  instantiate_msg = MsgInstantiateContract(
    wallet.key.acc_address,
    wallet.key.acc_address,
    code_id,
    init_msg,
    {"uluna": 1000000, "uusd": 1000000},
  )

  #there is a fixed UST fee component now, so it's easier to pay fee in UST
  instantiate_tx = wallet.create_and_sign_tx(CreateTxOptions(msgs=[instantiate_msg], fee=Fee(5000000, "1000000uusd")))
  instantiate_tx_result = terra.tx.broadcast(instantiate_tx)

  return instantiate_tx_result


def execute_msg(address, msg, wallet, terra, coins=None):

  execute_msg = MsgExecuteContract(
    sender=wallet.key.acc_address,
    contract=address,
    execute_msg=msg,
    coins=coins 
  )

  #there is a fixed UST fee component now, so it's easier to pay fee in UST
  tx = wallet.create_and_sign_tx(CreateTxOptions(msgs=[execute_msg], fee=Fee(2000000, "10000000uusd")))
  tx_result = terra.tx.broadcast(tx)

  return tx_result

def bank_msg_send(recipient, amount, wallet, terrra):

  bank_msg = MsgSend(
    from_address=wallet.key.acc_address,
    to_address=recipient,
    amount=amount,
  )

  #there is a fixed UST fee component now, so it's easier to pay fee in UST
  tx = wallet.create_and_sign_tx(CreateTxOptions(msgs=[bank_msg], fee=Fee(2000000, "10000000uusd")))
  tx_result = terra.tx.broadcast(tx)

  return tx_result


################################################
# deploy code id
################################################

cw20_guardian_code_id = deploy_local_wasm("/repos/anchor_guardian/artifacts/anchor_guardian_cw20.wasm", wallet1, terra)
multisig_code_id = deploy_local_wasm("/repos/cw3_fixed_multisig.wasm", wallet1, terra)
smart_wallet_code_id = deploy_local_wasm("/repos/smart_wallet/artifacts/smartwallet_wallet.wasm", wallet1, terra)
cw20_code_id = contracts_df[contracts_df["name"]=="lp_token"]["code_id"].values[0]

################################################
# init guardian
################################################

market_contract = contracts_df[contracts_df["name"]=="market"]["deployed_address"].values[0]
overseer_contract = contracts_df[contracts_df["name"]=="overseer"]["deployed_address"].values[0]
liquidation_contract = contracts_df[contracts_df["name"]=="liquidation"]["deployed_address"].values[0]
oracle_contract = contracts_df[contracts_df["name"]=="oracle"]["deployed_address"].values[0]

init_msg = {
  "owner": wallet1.key.acc_address,
  "anchor_market_contract": market_contract,
  "anchor_overseer_contract": overseer_contract,
  "anchor_liquidation_contract": liquidation_contract,
  "anchor_oracle_contract": oracle_contract,
  "liquidator_fee": "0.03",
}

guardian_result = init_contract(cw20_guardian_code_id, init_msg, wallet1, terra)
guardian_address = guardian_result.logs[0].events_by_type["instantiate_contract"]["contract_address"][0]

################################################
# run init that spawns a multisig
################################################

reward_contract = contracts_df[contracts_df["name"]=="reward"]["deployed_address"].values[0]

init_msg = {
  "spawn_multi_sig":{
    "hot_wallets": [
      {
        "address": worker_wallet.key.acc_address,
        "label": "farmer",
        "gas_cooldown": 1000,
        "gas_tank_max": "100000000",
        "whitelisted_messages": [0, 1, 2],
      }
    ],
    "whitelisted_contracts":[
      {"address": market_contract, "label": "anchor_market", "code_id": 	226},
      {"address": reward_contract, "label": "bluna_reward", "code_id": 220},
    ],
    "max_voting_period_in_blocks": 100,
    "required_weight": 2,
    "multisig_voters": [
      {"addr": wallet1.key.acc_address, "weight": 1},
      {"addr": wallet2.key.acc_address, "weight": 1},
      {"addr": wallet3.key.acc_address, "weight": 1},
    ],
    "cw3_code_id": int(multisig_code_id),
  }
}

smart_wallet_result = init_contract(smart_wallet_code_id, init_msg, wallet1, terra)
smart_wallet_address = smart_wallet_result.logs[0].events_by_type["instantiate_contract"]["contract_address"][0]
cw3_address = terra.wasm.contract_query(smart_wallet_address, {"config":{}})["cw3_address"]

funding_result = bank_msg_send(smart_wallet_address, "1000000000uusd", wallet1, terra)

################################################
# bond luna for bluna
################################################

hub_contract = contracts_df[(contracts_df["protocol"] == "basset")&(contracts_df["name"]=="hub")]["deployed_address"].values[0]
bluna_contract = contracts_df[contracts_df["name"]=="bluna"]["deployed_address"].values[0]

DECIMALS=1000000
num_luna = 1000

message = {"bond": {}}
coins = Coins.from_str(f"{num_luna*DECIMALS}uluna")
result = execute_msg(hub_contract, message, wallet2, terra, coins)

transfer_msg = {
  "transfer":{
    "recipient": smart_wallet_address,
    "amount": "500000000"
  }
}

transfer_result = execute_msg(bluna_contract, transfer_msg, wallet2, terra)

################################################
# make, vote, execute proposals to deposit/lock collateral
################################################


custody_contract = contracts_df[contracts_df["name"]=="bluna_custody"]["deployed_address"].values[0]
bluna_to_deposit = 1000000

deposit_collateral_core_msg = json.dumps({
  "send":{
    "contract": custody_contract,
    "amount": str(bluna_to_deposit),
    "msg": base64.b64encode(json.dumps({"deposit_collateral":{}}).encode("utf-8")).decode("utf-8"),
  }
})


deposit_collateral_msg = json.dumps({
  "execute":{
    "command":{
      "wasm":{
        "execute":{
          "contract_addr": bluna_contract,
          "funds": [],
          "msg": base64.b64encode(deposit_collateral_core_msg.encode("utf-8")).decode("utf-8"),
        }
      }
    }
  }
})


lock_collateral_core_msg = json.dumps({
  "lock_collateral":{
    "collaterals":[
      [bluna_contract, str(bluna_to_deposit)]
    ]
  }
})

lock_collateral_msg = json.dumps({
  "execute":{
    "command":{
      "wasm":{
        "execute":{
          "contract_addr": overseer_contract,
          "funds": [],
          "msg": base64.b64encode(lock_collateral_core_msg.encode("utf-8")).decode("utf-8"),
        }
      }
    }
  }
})

message = {
  "propose":{
    "title": "test",
    "description": "test69",
    "msgs":[
      {
        "wasm": {
          "execute":{
            "contract_addr": smart_wallet_address, 
            "funds": [],
            "msg": base64.b64encode(deposit_collateral_msg.encode("utf-8")).decode("utf-8"),
          }
        }
      },

      {
        "wasm": {
          "execute":{
            "contract_addr": smart_wallet_address, 
            "funds": [],
            "msg": base64.b64encode(lock_collateral_msg.encode("utf-8")).decode("utf-8"),
          }
        }
      },

      
    ]
  }
}

result = execute_msg(cw3_address, message, wallet3, terra)
proposal_id = int(result.logs[0].events_by_type["wasm"]["proposal_id"][0])

vote_result = execute_msg(cw3_address, {"vote":{"proposal_id":proposal_id, "vote": "yes"}}, wallet1, terra)

execute_result = execute_msg(cw3_address, {"execute":{"proposal_id":proposal_id}}, wallet2, terra)


################################################
# deposit ust, update bluna oracle price, take out loan
################################################

aust_contract = contracts_df[contracts_df["name"]=="aterra"]["deployed_address"].values[0]

message = {
  "deposit_stable":{}
}

num_ust = 1000
coins = Coins.from_str(f"{num_ust*DECIMALS}uusd")
deposit_result = execute_msg(market_contract, message, wallet1, terra, coins)

message = {
  "feed_price":{
    "prices":[
      [bluna_contract, "100.00"]
    ]
  }
}

oracle_result = execute_msg(oracle_contract, message, wallet3, terra)

borrow_core_msg = json.dumps({
  "borrow_stable":{
    "borrow_amount": "75000000"
  }
})

borrow_msg = json.dumps({
  "execute":{
    "command":{
      "wasm":{
        "execute":{
          "contract_addr": market_contract,
          "funds": [],
          "msg": base64.b64encode(borrow_core_msg.encode("utf-8")).decode("utf-8"),
        }
      }
    }
  }
})


message = {
  "propose":{
    "title": "test",
    "description": "test69",
    "msgs":[
      {
        "wasm": {
          "execute":{
            "contract_addr": smart_wallet_address, 
            "funds": [],
            "msg": base64.b64encode(borrow_msg.encode("utf-8")).decode("utf-8"),
          }
        }
      },
      
    ]
  }
}

result = execute_msg(cw3_address, message, wallet3, terra)
proposal_id = int(result.logs[0].events_by_type["wasm"]["proposal_id"][0])

vote_result = execute_msg(cw3_address, {"vote":{"proposal_id":proposal_id, "vote": "yes"}}, wallet1, terra)

execute_result = execute_msg(cw3_address, {"execute":{"proposal_id":proposal_id}}, wallet2, terra)

################################################
# setup cw20 shitcoin as guardian 
################################################



#create cw20
init_cw20 = {
  "name": "shit coin",
  "symbol": "SHIT",
  "decimals": 6,
  "initial_balances":[
    {
      "address": smart_wallet_address,
      "amount": "69000000",
    },
    {
      "address": wallet2.key.acc_address,
      "amount": "1000000000000",
    },
  ],
  "mint":{
    "minter": wallet2.key.acc_address,
  }
}

init_result = init_contract(cw20_code_id, init_cw20, wallet2, terra)
shitcoin_address = init_result.logs[0].events_by_type["instantiate_contract"]["contract_address"][0]

#create astroport liquidity pool
factory_contract = contracts_df[(contracts_df["protocol"] == "astroport")&(contracts_df["name"]=="factory")]["deployed_address"].values[0]

message = {
  "create_pair":
  {
    "pair_type": { "xyk":{}},
    "asset_infos":
    [
      { "token": {"contract_addr": shitcoin_address}},
      { "native_token": {"denom": "uusd"}},
    ],
  }
}

result = execute_msg(factory_contract, message, wallet1, terra)
lp_token_address = result.logs[0].events_by_type["wasm"]["liquidity_token_addr"][0]
pair_address = result.logs[0].events_by_type["wasm"]["pair_contract_addr"][0]

#provide liquidity

DECIMALS=1000000
num_shitcoin = 10000
num_ust = 100000

message = {
  "increase_allowance":{
    "spender": pair_address,
    "amount": str(num_shitcoin*DECIMALS),
  }
}

allowance_result = execute_msg(shitcoin_address, message, wallet2, terra)

message = {
  "provide_liquidity":
  {
    "assets":
    [
      {
        "info": {"token": {"contract_addr": shitcoin_address}},
        "amount": str(num_shitcoin*DECIMALS)
      },
      {
        "info": {"native_token": {"denom": "uusd"}},
        "amount": str(num_ust*DECIMALS)
      },
    ]
  }
}
coins = Coins.from_str(f"{num_ust*DECIMALS}uusd")
result = execute_msg(pair_address, message, wallet2, terra, coins)

#add whitelist shitcoin
message = {
  "whitelist_cw20": shitcoin_address
}

whitelist_result = execute_msg(guardian_address, message, wallet1, terra)


guardian_core_msg = json.dumps({
  "add_guardian":{
    "cw20_address": shitcoin_address,
    "amount": "69000000",
    "pair_address": pair_address
  }
})

guardian_msg = json.dumps({
  "execute":{
    "command":{
      "wasm":{
        "execute":{
          "contract_addr": guardian_address,
          "funds": [],
          "msg": base64.b64encode(guardian_core_msg.encode("utf-8")).decode("utf-8"),
        }
      }
    }
  }
})


message = {
  "propose":{
    "title": "test",
    "description": "test69",
    "msgs":[
      {
        "wasm": {
          "execute":{
            "contract_addr": smart_wallet_address, 
            "funds": [],
            "msg": base64.b64encode(guardian_msg.encode("utf-8")).decode("utf-8"),
          }
        }
      },
      
    ]
  }
}

result = execute_msg(cw3_address, message, wallet3, terra)
proposal_id = int(result.logs[0].events_by_type["wasm"]["proposal_id"][0])

vote_result = execute_msg(cw3_address, {"vote":{"proposal_id":proposal_id, "vote": "yes"}}, wallet1, terra)

execute_result = execute_msg(cw3_address, {"execute":{"proposal_id":proposal_id}}, wallet2, terra)


guardian_result = execute_msg(guardian_address, message, )

################################################
# reset oracle price, invoke guardian liquidation
################################################

wasm_msg = json.dumps({
            "upsert_hot":{
              "hot_wallet": {
                "address": wallet4.key.acc_address,
                "label": "farmer",
                "gas_cooldown": 1000,
                "gas_tank_max": "100000000",
                "whitelisted_messages": [1],
              }
            }
})

message = {
  "propose":{
    "title": "test33",
    "description": "test6933",
    "msgs":[{
        "wasm": {
          "execute":{
            "contract_addr": smart_wallet_address,
            "funds": [],
            "msg": base64.b64encode(wasm_msg.encode("utf-8")).decode("utf-8"),
          }
        }
      }
    ]
  }
}

result = execute_msg(cw3_address, message, wallet3, terra)
proposal_id = int(result.logs[0].events_by_type["wasm"]["proposal_id"][0])

vote_result = execute_msg(cw3_address, {"vote":{"proposal_id":proposal_id, "vote": "yes"}}, wallet1, terra)

execute_result = execute_msg(cw3_address, {"execute":{"proposal_id":proposal_id}}, wallet2, terra)
