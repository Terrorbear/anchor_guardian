use cosmwasm_std::{Decimal, Uint128, Addr,};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

use cw_storage_plus::{Item, Map};

pub const BORROWERS: Map<Addr, Borrower> = Map::new("borrowers");
pub const STATE: Item<State> = Item::new("\u{0}\u{6}config");
pub const CONFIG: Item<Config> = Item::new("\u{0}\u{6}config");

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, JsonSchema)]
pub struct Config {
    pub owner: Addr,
    pub anchor_market_contract: Addr,
    pub anchor_overseer_contract: Addr,
    pub anchor_liquidation_contract: Addr,
    pub anchor_oracle_contract: Addr,
    pub liquidator_fee: Decimal,
}

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, JsonSchema)]
pub struct State {
    pub whitelisted_cw20s: Vec<Addr>,
}

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, JsonSchema)]
pub struct Borrower {
    pub guardians: Vec<Guardian>,
}

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, JsonSchema)]
pub struct Guardian {
    pub address: Addr,
    pub amount: Uint128,
    pub pair_address: Addr, //this is the astro pair where the guardian will be swapped to ust
}
