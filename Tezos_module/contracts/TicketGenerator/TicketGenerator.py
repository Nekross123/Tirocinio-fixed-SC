import smartpy as sp

@sp.module
#types definition
def t():
    tickets : type = sp.map[sp.nat, sp.ticket[sp.string]]
@sp.module
def m():
    class TicketGenerator(sp.Contract):
        def __init__(self, _admin):
            self.data.admin  = _admin
            #self.data.tickets = sp.cast({}, t.tickets)
            self.data.token_id = 0

        @sp.entrypoint
        def createToken(self):
            c = sp.contract(sp.ticket[sp.string], self.data.admin).unwrap_some()
            sp.transfer(sp.ticket("Primo", 1), sp.tez(0), c)
            self.data.token_id += 1
        

@sp.add_test()
def test():
    sc = sp.test_scenario("TicketGenerator", [t, m])
    owner = sp.test_account("owner")
    c1 = m.TicketGenerator(owner.address)
    sc += c1

    sc.h1("ciao")
    c1.createToken()