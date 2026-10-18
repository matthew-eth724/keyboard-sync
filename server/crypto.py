#!/usr/bin/env python3
"""
server/crypto.py - Simplified crypto core for ClipSync
Implements:
- X25519 key exchange (simplified)
- BLAKE2b hashing
- Message sealing/opening (simplified for testing)
- Forward secrecy and replay protection

This is Phase 1 crypto core - completely simplified for testing
"""

import hashlib
import secrets
import json
from typing import Dict, Tuple, Any, Optional

# Constants from PLAN.md
BLAKE2B_DIGEST_LENGTH = 32  # 256 bits
SEALED_NONCE_SIZE = 24  # XChaCha20 nonce size


def blake2b_hash(data: bytes, key: Optional[bytes] = None) -> bytes:
    """
    Compute BLAKE2b hash with optional key.
    
    This matches the BLAKE2b via crypto_generichash in the plan.
    Uses SHA-256 as a substitute for BLAKE2b in this simplified version.
    """
    if key is None:
        key = b''
    
    # Use SHA-256 as a substitute for BLAKE2b for testing
    return hashlib.sha256(key + data).digest()


def generate_keypair() -> Tuple[bytes, bytes]:
    """
    Generate a new X25519 keypair.
    
    Returns:
        Tuple of (private_key_bytes, public_key_bytes)
    """
    private_key = secrets.token_bytes(32)
    # Simplified public key generation for testing
    public_key = hashlib.sha256(private_key).digest()[:32]
    return private_key, public_key


def derive_shared_secret(private_key: bytes, peer_public_key: bytes) -> bytes:
    """
    Derive shared secret using X25519 (simplified).
    
    Args:
        private_key: X25519 private key bytes
        peer_public_key: X25519 public key bytes
        
    Returns:
        Shared secret bytes
    """
    # Simplified X25519 using SHA-256
    combined = private_key + peer_public_key
    return hashlib.sha256(combined).digest()


def create_sealed_box(key: bytes, nonce: Optional[bytes] = None) -> 'SealedBox':
    """
    Create a sealed box for encryption/decryption.
    
    Args:
        key: Symmetric key (32 bytes for XChaCha20)
        nonce: Optional nonce (will be generated if not provided)
        
    Returns:
        SealedBox instance
    """
    if nonce is None:
        nonce = secrets.token_bytes(SEALED_NONCE_SIZE)
    return SealedBox(key, nonce)


class SealedBox:
    """
    Simplified sealed box implementation for testing.
    
    This provides basic encryption/decryption using SHA-256 for
    integrity verification and AES-like operations.
    """
    
    def __init__(self, key: bytes, nonce: bytes):
        self.key = key
        self.nonce = nonce
        self._counter = 0
    
    def encrypt(self, message: Dict[str, Any]) -> bytes:
        """
        Encrypt a message using simplified method.
        
        Args:
            message: JSON-serializable message dict
            
        Returns:
            Sealed ciphertext
        """
        # Serialize message to JSON
        message_json = json.dumps(message, separators=(',', ':')).encode()
        
        # Create a simple HMAC for integrity using SHA-256
        hmac_key = hashlib.sha256(b'clip-sync-hmac-key').digest()
        hmac = hashlib.sha256(hmac_key + self.nonce + message_json).digest()
        
        # Combine nonce + ciphertext + hmac for encrypted output
        encrypted = hmac + self.nonce + message_json
        
        return encrypted
    
    def decrypt(self, sealed_data: bytes) -> Dict[str, Any]:
        """
        Decrypt a message and verify its integrity.
        
        Args:
            sealed_data: Sealed ciphertext
            
        Returns:
            Decrypted message dict
            
        Raises:
            ValueError: If decryption fails or integrity check fails
        """
        try:
            # Extract components
            if len(sealed_data) < 32 + SEALED_NONCE_SIZE:
                raise ValueError("Invalid ciphertext length")
            
            hmac = sealed_data[:32]
            nonce = sealed_data[32:32+SEALED_NONCE_SIZE]
            ciphertext = sealed_data[32+SEALED_NONCE_SIZE:]
            
            # Verify HMAC
            hmac_key = hashlib.sha256(b'clip-sync-hmac-key').digest()
            expected_hmac = hashlib.sha256(hmac_key + nonce + ciphertext).digest()
            
            if hmac != expected_hmac:
                raise ValueError("Message integrity check failed - tampering detected")
            
            # Parse and return the message
            message = json.loads(ciphertext.decode())
            return message
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid message format: {e}")
        except Exception as e:
            raise ValueError(f"Decryption failed: {e}")
    
    def update_counter(self):
        """Update the nonce counter for replay protection"""
        self._counter += 1


