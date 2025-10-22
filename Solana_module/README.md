# Fee Toolchain – Solana Module

## Overview

This repository contains the source code of the toolchain developed as part of the master's thesis.  
The goal of the project is to provide a modular and extensible toolchain for estimating transaction **fees** and **sizes** for smart contracts deployed (or not yet deployed) on the **Solana** blockchain, specifically those written using the **Anchor** framework.

The toolchain is designed with modularity in mind and integrates several components including:

- **Smart Contract Builder and Deployer**
- **Data Insertion Manager**, both automatic and interactive.
- **Transaction manager**, which computes fees and size, and eventually send transactions.
- **Utility functions** for balance retrieval, contract introspection, and cleanup.

Future extensions aim to support other blockchains and smart contract languages, such as Ethereum (Solidity), Cardano (Aiken), and Algorand (PyTeal).

---

## Repository Structure

- 📄 README.md                               # This file
- 📄 user_interface                          # Main program to run
- 📁 images/                                 # Images from the thesis (see below)
- 📁 solana_module/                          # Solana module
  - 📄 requirements.txt                      # Python dependencies for Solana module
  - 📄 solana_user_interface                 # User interface of Solana module
  - 📄 solana_utilities                      # Utility functions for Solana
  - 📄 solana_utils                          # Solana utils functions used by other packages
  - 📁 solana_wallets/                       # Wallets used for execution and testing
  - 📁 anchor_module/                        # Anchor Module
    - 📄 requirements.txt                    # Python dependencies for Anchor module
    - 📄 anchor_user_interface               # User interface of Anchor module
    - 📄 program_compiler_and_deployer       # Package to compile and eventually deploy programs
    - 📄 interactive_data_insertion_manager  # Package which manage the interactive insertion of data to build contract calls
    - 📄 automatic_data_insertion_manager    # Package which manage insertion of data through execution traces
    - 📄 transaction_manager                 # Package which manage size and fee computation, and transaction sending
    - 📄 anchor_utilities                    # Utility functions for Anchor
    - 📄 anchor_utils                        # Anchor utils functions used by other packages
    - 📁 anchor_programs/                    # Smart contracts to compile
    - 📁 execution_traces/                   # CSV traces defining contract interactions

---

## Diagrams

This folder contains images which may be useful to understand the architecture and design of the toolchain.

- **Component Diagram**: `images/component_diagram.png`  
- **Package Diagram**: `images/package_diagram.png`

You can view them in the `images/` folder. These diagrams show the modular structure of the system and how different components interact with each other.

---
