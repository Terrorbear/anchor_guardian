use cosmwasm_std::{Decimal, StdResult, Storage, Uint128, Addr, Deps, Api, Order};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

use cw_storage_plus::{Item, Map};

pub const BORROWERS: Map<Addr, Borrower> = Map::new("borrowers");
pub const CONFIG: Item<Config> = Item::new("\u{0}\u{6}config");

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, JsonSchema)]
pub struct Config {
    pub owner: Addr,
}


#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, JsonSchema)]
pub struct Borrower {
    pub guardians: Vec<Guardian>,
}

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, JsonSchema)]
pub struct Guardian {
    pub address: Addr,
    pub amount: Uint128,
}