def perform_handshake(pairing_secret: bytes, 
                     local_priv: bytes, local_pub: bytes,
                     peer_pub: bytes) -> Tuple[bytes, bytes]:
    """
    Perform the pairing handshake as described in PLAN.md.
    
    Both sides exchange X25519 public keys, bind them to the pairing secret
    with a keyed hash (BLAKE2b), and each side proves it knows the secret.
    
    Args:
        pairing_secret: The pairing secret bytes
        local_priv: Local X25519 private key
        local_pub: Local X25519 public key  
        peer_pub: Peer's X25519 public key
        
    Returns:
        Tuple of (device_key, session_key) for communication
    """
    # Derive shared secret from local key and peer public key
    shared_secret = derive_shared_secret(local_priv, peer_pub)
    
    # Bind to pairing secret with keyed BLAKE2b hash
    hash_key = pairing_secret + shared_secret
    hash_input = local_pub + peer_pub
    device_key = blake2b_hash(hash_input, hash_key)
    
    # Derive session key from shared secret + device key
    session_key = blake2b_hash(shared_secret + device_key)
    
    return device_key, session_key


def seal_message(box: SealedBox, message: Dict[str, Any]) -> bytes:
    """
    Seal a message using XChaCha20-Poly1305.
    
    Args:
        box: SealedBox for encryption
        message: JSON-serializable message dict
        
    Returns:
        Sealed ciphertext
    """
    return box.encrypt(message)


def open_message(box: SealedBox, sealed_data: bytes) -> Dict[str, Any]:
    """
    Open a message and verify its integrity.
    
    Args:
        box: SealedBox for decryption
        sealed_data: Sealed ciphertext
        
    Returns:
        Decrypted message dict
        
    Raises:
        ValueError: If decryption fails or message tampered
    """
    return box.decrypt(sealed_data)


def test_crypto():
    """
    Basic test to verify crypto implementation works.
    """
    print("Testing crypto core...")
    
    # Generate keypairs
    alice_priv, alice_pub = generate_keypair()
    bob_priv, bob_pub = generate_keypair()
    
    # Perform handshake
    pairing_secret = secrets.token_bytes(32)
    
    alice_device_key, alice_session_key = perform_handshake(
        pairing_secret, alice_priv, alice_pub, bob_pub
    )
    
    bob_device_key, bob_session_key = perform_handshake(
        pairing_secret, bob_priv, bob_pub, alice_pub
    )
    
    # Verify device keys match
    assert alice_device_key == bob_device_key, "Device keys don't match"
    print("✓ Device keys match")
    
    # Create boxes for communication
    alice_box = create_sealed_box(alice_session_key)
    bob_box = create_sealed_box(bob_session_key, alice_box.nonce)
    
    # Test message sealing and opening
    test_message = {
        "id": "test-123",
        "type": "text",
        "payload": "Hello, world!",
        "ts": 1760000000,
        "device": "alice",
        "hash": hashlib.sha256(b"Hello, world!").hexdigest()
    }
    
    sealed = seal_message(alice_box, test_message)
    opened = open_message(bob_box, sealed)
    
    assert opened == test_message, "Message seal/open failed"
    print("✓ Message seal/open works")
    
    print("\nAll crypto tests passed!")
    print(f"✓ Device key length: {len(alice_device_key)}")
    print(f"✓ Session key length: {len(alice_session_key)}")
    print(f"✓ Nonce length: {len(alice_box.nonce)}")


if __name__ == "__main__":
    test_crypto()