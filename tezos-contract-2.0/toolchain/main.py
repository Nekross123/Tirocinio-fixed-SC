from contractUtils import *    
from folderScan import *
from csvUtils import *
from jsonUtils import *

def interactionSetup(client, contract):
    addressValid = getAddress()
    contractAddress = addressValid[contract]
    contractInterface = pytezos.contract(contractAddress)
    entrypoints = contractInterface.entrypoints
    if len(entrypoints) > 1:
        del entrypoints["default"]
    
    i = 1
    entryList = []
    for entry in entrypoints:
        print(i, entry)
        entryList.append(entry)
        i += 1
        
    entrypointSel = int(input("Which entrypoint do you want to use?\n"))
    entrypointSchema = entrypointAnalyse(client=client, contractAddress=contractAddress)
    entrypointParam = entrypointSchema[entryList[entrypointSel-1]]
    parameters = None
    if entrypointParam != "unit":
        parameters = input("Insert parameters value: ")
        if "," in parameters:
            parameters = parameters.split(",")
        else:
            parameters = [parameters]
    tezAmount = int(input("Insert tez amount: "))
    
    opResult = entrypointCall(client=client, contractAddress=contractAddress, entrypointName=entryList[entrypointSel-1], parameters=parameters, tezAmount=tezAmount)
    infoResult = callInfoResult(opResult=opResult)
    infoResult["contract"] = contract
    infoResult["entryPoint"] = entryList[entrypointSel-1]
    return infoResult

def executionSetup(contract,rows):
    infoResultDict = {}
    for element in rows:
        row = rows[element]
        entrypointSel = row[0]
        walletSel = row[1]
        tezAmount = int(row[len(row)-1])
        if row[2:len(row)-1] == []:
            parameters = []
        else:
            parameters = row[2:len(row)-1]
         
        addressValid = getAddress()
        contractAddress = addressValid[contract]
        contractInterface = pytezos.contract(contractAddress)
        entrypoints = contractInterface.entrypoints
        if entrypointSel not in entrypoints:
            raise "Entrypoint not found: " + entrypointSel
        
        with open("wallet.json", 'r', encoding='utf-8') as file:
                wallet = json.load(file)
        key = wallet[walletSel]
        client = pytezos.using(shell="ghostnet", key=key)
        
        opResult = entrypointCall(client=client, contractAddress=contractAddress, entrypointName=entrypointSel, parameters=parameters, tezAmount=tezAmount)
        infoResult = callInfoResult(opResult=opResult)
        infoResult["contract"] = contract
        infoResult["entryPoint"] = entrypointSel

        infoResultDict[element] = infoResult

    return infoResultDict
    
def exportResult(opResult):
    fileName = "transactionsOutput"
    csvWriter(fileName=fileName+".csv", op_result=opResult)
    print("\nCSV Updated!\n\n")
    jsonWriter(fileName=fileName+".json", opReport=opResult)
    print("\nJSON Updated!\n\n")
        
    
      
def main():
    print("Hi, welcome to the Tezos-Contract toolchain!\n")
    print("Here you can compile, deploy or interact with any contract from the archive.\n")
    
    stdPath = "../contracts/"
    operationSel = int(input("Now, select an option: \n"
        "1 Compile\n" 
        "2 Deploy\n" 
        "3 Interact\n"
        "4 Use Execution Trace\n"))

    if operationSel != 4:
        walletSel = input("Which account do you want to use?\n")
        with open("wallet.json", 'r', encoding='utf-8') as file:
            wallet = json.load(file)
            
        key = wallet[walletSel]
        client = pytezos.using(shell="ghostnet", key=key)
    
        allContracts = folderScan("../contracts")
        print("\nContracts avaiable: \n")
        i = 1
        for contract in allContracts:
            print(i," " + contract)
            i += 1
   
        contractSel = int(input("Which contract do you want to use?\n"))
        contract = allContracts[contractSel-1]
    
    match operationSel:
        case 1:
            contractPath = stdPath+contract+"/"+contract+".py"
            compileContract(contractPath=contractPath)
            main()
        
        case 2: 
            if Path("./"+contract).exists():   
                michelsonPath = Path(f"./{contract}/step_001_cont_0_contract.tz").read_text()
                storagePath = Path(f"./{contract}/step_001_cont_0_storage.tz").read_text()
                initialBalance = int(input("Insert an initial balance:"))
                op_result = origination(client=client, michelsonCode=michelsonPath, initialStorage=storagePath, initialBalance=initialBalance)
                contractInfo = contractInfoResult(op_result=op_result)
                addressUpdate(contract=contract, newAddress=contractInfo["address"])
            else:
                print("\n\033[1m Contract must be compiled before \033[0m\n\n")
            
            main()
            
        case 3: 
            op_report = interactionSetup(client=client, contract=contract)
            sel = input("Do you want to export the result?(y/n):  ")
            if sel == "y":
                exportResult(opResult=op_report)
            main()
        
        case 4:
            contractExecutionTraces = csvReader()
            for contract in contractExecutionTraces:
                results = executionSetup(contract=contract, rows=contractExecutionTraces[contract])
                for result in results:
                    exportResult(results[result])
            
            main()
            
    
    
        
    