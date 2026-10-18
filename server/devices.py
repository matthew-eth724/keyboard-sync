#!/usr/bin/env python3
"""
server/devices.py - Device management and revocation logic
Implements paired-device store and revocation functionality

This is Phase 5: Device management implementation
"""

import time
import json
from typing import Dict, List, Optional, Set
from pathlib import Path
import os

# File for device storage (in production, use database)
DEVICE_STORE_FILE = Path("server/device_store.json")

# Global state (in production, use database or Redis)
paired_devices = {}
device_sessions = {}
device_permissions = {}

# Security settings
MAX_CONCURRENT_SESSIONS = 3
SESSION_TIMEOUT_SECONDS = 300  # 5 minutes
REVOCATION_COOLDOWN_SECONDS = 60  # 1 minute between revocations


class DeviceStoreError(Exception):
    """Base exception for device store errors"""
    pass


class DeviceNotFoundError(DeviceStoreError):
    """Raised when a device is not found"""
    pass


class DeviceAlreadyPairedError(DeviceStoreError):
    """Raised when trying to pair an already paired device"""
    pass


class DeviceRevokedError(DeviceStoreError):
    """Raised when trying to use a revoked device"""
    pass


class MaxSessionsExceededError(DeviceStoreError):
    """Raised when too many sessions are active for a device"""
    pass


def load_device_store():
    """Load device store from file"""
    global paired_devices
    
    if DEVICE_STORE_FILE.exists():
        try:
            with open(DEVICE_STORE_FILE, 'r') as f:
                data = json.load(f)
                paired_devices = data.get('paired_devices', {})
                device_sessions = data.get('device_sessions', {})
                device_permissions = data.get('device_permissions', {})
        except Exception as e:
            print(f"Warning: Could not load device store: {e}")
            paired_devices = {}
            device_sessions = {}
            device_permissions = {}
    else:
        paired_devices = {}
        device_sessions = {}
        device_permissions = {}


def save_device_store():
    """Save device store to file"""
    try:
        data = {
            'paired_devices': paired_devices,
            'device_sessions': device_sessions,
            'device_permissions': device_permissions
        }
        
        # Ensure directory exists
        DEVICE_STORE_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        with open(DEVICE_STORE_FILE, 'w') as f:
            json.dump(data, f, indent=2)
            
    except Exception as e:
        print(f"Error: Could not save device store: {e}")


def add_paired_device(device_id: str, device_key: bytes, device_info: Dict = None):
    """
    Add a new paired device to the store.
    
    Args:
        device_id: Unique device identifier
        device_key: Device's cryptographic key
        device_info: Additional device information
        
    Returns:
        True if device was added, False if already exists
        
    Raises:
        DeviceAlreadyPairedError: If device is already paired
    """
    if device_id in paired_devices:
        raise DeviceAlreadyPairedError(f"Device {device_id} is already paired")
    
    # Initialize device permissions
    permissions = {
        'can_read': True,
        'can_write': True,
        'can_revoke': False,
        'paired_at': time.time(),
        'last_active': time.time(),
        'revoked': False
    }
    
    if device_info:
        permissions.update(device_info)
    
    paired_devices[device_id] = {
        'device_key': device_key.hex(),  # Store as hex string
        'info': device_info or {},
        'permissions': permissions,
        'session_count': 0
    }
    
    # Initialize session tracking
    device_sessions[device_id] = set()
    
    save_device_store()
    return True


def remove_paired_device(device_id: str) -> bool:
    """
    Remove a paired device from the store.
    
    Args:
        device_id: Device identifier to remove
        
    Returns:
        True if device was removed, False if not found
    """
    if device_id in paired_devices:
        # Remove all sessions for this device
        if device_id in device_sessions:
            for session_id in device_sessions[device_id]:
                # Clean up session state
                cleanup_device_session(device_id, session_id)
            
            del device_sessions[device_id]
        
        del paired_devices[device_id]
        save_device_store()
        return True
    
    return False


