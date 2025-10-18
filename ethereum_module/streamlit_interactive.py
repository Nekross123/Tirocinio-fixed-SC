# MIT License
#
# Streamlit implementation of Interactive Contract Interface
# Provides guided step-by-step contract interaction

import streamlit as st
from typing import Dict, Any, List
from ethereum_module.interactive_interface import InteractiveContractInterface, create_interactive_session


class StreamlitInteractiveInterface(InteractiveContractInterface):
    """Streamlit-specific implementation of interactive contract interface."""
    
    def display_contract_selection(self) -> str:
        """Display contract selection interface."""
        contracts = self.get_available_contracts()
        
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
            info = self.get_contract_info(contract)
            with st.expander(f"📊 Contract Info: {contract}"):
                st.write(f"**Address:** `{info['address']}`")
                st.write(f"**Network:** {info['network']}")
                if info.get('deployed_at'):
                    st.write(f"**Deployed:** {info['deployed_at']}")
                
                st.write("**Available Functions:**")
                for func in info['interaction_functions']:
                    payable_indicator = " 💰" if func['payable'] else ""
                    st.write(f"- `{func['name']}(){payable_indicator}`")
            
            return contract
        
        return None
    
    def display_function_selection(self, contract_id: str) -> str:
        """Display function selection interface."""
        functions = fetch_functions_for_contract(contract_id)
        
        st.markdown("### 🎯 Select Function")
        
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
            guidance = self.get_function_guidance(contract_id, function_name)
            self.display_function_guidance(guidance)
            
            return function_name
        
        return None
    
    def display_function_guidance(self, guidance: Dict[str, Any]) -> None:
        """Display detailed function guidance."""
        st.markdown("### Function Information")
        
        # Examples
        if guidance['examples']:
            with st.expander("💡 Usage Examples"):
                for example in guidance['examples']:
                    st.code(example)
        
        # Warnings
        if guidance['warnings']:
            with st.expander("⚠️ Important Notes"):
                for warning in guidance['warnings']:
                    st.warning(warning)
        
        # Parameters info
        if guidance['parameters']:
            with st.expander("📝 Parameter Details"):
                for param in guidance['parameters']:
                    st.write(f"**{param['name']}** ({param['type']})")
                    st.write(f"- {param['description']}")
                    if param['examples']:
                        st.write(f"- Examples: {', '.join(param['examples'])}")
                    st.write("---")
    
    def collect_parameters_interactive(self, guidance: Dict[str, Any]) -> Dict[str, Any]:
        """Collect parameters using Streamlit interface."""
        st.markdown("### ⚙️ Configure Parameters")
        
        parameters = {}
        
        # Function parameters
        if guidance['parameters']:
            st.markdown("#### Function Parameters")
            
            for param in guidance['parameters']:
                param_name = param['name']
                param_type = param['type']
                description = param['description']
                examples = param['examples']
                validation = param['validation']
                
                st.markdown(f"**{param_name}** `({param_type})`")
                st.caption(description)
                
                if param_type == 'address':
                    parameters[param_name] = self._collect_address_parameter(param_name)
                elif param_type.startswith('uint') or param_type.startswith('int'):
                    parameters[param_name] = self._collect_integer_parameter(
                        param_name, examples, validation
                    )
                elif param_type == 'string':
                    parameters[param_name] = self._collect_string_parameter(
                        param_name, examples
                    )
                elif param_type == 'bool':
                    parameters[param_name] = self._collect_boolean_parameter(param_name)
                else:
                    parameters[param_name] = self._collect_generic_parameter(
                        param_name, param_type
                    )
                
                st.markdown("---")
        
        # Value for payable functions
        value_eth = "0"
        if guidance['is_payable']:
            st.markdown("#### 💰 Ether Value")
            st.info("This function can receive Ether. Specify the amount to send.")
            value_eth = st.number_input(
                "ETH Amount",
                min_value=0.0,
                value=0.0,
                step=0.001,
                format="%.6f",
                help="Amount of ETH to send with the transaction"
            )
        
        # Wallet selection
        st.markdown("#### 👛 Transaction Sender")
        wallets = self.get_available_wallets()
        if not wallets:
            st.error("No wallets found. Please create a wallet first.")
            return None
        
        wallet = st.selectbox(
            "Select Wallet:",
            ["--Select Wallet--"] + wallets,
            help="Choose the wallet to send the transaction from"
        )
        
        if wallet == "--Select Wallet--":
            st.warning("Please select a wallet to continue.")
            return None
        
        return {
            "parameters": parameters,
            "value_eth": str(value_eth),
            "wallet": wallet
        }
    
    def _collect_address_parameter(self, param_name: str) -> Dict[str, Any]:
        """Collect address parameter with multiple input methods."""
        method = st.radio(
            f"How to provide {param_name}:",
            ["Wallet Address", "Manual Address", "Contract Address"],
            key=f"addr_method_{param_name}"
        )
        
        result = {"method": method}
        
        if method == "Wallet Address":
            wallets = self.get_available_wallets()
            wallet = st.selectbox(
                "Select Wallet:",
                ["--Select Wallet--"] + wallets,
                key=f"addr_wallet_{param_name}"
            )
            result["wallet"] = wallet if wallet != "--Select Wallet--" else None
            
        elif method == "Manual Address":
            address = st.text_input(
                "Enter Address:",
                placeholder="0x742d35Cc6641C93988D0Ac4C95a36D98C41A30Ee",
                key=f"addr_manual_{param_name}"
            )
            result["address_manual"] = address
            
        elif method == "Contract Address":
            contracts = self.get_available_contracts()
            contract = st.selectbox(
                "Select Contract:",
                ["--Select Contract--"] + contracts,
                key=f"addr_contract_{param_name}"
            )
            result["contract"] = contract if contract != "--Select Contract--" else None
        
        return result
    
    def _collect_integer_parameter(self, param_name: str, examples: List[str], 
                                 validation: Dict[str, Any]) -> str:
        """Collect integer parameter."""
        if examples:
            st.caption(f"Examples: {', '.join(examples)}")
        
        value = st.text_input(
            f"Enter {param_name}:",
            placeholder="Enter number",
            key=f"int_{param_name}",
            help=validation.get('format', 'Enter a valid integer')
        )
        return value
    
    def _collect_string_parameter(self, param_name: str, examples: List[str]) -> str:
        """Collect string parameter."""
        if examples:
            st.caption(f"Examples: {', '.join(examples)}")
        
        value = st.text_input(
            f"Enter {param_name}:",
            placeholder="Enter text",
            key=f"str_{param_name}"
        )
        return value
    
    def _collect_boolean_parameter(self, param_name: str) -> str:
        """Collect boolean parameter."""
        value = st.selectbox(
            f"Select {param_name}:",
            ["--Select--", "true", "false"],
            key=f"bool_{param_name}"
        )
        return value if value != "--Select--" else ""
    
    def _collect_generic_parameter(self, param_name: str, param_type: str) -> str:
        """Collect generic parameter."""
        value = st.text_input(
            f"Enter {param_name} ({param_type}):",
            placeholder=f"Enter {param_type} value",
            key=f"generic_{param_name}"
        )
        return value


