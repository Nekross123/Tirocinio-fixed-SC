# MIT License
#
# Copyright (c) 2025 Manuel Boi, Palumbo Lorenzo, Piras Mauro - Università degli Studi di Cagliari
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
from Solana_module.solana_module.anchor_module.automatic_data_insertion_manager import run_execution_trace
from Solana_module.solana_module.anchor_module.anchor_utilities import choose_program_for_pda_generation, get_initialized_programs, \
    get_program_instructions, get_instruction_args, get_instruction_accounts, close_anchor_program, \
    remove_anchor_program
from Solana_module.solana_module.anchor_module.program_compiler_and_deployer import compile_programs
from Solana_module.solana_module.anchor_module.interactive_data_insertion_manager import choose_program_to_run

def choose_action():
    """Top-level Anchor CLI menu: compile, run, or open utilities."""
    allowed_choices = ["1", "2", "3", "0"]
    choice = None

    while choice != "0":
        print("What you wanna do?")
        print("1) Compile new program(s)")
        print("2) Run program")
        print("3) Utilities")
        print("0) Back to language selection")

        choice = input()
        if choice == "1":
            compile_programs()
        elif choice == "2":
            _choose_running_mode()
        elif choice == "3":
            _choose_utility()
        elif choice == "0":
            return
        elif choice not in allowed_choices:
            print("Please insert a valid choice.")

def _choose_running_mode():
    """Choose between interactive or automatic execution trace mode."""
    allowed_choices = ["1", "2", "0"]
    choice = None

    while choice != "0":
        print("Which mode?")
        print("1) Interactive mode")
        print("2) Automatic mode")
        print("0) Back to Anchor menu")

        choice = input()
        if choice == "1":
            repeat = choose_program_to_run()
            if repeat:
                choice = None
            else:
                return
        elif choice == "2":
            asyncio.run(run_execution_trace())
            return
        elif choice == "0":
            return
        elif choice not in allowed_choices:
            print("Please insert a valid choice.")

def _choose_utility():
    """Utilities menu: list programs, inspect IDL, generate PDA, close/remove."""
    allowed_choices = ["1", "2", "3", "4", "5", "6", "0"]
    choice = None

    while choice != "0":
        print("What you wanna do?")
        print("1) Get available programs")
        print("2) Get program instructions")
        print("3) Get instruction accounts")
        print("4) Get instruction args")
        print("5) Generate PDA key")
        print("6) Remove initialized Anchor program")
        print("7) Close and remove initialized Anchor program")
        print("0) Back to Anchor menu")

        choice = input()
        if choice == "1":
            get_initialized_programs()
        if choice == "2":
            get_program_instructions()
        if choice == "3":
            get_instruction_accounts()
        if choice == "4":
            get_instruction_args()
        elif choice == "5":
            choose_program_for_pda_generation()
        elif choice == "6":
            remove_anchor_program()
        elif choice == "7":
            close_anchor_program()
        elif choice == "0":
            return
        elif choice not in allowed_choices:
            print("Please insert a valid choice.")