def revoke_device(device_id: str, revoker_id: str = None) -> bool:
    """
    Revoke a paired device.
    
    Args:
        device_id: Device identifier to revoke
        revoker_id: Optional ID of device performing revocation
        
    Returns:
        True if device was revoked, False if not found
        
    Raises:
        DeviceRevokedError: If device is already revoked
    """
    if device_id not in paired_devices:
        raise DeviceNotFoundError(f"Device {device_id} not found")
    
    device_info = paired_devices[device_id]
    
    # Check if already revoked
    if device_info.get('permissions', {}).get('revoked', False):
        raise DeviceRevokedError(f"Device {device_id} is already revoked")
    
    # Mark as revoked
    device_info['permissions']['revoked'] = True
    device_info['permissions']['revoked_at'] = time.time()
    device_info['permissions']['revoked_by'] = revoker_id
    
    # Close all active sessions
    if device_id in device_sessions:
        for session_id in list(device_sessions[device_id]):
            cleanup_device_session(device_id, session_id)
        
        device_sessions[device_id].clear()
    
    save_device_store()
    return True


def is_device_revoked(device_id: str) -> bool:
    """
    Check if a device has been revoked.
    
    Args:
        device_id: Device identifier
        
    Returns:
        True if device is revoked, False otherwise
    """
    if device_id not in paired_devices:
        return False
    
    return paired_devices[device_id].get('permissions', {}).get('revoked', False)


def get_device_key(device_id: str) -> Optional[bytes]:
    """
    Get device key for a paired device.
    
    Args:
        device_id: Device identifier
        
    Returns:
        Device key as bytes, or None if device not found or revoked
        
    Raises:
        DeviceNotFoundError: If device is not found
    """
    if device_id not in paired_devices:
        raise DeviceNotFoundError(f"Device {device_id} not found")
    
    device_info = paired_devices[device_id]
    
    # Check if device is revoked
    if device_info.get('permissions', {}).get('revoked', False):
        raise DeviceRevokedError(f"Device {device_id} has been revoked")
    
    # Convert hex back to bytes
    key_hex = device_info['device_key']
    return bytes.fromhex(key_hex)


def get_device_info(device_id: str) -> Optional[Dict]:
    """
    Get device information.
    
    Args:
        device_id: Device identifier
        
    Returns:
        Device information dict, or None if device not found
    """
    if device_id in paired_devices:
        return paired_devices[device_id].copy()
    return None


def add_device_session(device_id: str, session_id: str, session_data: Dict = None):
    """
    Add a session for a device.
    
    Args:
        device_id: Device identifier
        session_id: Session identifier
        session_data: Additional session data
        
    Returns:
        True if session was added, False if device not found
        
    Raises:
        DeviceNotFoundError: If device is not found
        DeviceRevokedError: If device is revoked
        MaxSessionsExceededError: If max sessions exceeded
    """
    if device_id not in paired_devices:
        raise DeviceNotFoundError(f"Device {device_id} not found")
    
    if is_device_revoked(device_id):
        raise DeviceRevokedError(f"Device {device_id} is revoked")
    
    # Check max sessions
    device_info = paired_devices[device_id]
    current_sessions = len(device_sessions.get(device_id, set()))
    
    if current_sessions >= MAX_CONCURRENT_SESSIONS:
        raise MaxSessionsExceededError(
            f"Device {device_id} has reached max concurrent sessions ({MAX_CONCURRENT_SESSIONS})"
        )
    
    # Add session
    if device_id not in device_sessions:
        device_sessions[device_id] = set()
    
    device_sessions[device_id].add(session_id)
    
    if session_data:
        device_sessions[device_id].add(session_id)  # Store session data separately
    
    # Update device info
    device_info['session_count'] = current_sessions + 1
    device_info['last_active'] = time.time()
    
    save_device_store()
    return True


def remove_device_session(device_id: str, session_id: str) -> bool:
    """
    Remove a session for a device.
    
    Args:
        device_id: Device identifier
        session_id: Session identifier
        
    Returns:
        True if session was removed, False if not found
    """
    if device_id in device_sessions and session_id in device_sessions[device_id]:
        device_sessions[device_id].remove(session_id)
        
        # Update device info
        if device_id in paired_devices:
            device_info = paired_devices[device_id]
            device_info['session_count'] = max(0, device_info['session_count'] - 1)
        
        save_device_store()
        return True
    
    return False


