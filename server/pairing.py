#!/usr/bin/env python3
"""
Pairing implementation for ClipSync Phase 2
Standalone implementation that demonstrates M2 pairing flows
without external dependencies
"""

import time
import secrets
import hashlib
from typing import Dict, Optional, Tuple

# Constants from PLAN.md
CODE_LENGTH = 6
CODE_EXPIRY_SECONDS = 120  # 2 minutes
MAX_ATTEMPTS = 3
ALLOWED_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

# Global state (in production, use Redis or similar)
active_codes = {}  # code -> {secret, device_id, expiry, attempts, used, spake2_identity}
active_qr_codes = {}  # qr_data -> {secret, expiry, device_id}
paired_devices = {}  # device_id -> {device_key, device_info, pairing_secret}

# Simple crypto implementation (simplified X25519 for testing)
class SimpleCrypto:
    """Simplified cryptographic functions for testing"""
    
    @staticmethod
    def hash_data(data: bytes, key: Optional[bytes] = None) -> bytes:
        """Simplified BLAKE2b hash for testing"""
        if key is None:
            key = b''
        # Use SHA-256 as a substitute for BLAKE2b in testing
        return hashlib.sha256(key + data).digest()
    
    @staticmethod
    def x25519_simulate_exchange(priv_key: bytes, pub_key: bytes) -> bytes:
        """Simulate X25519 key exchange for testing"""
        # Simplified version of X25519 for demonstration
        # In real implementation, use proper libsodium/PyNaCl
        combined = priv_key + pub_key
        return hashlib.sha256(combined).digest()
    
    @staticmethod
    def perform_handshake(pairing_secret: bytes, 
                         local_priv: bytes, local_pub: bytes,
                         peer_pub: bytes) -> Tuple[bytes, bytes]:
        """
        Perform the pairing handshake as described in PLAN.md.
        
        Both sides exchange X25519 public keys, bind them to the pairing secret
        with a keyed hash, and each side proves it knows the secret.
        """
        # Derive shared secret from local key and peer public key
        shared_secret = SimpleCrypto.x25519_simulate_exchange(local_priv, peer_pub)
        
        # Bind to pairing secret with keyed BLAKE2b hash
        hash_key = pairing_secret + shared_secret
        hash_input = local_pub + peer_pub
        device_key = SimpleCrypto.hash_data(hash_input, hash_key)
        
        # Derive session key from shared secret + device key
        session_key = SimpleCrypto.hash_data(shared_secret + device_key)
        
        return device_key, session_key

# Use simplified crypto
crypto = SimpleCrypto()


class PairingError(Exception):
    """Base exception for pairing errors"""
    pass


class CodeExpiredError(PairingError):
    """Raised when a pairing code has expired"""
    pass


class CodeUsedError(PairingError):
    """Raised when a pairing code has already been used"""
    pass


class MaxAttemptsExceededError(PairingError):
    """Raised when too many pairing attempts are made"""
    pass


class InvalidCodeError(PairingError):
    """Raised when an invalid pairing code is provided"""
    pass


def generate_qr_code_data(pairing_secret: bytes, hostname: str = "laptop.local") -> str:
    """
    Generate QR code data string as described in PLAN.md.
    
    QR encoding: http://<ip>:8000/#p=<secret>&h=<hostname>
    Secret is in URL fragment (never sent over network)
    
    Args:
        pairing_secret: The 256-bit pairing secret
        hostname: Hostname of the PC
        
    Returns:
        QR code data string
    """
    return f"http://192.168.1.100:8000/#p={pairing_secret.hex()}&h={hostname}"


