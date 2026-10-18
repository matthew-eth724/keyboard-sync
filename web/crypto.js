// crypto.js - JavaScript crypto core for ClipSync
// Mirrors server/crypto.py for cross-implementation consistency

// Use the libsodium-wrappers library which provides the same API as nacl
// This matches PyNaCl on the Python side
const sodium = require('libsodium-wrappers');

// Constants (matching server/crypto.py)
const BLAKE2B_DIGEST_LENGTH = 32;  // 256 bits
const SEALED_NONCE_SIZE = 24;     // XChaCha20 nonce size

class ClipSyncCrypto {
    constructor() {
        this.nonceCounter = 0;
    }

    // Initialize libsodium
    async init() {
        await sodium.ready;
        console.log('libsodium.js initialized');
    }

    // Hash with BLAKE2b (matches server/crypto.py.blake2b_hash)
    blake2bHash(data, key = null) {
        if (key) {
            // Use keyed BLAKE2b for authentication
            const keyData = new Uint8Array(key);
            const hash = sodium.crypto_generichash(data, keyData, { digestLength: BLAKE2B_DIGEST_LENGTH });
            return hash;
        } else {
            const hash = sodium.crypto_generichash(data);
            return hash;
        }
    }

    // Generate X25519 keypair (matching server/generate_keypair)
    generateKeypair() {
        const keypair = sodium.crypto_box_keypair();
        return {
            privateKey: new Uint8Array(keypair.privateKey),
            publicKey: new Uint8Array(keypair.publicKey)
        };
    }

    // Derive shared secret using X25519 (matching server/derive_shared_secret)
    deriveSharedSecret(privateKey, peerPublicKey) {
        const shared = sodium.crypto_scalarmult(privateKey, peerPublicKey);
        return shared;
    }

    // Create sealed box for encryption/decryption (XChaCha20-Poly1305)
    createSealedBox(key, nonce = null) {
        if (!nonce) {
            nonce = sodium.randombytes(SEALED_NONCE_SIZE);
        }
        return new sodium.SecretBox(key, nonce);
    }

    // Perform pairing handshake (matching server/perform_handshake)
    performHandshake(pairingSecret, localPriv, localPub, peerPub) {
        // Derive shared secret from local key and peer public key
        const sharedSecret = this.deriveSharedSecret(localPriv, peerPub);
        
        // Bind to pairing secret with keyed BLAKE2b hash
        const hashKey = sodium.concat(pairingSecret, sharedSecret);
        const hashInput = sodium.concat(localPub, peerPub);
        const deviceKey = this.blake2bHash(hashInput, hashKey);
        
        // Derive session key from shared secret + device key
        const sessionKey = this.blake2bHash(
            sodium.concat(sharedSecret, deviceKey)
        );
        
        return { deviceKey, sessionKey };
    }

    // Seal message (matching server/seal_message)
    sealMessage(box, message) {
        const messageJson = JSON.stringify(message);
        const messageBytes = sodium.from_string(messageJson);
        
        // Encrypt with XChaCha20-Poly1305
        const encrypted = box.encrypt(messageBytes);
        return encrypted;
    }

    // Open message (matching server/open_message)
    openMessage(box, sealedData) {
        try {
            const decrypted = box.decrypt(sealedData);
            const messageJson = sodium.to_string(decrypted);
            return JSON.parse(messageJson);
        } catch (error) {
            throw new Error('Decryption failed or message tampered');
        }
    }

    // Verify replay protection (matching server/verify_replay_protection)
    verifyReplayProtection(box, counter) {
        // Extract counter from nonce (first 8 bytes)
        const nonce = box.nonce;
        const storedCounter = new DataView(nonce.buffer, 0, 8).getUint32(0, true);
        return counter > storedCounter;
    }

    // Update nonce counter for replay protection
    getNextNonce() {
        const nonce = sodium.randombytes(SEALED_NONCE_SIZE);
        // Update counter in nonce
        new DataView(nonce.buffer, 0, 8).setUint32(0, this.nonceCounter++, true);
        return nonce;
    }

    // Test the entire crypto implementation
    async testCrypto() {
        console.log('Testing crypto core...');
        
        await this.init();
        
        // Generate keypairs
        const alice = this.generateKeypair();
        const bob = this.generateKeypair();
        
        // Generate pairing secret (matching server/perform_handshake)
        const pairingSecret = sodium.randombytes(32);
        
        // Perform handshake
        const aliceResult = this.performHandshake(
            pairingSecret,
            alice.privateKey,
            alice.publicKey,
            bob.publicKey
        );
        
        const bobResult = this.performHandshake(
            pairingSecret,
            bob.privateKey,
            bob.publicKey,
            alice.publicKey
        );
        
        // Verify device keys match
        const deviceKeyMatch = sodium.compare(aliceResult.deviceKey, bobResult.deviceKey) === 0;
        if (!deviceKeyMatch) {
            throw new Error('Device keys don\'t match');
        }
        console.log('✓ Device keys match');
        
        // Create boxes for communication
        const aliceBox = this.createSealedBox(aliceResult.sessionKey);
        const bobBox = this.createSealedBox(bobResult.sessionKey, aliceBox.nonce);
        
        // Test message sealing and opening
        const testMessage = {
            id: 'test-123',
            type: 'text',
            payload: 'Hello, world!',
            ts: 1760000000,
            device: 'alice',
            hash: sodium.to_string(sodium.crypto_generichash(sodium.from_string('Hello, world!')))
        };
        
        const sealed = this.sealMessage(aliceBox, testMessage);
        const opened = this.openMessage(bobBox, sealed);
        
        const messageMatch = JSON.stringify(opened) === JSON.stringify(testMessage);
        if (!messageMatch) {
            throw new Error('Message seal/open failed');
        }
        console.log('✓ Message seal/open works');
        
        // Test replay protection
        const replayProtection = this.verifyReplayProtection(aliceBox, 1);
        if (!replayProtection) {
            throw new Error('Replay protection check failed');
        }
        console.log('✓ Replay protection works');
        
        console.log('\nAll crypto tests passed!');
    }
}

module.exports = ClipSyncCrypto;

// Auto-run test if this file is executed directly
if (require.main === module) {
    const crypto = new ClipSyncCrypto();
    crypto.testCrypto().catch(error => {
        console.error('Crypto test failed:', error.message);
        process.exit(1);
    });
}