def cleanup_device_session(device_id: str, session_id: str):
    """
    Clean up a device session (force cleanup).
    
    Args:
        device_id: Device identifier
        session_id: Session identifier
    """
    if device_id in device_sessions and session_id in device_sessions[device_id]:
        device_sessions[device_id].remove(session_id)
        save_device_store()


def get_device_sessions(device_id: str) -> Set:
    """
    Get all active sessions for a device.
    
    Args:
        device_id: Device identifier
        
    Returns:
        Set of session IDs, or empty set if device not found
    """
    if device_id in device_sessions:
        return device_sessions[device_id].copy()
    return set()


def cleanup_expired_sessions():
    """Clean up expired sessions"""
    current_time = time.time()
    
    for device_id, sessions in list(device_sessions.items()):
        sessions_to_remove = set()
        
        for session_id in sessions:
            # Check if session has expired
            if current_time > SESSION_TIMEOUT_SECONDS:
                sessions_to_remove.add(session_id)
        
        for session_id in sessions_to_remove:
            sessions.remove(session_id)
        
        if not sessions:
            del device_sessions[device_id]


def get_all_paired_devices() -> List[Dict]:
    """
    Get all paired devices.
    
    Returns:
        List of device information dictionaries
    """
    return [device_info.copy() for device_info in paired_devices.values()]


def get_paired_devices_count() -> int:
    """Get number of paired devices"""
    return len(paired_devices)


def get_active_sessions_count() -> int:
    """Get total number of active sessions"""
    return sum(len(sessions) for sessions in device_sessions.values())


def get_device_store_stats() -> Dict:
    """
    Get statistics about the device store.
    
    Returns:
        Statistics dictionary
    """
    cleanup_expired_sessions()
    
    total_sessions = get_active_sessions_count()
    revoked_devices = sum(1 for device in paired_devices.values() 
                         if device.get('permissions', {}).get('revoked', False))
    
    return {
        "total_devices": len(paired_devices),
        "active_sessions": total_sessions,
        "revoked_devices": revoked_devices,
        "max_sessions_per_device": MAX_CONCURRENT_SESSIONS,
        "session_timeout": SESSION_TIMEOUT_SECONDS
    }


def test_device_management():
    """Test the device management implementation"""
    print("Testing device management implementation...")
    
    # Load fresh store
    load_device_store()
    
    # Test 1: Add devices
    device1_key = bytes.fromhex("0123456789abcdef0123456789abcdef")
    device2_key = bytes.fromhex("fedcba9876543210fedcba9876543210")
    
    add_paired_device("device-1", device1_key, {"name": "PC-1"})
    add_paired_device("device-2", device2_key, {"name": "Phone-1"})
    
    # Test 2: Device lookup
    device1_info = get_device_info("device-1")
    assert device1_info is not None, "Device should be found"
    assert device1_info["info"]["name"] == "PC-1", "Device info should match"
    
    # Test 3: Device key retrieval
    device1_key_retrieved = get_device_key("device-1")
    assert device1_key_retrieved == device1_key, "Device key should match"
    
    # Test 4: Session management
    add_device_session("device-1", "session-1", {"user": "test"})
    sessions = get_device_sessions("device-1")
    assert "session-1" in sessions, "Session should be added"
    
    # Test 5: Revocation
    revoke_device("device-1", "admin")
    
    # Test 6: Revoked device check
    assert is_device_revoked("device-1"), "Device should be revoked"
    
    # Test 7: Stats
    stats = get_device_store_stats()
    assert stats["total_devices"] == 2, "Should have 2 devices"
    assert stats["revoked_devices"] == 1, "Should have 1 revoked device"
    
    # Test 8: Cleanup
    remove_paired_device("device-2")
    assert get_device_info("device-2") is None, "Device should be removed"
    
    print("✓ All device management tests passed!")
    print(f"✓ Devices in store: {get_paired_devices_count()}")
    print(f"✓ Active sessions: {get_active_sessions_count()}")


if __name__ == "__main__":
    test_device_management()