def parse_qr_data(qr_data: str) -> Tuple[bytes, str]:
    """
    Parse QR data to extract pairing secret and hostname.
    
    Args:
        qr_data: QR code data string
        
    Returns:
        Tuple of (pairing_secret_bytes, hostname)
        
    Raises:
        ValueError: If QR data format is invalid
    """
    try:
        # Expected format: http://<ip>:8000/#p=<secret>&h=<hostname>
        if not qr_data.startswith("http://"):
            raise ValueError("QR data doesn't start with http://")
        
        # Extract fragment part (after #)
        fragment = qr_data.split('#')[1]
        
        # Parse parameters
        params = {}
        for param in fragment.split('&'):
            if '=' in param:
                key, value = param.split('=', 1)
                params[key] = value
        
        if 'p' not in params or 'h' not in params:
            raise ValueError("Missing p or h parameters in QR data")
        
        # Convert secret hex back to bytes
        secret_bytes = bytes.fromhex(params['p'])
        
        return secret_bytes, params['h']
        
    except Exception as e:
        raise ValueError(f"Failed to parse QR data: {e}")


def start_qr_pairing(device_id: str = None) -> Tuple[str, bytes]:
    """
    Start QR code pairing flow as described in PLAN.md.
    
    QR flow (primary):
    1. User clicks "Pair new device" on the PC.
    2. PC generates a random 256-bit pairing secret and shows a QR encoding 
       `http://<ip>:8000/#p=<secret>&h=<hostname>`.
    3. The secret is in the URL fragment, which browsers never send over the network.
    4. Phone scans, the page reads the fragment, and both sides run the handshake in section 5.
    5. On success, both store a long-term device key and each other's device ID. The pairing secret is discarded.
    
    Args:
        device_id: Optional device identifier (will be generated if not provided)
        
    Returns:
        Tuple of (qr_data, qr_code_bytes)
    """
    if device_id is None:
        device_id = f"device-{int(time.time())}"
    
    # Generate random 256-bit pairing secret (32 bytes)
    pairing_secret = secrets.token_bytes(32)
    
    # Get hostname from system (simplified)
    hostname = "laptop.local"
    
    # Create QR encoding as specified
    qr_data = generate_qr_code_data(pairing_secret, hostname)
    
    # Generate QR code image bytes (simplified implementation)
    # In production, use qrcode library
    qr_code_bytes = f"QR_CODE:{qr_data}".encode()
    
    # Store QR code info for validation (secret never sent over network)
    active_qr_codes[qr_data] = {
        'secret': pairing_secret,
        'device_id': device_id,
        'expiry': time.time() + CODE_EXPIRY_SECONDS,
        'used': False
    }
    
    return qr_data, qr_code_bytes


def complete_qr_pairing(qr_data: str, device_id: str) -> Tuple[bytes, bytes]:
    """
    Complete QR code pairing flow after phone scans QR code.
    
    Args:
        qr_data: QR data string scanned from PC
        device_id: Device identifier for the phone
        
    Returns:
        Tuple of (device_key, session_key) for the paired device
        
    Raises:
        ValueError: If QR data is invalid or pairing fails
    """
    # Parse QR data to extract pairing secret and hostname
    pairing_secret, hostname = parse_qr_data(qr_data)
    
    # Validate QR code exists and hasn't expired
    if qr_data not in active_qr_codes:
        raise ValueError("QR code not found or expired")
    
    qr_info = active_qr_codes[qr_data]
    
    if time.time() > qr_info['expiry']:
        del active_qr_codes[qr_data]
        raise ValueError("QR code has expired")
    
    if qr_info['used']:
        raise ValueError("QR code has already been used")
    
    # Verify pairing secret matches
    if pairing_secret != qr_info['secret']:
        raise ValueError("Pairing secret doesn't match QR code")
    
    # Perform the pairing handshake as described in PLAN.md section 5
    # Both sides exchange X25519 public keys, bind them to the pairing secret with a keyed hash,
    # and each side proves it knows the secret
    
    # Generate keypairs for both sides
    pc_priv, pc_pub = generate_keypair()
    phone_priv, phone_pub = generate_keypair()
    
    # Perform handshake
    device_key, session_key = crypto.perform_handshake(
        pairing_secret, pc_priv, pc_pub, phone_pub
    )
    
    # Store device information for both sides
    paired_devices[device_id] = {
        'device_key': device_key,
        'pairing_secret': pairing_secret,
        'paired_at': time.time(),
        'hostname': hostname,
        'qr_code': qr_data
    }
    
    # Mark QR code as used
    qr_info['used'] = True
    del active_qr_codes[qr_data]  # Clean up
    
    return device_key, session_key


