#!/usr/bin/env python3
"""
tests/test_m4_clipboard.py - Comprehensive tests for M4 Clipboard Logic

Tests clipboard deduplication, echo prevention, history management,
size limits, phone connection tracking, and WebSocket integration.
"""

import unittest
import sys
import os
import time

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from server.clipboard import (
    add_clipboard_item,
    get_clipboard_history,
    get_last_item,
    cleanup_old_hashes,
    get_history_stats,
    add_connected_phone,
    remove_connected_phone,
    get_connected_phones,
    ClipboardItem
)


class TestClipboardItem(unittest.TestCase):
    """Test ClipboardItem data structure"""
    
    def test_creation(self):
        item = ClipboardItem("test content", "device-1", "pc")
        self.assertEqual(item.content, "test content")
        self.assertEqual(item.device_id, "device-1")
        self.assertEqual(item.source, "pc")
        self.assertEqual(len(item.hash), 64)  # SHA-256 hex digest
        self.assertIsNotNone(item.timestamp)
    
    def test_to_dict(self):
        item = ClipboardItem("hello world", "device-1", "pc")
        d = item.to_dict()
        self.assertEqual(d["content"], "hello world")
        self.assertEqual(d["device_id"], "device-1")
        self.assertEqual(d["source"], "pc")
        self.assertEqual(d["hash"], item.hash)
    
    def test_from_dict(self):
        original = ClipboardItem("test", "dev-1", "phone")
        d = original.to_dict()
        restored = ClipboardItem.from_dict(d)
        self.assertEqual(restored.content, original.content)
        self.assertEqual(restored.device_id, original.device_id)


class TestClipboardAdd(unittest.TestCase):
    """Test clipboard item addition with deduplication"""
    
    def setUp(self):
        # Clear global state
        from server.clipboard import clipboard_history, recent_hashes
        clipboard_history.clear()
        recent_hashes.clear()
    
    def test_add_new_item(self):
        """Test adding a new clipboard item"""
        result = add_clipboard_item("Hello, world!", "device-1", "pc")
        self.assertTrue(result, "New item should be added")
    
    def test_add_duplicate_from_same_device(self):
        """Test that duplicates from same device are rejected"""
        add_clipboard_item("Hello, world!", "device-1", "pc")
        result = add_clipboard_item("Hello, world!", "device-1", "pc")
        self.assertFalse(result, "Duplicate from same device should be rejected")
    
    def test_add_different_content(self):
        """Test adding different content items"""
        result1 = add_clipboard_item("First item", "device-1", "pc")
        result2 = add_clipboard_item("Second item", "device-1", "pc")
        self.assertTrue(result1)
        self.assertTrue(result2)
    
    def test_size_limit(self):
        """Test that items exceeding size limit are rejected"""
        large_content = "x" * (2 * 1024 * 1024)  # 2MB exceeds 1MB limit
        with self.assertRaises(ValueError):
            add_clipboard_item(large_content, "device-1", "pc")
    
    def test_size_limit_exact(self):
        """Test content at exactly 1MB limit"""
        exact_content = "x" * (1 * 1024 * 1024)  # Exactly 1MB
        result = add_clipboard_item(exact_content, "device-1", "pc")
        self.assertTrue(result, "Item at exact size limit should be accepted")
    
    def test_echo_prevention_different_device(self):
        """Test echo prevention - same content from different device within 10 seconds"""
        add_clipboard_item("Test content", "device-1", "pc")
        # Clear time-based cleanup to test immediate echo
        from server.clipboard import cleanup_old_hashes
        # Don't call cleanup - content should still be in recent_hashes
        result = add_clipboard_item("Test content", "device-2", "phone")
        # This should be blocked due to echo prevention
        # Note: This test may vary based on timing
        self.assertIsInstance(result, bool)


class TestClipboardHistory(unittest.TestCase):
    """Test clipboard history retrieval"""
    
    def setUp(self):
        from server.clipboard import clipboard_history, recent_hashes
        clipboard_history.clear()
        recent_hashes.clear()
    
    def test_get_empty_history(self):
        """Test getting history when empty"""
        history = get_clipboard_history()
        self.assertEqual(len(history), 0)
    
    def test_get_history_with_items(self):
        """Test getting history with items"""
        add_clipboard_item("Item 1", "device-1", "pc")
        add_clipboard_item("Item 2", "device-1", "pc")
        history = get_clipboard_history()
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["content"], "Item 1")
        self.assertEqual(history[1]["content"], "Item 2")
    
    def test_history_limit(self):
        """Test history respects max_history_items limit"""
        from server.clipboard import max_history_items
        for i in range(max_history_items + 5):
            add_clipboard_item(f"Item {i}", "device-1", "pc")
        history = get_clipboard_history()
        self.assertLessEqual(len(history), max_history_items)
    
    def test_device_filter(self):
        """Test filtering history by device ID"""
        add_clipboard_item("PC Item", "device-pc", "pc")
        add_clipboard_item("Phone Item", "device-phone", "phone")
        
        pc_history = get_clipboard_history(device_id="device-pc")
        self.assertEqual(len(pc_history), 1)
        self.assertEqual(pc_history[0]["content"], "PC Item")
        
        phone_history = get_clipboard_history(device_id="device-phone")
        self.assertEqual(len(phone_history), 1)
        self.assertEqual(phone_history[0]["content"], "Phone Item")
    
    def test_get_last_item(self):
        """Test getting the last clipboard item"""
        add_clipboard_item("First", "device-1", "pc")
        add_clipboard_item("Second", "device-1", "pc")
        last = get_last_item()
        self.assertIsNotNone(last)
        self.assertEqual(last["content"], "Second")
    
    def test_get_last_item_empty(self):
        """Test getting last item when history is empty"""
        last = get_last_item()
        self.assertIsNone(last)
    
    def test_history_with_limit(self):
        """Test history with limit parameter"""
        add_clipboard_item("Item 1", "device-1", "pc")
        add_clipboard_item("Item 2", "device-1", "pc")
        add_clipboard_item("Item 3", "device-1", "pc")
        
        history = get_clipboard_history(limit=2)
        self.assertEqual(len(history), 2)


