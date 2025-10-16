# MIT License
#
# Copyright (c) 2025 Manuel Boi - Università degli Studi di Cagliari
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.


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

