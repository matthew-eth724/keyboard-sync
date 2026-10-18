#!/usr/bin/env python3
"""
server/clipboard.py - Clipboard history and deduplication logic
Implements clipboard watcher, history tracking, and echo prevention

This is Phase 4: Clipboard logic implementation
"""

import time
import hashlib
import threading
from typing import List, Dict, Optional, Set
from datetime import datetime, timedelta

# Global state (in production, use Redis or similar)
clipboard_history = []  # List of clipboard items
clipboard_lock = threading.Lock()
connected_phones = set()  # Set of connected phone device IDs
max_history_items = 20  # Keep last 20 items
max_message_size = 1 * 1024 * 1024  # 1 MB size limit

# Recent items for deduplication
recent_hashes = set()  # Set of hash values for last 10 seconds


class ClipboardItem:
    """Represents a clipboard item"""
    
    def __init__(self, content: str, device_id: str, source: str = "pc"):
        self.content = content
        self.device_id = device_id
        self.source = source  # "pc" or "phone"
        self.timestamp = time.time()
        self.hash = hashlib.sha256(content.encode()).hexdigest()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "id": self.hash,
            "content": self.content,
            "device_id": self.device_id,
            "source": self.source,
            "timestamp": self.timestamp,
            "hash": self.hash
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ClipboardItem':
        """Create from dictionary"""
        item = cls(data['content'], data['device_id'], data['source'])
        item.timestamp = data['timestamp']
        item.hash = data['hash']
        return item


def add_clipboard_item(content: str, device_id: str, source: str = "pc") -> bool:
    """
    Add a new clipboard item with deduplication and history management.
    
    Args:
        content: Clipboard content
        device_id: Device that generated the content
        source: "pc" or "phone"
        
    Returns:
        True if item was added, False if it was a duplicate
    """
    # Size check
    if len(content.encode()) > max_message_size:
        raise ValueError(f"Content size exceeds {max_message_size} bytes limit")
    
    # Create item
    item = ClipboardItem(content, device_id, source)
    
    with clipboard_lock:
        # Check for duplicates (same content and hash from same device)
        for existing in clipboard_history:
            if (existing.hash == item.hash and 
                existing.device_id == item.device_id and
                existing.source == item.source):
                return False  # Duplicate
        
        # Clean up old hashes for deduplication
        cleanup_old_hashes()
        
        # Check for echo prevention (same hash from any device in recent history)
        if item.hash in recent_hashes:
            return False  # Echo detected
        
        # Add to history
        clipboard_history.append(item)
        
        # Maintain max history size
        if len(clipboard_history) > max_history_items:
            clipboard_history.pop(0)
        
        # Add to recent hashes for echo prevention
        recent_hashes.add(item.hash)
        
        return True


def get_clipboard_history(device_id: str = None, limit: int = None) -> List[Dict]:
    """
    Get clipboard history, optionally filtered by device.
    
    Args:
        device_id: Optional device filter
        limit: Optional limit on number of items
        
    Returns:
        List of clipboard items
    """
    with clipboard_lock:
        # Filter by device if specified
        if device_id:
            filtered_history = [item for item in clipboard_history 
                              if item.device_id == device_id]
        else:
            filtered_history = clipboard_history
        
        # Apply limit
        if limit:
            filtered_history = filtered_history[-limit:]
        
        return [item.to_dict() for item in filtered_history]


def get_last_item(device_id: str = None) -> Optional[Dict]:
    """
    Get the last clipboard item, optionally filtered by device.
    
    Args:
        device_id: Optional device filter
        
    Returns:
        Last clipboard item or None if no history
    """
    history = get_clipboard_history(device_id, 1)
    return history[0] if history else None


def cleanup_old_hashes():
    """Clean up hashes older than 10 seconds for deduplication"""
    global recent_hashes
    current_time = time.time()
    
    # Keep only items from last 10 seconds
    recent_hashes = {
        item.hash for item in clipboard_history 
        if current_time - item.timestamp < 10
    }


def get_history_stats() -> Dict:
    """
    Get statistics about clipboard history.
    
    Returns:
        Statistics dictionary
    """
    with clipboard_lock:
        pc_items = len([item for item in clipboard_history if item.source == "pc"])
        phone_items = len([item for item in clipboard_history if item.source == "phone"])
        unique_devices = len(set(item.device_id for item in clipboard_history))
        
        return {
            "total_items": len(clipboard_history),
            "pc_items": pc_items,
            "phone_items": phone_items,
            "unique_devices": unique_devices,
            "max_history": max_history_items,
            "max_message_size": max_message_size
        }


def add_connected_phone(device_id: str):
    """Add a connected phone device"""
    connected_phones.add(device_id)


def remove_connected_phone(device_id: str):
    """Remove a disconnected phone device"""
    connected_phones.discard(device_id)


def get_connected_phones() -> Set:
    """Get set of connected phone device IDs"""
    return connected_phones.copy()


def simulate_clipboard_change(new_content: str, device_id: str = "pc"):
    """
    Simulate a clipboard change (for testing/demo purposes).
    
    Args:
        new_content: New clipboard content
        device_id: Device generating the change
    """
    # Simulate polling mechanism from PLAN.md
    # In real implementation, this would use platform-specific APIs
    success = add_clipboard_item(new_content, device_id, "pc")
    
    if success:
        print(f"[Clipboard] New item added: {new_content[:50]}...")
    else:
        print(f"[Clipboard] Duplicate item ignored: {new_content[:50]}...")


def test_clipboard_logic():
    """Test the clipboard logic implementation"""
    print("Testing clipboard logic implementation...")
    
    # Clear history
    global clipboard_history, recent_hashes
    clipboard_history = []
    recent_hashes = set()
    
    # Test 1: Add new items
    item1 = add_clipboard_item("Hello, world!", "pc")
    assert item1, "First item should be added"
    
    item2 = add_clipboard_item("Different text", "pc")
    assert item2, "Different item should be added"
    
    # Test 2: Duplicate detection
    item3 = add_clipboard_item("Hello, world!", "pc")
    assert not item3, "Duplicate should be rejected"
    
    # Test 3: Get history
    history = get_clipboard_history()
    assert len(history) == 2, "Should have 2 items in history"
    
    # Test 4: Get last item
    last = get_last_item()
    assert last["content"] == "Different text", "Last item should be 'Different text'"
    
    # Test 5: Device filtering
    pc_history = get_clipboard_history("pc")
    assert len(pc_history) == 2, "PC history should have 2 items"
    
    # Test 6: Statistics
    stats = get_history_stats()
    assert stats["total_items"] == 2, "Should have 2 total items"
    assert stats["pc_items"] == 2, "Should have 2 PC items"
    
    # Test 7: Phone connection tracking
    add_connected_phone("phone-123")
    phones = get_connected_phones()
    assert "phone-123" in phones, "Phone should be connected"
    
    remove_connected_phone("phone-123")
    phones = get_connected_phones()
    assert "phone-123" not in phones, "Phone should be disconnected"
    
    print("✓ All clipboard logic tests passed!")
    print(f"✓ History items: {stats['total_items']}")
    print(f"✓ Connected phones: {len(get_connected_phones())}")


if __name__ == "__main__":
    test_clipboard_logic()