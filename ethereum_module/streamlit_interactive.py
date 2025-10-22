# MIT License
#
# Streamlit implementation of Interactive Contract Interface
# Provides guided step-by-step contract interaction - Functional Approach

import streamlit as st
from typing import Dict, Any, List, Optional
from ethereum_module.interactive_interface import (
    get_available_contracts,
    get_available_wallets, 
    get_contract_info,
    get_function_guidance,
    execute_function_call,
    create_interactive_session
)
from ethereum_module.hardhat_module.contract_utils import fetch_functions_for_contract


# ========================================
# STREAMLIT INTERFACE FUNCTIONS
# ========================================

def display_contract_selection() -> Optional[str]:
    """Display contract selection interface."""
    contracts = get_available_contracts()
    
    if not contracts:
        st.warning("🚫 No contracts deployed yet. Please deploy a contract first.")
        return None
    
    st.markdown("### 📋 Select Contract")
    contract = st.selectbox(
        "Available Contracts:",
        ["--Select Contract--"] + contracts,
        help="Choose a deployed contract to interact with"
    )
    
    if contract != "--Select Contract--":
        # Show contract info
        info = get_contract_info(contract)
        
        with st.expander("ℹ️ Contract Information", expanded=False):
            st.markdown(f"**Address:** `{info['address']}`")
            st.markdown(f"**Network:** {info['network']}")
            if info.get('transaction_hash'):
                st.markdown(f"**Deployment Tx:** `{info['transaction_hash']}`")
        
        return contract
    
    return None


def display_function_selection(contract_id: str) -> Optional[str]:
    """Display function selection interface."""
    if not contract_id:
        return None
    
    st.markdown("### ⚙️ Select Function")
    
    try:
        functions = fetch_functions_for_contract(contract_id)
    except Exception as e:
        st.error(f"Error fetching functions: {e}")
        return None
    
    if not functions:
        st.warning("No functions available for this contract.")
        return None
    
    # Create function options with descriptions
    function_options = ["--Select Function--"]
    function_map = {}
    
    for func in functions:
        payable_str = " [PAYABLE]" if func['payable'] else ""
        param_count = len(func['inputs'])
        param_str = f"({param_count} params)" if param_count > 0 else "(no params)"
        
        display_name = f"{func['name']}{param_str}{payable_str}"
        function_options.append(display_name)
        function_map[display_name] = func['name']
    
    selected_display = st.selectbox(
        "Available Functions:",
        function_options,
        help="Choose a function to call"
    )
    
    if selected_display != "--Select Function--":
        function_name = function_map[selected_display]
        
        # Show function guidance
        guidance = get_function_guidance(contract_id, function_name)
        display_function_guidance(guidance)
        
        return function_name
    
    return None


def display_function_guidance(guidance: Dict[str, Any]) -> None:
    """Display detailed function guidance."""
    st.markdown("### Function Information")
    
    # Warnings
    if guidance['warnings']:
        with st.expander("⚠️ Important Notes"):
            for warning in guidance['warnings']:
                st.warning(warning)
    
    # Payable information
    if guidance['is_payable']:
        st.info("💰 This function accepts ETH payments")
    
    # Parameters info
    if guidance['parameters']:
        st.markdown("**Parameters Required:**")
        for i, param in enumerate(guidance['parameters'], 1):
            st.markdown(f"**{i}.** `{param['name']}` ({param['type']})")


def collect_function_parameters(guidance: Dict[str, Any]) -> Dict[str, Any]:
    """Collect all function parameters from user."""
    if not guidance['parameters']:
        return {}
    
    st.markdown("### 📝 Enter Parameters")
    parameters = {}
    
    for param in guidance['parameters']:
        param_name = param['name']
        param_type = param['type']
        validation = param['validation']
        
        st.markdown(f"**{param_name}** ({param_type})")
        
        if param_type == 'address':
            parameters[param_name] = collect_address_parameter(param_name)
        elif param_type.startswith('uint') or param_type.startswith('int'):
            parameters[param_name] = collect_integer_parameter(param_name, validation)
        elif param_type == 'string':
            parameters[param_name] = collect_string_parameter(param_name, validation)
        elif param_type == 'bool':
            parameters[param_name] = collect_boolean_parameter(param_name)
        else:
            parameters[param_name] = collect_generic_parameter(param_name, param_type)
        
        st.markdown("---")
    
    return parameters


