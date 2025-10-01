import csv
from folderScan import *

def csvReader():
    executionTraces = folderScan("execution_traces")
    executionTracesDict = {}
    try:
        for trace in executionTraces:
            fileName = "execution_traces/"+trace
            rows = {}
            
            with open(fileName, mode='r', newline='', encoding='utf-8') as file_csv:
                csv_read = csv.reader(file_csv, delimiter = ",")

                i = 0
                for row in csv_read:
                    rows[row.pop(0)] = row
                    i += 1
                    
            executionTracesDict[trace.replace(".csv","")] = rows
            
        return executionTracesDict
    
    except FileNotFoundError:
        print(f"Error: File '{fileName}' not found.")
    except Exception as e:
        print(f"Error: {e}")
    


def csvWriter(fileName, op_result):
    '''
    with open(fileName, mode='r', newline='', encoding='utf-8') as file_csv:
        csv_read = csv.reader(file_csv)
    ''' 
        
    newRow = [op_result["contract"], op_result["entryPoint"], op_result["TotalCost"], op_result["Weight"], op_result["Hash"]]
    with open(fileName, mode='a', newline='', encoding='utf-8') as file_csv:
        writer = csv.writer(file_csv)

        writer.writerow(newRow)
    