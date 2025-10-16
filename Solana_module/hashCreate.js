#!/usr/bin/env node

const { keccak256 } = require('js-sha3');

function generateHashlock(secret) {
    // Converti la stringa in bytes
    const secretBytes = Buffer.from(secret, 'utf8');
    
    // Calcola keccak256 hash
    const hash = keccak256(secretBytes);
    
    // Converti in array di uint8 (come richiesto da Solana)
    const hashArray = Buffer.from(hash, 'hex');
    const uint8Array = Array.from(hashArray);
    
    return uint8Array;
}

function findSecretForHash(targetHashArray, maxAttempts = 1000000) {
    console.log('🔍 Cercando segreto per hash:', targetHashArray.join(' '));
    
    // Prova vari formati di segreti
    const patterns = [
        (i) => `secret${i}`,
        (i) => `player_secret_${i}`,
        (i) => `lottery_${i}`,
        (i) => `test_${i}`,
        (i) => `${i}`,
        (i) => `key_${i}`,
        (i) => `hash_${i}`
    ];
    
    for (let pattern of patterns) {
        for (let i = 0; i < maxAttempts; i++) {
            const secret = pattern(i);
            const hash = generateHashlock(secret);
            
            if (arraysEqual(hash, targetHashArray)) {
                console.log(`✅ TROVATO! Segreto: "${secret}"`);
                console.log(`   Hash: ${hash.join(' ')}`);
                return secret;
            }
            
            if (i % 10000 === 0) {
                console.log(`   Provato ${i} combinazioni per pattern ${pattern.toString()}...`);
            }
        }
    }
    
    console.log('❌ Segreto non trovato con i pattern testati');
    return null;
}

function arraysEqual(a, b) {
    return a.length === b.length && a.every((val, index) => val === b[index]);
}

// Se eseguito direttamente da terminale
if (require.main === module) {
    const args = process.argv.slice(2);
    
    if (args.length === 0) {
        console.log('📋 USO:');
        console.log('  node generate_hashlock.js "mio_segreto"                    - Genera hash');
        console.log('  node generate_hashlock.js find "189 128 128 0 0..."        - Trova segreto');
        console.log('  node generate_hashlock.js both "segreto1" "segreto2"       - Genera entrambi');
        console.log('');
        console.log('🎯 I tuoi hashlock target:');
        console.log('  Hashlock1: 189 128 128 0 0 0 0 0 64 0 64 128 0 64 0 64 0 64 0 64 0 64 128 0 0 0 0 64 128 0 64 0');
        console.log('  Hashlock2: 128 192 0 0 56 0 0 0 0 0 0 64 128 0 0 0 0 64 128 0 0 0 0 64 0 64 0 0 0 0 0 0');
        return;
    }
    
    if (args[0] === 'find') {
        // Trova segreto per hash fornito
        const hashString = args[1];
        if (!hashString) {
            console.log('❌ Fornisci l\'hash come stringa di numeri separati da spazi');
            return;
        }
        
        const targetHash = hashString.split(' ').map(n => parseInt(n.trim()));
        if (targetHash.length !== 32) {
            console.log('❌ L\'hash deve essere di 32 numeri');
            return;
        }
        
        findSecretForHash(targetHash);
        
    } else if (args[0] === 'both') {
        // Genera entrambi gli hash
        const secret1 = args[1] || 'player1_secret';
        const secret2 = args[2] || 'player2_secret';
        
        console.log('🎲 GENERAZIONE HASHLOCK PER LOTTERY');
        console.log('=====================================');
        console.log('');
        
        const hash1 = generateHashlock(secret1);
        const hash2 = generateHashlock(secret2);
        
        console.log(`🔑 Segreto Player 1: "${secret1}"`);
        console.log(`   Hashlock1: ${hash1.join(' ')}`);
        console.log('');
        console.log(`🔑 Segreto Player 2: "${secret2}"`);
        console.log(`   Hashlock2: ${hash2.join(' ')}`);
        console.log('');
        
        // Calcola vincitore
        const sum = secret1.length + secret2.length;
        const winner = sum % 2 === 0 ? 'Player 1' : 'Player 2';
        
        console.log('🏆 PREVISIONE VINCITORE:');
        console.log(`   Lunghezza segreto 1: ${secret1.length}`);
        console.log(`   Lunghezza segreto 2: ${secret2.length}`);
        console.log(`   Somma: ${sum}`);
        console.log(`   ${sum} % 2 = ${sum % 2}`);
        console.log(`   Vincitore: ${winner}`);
        
    } else {
        // Genera hash per un singolo segreto
        const secret = args[0];
        console.log(`🔒 Generando hashlock per: "${secret}"`);
        
        const hash = generateHashlock(secret);
        console.log(`📋 Hashlock: ${hash.join(' ')}`);
        console.log(`📋 Hex: ${Buffer.from(hash).toString('hex')}`);
    }
}

module.exports = { generateHashlock, findSecretForHash };