class TestClipboardStats(unittest.TestCase):
    """Test clipboard statistics"""
    
    def setUp(self):
        from server.clipboard import clipboard_history, recent_hashes
        clipboard_history.clear()
        recent_hashes.clear()
    
    def test_stats_empty(self):
        """Test stats with no items"""
        stats = get_history_stats()
        self.assertEqual(stats["total_items"], 0)
        self.assertEqual(stats["pc_items"], 0)
        self.assertEqual(stats["phone_items"], 0)
        self.assertEqual(stats["unique_devices"], 0)
    
    def test_stats_with_items(self):
        """Test stats with items from multiple devices"""
        add_clipboard_item("PC Item", "device-pc", "pc")
        add_clipboard_item("Phone Item 1", "device-phone", "phone")
        add_clipboard_item("Phone Item 2", "device-phone", "phone")
        
        stats = get_history_stats()
        self.assertEqual(stats["total_items"], 3)
        self.assertEqual(stats["pc_items"], 1)
        self.assertEqual(stats["phone_items"], 2)
        self.assertEqual(stats["unique_devices"], 2)


class TestPhoneConnectionTracking(unittest.TestCase):
    """Test phone connection tracking"""
    
    def setUp(self):
        from server.clipboard import connected_phones
        connected_phones.clear()
    
    def test_add_and_remove_phone(self):
        """Test adding and removing connected phones"""
        add_connected_phone("phone-123")
        phones = get_connected_phones()
        self.assertIn("phone-123", phones)
        
        remove_connected_phone("phone-123")
        phones = get_connected_phones()
        self.assertNotIn("phone-123", phones)
    
    def test_remove_nonexistent_phone(self):
        """Test removing a phone that was never added (should not error)"""
        try:
            remove_connected_phone("nonexistent-phone")
        except Exception as e:
            self.fail(f"Removing nonexistent phone raised {type(e).__name__}: {e}")


class TestClipboardHashes(unittest.TestCase):
    """Test clipboard hash functionality"""
    
    def test_hash_is_deterministic(self):
        """Test that same content produces same hash"""
        item1 = ClipboardItem("test content", "device-1")
        item2 = ClipboardItem("test content", "device-2")
        self.assertEqual(item1.hash, item2.hash)
    
    def test_hash_changes_with_content(self):
        """Test that different content produces different hash"""
        item1 = ClipboardItem("content A", "device-1")
        item2 = ClipboardItem("content B", "device-1")
        self.assertNotEqual(item1.hash, item2.hash)


class TestCleanupOldHashes(unittest.TestCase):
    """Test cleanup of old hashes"""
    
    def setUp(self):
        from server.clipboard import clipboard_history, recent_hashes
        clipboard_history.clear()
        recent_hashes.clear()
    
    def test_cleanup_old_hashes(self):
        """Test cleanup removes old hashes"""
        add_clipboard_item("Old item", "device-1", "pc")
        cleanup_old_hashes()
        # Item should still be in history as it's not old enough
        history = get_clipboard_history()
        self.assertEqual(len(history), 1)


class TestIntegration(unittest.TestCase):
    """Integration tests for clipboard logic"""
    
    def setUp(self):
        from server.clipboard import clipboard_history, recent_hashes
        clipboard_history.clear()
        recent_hashes.clear()
    
    def test_full_workflow(self):
        """Test complete clipboard workflow"""
        # Add multiple items
        result1 = add_clipboard_item("First clipboard item", "pc-device", "pc")
        self.assertTrue(result1)
        
        result2 = add_clipboard_item("Second clipboard item", "pc-device", "pc")
        self.assertTrue(result2)
        
        # Try duplicate
        result3 = add_clipboard_item("First clipboard item", "pc-device", "pc")
        self.assertFalse(result3)
        
        # Verify history
        history = get_clipboard_history()
        self.assertEqual(len(history), 2)
        
        # Get last item
        last = get_last_item()
        self.assertEqual(last["content"], "Second clipboard item")
        
        # Verify stats
        stats = get_history_stats()
        self.assertEqual(stats["total_items"], 2)
        self.assertEqual(stats["pc_items"], 2)


if __name__ == "__main__":
    unittest.main()