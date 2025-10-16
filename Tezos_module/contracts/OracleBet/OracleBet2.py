import smartpy as sp

@sp.module
def main():
    class OracleBet(sp.Contract):
        def __init__(self):
            self.data.player1 = None
            self.data.player1Withdraw = None
            self.data.player2 = None
            self.data.player2Deposit = False
            self.data.player2Withdraw = None
            self.data.oracle = None
            self.data.winner = None
            self.data.deadline = 1000

            
        @sp.entrypoint
        def stipulation(self, params):
            assert self.data.player1 == None, "There's already a player 1"
            assert sp.amount == sp.tez(1), "Amount incorrect, must be 1 tez"
            assert not params._oracle == sp.sender, "You can't be the oracle"
            
            self.data.player1 = sp.Some(sp.sender)
            
            self.data.oracle = sp.Some(params._oracle)
            self.data.player2 = sp.Some(params._player2)
            
            self.data.deadline += sp.level

        @sp.entrypoint
        def deposit2(self):
            assert sp.sender == self.data.player2.unwrap_some(), "You are not player 2"
            assert sp.amount == sp.tez(1), "Amount incorrect, must be 1 tez"
            assert self.data.player2Deposit == False, "You already deposited"
            assert sp.level <= self.data.deadline, "Deadline reached"
            
            self.data.player2Deposit = True
            
        
        @sp.entrypoint
        def redeem(self):
            assert sp.sender == self.data.winner.unwrap_some(), "You are not the winner"
            
            sp.send(sp.sender, sp.balance)
            
        @sp.entrypoint
        def withdraw(self):
            assert sp.sender == self.data.player1.unwrap_some() or sp.sender == self.data.player2.unwrap_some(), "You are not a player"
            assert self.data.winner == None, "There's a winner"
            assert sp.level > self.data.deadline, "Deadline not reached"
            
            if sp.sender == self.data.player1.unwrap_some():
                assert self.data.player1Deposit == True, "You didn't deposit yet"
                assert self.data.player1Withdraw == None, "You already withdrew"
                self.data.player1Withdraw = True
            else:
                assert self.data.player2Deposit == True, "You didn't deposit yet"
                assert self.data.player2Withdraw == None, "You already withdrew"
                self.data.player2Withdraw = True
            
            sp.send(sp.sender, sp.balance)

        @sp.entrypoint
        def election(self, _winner):
            assert sp.sender == self.data.oracle.unwrap_some(), "You are not the oracle"
            assert not self.data.player1 == None and self.data.player2Deposit == True, "1(2) player(s) didn't deposit yet"
            assert sp.level <= self.data.deadline, "Deadline reached"
            assert _winner == self.data.player1.unwrap_some() or _winner == self.data.player2.unwrap_some(), "The winner you insert is not a player"

            self.data.winner = sp.Some(_winner)



@sp.add_test()
def test():
    #set scenario
    sc = sp.test_scenario("OracleBet",main)
    #create object simple wallet
    OracleBet = main.OracleBet()
    #start scenario
    sc += OracleBet
    
    

    
    
    


            
            


    