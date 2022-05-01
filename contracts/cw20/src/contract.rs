#[cfg(not(feature = "library"))]
use cosmwasm_std::entry_point;
use cosmwasm_std::{
    from_binary, to_binary, Binary, Decimal, Deps, DepsMut, Env,
    MessageInfo, Response, StdError, StdResult, Uint128, Addr,
};

use anchor_guardian::cw20::{ExecuteMsg, InstantiateMsg, QueryMsg, ConfigResponse};

use crate::state::{CONFIG, STATE, BORROWERS, Config, State, Borrower};
use terra_cosmwasm::TerraMsgWrapper;


#[cfg_attr(not(feature = "library"), entry_point)]
pub fn instantiate(
    deps: DepsMut,
    _env: Env,
    info: MessageInfo,
    msg: InstantiateMsg,
) -> StdResult<Response<TerraMsgWrapper>> {

    let config = Config {
        owner: deps.api.addr_validate(&msg.owner)?,
    };

    CONFIG.save(deps.storage, &config)?;

    Ok(Response::default())
}

#[cfg_attr(not(feature = "library"), entry_point)]
pub fn execute(
    deps: DepsMut,
    env: Env,
    info: MessageInfo,
    msg: ExecuteMsg,
) -> StdResult<Response<TerraMsgWrapper>> {
    match msg {
        ExecuteMsg::WhitelistCw20{address} => execute_whitelist_cw20(deps, env, info, address),
        ExecuteMsg::UpdateConfig {owner} => Ok(Response::new()),
    
        //user funcs
        ExecuteMsg::AddGuardian { cw20_address, amount} => Ok(Response::new()),
    
        //liquidator funcs
        ExecuteMsg::LiquidateCollateral { address } => Ok(Response::new()),
    }
}

#[allow(clippy::too_many_arguments)]
pub fn execute_whitelist_cw20(
    deps: DepsMut,
    env: Env,
    info: MessageInfo,
    address: String,
) -> StdResult<Response<TerraMsgWrapper>> {

    //priv check
    let config: Config = CONFIG.load(deps.storage)?;
    if config.owner != info.sender{
        return Err(StdError::generic_err("Unauthorized"));
    }

    //valid address
    let cw20_address: Addr = deps.api.addr_validate(&address)?;

    //check if address already whitelisted
    let mut state: State = STATE.load(deps.storage)?;
    let cw20_address_check = state.whitelisted_cw20s.iter().find(|&x| x == &cw20_address);

    if cw20_address_check.is_none(){
        state.whitelisted_cw20s.push(cw20_address);
        STATE.save(deps.storage, &state);
    }

    Ok(Response::new().add_attributes(vec![("action", "update_config")]))
}


#[cfg_attr(not(feature = "library"), entry_point)]
pub fn query(deps: Deps, _env: Env, msg: QueryMsg) -> StdResult<Binary> {
    match msg {
        QueryMsg::Config {} => Ok(to_binary(&query_config(deps)?)?),
        QueryMsg::Guardians {address} => Ok(to_binary(&query_guardians(deps, address)?)?),
    }
}


pub fn query_config(deps: Deps) -> StdResult<ConfigResponse> {
    let config: Config = CONFIG.load(deps.storage)?;
    Ok(ConfigResponse {
        owner: config.owner.into(),
    })
  }
  
  pub fn query_guardians(deps: Deps, address: String) -> StdResult<Borrower> {
    let borrower: Borrower = BORROWERS.load(deps.storage, deps.api.addr_validate(&address)?)?;
    Ok(borrower)
  }