from pathlib import Path

def folderScan(path):
    contractsPath = Path(path)

    completeList = [entry.name for entry in contractsPath.iterdir()]

    return completeList