import json
import os
from ethereum_module.hardhat_module.contract_utils import interact_with_contract
from ethereum_module.ethereum_utils import ethereum_base_path

hardhat_base_path = f"{ethereum_base_path}/hardhat_module"


def run_execution_trace(trace_file_name):
    print(f"\nStarting automatic execution trace: {trace_file_name}")
    print("="*60)
    
    trace_path = f"{hardhat_base_path}/execution_traces/{trace_file_name}"
    if not os.path.exists(trace_path):
        error_msg = f"Trace file not found: {trace_path}"
        print(f"Error: {error_msg}")
        return {"success": False, "error": error_msg}
    
    try:
        with open(trace_path, 'r', encoding='utf-8') as f:
            trace_data = json.load(f)
    except Exception as e:
        error_msg = f"Failed to read trace file: {str(e)}"
        print(f"Error: {error_msg}")
        return {"success": False, "error": error_msg}
    
    trace_title = trace_data.get("trace_title", "unknown")
    trace_actors = trace_data.get("trace_actors", [])
    configuration = trace_data.get("configuration", {}).get("ethereum", {})
    trace_execution = trace_data.get("trace_execution", [])
    network = configuration.get("network", "localhost")
    
    print(f"Trace Title: {trace_title}")
    print(f"Actors: {', '.join(trace_actors)}")
    print(f"Network: {network}")
    print(f"Actions to execute: {len(trace_execution)}\n")
    
    results_file = f"{hardhat_base_path}/interaction_results/{trace_title}_{network}_results.json"
    if os.path.exists(results_file):
        os.remove(results_file)
        print(f"Removed old results file\n")
    
    actor_wallets = {}
    for i, actor in enumerate(trace_actors):
        wallet_file = f"hardhat_account_{i}.json"
        actor_wallets[actor] = wallet_file
        print(f"  {actor} -> {wallet_file}")
    
    print()
    
    results = []
    
    for action in trace_execution:
        sequence_id = action.get("sequence_id", "?")
        function_name = action.get("function_name", "")
        args = action.get("args", {})
        ethereum_config = action.get("ethereum", {})
        
        contract_id = f"{trace_title}_{network}"
        value_eth = str(ethereum_config.get("value_eth", "0"))
        
        caller_actor = ethereum_config.get("caller", trace_actors[0] if trace_actors else None)
        if not caller_actor:
            print(f"No caller specified for action {sequence_id}, skipping...")
            continue
            
        caller_wallet = actor_wallets.get(caller_actor)
        if not caller_wallet:
            print(f"No wallet found for actor {caller_actor}, skipping...")
            continue
        
        print(f"Action {sequence_id}: {function_name}()")
        print(f"   Caller: {caller_actor} ({caller_wallet})")
        print(f"   Args: {args}")
        print(f"   Value: {value_eth} ETH")
        
        try:
            result = interact_with_contract(
                contract_deployment_id=contract_id,
                function_name=function_name,
                param_values=args,
                address_inputs=[],
                value_eth=value_eth,
                caller_wallet=caller_wallet,
                gas_limit=None,
                gas_price=None,
                network=network
            )
            
            if result.get("success"):
                print(f"   Success!")
            else:
                print(f"   Failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"   Exception: {str(e)}")
    
    print("\n" + "="*60)
    
    results_file = f"{hardhat_base_path}/interaction_results/{contract_id}_results.json"
    
    if os.path.exists(results_file):
        print(f"Execution completed! Results saved to:")
        print(f"   {results_file}")
        
        with open(results_file, 'r', encoding='utf-8') as f:
            final_results = json.load(f)
        
        return {
            "success": True,
            "results_file": results_file,
            "results_data": final_results
        }
    else:
        return {
            "success": False,
            "error": "Results file was not generated"
        }


def find_execution_traces():
    traces_path = f"{hardhat_base_path}/execution_traces"
    
    if not os.path.exists(traces_path):
        print(f"Creating execution_traces folder: {traces_path}")
        os.makedirs(traces_path, exist_ok=True)
        return []
    
    traces = [f for f in os.listdir(traces_path) if f.lower().endswith('.json')]
    return sorted(traces)


def create_execution_trace_template(contract_name, network="localhost"):
    template = {
        "trace_title": contract_name,
        "trace_actors": [
            "player1",
            "player2",
            "oracle"
        ],
        "configuration": {
            "ethereum": {
                "network": network,
                "use": "True"
            }
        },
        "trace_execution": [
            {
                "sequence_id": "1",
                "function_name": "exampleFunction",
                "args": {
                    "param1": "value1",
                    "param2": 123
                },
                "ethereum": {
                    "caller": "player1",
                    "value_eth": "0",
                    "send_transaction": True
                }
            }
        ]
    }
    
    traces_path = f"{hardhat_base_path}/execution_traces"
    os.makedirs(traces_path, exist_ok=True)
    
    template_file = f"{traces_path}/{contract_name}_template.json"
    
    with open(template_file, 'w', encoding='utf-8') as f:
        json.dump(template, f, indent=2)
    
    print(f"Template created: {template_file}")
    return template_file


if __name__ == "__main__":
    print("Available execution traces:")
    traces = find_execution_traces()
    for trace in traces:
        print(f"  - {trace}")
    
    if traces:
        print(f"\nRunning first trace: {traces[0]}")
        result = run_execution_trace(traces[0])
        print(f"\nResult: {result}")