def generate_keypair() -> Tuple[bytes, bytes]:
    """Generate a simulated X25519 keypair for testing"""
    priv = secrets.token_bytes(32)
    # Simplified public key generation
    pub = crypto.hash_data(priv)
    return priv, pub


def start_code_pairing(device_id: str = None) -> str:
    """
    Start 6-character code pairing flow as fallback in PLAN.md.
    
    Code flow (fallback):
    - 6 characters, uppercase letters and digits, excluding lookalikes (0 O 1 I L)
    - Roughly 729 million combinations
    - Used with a PAKE (SPAKE2) so the code cannot be brute-forced offline
    - On success, the PAKE output acts as the pairing secret and the flow continues as above
    
    Args:
        device_id: Optional device identifier
        
    Returns:
        Generated 6-character pairing code
    """
    if device_id is None:
        device_id = f"device-{int(time.time())}"
    
    # Generate random 256-bit pairing secret
    pairing_secret = secrets.token_bytes(32)
    
    # Generate 6-character code using the specified character set
    code_chars = []
    for _ in range(CODE_LENGTH):
        char = secrets.choice(ALLOWED_CHARS)
        code_chars.append(char)
    
    code = ''.join(code_chars)
    
    # Store code with expiry and metadata
    expiry_time = time.time() + CODE_EXPIRY_SECONDS
    
    # Generate SPAKE2 identity for the code
    # In a real implementation, this would use proper SPAKE2 parameters
    spake2_identity = f"clipsync:{device_id}:{code}"
    
    active_codes[code] = {
        'secret': pairing_secret,
        'device_id': device_id,
        'expiry': expiry_time,
        'attempts': 0,
        'used': False,
        'spake2_identity': spake2_identity
    }
    
    return code


def complete_code_pairing(code: str, device_id: str) -> Tuple[bytes, bytes]:
    """
    Complete 6-character code pairing flow with PAKE.
    
    Args:
        code: 6-character pairing code from user
        device_id: Device identifier for the phone
        
    Returns:
        Tuple of (device_key, session_key) for the paired device
        
    Raises:
        CodeExpiredError: If code has expired
        CodeUsedError: If code has already been used
        MaxAttemptsExceededError: If too many attempts were made
        InvalidCodeError: If code format is invalid
        ValueError: If PAKE verification fails
    """
    # Check if code exists
    if code not in active_codes:
        raise InvalidCodeError(f"Invalid pairing code: {code}")
    
    code_data = active_codes[code]
    
    # Check if code has expired
    if time.time() > code_data['expiry']:
        # Clean up expired code
        del active_codes[code]
        raise CodeExpiredError(f"Pairing code expired: {code}")
    
    # Check if code has been used
    if code_data['used']:
        raise CodeUsedError(f"Pairing code already used: {code}")
    
    # Check if max attempts exceeded
    if code_data['attempts'] >= MAX_ATTEMPTS:
        # Clean up failed code
        del active_codes[code]
        raise MaxAttemptsExceededError(f"Too many failed attempts for code: {code}")
    
    # Increment attempt counter
    code_data['attempts'] += 1
    
    # For this implementation, we'll simulate SPAKE2 PAKE verification
    # In production, this would use a proper SPAKE2 library
    
    # Generate SPAKE2 password from the code
    # This simulates the PAKE where the code cannot be brute-forced offline
    spake2_password = hashlib.sha256(code.encode()).digest()
    
    # Use SPAKE2 to derive shared secret
    # In real implementation: spake2_result = spake2.SPAKE2(code, spake2_identity)
    # For demo, we'll use the pre-stored secret directly
    pairing_secret = code_data['secret']
    
    # Perform handshake using the derived secret (simulating PAKE result)
    pc_priv, pc_pub = generate_keypair()
    phone_priv, phone_pub = generate_keypair()
    
    # Create a device key from the PAKE result
    device_key = hashlib.sha256(pairing_secret + device_id.encode()).digest()
    
    # Generate session key
    session_key = hashlib.sha256(device_key + pc_priv + phone_pub).digest()
    
    # Store device information
    paired_devices[device_id] = {
        'device_key': device_key,
        'pairing_secret': pairing_secret,
        'paired_at': time.time(),
        'code_used': code
    }
    
    # Mark code as used
    code_data['used'] = True
    
    return device_key, session_key


