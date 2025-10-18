# MIT License
#
# Copyright (c) 2025 Manuel Boi, Palumbo Lorenzo, Piras Mauro - Università degli Studi di Cagliari
#
# Streamlit Constructor Parameter Interface for Ethereum Smart Contracts

import streamlit as st
from typing import List, Dict, Any, Optional
from ethereum_module.hardhat_module.compiler_and_deployer import _get_constructor_parameters_from_abi


def collect_constructor_args_streamlit(contract_name: str, abi_data: List[Dict]) -> Optional[List[Any]]:
    """
    Collect constructor arguments using Streamlit interface.
    
    Args:
        contract_name: Name of the contract
        abi_data: Contract ABI data
        
    Returns:
        List of constructor arguments or None if cancelled
    """
    constructor_inputs = _get_constructor_parameters_from_abi(abi_data)
    
    if not constructor_inputs:
        st.success(f"✅ Contract '{contract_name}' has no constructor parameters")
        return []
    
    st.subheader(f"🔧 Constructor Parameters for '{contract_name}'")
    st.markdown("---")
    
    args = []
    valid_inputs = True
    
    # Create input fields for each parameter
    for i, param in enumerate(constructor_inputs):
        param_name = param['name']
        param_type = param['type']
        
        st.markdown(f"**Parameter {i+1}: `{param_name}` ({param_type})**")
        
        # Create appropriate input widget based on parameter type
        if param_type == 'string':
            value = st.text_input(
                f"Enter {param_name}:",
                key=f"constructor_{contract_name}_{param_name}",
                placeholder="Enter string value..."
            )
            if value.strip():
                args.append(value.strip())
            else:
                st.error(f"❌ {param_name} cannot be empty")
                valid_inputs = False
                
        elif param_type.startswith('uint') or param_type.startswith('int'):
            value = st.number_input(
                f"Enter {param_name}:",
                min_value=0 if param_type.startswith('uint') else None,
                step=1,
                key=f"constructor_{contract_name}_{param_name}",
                format="%d"
            )
            args.append(int(value))
            
        elif param_type == 'bool':
            value = st.selectbox(
                f"Select {param_name}:",
                options=[True, False],
                key=f"constructor_{contract_name}_{param_name}"
            )
            args.append(value)
            
        elif param_type == 'address':
            value = st.text_input(
                f"Enter {param_name}:",
                key=f"constructor_{contract_name}_{param_name}",
                placeholder="0x..."
            )
            
            if value.strip():
                if value.startswith('0x') and len(value) == 42:
                    try:
                        # Validate hex format
                        int(value, 16)
                        args.append(value)
                    except ValueError:
                        st.error(f"❌ Invalid address format for {param_name}")
                        valid_inputs = False
                else:
                    st.error(f"❌ Address must start with 0x and be 42 characters long")
                    valid_inputs = False
            else:
                st.error(f"❌ {param_name} cannot be empty")
                valid_inputs = False
                
        else:
            # For other types, use text input
            value = st.text_input(
                f"Enter {param_name}:",
                key=f"constructor_{contract_name}_{param_name}",
                placeholder=f"Enter {param_type} value..."
            )
            if value.strip():
                args.append(value.strip())
            else:
                st.error(f"❌ {param_name} cannot be empty")
                valid_inputs = False
        
        st.markdown("") # Add spacing
    
    # Show summary
    if args and valid_inputs:
        st.markdown("---")
        st.subheader("📋 Parameter Summary")
        for i, (param, arg) in enumerate(zip(constructor_inputs, args)):
            st.markdown(f"**{param['name']}** ({param['type']}): `{arg}`")
    
    return args if valid_inputs else None


def display_constructor_preview(contract_name: str, abi_data: List[Dict]) -> None:
    """
    Display a preview of constructor parameters without collecting input.
    
    Args:
        contract_name: Name of the contract
        abi_data: Contract ABI data
    """
    constructor_inputs = _get_constructor_parameters_from_abi(abi_data)
    
    if not constructor_inputs:
        st.info(f"ℹ️ Contract '{contract_name}' has no constructor parameters")
        return
    
    st.markdown(f"**🔧 Constructor Parameters Required for '{contract_name}':**")
    
    for i, param in enumerate(constructor_inputs, 1):
        param_name = param['name']
        param_type = param['type']
        
        st.markdown(f"**{i}.** `{param_name}` ({param_type})")


def validate_constructor_args(args: List[Any], abi_data: List[Dict]) -> bool:
    """
    Validate constructor arguments against ABI specification.
    
    Args:
        args: List of constructor arguments
        abi_data: Contract ABI data
        
    Returns:
        True if valid, False otherwise
    """
    constructor_inputs = _get_constructor_parameters_from_abi(abi_data)
    
    if len(args) != len(constructor_inputs):
        return False
    
    for arg, param in zip(args, constructor_inputs):
        param_type = param['type']
        
        try:
            if param_type == 'string' and not isinstance(arg, str):
                return False
            elif param_type.startswith('uint') or param_type.startswith('int'):
                int(arg)
            elif param_type == 'bool' and not isinstance(arg, bool):
                return False
            elif param_type == 'address':
                if not isinstance(arg, str) or not arg.startswith('0x') or len(arg) != 42:
                    return False
                int(arg, 16)  # Validate hex format
        except (ValueError, TypeError):
            return False
    
    return True