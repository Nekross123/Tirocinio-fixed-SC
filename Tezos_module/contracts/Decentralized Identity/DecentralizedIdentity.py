import smartpy as sp

print("Decentralized Identity")
@sp.module
def main():
    class DecentralizedIdentity(sp.Contract):
        # Define the contract's data
        def __init__(self, owner1, owner2):
            self.data.owner1 = owner1
            self.data.owner2 = owner2
            self.data.ownership = {None : None}
            
        @sp.entrypoint
        def changeOwner(self, admin):
            sp.cast(admin, sp.address)
            self.data.ownership[sp.Some(admin)] = sp.Some(admin)
            
            
@sp.add_test()
def test():
    #set scenario
    sc = sp.test_scenario("DecentralizedIdentity",main)
    #create admin
    admin = sp.test_account("admin")
    #create users
    pippo = sp.test_account("pippo")
    #create object
    DecentIdent = main.DecentralizedIdentity(admin.address,pippo.address)
    #start scenario
    sc += DecentIdent


    #entrypoint calls
    DecentIdent.changeOwner(admin.address)