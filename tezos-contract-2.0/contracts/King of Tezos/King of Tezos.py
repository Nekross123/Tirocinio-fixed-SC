import smartpy as sp

@sp.module
def main():
    class Throne(sp.Contract):
        def __init__(self, admin):
            self.data.king = admin
            self.data.history = {None : sp.record(value = None, data = None)}
            self.data.floorPrice = sp.mutez(5000)
        
        @sp.entrypoint
        def newKing(self):
            #verify amount
            assert sp.amount == self.data.floorPrice, "Amount incorrect"
            #refund previous king
            #sp.if self.data.king != self.data.admin: with # send to admin the revenue
            sp.send(self.data.king, sp.amount)
            #update history
            self.data.history[sp.Some(sp.sender)] = sp.record(value = sp.Some(sp.amount), data = sp.Some(sp.now))
            self.data.king = sp.sender
            #update price -> plus 10%
            self.data.floorPrice += sp.fst(sp.ediv(self.data.floorPrice, sp.nat(10)).unwrap_some()) 
    
        @sp.entrypoint
        def killKing(self):
            #reset king
            self.data.king = sp.sender
            #reset floorPrice
            self.data.floorPrice = sp.mutez(5000)
        

@sp.add_test()
def test():
    #create scenario
    sc = sp.test_scenario("KingOfTezos", main)
    #create admin
    admin = sp.test_account("admin")
    #object Lottery
    throne = main.Throne(admin.address)
    #start scenario
    sc.h1("Initial State")
    sc += throne
     
