import smartpy as sp

@sp.module
def main():
    class Auction(sp.Contract):
        def __init__ (self, startingBid, time, admin):
            self.data.admin = admin
            self.data.top = sp.record(address = None ,amount = sp.mutez(0))
            self.data.startBid = startingBid
            self.data.duration = time
            self.data.isStart = False
            
        
        @sp.entrypoint
        def start(self):
           #check if the caller is the admin
            assert sp.sender == self.data.admin, "You are not the admin"
            
            #start the auction
            self.data.isStart = True 
        
        @sp.entrypoint
        def bid(self):
            #check if the Auction is started
            assert self.data.isStart == True, "The auction is not started yet"
            
            #check if the bid is grater then the current one
            assert sp.amount > self.data.top.amount, "The bid has to be greater"
            
            if not self.data.top.address == None: #refund
                sp.send(self.data.top.address.unwrap_some(), self.data.top.amount)
                
            self.data.top.address = sp.Some(sp.sender)
            self.data.top.amount = sp.amount
            

        @sp.entrypoint
        def end(self):
            #check if the caller is the admin
            assert sp.sender == self.data.admin, "You are not the admin"

            #check if deadline is reached
            assert sp.now >= self.data.duration, "Deadline is not reached"
            
            #withdraw all the assets
            sp.send(self.data.admin, sp.balance)
            
                      
        


@sp.add_test()
def test():
    #set scenario
    sc = sp.test_scenario("Auction",main)
    #create admin
    admin = sp.test_account("admin")
    #create time 
    time = sp.timestamp_from_utc_now() #calculate execution time
    #new object Auction
    auction = main.Auction(sp.mutez(5), time, admin.address)
    #start scenario
    sc += auction


    