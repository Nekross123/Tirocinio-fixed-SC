from pytezos import pytezos
import traceback
from pytezos.michelson.parse import michelson_to_micheline
import time
import subprocess
import sys

MUTEZ_CONV = 1000000
##Compiler
def compileContract(contractPath) :
    print(f">>> Compiling '{contractPath}'...")

    try:
        subprocess.run([sys.executable, contractPath], check=True)

        print(f"\n>>> '{contractPath}' compiled!")

    except FileNotFoundError:
        print(f"ERROR: '{contractPath}' not found.")
    except subprocess.CalledProcessError:
        print(f"\nERROR: '{contractPath}' raise an exception.")

##Deploy
def origination(client, michelsonCode, initialStorage, initialBalance):

    parsed_code = michelson_to_micheline(michelsonCode)
    parsed_storage = michelson_to_micheline(initialStorage)

    print("Origination")

    try:
        op_group = client.origination(
            script={
                'code': parsed_code,
                'storage': parsed_storage
            },
            balance = initialBalance * MUTEZ_CONV
        ).autofill().sign()
        
        op_hash = op_group.inject(_async=False)['hash']
        print(f"Operation send! Hash: {op_hash}")
        
        start_time = time.time()
        timeout = 500 
        op_result = None
        
        while time.time() - start_time < timeout:
            try:
                op_result = client.shell.blocks[-10:].find_operation(op_hash)
                print(f"Operation Found")
                break 
            except StopIteration:
                print(f"   -> Not yet completed (time passed: {int(time.time() - start_time)}s)")
                time.sleep(15)

        if not op_result:
            print(f"\n❌ TIMEOUT: The operation has not be included after {timeout} seconds.")
            print("Operation could be failed or not choosen by bakers. (check fees)")
            return None
        
        return op_result

    except Exception as e:
        print(traceback.format_exc())
        print(f"Error {e}")

def contractInfoResult(op_result):
    #print("\n" + "="*20 + " COST ANALYZIS " + "="*20)
    deployReport = {}
    
    try:
        deployReport["hash"] = op_result["hash"]
        content = op_result['contents'][0]
        metadata = content.get('metadata', {})
        op_result_info = metadata.get('operation_result', {})
        originated_contracts = op_result_info.get('originated_contracts')
        if originated_contracts:
            contract_address = originated_contracts[0]
        
        deployReport["address"] = contract_address
        
        # BakerFee
        fee_mutez = int(content.get('fee', 0))
        deployReport["BakerFee"] = fee_mutez

        # Gas
        consumed_milligas = int(op_result_info.get('consumed_milligas', 0))
        deployReport["Gas"] = consumed_milligas

        # Storage Fee (Burn)
        storage_size_diff = int(op_result_info.get('paid_storage_size_diff', 0))
        storage_burn_cost_mutez = storage_size_diff * 250
        deployReport["Storage"] = storage_burn_cost_mutez
        
        total_cost_mutez = fee_mutez + storage_burn_cost_mutez
        deployReport["TotalCost"] = total_cost_mutez
        
        return deployReport

    except (KeyError, IndexError, TypeError) as e:
        print(f"Errore: {e}")

##Contract Call
def entrypointCall(client, contractAddress, entrypointName, parameters, tezAmount):

    contract_interface = client.contract(contractAddress)

    print(f"\n Calling {entrypointName} entrypoint...\n")
    
    parametersDict = {}
    if parameters != [] and "=" in parameters[0]:
        for param in parameters:
            paramSplitted = param.split("=")
            parametersDict[paramSplitted[0]] = paramSplitted[1]
        parameters = [parametersDict]            

    try:
        entrypoint = getattr(contract_interface, entrypointName)
        if parameters == []:
            op = entrypoint().with_amount(tezAmount * MUTEZ_CONV).send()
        else:
            op = entrypoint(*parameters).with_amount(tezAmount * MUTEZ_CONV).send()
        
        forged_op = op.forge()
   
        op_hash = op.hash()
        print(f"Operation Send! Hash: {op_hash}")
        
        start_time = time.time()
        timeout = 500 
        op_result = None
        
        # Attendi la conferma
        while time.time() - start_time < timeout:
            try:
                op_result = client.shell.blocks[-10:].find_operation(op_hash)
                print(f"   -> Operation Found")
                break 
            except StopIteration:
                print(f"   -> Not yet completed (time passed: {int(time.time() - start_time)}s)")
                time.sleep(15)

        if not op_result:
            print(f"\n❌ TIMEOUT: The operation has not be included after {timeout} seconds.")
            print("Operation could be failed or not choosen by bakers. (check fees)")

        op_result["weight"] = len(forged_op) // 2
        return op_result
    except Exception as e:
        print(f"Si è verificato un errore: {e}")

def entrypointAnalyse(client, contractAddress):
    entrypointSchema = {}
    
    try:
        contract = client.contract(contractAddress)
        if len(contract.entrypoints) > 1:
            del contract.entrypoints["default"]
        
        for entrypoint_name, entrypoint_object in contract.entrypoints.items():
            #print(f"📌 Entrypoint: \"{entrypoint_name}\"")
    
            if hasattr(entrypoint_object, 'json_type'):
                parameter_schema = entrypoint_object.json_type()
                
                if parameter_schema.get('title') == 'unit':
                    #print("   Parameter: No required (type 'Unit').")
                    entrypointSchema[entrypoint_name] = "unit"
                else:
                    #print("   Parameter:")
                    lst = []
                    properties = parameter_schema.get('properties', {})
                    for param_name, param_details in properties.items():
                        param_type = param_details.get('title')
                        param_format = f" (details: {param_details.get('format', 'N/D')})"
                        #print(f"     - name: `{param_name}`, Type: `{param_type}`{param_format}")
                        entrypointSchema[entrypoint_name] = lst.append((param_name, (param_type, param_format)))
            else:
                param_type = entrypoint_object.prim
                #print("   Parameter required:")
                #print(f"     - Name: `_` (parametro singolo), Type: `{param_type}`")
                entrypointSchema[entrypoint_name] = param_type
                    
        return entrypointSchema

    except Exception as e:
        print(f"An error occurred: {e}")
        
def callInfoResult(opResult):
    #print("\n" + "="*20 + " COST ANALYZIS " + "="*20)
    callReport = {}
    
    try:
        callReport["Hash"] = opResult["hash"]
        content = opResult['contents'][0]
        metadata = content.get('metadata', {})
        op_result_info = metadata.get('operation_result', {})
        

        # BakerFee
        fee_mutez = int(content.get('fee', 0))
        callReport["BakerFee"] = fee_mutez

        # Gas
        consumed_milligas = int(op_result_info.get('consumed_milligas', 0))
        callReport["Gas"] = consumed_milligas

        # Storage Fee (Burn)
        if ('paid_storage_size_diff' in op_result_info):
            storage_size_diff = int(op_result_info.get('paid_storage_size_diff', 0))
            storage_burn_cost_mutez = storage_size_diff * 250
            callReport["Storage"] = storage_burn_cost_mutez
        else:
            storage_burn_cost_mutez = 0
            
        
        total_cost_mutez = fee_mutez + storage_burn_cost_mutez
        callReport["TotalCost"] = total_cost_mutez
        
        callReport["Weight"] = opResult["weight"]
        
        return callReport

    except (KeyError, IndexError, TypeError) as e:
        print(f"Errore: {e}")