use cosmwasm_std::{Decimal, Uint128};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, JsonSchema)]
pub struct InstantiateMsg {
    pub owner: String,
    pub anchor_market_contract: String,
    pub anchor_overseer_contract: String,
    pub anchor_liquidation_contract: String,
    pub anchor_oracle_contract: String,
    pub liquidator_fee: Decimal,
}

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, JsonSchema)]
#[serde(rename_all = "snake_case")]
pub enum ExecuteMsg {

    //admin funcs
    WhitelistCw20{address: String},
    UpdateConfig {owner: String},

    //user funcs
    //give guardian contract spend allowance to dump/payoff anchor loan
    AddGuardian { cw20_address: String, pair_address: String},
    
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
    pub anchor_market_contract: String,
    pub anchor_overseer_contract: String,
    pub anchor_liquidation_contract: String,
    pub anchor_oracle_contract: String,
    pub liquidator_fee: Decimal,
}

//smart wallet messages
#[derive(Serialize, Deserialize, Clone, PartialEq, JsonSchema)]
pub struct RepayStable {
    pub amount: Uint128,
}