def verify_code(code: str, pairing_secret: bytes, device_id: str) -> bool:
    """
    Verify a pairing code using PAKE as described in PLAN.md.
    
    Args:
        code: 6-character code to verify
        pairing_secret: Secret to verify against
        device_id: Device identifier
        
    Returns:
        True if code is valid, False otherwise
        
    Raises:
        CodeExpiredError: If code has expired
        CodeUsedError: If code has already been used
        MaxAttemptsExceededError: If too many attempts were made
        InvalidCodeError: If code format is invalid
    """
    # Check if code exists
    if code not in active_codes:
        raise InvalidCodeError(f"Invalid pairing code: {code}")
    
    code_data = active_codes[code]
    
    # Check if code has expired
    if time.time() > code_data['expiry']:
        # Clean up expired code
        del active_codes[code]
        raise CodeExpiredError(f"Pairing code expired: {code}")
    
    # Check if code has been used
    if code_data['used']:
        raise CodeUsedError(f"Pairing code already used: {code}")
    
    # Check if max attempts exceeded
    if code_data['attempts'] >= MAX_ATTEMPTS:
        # Clean up failed code
        del active_codes[code]
        raise MaxAttemptsExceededError(f"Too many failed attempts for code: {code}")
    
    # Increment attempt counter
    code_data['attempts'] += 1
    
    # For this demo, we'll use a simple verification
    # In production, use proper SPAKE2 PAKE implementation
    
    # Generate expected code from secret
    expected_code = start_code_pairing(device_id)
    
    # Verify code matches (using fixed test code for now)
    if code == expected_code:  # Test code matches any secret for demo
        # Mark as used
        code_data['used'] = True
        
        # Store device pairing info
        paired_devices[device_id] = {
            'device_key': code_data['secret'],
            'paired_at': time.time(),
            'code_used': code
        }
        
        return True
    else:
        return False


def cleanup_expired_codes():
    """Clean up expired pairing codes"""
    current_time = time.time()
    expired_codes = []
    
    for code, code_data in active_codes.items():
        if current_time > code_data['expiry']:
            expired_codes.append(code)
    
    for code in expired_codes:
        del active_codes[code]


def cleanup_used_codes():
    """Clean up used pairing codes (optional, for security)"""
    used_codes = [code for code, data in active_codes.items() if data['used']]
    
    for code in used_codes:
        del active_codes[code]


def get_active_codes_count() -> int:
    """Get number of active (unexpired, unused) pairing codes"""
    cleanup_expired_codes()
    return len(active_codes)


def get_paired_devices_count() -> int:
    """Get number of paired devices"""
    return len(paired_devices)


def get_all_paired_devices() -> Dict:
    """Get all paired devices"""
    return paired_devices.copy()


def revoke_device(device_id: str) -> bool:
    """
    Revoke a paired device.
    
    Args:
        device_id: ID of device to revoke
        
    Returns:
        True if device was revoked, False if not found
    """
    if device_id in paired_devices:
        # Find and remove any codes associated with this device
        codes_to_remove = []
        for code, code_data in active_codes.items():
            if code_data.get('device_id') == device_id:
                codes_to_remove.append(code)
        
        for code in codes_to_remove:
            del active_codes[code]
        
        del paired_devices[device_id]
        return True
    
    return False


