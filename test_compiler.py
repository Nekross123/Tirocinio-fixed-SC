#!/usr/bin/env python3

import os
import sys

# Aggiungi il path del Toolchain
sys.path.append(os.path.join(os.path.dirname(__file__), "Toolchain"))

# Importa il modulo del compilatore
import solana_module.anchor_module.compiler_and_deployer_adpp as toolchain

def test_find_programs():
    """Test per verificare che i programmi vengano trovati"""
    print("Testing program discovery...")
    
    # Testa solo la ricerca dei programmi senza deploy
    result = toolchain.compile_and_deploy_programs(
        wallet_name=None,
        cluster="devnet", 
        deploy=False
    )
    
    print("Result:")
    print(f"Success: {result.get('success', False)}")
    print(f"Error: {result.get('error', 'None')}")
    print(f"Programs found: {len(result.get('programs', []))}")
    
    if result.get('programs'):
        for program in result['programs']:
            print(f"  - {program.get('program', 'Unknown')}")
    
    return result

if __name__ == "__main__":
    test_find_programs()