#[cfg(not(feature = "library"))]
use cosmwasm_std::entry_point;
use cosmwasm_std::{
    from_binary, to_binary, Binary, Decimal, Deps, DepsMut, Env,
    MessageInfo, Response, StdError, StdResult, Uint128, Addr,
    WasmMsg, CosmosMsg,
};

use anchor_guardian::cw20::{ExecuteMsg, InstantiateMsg, QueryMsg, ConfigResponse};
use cw20::{Cw20ExecuteMsg, Expiration};
use crate::state::{CONFIG, STATE, BORROWERS, Config, State, Borrower, Guardian};
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
        ExecuteMsg::UpdateConfig {owner} => execute_update_config(deps, env, info, owner),
    
        //user funcs
        ExecuteMsg::AddGuardian { cw20_address, amount} => Ok(Response::new()),
    
        //liquidator funcs
        ExecuteMsg::LiquidateCollateral { address } => Ok(Response::new()),
    }
}


#[allow(clippy::too_many_arguments)]
pub fn execute_add_guardian(
    deps: DepsMut,
    env: Env,
    info: MessageInfo,
    cw20_address: String,
    amount: Uint128,
) -> StdResult<Response<TerraMsgWrapper>> {

    //confirm cw20 is whitelisted
    let state: State = STATE.load(deps.storage)?;
    let cw20_address = deps.api.addr_validate(&cw20_address)?;

    if !state.whitelisted_cw20s.contains(&cw20_address){
        return Err(StdError::generic_err("Unauthorized"));
    }

    //send allowance message
    let allowance_msg = CosmosMsg::Wasm(WasmMsg::Execute{
        contract_addr: cw20_address.clone().into(),
        funds: vec![],
        msg: to_binary(&Cw20ExecuteMsg::IncreaseAllowance{
            spender: env.contract.address.into(),
            amount: amount,
            expires: Some(Expiration::Never{}),
        })?,
    });

    //update internal borrower guardian state
    let mut borrower: Borrower = BORROWERS.load(deps.storage, info.sender)?;

    let new_guardian: Guardian = Guardian{
        address: cw20_address.clone(),
        amount: amount,
    };

    let guardian_position = borrower
        .guardians
        .iter()
        .position(|x| x.address == cw20_address);

    if let Some(guardian_position) = guardian_position{
        borrower.guardians.remove(guardian_position);
    }

    borrower.guardians.push(new_guardian);

    BORROWERS.save(deps.storage, cw20_address, &borrower)?;

    Ok(Response::new().add_attributes(vec![("action", "update_config")]).add_message(allowance_msg))
}


#[allow(clippy::too_many_arguments)]
pub fn execute_update_config(
    deps: DepsMut,
    env: Env,
    info: MessageInfo,
    owner: String,
) -> StdResult<Response<TerraMsgWrapper>> {

    //priv check
    let mut config: Config = CONFIG.load(deps.storage)?;
    if config.owner != info.sender{
        return Err(StdError::generic_err("Unauthorized"));
    }

    //update config
    config.owner = deps.api.addr_validate(&owner)?;

    CONFIG.save(deps.storage, &config)?;

    Ok(Response::new().add_attributes(vec![("action", "update_config")]))
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
    let cw20_address_check = state.whitelisted_cw20s.iter().any(|x| x == &cw20_address);

    if !cw20_address_check{
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