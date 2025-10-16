import smartpy as sp
from smartpy.templates import fa2_lib as fa2

@sp.module
#Type Definition
def types():
    exam_grade: type = sp.record(name = sp.string, grade = sp.nat, date = sp.timestamp)
    
    ledger_transcript: type = sp.big_map[sp.address, sp.list[exam_grade]]
    
    
@sp.module
def m():         
    class CommonInterface(main.OwnerOrOperatorTransfer):
        def __init__(self):
            main.OwnerOrOperatorTransfer.__init__(self)
            
        @sp.private()
        def balance_(self, params):
            """Return the balance of an account.
            Must be redefined in child"""
            sp.cast(params, t.balance_params)
            raise "NotImplemented"
            return 0

        @sp.private()
        def is_defined_(self, token_address):
            """Return True if the token is defined, else otherwise.
            Must be redefined in child"""
            sp.cast(token_address, sp.address)
            raise "NotImplemented"
            return False
            
    class Common(CommonInterface):
        def __init__(self): 
            CommonInterface.__init__(self)
    class NftInterface(sp.Contract):
        def __init__(self):
            self.data.ledger = sp.cast(sp.big_map(), types.ledger_transcript)
            self.private.ledger_type = "SBT"
    class Nft(NftInterface, Common):
        def __init__(self): 
            Common.__init__(self) 
            NftInterface.__init__(self)
    class Admin(sp.Contract):
        """(Mixin) Provide the basics for having an administrator in the contract.

        Adds an `administrator` attribute in the storage. Provides a
        `set_administrator` entrypoint.
        """

        def __init__(self, administrator):
            self.data.administrator = administrator

        @sp.private(with_storage="read-only")
        def is_administrator_(self):
            return sp.sender == self.data.administrator

        @sp.entrypoint
        def set_administrator(self, administrator):
            """(Admin only) Set the contract administrator."""
            assert self.is_administrator_(), "FA2_NOT_ADMIN"
            self.data.administrator = administrator
    class MintNft(main.AdminInterface, NftInterface, CommonInterface):
        def __init__(self):
            CommonInterface.__init__(self)
            NftInterface.__init__(self)
            main.AdminInterface.__init__(self)

        @sp.entrypoint
        def mint(self, batch):
            """Admin can mint new or existing tokens."""
            sp.cast(
                batch,
                sp.list[
                    sp.record(
                        to_=sp.address,
                        metadata=types.exam_grade,
                    ).layout(("to_", "metadata"))
                ],
            )
            assert self.is_administrator_(), "FA2_NOT_ADMIN"
            for action in batch:
                self.data.ledger[action.to_] = [action.metadata]
                
    class TokenGenerator(
        Admin,
        Nft,
        MintNft,
    ):
        def __init__(self, administrator):
            MintNft.__init__(self)
            Nft.__init__(self) 
            Admin.__init__(self, administrator)
            

                   
def make_metadata(batch):
    '''
    sp.cast(
        batch,
        sp.list[
        sp.
        ]
    )
    return sp.map(
        l={
            "name": name,
            "symbol": sp.scenario_utils.bytes_of_string(symbol),
            "image" : sp.scenario_utils.bytes_of_string(image),
        }
    )    
    '''

@sp.add_test()
def test():  
    #Create Scenario
    sc = sp.test_scenario("SBT", [fa2.t, fa2.main, types, m])
    #Create Users
    owner = sp.test_account("owner")
    #create Contract Object
    sc.h1("TokenGenerator Contract Creation")   
    sc.h3("Empty Value")
    c1 = m.TokenGenerator(
        administrator = owner.address
    )
    sc += c1

    '''
    tok0_md = make_metadata(name="Token Zero", decimals=1, symbol="Tok0", image = "imagine")
    sc.h1("Mint a new token")
    c1.mint(
         [
             sp.record(
                 to_  = owner.address, # Who will receive the original mint
                 metadata = tok0_md
             )
         ],
         _sender=owner)
         '''
    