def run_interactive_contract_interface():
    """Main function to run the interactive contract interface."""
    st.markdown("## 🎮 Interactive Contract Interface")
    st.caption("Step-by-step guided contract interaction")
    
    interface = StreamlitInteractiveInterface()
    
    # Step 1: Select Contract
    contract_id = interface.display_contract_selection()
    if not contract_id:
        return
    
    # Step 2: Select Function
    function_name = interface.display_function_selection(contract_id)
    if not function_name:
        return
    
    # Step 3: Get function guidance
    guidance = interface.get_function_guidance(contract_id, function_name)
    
    # Step 4: Collect parameters
    collected_data = interface.collect_parameters_interactive(guidance)
    if not collected_data:
        return
    
    # Step 5: Execute
    st.markdown("### 🚀 Execute Transaction")
    
    if st.button("Execute Function Call", type="primary"):
        with st.spinner("Processing transaction..."):
            result = interface.execute_function_call(
                contract_id=contract_id,
                function_name=function_name,
                parameters=collected_data["parameters"],
                wallet=collected_data["wallet"],
                value_eth=collected_data["value_eth"]
            )
        
        # Display results
        if result["success"]:
            st.success("✅ Transaction successful!")
            
            if result.get("is_view"):
                st.info(f"**Return Value:** {result.get('return_value')}")
            else:
                st.write(f"**Transaction Hash:** `{result.get('transaction_hash')}`")
                st.write(f"**Gas Used:** {result.get('gas_used')}")
                st.write(f"**Status:** {result.get('status')}")
        else:
            st.error(f"❌ Transaction failed: {result.get('error')}")


# Import this in the main file to use
from ethereum_module.hardhat_module.contract_utils import fetch_functions_for_contract