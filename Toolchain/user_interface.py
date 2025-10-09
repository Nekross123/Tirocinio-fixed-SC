# MIT License
#
# Copyright (c) 2025 Manuel Boi - Università degli Studi di Cagliari
#1
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


import os
import sys

# Aggiungi la directory parent al Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solana_module.solana_user_interface import choose_action
# ADD HERE NEW MODULES REQUIRED IMPORTS (STARTING FROM THE PROJECT ROOT)


def choose_module(supported_modules):
    # Manage allowed choices
    allowed_choices = list(map(str, range(1, len(supported_modules) + 1))) + ['0']
    choice = None

    # Print available choices
    while choice not in allowed_choices:
        print("Choose a module:")
        for i, lang in enumerate(supported_modules, start=1):
            print(f"{i}) {lang}")
        print("0) Exit")

        choice = input()

        if choice == '1':
            choose_action()
            choice = None # Reset choice
        # ADD HERE NEW MODULE CALLS (elif)
        elif choice == '0':
            print("Exiting...")
        else:
            print("Invalid choice. Please insert a valid choice.")


if __name__ == "__main__":
    # ADD HERE NEW SUPPORTED MODULES
    supported_modules = ['Solana']

    # Start toolchain
    choose_module(supported_modules)