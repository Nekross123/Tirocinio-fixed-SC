import smartpy as sp

@sp.module
def t():
    player_ : type = sp.record(
        address = sp.address,
        deposit = sp.bool, 
        withdraw = sp.bool
    ).layout(("address", ("deposit", "withdraw")))
    
    game_ : type = sp.record(
        oracle = sp.address,
        winner = sp.address,
        stake = sp.mutez,
        deadline = sp.nat
    ).layout(("oracle", ("winner", ("stake", "deadline"))))

    stipulation_ : type = sp.record(
        oracle = sp.address,
        player2 = sp.address
    ).layout(("oracle", "player2"))
    
@sp.module
def main():
    class OracleBet(sp.Contract):
        def __init__(self):
            self.data.player1 = sp.cast(
                sp.record(
                    address = sp.address(""), 
                    deposit = False,
                    withdraw = False
                ),
                t.player_
            )
            self.data.player2 = sp.cast(
                sp.record(
                    address = sp.address(""), 
                    deposit = False,
                    withdraw = False
                ),
                t.player_
            )
            self.data.game = sp.cast(
                sp.record(
                    oracle = sp.address(""),
                    winner = sp.address(""),
                    stake = sp.mutez(0),
                    deadline = 1000
                ),
                t.game_
            )

        
        @sp.entrypoint
        def stipulation(self, params):
            sp.cast(
                params, 
                t.stipulation_
                )
            assert self.data.player1.address == sp.address(""), "There's already a player 1"
            assert sp.amount >= sp.mutez(1), "Amount incorrect, must be greater then 1 mutez"
            assert not params.oracle == sp.sender, "You can't be the oracle"
            
            self.data.player1.address = sp.sender
            self.data.player1.deposit = True
            
            self.data.game.oracle = params.oracle
            self.data.player2.address = params.player2
            
            self.data.game.deadline += sp.level
        
        @sp.entrypoint
        def deposit(self):
            assert sp.sender == self.data.player2.address, "You are not player 2"
            assert sp.amount == self.data.game.stake, "Amount incorrect, must be equal to stake"
            assert self.data.player2.deposit == False, "You already deposited"
            assert sp.level <= self.data.game.deadline, "Deadline reached"
            
            self.data.player2.deposit = True
            
          
        @sp.entrypoint
        def timeout(self):
            assert self.data.game.winner == sp.address(""), "There's a winner"
            assert sp.level > self.data.game.deadline, "Deadline not reached"
            assert self.data.player1.deposit == True or self.data.player2.deposit == True, "Anyone deposited yet"
            
            if self.data.player1.deposit == True and self.data.player1.withdraw == False:
                self.data.player1.withdraw = True
                sp.send(self.data.player1.address, sp.tez(1))
           
            if self.data.player2.deposit == True and self.data.player2.withdraw == False :
                self.data.player2.withdraw = True
                sp.send(self.data.player2.address, sp.tez(1))
                
        
        @sp.entrypoint
        def win(self, winner):
            assert sp.sender == self.data.game.oracle, "You are not the oracle"
            assert not self.data.player1.address == sp.address("") and self.data.player2.deposit == True, "1(2) player(s) didn't deposit yet"
            assert sp.level <= self.data.game.deadline, "Deadline reached"
            assert winner == self.data.player1.address or winner == self.data.player2.address, "The winner you insert is not a player"

            self.data.game.winner = winner
            
            sp.send(winner, sp.balance)
            



@sp.add_test()
def test():
    #set scenario
    sc = sp.test_scenario("OracleBet",[t, main])
    #create object simple wallet
    OracleBet = main.OracleBet()
    #start scenario
    sc += OracleBet