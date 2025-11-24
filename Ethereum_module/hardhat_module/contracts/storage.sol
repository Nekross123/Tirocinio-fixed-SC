// SPDX-License-Identifier: GPL-3.0
// ↑ Licenza open source richiesta da Ethereum
// GPL-3.0 = GNU General Public License versione 3
// Senza questa riga, il compilatore da WARNING

pragma solidity ^0.8.0;
// ↑ Definisce la versione del compilatore Solidity
// ^0.8.0 = Compatibile con versioni 0.8.0 fino a 0.9.0 (esclusa)
// pragma = direttiva di compilazione (come #include in C)

contract Storage {
// ↑ Definisce un nuovo contratto chiamato "Storage"
// contract = parola chiave come "class" in altri linguaggi
// Storage = nome del contratto (deve essere uguale al nome file)
// { inizia il corpo del contratto

    bytes public byteSequence;
    // ↑ Variabile di stato (salvata permanentemente sulla blockchain)
    // bytes = array dinamico di byte (come Vec<u8> in Rust)
    // public = visibilità pubblica, crea automaticamente getter function
    // byteSequence = nome della variabile
    // Salvata nello storage slot 0 della blockchain
    
    string public textString;
    // ↑ Seconda variabile di stato per memorizzare testo
    // string = sequenza di caratteri UTF-8 (internamente è bytes)
    // public = crea automaticamente function textString() returns (string)
    // textString = nome della variabile
    // Salvata nello storage slot 1 della blockchain

    function storeBytes(bytes memory _byteSequence) public {
    // ↑ Definisce una funzione pubblica per salvare bytes
    // function = parola chiave per dichiarare funzione
    // storeBytes = nome della funzione
    // bytes memory _byteSequence = parametro di input
    //   - bytes = tipo di dato
    //   - memory = locazione in memoria temporanea (non storage)
    //   - _byteSequence = nome del parametro (underscore è convenzione)
    // public = chiunque può chiamare questa funzione
    // { inizia il corpo della funzione
    
        byteSequence = _byteSequence;
        // ↑ Assegnazione che copia i dati da memory a storage
        // byteSequence = variabile di stato (storage slot 0)
        // _byteSequence = parametro della funzione (memory)
        // = operatore di assegnazione (copia automatica memory → storage)
        // Questa operazione COSTA GAS perché modifica la blockchain
    }
    // ↑ Fine della funzione storeBytes

    function storeString(string memory _textString) public {
    // ↑ Funzione per salvare stringhe di testo
    // function storeString = nome della funzione
    // string memory _textString = parametro stringa in memoria temporanea
    // public = accessibile dall'esterno del contratto
    
        textString = _textString;
        // ↑ Copia la stringa da memory a storage permanente
        // textString = variabile di stato (storage slot 1)
        // _textString = parametro ricevuto (memory)
        // Operazione costosa in gas perché scrive sulla blockchain
    }
    // ↑ Fine della funzione storeString

}
// ↑ Fine del contratto Storage