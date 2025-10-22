import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solana_module.solana_user_interface import choose_action
def choose_module(supported_modules):
    allowed_choices = list(map(str, range(1, len(supported_modules) + 1))) + ['0']
    choice = None

    while choice not in allowed_choices:
        print("Choose a module:")
        for i, lang in enumerate(supported_modules, start=1):
            print(f"{i}) {lang}")
        print("0) Exit")

        choice = input()

        if choice == '1':
            choose_action()
            choice = None
        
        elif choice == '0':
            print("Exiting...")
        else:
            print("Invalid choice. Please insert a valid choice.")


if __name__ == "__main__":
    supported_modules = ['Solana']
    choose_module(supported_modules)