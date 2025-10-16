#!/usr/bin/env python3
"""
Script per generare wallet Ethereum crittografati
Autore: Rosetta Smart Contract Toolchain
Data: 2025
"""

import json
import secrets
import getpass
import os
import sys
from datetime import datetime
from eth_account import Account

def generate_wallet():
    """Genera un nuovo wallet Ethereum (crittografato o non crittografato)"""
    
    print("🔐 Generatore Wallet Ethereum")
    print("=" * 35)
    
    # Genera chiave privata sicura
    print("📝 Generazione chiave privata sicura...")
    private_key = "0x" + secrets.token_hex(32)
    
    # Crea account
    account = Account.from_key(private_key)
    print(f"✅ Account creato: {account.address}")
    
    # Chiedi tipo di wallet
    print("\n🔒 Tipo di wallet:")
    print("1. Wallet crittografato (sicuro)")
    print("2. Wallet NON crittografato (solo per testing)")
    
    while True:
        choice = input("Scegli opzione (1-2): ").strip()
        if choice in ['1', '2']:
            break
        print("❌ Scelta non valida")
    
    if choice == '1':
        # Wallet crittografato
        print("\n🔒 Configurazione crittografia:")
        while True:
            password = getpass.getpass("Inserisci password: ")
            password_confirm = getpass.getpass("Conferma password: ")
            
            if password == password_confirm and len(password) >= 8:
                break
            print("❌ Password non valide o troppo corte (min 8 caratteri)")
        
        encrypted_keystore = Account.encrypt(private_key, password)
        wallet_data = {
            "address": account.address,
            "encrypted": True,
            "created_at": datetime.now().isoformat(),
            "keystore": encrypted_keystore,
            "note": "Wallet crittografato - serve password"
        }
        wallet_type = "crittografato"
        
    else:
        # Wallet NON crittografato
        print("\n⚠️  ATTENZIONE: Wallet NON crittografato!")
        print("   Solo per testing locale - mai in produzione!")
        confirm = input("Confermi? (y/N): ").lower()
        if confirm != 'y':
            print("❌ Operazione annullata")
            return None, None
        
        wallet_data = {
            "address": account.address,
            "private_key": private_key,
            "encrypted": False,
            "created_at": datetime.now().isoformat(),
            "note": "Wallet NON crittografato - solo per testing!"
        }
        wallet_type = "non crittografato"
    
    # Nome file
    print(f"\n📁 Salvataggio wallet...")
    default_name = f"wallet_{account.address[-8:].lower()}"
    filename = input(f"Nome file (default: {default_name}): ").strip()
    
    if not filename:
        filename = default_name
    
    if not filename.endswith('.json'):
        filename += '.json'
    
    # Salva file
    try:
        with open(filename, 'w') as f:
            json.dump(wallet_data, f, indent=2)
        
        print(f"\n🎉 Wallet salvato con successo!")
        print(f"📍 File: {filename}")
        print(f"📍 Indirizzo: {account.address}")
        print(f"📍 Percorso completo: {os.path.abspath(filename)}")

        
        return filename, account.address
        
    except Exception as e:
        print(f"❌ Errore nel salvataggio: {e}")
        return None, None

def load_wallet():
    """Carica e decritta un wallet esistente per test"""
    
    filename = input("Nome file wallet da testare: ")
    if not filename.endswith('.json'):
        filename += '.json'
    
    if not os.path.exists(filename):
        print(f"❌ File {filename} non trovato")
        return
    
    try:
        with open(filename, 'r') as f:
            wallet_data = json.load(f)
        
        
        
        
        # Decritta
        private_key = Account.decrypt(wallet_data['keystore'], password)
        account = Account.from_key(private_key)
        
        print(f"✅ Wallet decrittato con successo!")
        print(f"📍 Indirizzo: {account.address}")
        print(f"🔑 Chiave privata: {private_key.hex()}")
        
    except Exception as e:
        print(f"❌ Errore: {e}")
        print("   Probabilmente password errata o file corrotto")

def main():
    """Menu principale"""
    
    while True:
        print(f"\n🔐 Wallet Manager")
        print("1. Genera nuovo wallet")
        print("2. Testa wallet esistente")
        print("3. Esci")
        
        choice = input("\nScegli opzione (1-3): ").strip()
        
        if choice == '1':
            generate_wallet()
        elif choice == '2':
            load_wallet()
        elif choice == '3':
            print("👋 Arrivederci!")
            break
        else:
            print("❌ Scelta non valida")

if __name__ == "__main__":
    main()