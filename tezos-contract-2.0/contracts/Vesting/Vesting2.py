import smartpy as sp

@sp.module
def main():
    class Vesting(sp.Contract):
        # Define the contract's data
        def __init__(self, _beneficiary, _start, _duration):
            self.data.beneficiary = _beneficiary
            self.data.start = _start
            self.data.duration = _duration

        @sp.entrypoint
        def release(self):
            assert sp.sender == self.data.beneficiary, "you are not the beneficiary"
            
            assert sp.now >= self.data.start, "Release not started"

            if sp.now > sp.add_days(self.data.start, self.data.duration):
                sp.send(sp.sender, sp.balance)
            else:
                vesting = sp.ediv(sp.mul(sp.balance, sp.as_nat(sp.now - self.data.start)), sp.as_nat(self.data.duration))
                released = sp.fst(vesting.unwrap_some())
                sp.send(sp.sender, released)
                
            
                
                
            
@sp.add_test()
def test():
    #set scenario
    sc = sp.test_scenario("Vesting2", main)
    #create users
    beneficiary = sp.test_account("beneficiary")
    #create object
    c1 = main.Vesting(beneficiary.address, sp.now, 5)
    #start scenario
    sc += c1