def collect_address_parameter(param_name: str) -> Dict[str, Any]:
    """Collect address parameter with multiple input methods."""
    method = st.radio(
        f"How to provide {param_name}:",
        ["Wallet Address", "Manual Address", "Contract Address"],
        key=f"method_{param_name}"
    )
    
    result = {"method": method}
    
    if method == "Wallet Address":
        wallets = get_available_wallets()
        if wallets:
            wallet = st.selectbox(f"Select wallet for {param_name}:", wallets, key=f"wallet_{param_name}")
            result["wallet"] = wallet
        else:
            st.error("No wallets available")
    
    elif method == "Manual Address":
        address = st.text_input(f"Enter address for {param_name}:", placeholder="0x...", key=f"address_{param_name}")
        result["address_manual"] = address
    
    elif method == "Contract Address":
        contracts = get_available_contracts()
        if contracts:
            contract = st.selectbox(f"Select contract for {param_name}:", contracts, key=f"contract_{param_name}")
            result["contract"] = contract
        else:
            st.error("No contracts available")
    
    return result


def collect_integer_parameter(param_name: str, validation: Dict[str, Any]) -> int:
    """Collect integer parameter with validation."""
    min_value = validation.get('min', 0 if validation['type'] == 'integer' and 'uint' in param_name else None)
    
    return st.number_input(
        f"Enter {param_name}:",
        min_value=min_value,
        step=1,
        key=f"int_{param_name}",
        format="%d"
    )


def collect_string_parameter(param_name: str, validation: Dict[str, Any]) -> str:
    """Collect string parameter."""
    return st.text_input(
        f"Enter {param_name}:",
        placeholder="Enter text...",
        key=f"str_{param_name}"
    )


def collect_boolean_parameter(param_name: str) -> bool:
    """Collect boolean parameter."""
    return st.selectbox(
        f"Select {param_name}:",
        [True, False],
        key=f"bool_{param_name}"
    )


def collect_generic_parameter(param_name: str, param_type: str) -> str:
    """Collect generic parameter as string."""
    return st.text_input(
        f"Enter {param_name} ({param_type}):",
        key=f"generic_{param_name}"
    )


def collect_execution_settings(guidance: Dict[str, Any] , network) -> Dict[str, Any]:
    """Collect execution settings (wallet, gas, value)."""
    st.markdown("### ⚙️ Execution Settings")
    
    # Wallet selection
    wallets = get_available_wallets()
    if not wallets:
        st.error("No wallets available for execution")
        return {}
    if network == "localhost":
        wallet = st.selectbox("Select wallet to execute transaction:", [w for w in wallets if w.startswith("localhost")])
    else:
        wallet = st.selectbox("Select wallet to execute transaction:", wallets)

    # ETH value (if payable)
    value_eth = "0"
    if guidance['is_payable']:
        value_eth = st.text_input("ETH to send (optional):", value="0", placeholder="0.1")
    
    # Gas settings (optional)
    with st.expander("Advanced Gas Settings (Optional)"):
        gas_limit = st.number_input("Gas Limit:", value=300000, min_value=21000)
        gas_price = st.number_input("Gas Price (Gwei):", value=20, min_value=1)
    
    return {
        "wallet": wallet,
        "value_eth": value_eth,
        "gas_limit": gas_limit,
        "gas_price": gas_price
    }


def execute_contract_function(contract_id: str, function_name: str, 
                            parameters: Dict[str, Any], settings: Dict[str, Any]) -> Dict[str, Any]:
    """Execute the contract function with provided parameters."""
    return execute_function_call(
        contract_id=contract_id,
        function_name=function_name,
        parameters=parameters,
        wallet=settings["wallet"],
        value_eth=settings["value_eth"],
        network=None  # Use default network from deployment
    )


def display_execution_result(result: Dict[str, Any]) -> None:
    """Display execution result."""
    if result["success"]:
        st.success("✅ Transaction executed successfully!")
        
        if "transaction_hash" in result:
            st.markdown(f"**Transaction Hash:** `{result['transaction_hash']}`")
        
        if "gas_used" in result:
            st.markdown(f"**Gas Used:** {result['gas_used']}")
        
        if "return_value" in result and result["return_value"]:
            st.markdown(f"**Return Value:** `{result['return_value']}`")
    else:
        st.error(f"❌ Transaction failed: {result.get('error', 'Unknown error')}")


# ========================================
# MAIN INTERFACE FUNCTION
# ========================================

def run_interactive_contract_interface() -> None:
    """Main function to run the complete interactive interface."""
    st.markdown("## 🔧 Interactive Contract Interface")
    
    # Step 1: Contract Selection
    contract_id = display_contract_selection()
    if not contract_id:
        return
    
    # Step 2: Function Selection
    function_name = display_function_selection(contract_id)
    if not function_name:
        return
    
    # Step 3: Parameter Collection
    try:
        guidance = get_function_guidance(contract_id, function_name)
        parameters = collect_function_parameters(guidance)
        
        # Step 4: Execution Settings
        settings = collect_execution_settings(guidance ,get_contract_info(contract_id)['network'])
        if not settings:
            return
        
        # Step 5: Execute
        if st.button("🚀 Execute Transaction", type="primary"):
            with st.spinner("Executing transaction..."):
                result = execute_contract_function(contract_id, function_name, parameters, settings)
                display_execution_result(result)
                
    except Exception as e:
        st.error(f"Error: {e}")