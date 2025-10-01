import smartpy as sp


@sp.module
def main():
    class OracleBet(sp.Contract):
        def __init__(self):
            self.data.player1 = None
            self.data.player1Deposit = False
            self.data.player2 = None
            self.data.player2Deposit = False
            self.data.oracle = None
            self.data.winner = None
            self.data.deadline = sp.level + 1000

            
        @sp.entrypoint
        def deposit(self, params):
            player2 = sp.Some(params.player2)
            oracle = sp.Some(params.oracle)
            if self.data.player1 == None:
                assert sp.amount == sp.tez(1), "Amount incorrect, must be 1 tez"
                
                self.data.player1 = sp.Some(sp.sender)
                self.data.player1Deposit = True
                assert not oracle.unwrap_some() == sp.sender, "You can't be the oracle"
                self.data.oracle = oracle

                self.data.player2 = player2

            else: 
                raise "Error, entrypoint already called"
                

        @sp.entrypoint
        def deposit2(self):
            if self.data.player2 != None:
                assert sp.sender == self.data.player2.unwrap_some(), "You are not player 2"
                assert sp.amount == sp.tez(1), "Amount incorrect, must be 1 tez"
                
                self.data.player2 = sp.Some(sp.sender)
                self.data.player2Deposit = True
            else:
                raise "Error, wait for player1 deposit first"


        @sp.entrypoint
        def withdraw(self):
            assert sp.sender == self.data.player1.unwrap_some() or sp.sender == self.data.player2.unwrap_some(), "You are not a player"
            assert not self.data.winner == None, "The oracle didn't select any winner yet"
            assert sp.sender == self.data.winner.unwrap_some(), "You are not the winner"

            sp.send(sp.sender, sp.balance)

        @sp.entrypoint
        def election(self, _winner):
            assert sp.sender == self.data.oracle.unwrap_some(), "You are not the oracle"
            assert self.data.player1Deposit == True and self.data.player2Deposit == True, "1(2) player(s) didn't deposit yet"
            assert sp.level >= self.data.deadline, "You have to wait for deadline"

            self.data.winner = sp.Some(_winner)

@sp.add_test()
def test():
    #set scenario
    sc = sp.test_scenario("OracleBet",main)
    #create object simple wallet
    OracleBet = main.OracleBet()
    #start scenario
    sc += OracleBet

    
    

    
    
    


            
            


    