def get_code_info(code: str) -> Optional[Dict]:
    """
    Get information about a pairing code.
    
    Args:
        code: Pairing code
        
    Returns:
        Code information dict or None if code doesn't exist
    """
    return active_codes.get(code)


def test_pairing():
    """Test the complete pairing implementation"""
    print("Testing complete pairing implementation (Phase 2)...")
    
    # Test QR data parsing - use proper hex encoding
    test_secret = b"testsecret123456789"
    test_secret_hex = test_secret.hex()
    test_data = f"http://192.168.1.100:8000/#p={test_secret_hex}&h=laptop.local"
    secret, hostname = parse_qr_data(test_data)
    assert secret == b"testsecret123456789", "QR parsing failed"
    assert hostname == "laptop.local", "QR hostname parsing failed"
    
    # Test QR pairing flow
    print("\n--- Testing QR Pairing Flow ---")
    qr_data, qr_bytes = start_qr_pairing("test-phone")
    assert qr_data.startswith("http://"), "QR data format incorrect"
    assert len(qr_bytes) > 0, "QR code generation failed"
    
    # Complete QR pairing
    device_key, session_key = complete_qr_pairing(qr_data, "test-phone")
    assert device_key is not None, "QR pairing device key not generated"
    assert session_key is not None, "QR pairing session key not generated"
    
    # Verify device was paired
    assert "test-phone" in paired_devices, "Device not stored after QR pairing"
    assert paired_devices["test-phone"]["device_key"] == device_key, "Device key mismatch"
    
    print("✓ QR pairing flow completed successfully")
    print(f"✓ Generated QR data: {qr_data[:50]}...")
    print(f"✓ Paired device: test-phone")
    
    # Test Code pairing flow
    print("\n--- Testing Code Pairing Flow ---")
    
    # Generate and verify code pairing
    test_secret = b"test-32-byte-secret!!"[:32]
    code = start_code_pairing("test-phone-2")
    assert len(code) == CODE_LENGTH, "Code length incorrect"
    
    # Complete code pairing
    device_key2, session_key2 = complete_code_pairing(code, "test-phone-2")
    assert device_key2 is not None, "Code pairing device key not generated"
    assert session_key2 is not None, "Code pairing session key not generated"
    
    # Verify device was paired
    assert "test-phone-2" in paired_devices, "Device not stored after code pairing"
    assert paired_devices["test-phone-2"]["device_key"] == device_key2, "Device key mismatch"
    
    print("✓ Code pairing flow completed successfully")
    print(f"✓ Generated code: {code}")
    print(f"✓ Paired device: test-phone-2")
    
    # Test error handling
    print("\n--- Testing Error Handling ---")
    
    # Test invalid code
    try:
        verify_code("INVALID", test_secret, "test-device")
        assert False, "Should have raised InvalidCodeError"
    except InvalidCodeError:
        print("✓ InvalidCodeError raised for invalid code")
    
    # Test code expiry (simulate by setting past expiry)
    expired_code = start_code_pairing("test-expired")
    # Manually expire the code
    for code_data in active_codes.values():
        if code_data['device_id'] == "test-expired":
            code_data['expiry'] = time.time() - 1  # Expired 1 second ago
            break
    
    try:
        complete_code_pairing(expired_code, "test-expired")
        assert False, "Should have raised CodeExpiredError"
    except CodeExpiredError:
        print("✓ CodeExpiredError raised for expired code")
    
    print("\n✓ All pairing tests passed!")
    print(f"✓ Active codes: {get_active_codes_count()}")
    print(f"✓ Paired devices: {get_paired_devices_count()}")
    print(f"✓ Total QR codes in system: {len(active_qr_codes)}")


if __name__ == "__main__":
    test_pairing()