## Unified Execution Trace JSON 

This document defines the single JSON format used to describe execution traces across toolchains (Solana, EVM, Tezos, Cardano). One file can target multiple chains at once via the configuration block and per-step chain sections.

### structure

- trace_title: string (required)
	- name of the trace or program.
- trace_actors: string[] (required)
	- Labels for the logical actors involved (e.g., "sender", "receiver", "user").
	- Use unique, lowercase/underscore names .
- configuration: object (required)
	- Keys: solana, evm, tezos, cardano (all optional, but at least one should be enabled).
	- For each chain key:
		- use: boolean or string "True"/"False" (default False). If true, that chain is considered active for this trace.
- trace_execution: Step[] (required, length >= 1)

Each item in trace_execution describes one action. Common fields are shared across chains; chain-specific sections refine execution.

- sequence_id: string | number (required)
	- identifier for ordering; unique within the file.
- function_name: string (required)
	- Logical function/entrypoint name. 
- waiting_time: number (required)
	- Delay in seconds to wait before executing this step (0 if not needed).
- actors: string[] (required)
	- Subset of trace_actors participating in this step.
- args: object (required)
	- Parameters for the logical function. Values should be JSON primitives or simple objects.
- solana | evm | tezos | cardano: object (all optional, but typically present; empty object {} is valid)
	- Chain-specific directives/overrides. Common optional keys across chains:
		- provider_wallet: string — one of trace_actors, indicates who signs the transaction.
		- send_transaction: boolean — if false, simulate/dry-run only (default true if omitted).
	- Examples of chain-specific extras:
		- Solana: derived addresses/PDAs, e.g. user_wallet_pda, balance_holder_pda with special shorthand:
			- { "opt": "s", "param": ["seedA", "seedB" | references like "recipient", "sender"] }
			- Additional fields like duration_slots, starting_bid, amount_to_deposit, transaction_lamports_amount.
		- EVM: method (string), contract_name/address (string), value (wei, number), gas_limit, gas_price, args (object/array) to override global args.
		- Tezos: entrypoint (string), parameters (object/string), mutez (number) or tezAmount, address/contract alias.
		- Cardano: policy_id, asset, ada_amount, datum/redeemer, script references.


### Minimal examples

Solana-only

```json
{
	"trace_title": "storage",
	"trace_actors": ["user"],
	"configuration": {
		"solana": { "use": "True" },
		"evm": {}, "tezos": {}, "cardano": {}
	},
	"trace_execution": [
		{
			"sequence_id": "1",
			"function_name": "initialize",
			"waiting_time": 0,
			"actors": ["user"],
			"args": {},
			"solana": {
				"string_storage_pda": { "opt": "s", "param": ["storage_string", "user"] },
				"provider_wallet": "user", "send_transaction": true
			},
			"evm": {}, "tezos": {}, "cardano": {}
		}
	]
}
```

Multi-chain (Solana + EVM)

```json
{
	"trace_title": "simple_transfer",
	"trace_actors": ["recipient", "sender"],
	"configuration": {
		"solana": { "use": "True" },
		"evm": { "use": "True" },
		"tezos": {}, "cardano": {}
	},
	"trace_execution": [
		{
			"sequence_id": 1,
			"function_name": "deposit",
			"waiting_time": 0,
			"actors": ["recipient", "sender"],
			"args": {"amount_to_deposit": 100000},
			"solana": {
				"balance_holder_pda": {"opt": "s", "param": ["recipient", "sender"]},
				"provider_wallet": "sender", "send_transaction": true
			},
			"evm": {
				"contract_name": "SimpleTransfer",
				"method": "deposit",
				"value": 0,
				"gas_limit": 200000,
				"args": {"amount": 100000},
				"provider_wallet": "sender", "send_transaction": true
			},
			"tezos": {}, "cardano": {}
		}
	]
}
```

### File placement in this repository

- Solana: put JSON traces under `Solana_module/solana_module/anchor_module/execution_traces/`.
- Tezos: current toolchain consumes CSV in `Tezos_module/toolchain/execution_traces/`. still to unified 
- EVM/Cardano: when JSON traces are added, follow the same schema and use the module’s `execution_traces/` folder.

