import smartpy as sp

@sp.module
def main():
    class Logic(sp.Contract):
        def __init__(self, admin):
            self.data.admin = admin
        
        @sp.entrypoint
        def check(self, value):
            assert value < 100, "The balance is more than 100"
    
    class Proxy(sp.Contract):
        def __init__(self, admin, logicAddress):
            self.data.admin = admin
            self.data.logicAddress = logicAddress
            
        @sp.entrypoint
        def upgradeTo(self, address):
            assert sp.sender == self.data.admin, "You are not the admin"
            
            self.data.logicAddress = address
            
        @sp.entrypoint
        def check(self, value):
            contract = sp.contract(sp.mutez, self.data.logicAddress , entrypoint="check")
            sp.transfer(value, sp.tez(0), contract.unwrap_some(error="ContractNotFound"))
            
        
    class Caller(sp.Contract):
        def __init__ (self, admin):
            self.data.admin = admin
            
        @sp.entrypoint
        def callLogicByProx(self, address):
            contract = sp.contract(sp.mutez, address , entrypoint="check")
            sp.transfer(sp.balance, sp.tez(0), contract.unwrap_some(error="ContractNotFound"))