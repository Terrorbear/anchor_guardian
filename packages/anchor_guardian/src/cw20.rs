use cosmwasm_std::{Binary, Decimal, Uint128};
use cw20::Cw20ReceiveMsg;
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};
use std::fmt;
use cw0::Expiration;

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, JsonSchema)]
pub struct InstantiateMsg {
    pub owner: String,
}

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, JsonSchema)]
#[serde(rename_all = "snake_case")]
pub enum ExecuteMsg {

    //admin funcs
    WhitelistCw20{address: String},
    UpdateConfig {owner: String},

    //user funcs
    //give guardian contract spend allowance to dump/payoff anchor loan
    AddGuardian { cw20_address: String, amount: Uint128},
    
    //liquidator funcs
    LiquidateCollateral { address: String },
}

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, JsonSchema)]
#[serde(rename_all = "snake_case")]
pub enum QueryMsg {
    Config {},
    Guardians { address: String },
}

#[derive(Serialize, Deserialize, Clone, PartialEq, JsonSchema)]
pub struct ConfigResponse {
    pub owner: String,
}

