import asyncio
from Solana_module.solana_module.solana_utilities import request_balance, get_public_key, close_program
from Solana_module.solana_module.anchor_module import anchor_user_interface
# ADD HERE NEW SOLANA LANGUAGES REQUIRED IMPORTS (STARTING FROM THE PROJECT ROOT)

def choose_action():
    allowed_choices = ['1', '2', '0']
    choice = None

    while choice not in allowed_choices:
        print("Choose an option:")
        print("1) Choose language")
        print("2) Utilities")
        print("0) Back to module selection")

        choice = input()

        if choice == '1':
            _choose_language()
            choice = None
        elif choice == '2':
            _choose_utility()
            choice = None
        elif choice == '0':
            return
        else:
            print("Invalid choice. Please insert a valid choice.")

def _choose_language():
    supported_languages = ['Anchor']

    allowed_choices = list(map(str, range(1, len(supported_languages) + 1))) + ['0']
    choice = None

    while choice not in allowed_choices:
        print("Choose a language:")
        for i, lang in enumerate(supported_languages, start=1):
            print(f"{i}) {lang}")
        print("0) Back to Solana menu")

        choice = input()

        if choice == '1':
            anchor_user_interface.choose_action()
            choice = None
        elif choice == '0':
            return
        else:
            print("Invalid choice. Please insert a valid choice.")

def _choose_utility():
    choice = None

    while choice != '0':
        print("What you wanna do?")
        print("1) Request balance")
        print("2) Get public key from wallet")
        print("3) Close program on blockchain")
        print("0) Back to Solana menu")

        choice = input()

        if choice == '1':
            request_balance()
            choice = None
        elif choice == '2':
            get_public_key()
            choice = None
        elif choice == '3':
            close_program()
        elif choice == '0':
            return
        else:
            print("Invalid choice. Please insert a valid choice.")

