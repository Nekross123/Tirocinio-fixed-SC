import smartpy as sp
    
@sp.module
def main():
    class PaymentSplitter(sp.Contract):
        def __init__(self, admin, owners):
            self.data.admin = admin
            self.data.owners = sp.cast(owners, sp.map[sp.address, sp.nat])

        @sp.entrypoint
        def receive(self):
            #deposit
            pass
            
        
        @sp.entrypoint
        def release(self):
            #send shares
            sp.send(sp.sender, sp.split_tokens(sp.balance, self.data.owners[sp.sender], 100))


@sp.add_test()
def test():
    # set scenario
    sc = sp.test_scenario("PaymentSplitter", main)
    admin = sp.test_account("admin")
    mario = sp.test_account("mario")
    map = { admin.address : sp.nat(80), mario.address : sp.nat(20)}
    # create object
    paymentSplitter = main.PaymentSplitter(admin.address, map)
    # start scenario
    sc += paymentSplitter

    sc.h1("Receive")
    paymentSplitter.receive(_amount = sp.tez(100), _sender = admin)

    sc.h1("Release")
    paymentSplitter.release(_sender = admin)
    