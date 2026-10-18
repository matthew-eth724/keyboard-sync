#!/usr/bin/env python3
"""
server/polling.py - Clipboard polling mechanism for continuous clipboard monitoring

Implements a background thread that polls the system clipboard every ~500ms
and detects changes to push to connected phones.
"""

import threading
import time
import logging
from typing import Callable, Optional

from server.clipboard_api import get_clipboard, set_clipboard
from server.clipboard import add_clipboard_item

logger = logging.getLogger(__name__)


class ClipboardPoller:
    """
    Background clipboard poller that monitors for changes every 500ms.
    
    When a change is detected, it calls the registered callback with the new content.
    """
    
    def __init__(self, interval: float = 0.5, device_id: str = "pc"):
        """
        Initialize the clipboard poller.
        
        Args:
            interval: Polling interval in seconds (default 0.5 = 500ms)
            device_id: Device ID for clipboard items
        """
        self.interval = interval
        self.device_id = device_id
        self.running = False
        self.last_content = ""
        self.callback: Optional[Callable[[str], None]] = None
        self.thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
    def start(self, callback: Callable[[str], None] = None):
        """
        Start the clipboard polling.
        
        Args:
            callback: Function to call when clipboard changes (receives new content)
        """
        if self.running:
            logger.warning("Clipboard poller already running")
            return
        
        self.callback = callback
        self.running = True
        
        # Get initial clipboard content
        initial = get_clipboard()
        if initial is not None:
            self.last_content = initial
            logger.info(f"[Clipboard] Initial content: {initial[:50]}...")
        
        # Start background thread
        self.thread = threading.Thread(target=self._poll_loop, daemon=True)
        self.thread.start()
        logger.info(f"[Clipboard] Poller started (interval: {self.interval}s)")
        
    def stop(self):
        """Stop the clipboard polling."""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)
        logger.info("[Clipboard] Poller stopped")
        
    def _poll_loop(self):
        """Main polling loop."""
        while self.running:
            try:
                current = get_clipboard()
                
                if current is not None and current != self.last_content:
                    # Clipboard changed!
                    with self._lock:
                        self.last_content = current
                        
                        logger.info(f"[Clipboard] Change detected: {current[:50]}...")
                        
                        # Add to clipboard history
                        try:
                            add_clipboard_item(current, self.device_id, source='pc')
                        except Exception as e:
                            logger.error(f"Failed to add clipboard item: {e}")
                        
                        # Call registered callback
                        if self.callback:
                            try:
                                self.callback(current)
                            except Exception as e:
                                logger.error(f"Callback error: {e}")
                                
            except Exception as e:
                logger.error(f"Clipboard poll error: {e}")
            
            # Sleep for the polling interval
            time.sleep(self.interval)


def start_clipboard_polling(interval: float = 0.5, device_id: str = "pc", 
                           callback: Callable[[str], None] = None) -> Optional[ClipboardPoller]:
    """
    Start clipboard polling with the given parameters.
    
    Args:
        interval: Polling interval in seconds
        device_id: Device ID for clipboard items
        callback: Function to call when clipboard changes
        
    Returns:
        ClipboardPoller instance or None if failed
    """
    try:
        poller = ClipboardPoller(interval=interval, device_id=device_id)
        poller.start(callback=callback)
        return poller
    except Exception as e:
        logger.error(f"Failed to start clipboard polling: {e}")
        return None


def stop_clipboard_polling(poller: ClipboardPoller):
    """
    Stop clipboard polling.
    
    Args:
        poller: ClipboardPoller instance to stop
    """
    if poller:
        poller.stop()