#!/usr/bin/env python3
"""
server/clipboard_api.py - Real clipboard API implementation for cross-platform clipboard access

Implements clipboard access for Windows, macOS, and Linux with fallback mechanisms.
"""

import platform
import subprocess
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Try to import pyperclip for cross-platform clipboard access
try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False
    logger.warning("pyperclip not available, using platform-specific fallbacks")

# Platform detection
SYSTEM = platform.system()


def set_clipboard(content: str) -> bool:
    """
    Set system clipboard content.
    
    Args:
        content: Content to copy to clipboard
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Try pyperclip first (cross-platform)
        if PYPERCLIP_AVAILABLE:
            pyperclip.copy(content)
            return True
        
        # Platform-specific fallbacks
        if SYSTEM == "Windows":
            return _set_clipboard_windows(content)
        elif SYSTEM == "Darwin":  # macOS
            return _set_clipboard_macos(content)
        elif SYSTEM == "Linux":
            return _set_clipboard_linux(content)
        else:
            logger.error(f"Unsupported platform: {SYSTEM}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to set clipboard: {e}")
        return False


def get_clipboard() -> Optional[str]:
    """
    Get system clipboard content.
    
    Returns:
        Clipboard content or None if failed
    """
    try:
        # Try pyperclip first (cross-platform)
        if PYPERCLIP_AVAILABLE:
            return pyperclip.paste()
        
        # Platform-specific fallbacks
        if SYSTEM == "Windows":
            return _get_clipboard_windows()
        elif SYSTEM == "Darwin":  # macOS
            return _get_clipboard_macos()
        elif SYSTEM == "Linux":
            return _get_clipboard_linux()
        else:
            logger.error(f"Unsupported platform: {SYSTEM}")
            return None
            
    except Exception as e:
        logger.error(f"Failed to get clipboard: {e}")
        return None


def _set_clipboard_windows(content: str) -> bool:
    """Set clipboard on Windows using PowerShell"""
    try:
        # Escape single quotes for PowerShell
        escaped_content = content.replace("'", "''")
        subprocess.run([
            'powershell', '-Command', 
            f'Set-Clipboard -Value "{escaped_content}"'
        ], check=True, capture_output=True)
        return True
    except Exception as e:
        logger.error(f"Windows clipboard set failed: {e}")
        return False


def _get_clipboard_windows() -> Optional[str]:
    """Get clipboard on Windows using PowerShell"""
    try:
        result = subprocess.run([
            'powershell', '-Command', 
            'Get-Clipboard'
        ], capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except Exception as e:
        logger.error(f"Windows clipboard get failed: {e}")
        return None


def _set_clipboard_macos(content: str) -> bool:
    """Set clipboard on macOS using pbcopy"""
    try:
        subprocess.run(['pbcopy'], input=content.encode('utf-8'), check=True)
        return True
    except Exception as e:
        logger.error(f"macOS clipboard set failed: {e}")
        return False


def _get_clipboard_macos() -> Optional[str]:
    """Get clipboard on macOS using pbpaste"""
    try:
        result = subprocess.run(['pbpaste'], capture_output=True, check=True)
        return result.stdout.decode('utf-8')
    except Exception as e:
        logger.error(f"macOS clipboard get failed: {e}")
        return None


def _set_clipboard_linux(content: str) -> bool:
    """Set clipboard on Linux using xclip or xsel"""
    # Try xclip first
    try:
        subprocess.run(
            ['xclip', '-selection', 'clipboard'], 
            input=content.encode('utf-8'), 
            check=True
        )
        return True
    except Exception:
        pass
    
    # Try xsel as fallback
    try:
        subprocess.run(
            ['xsel', '--clipboard', '--input'], 
            input=content.encode('utf-8'), 
            check=True
        )
        return True
    except Exception as e:
        logger.error(f"Linux clipboard set failed: {e}")
        return False


def _get_clipboard_linux() -> Optional[str]:
    """Get clipboard on Linux using xclip or xsel"""
    # Try xclip first
    try:
        result = subprocess.run(
            ['xclip', '-selection', 'clipboard', '-o'], 
            capture_output=True, 
            check=True
        )
        return result.stdout.decode('utf-8')
    except Exception:
        pass
    
    # Try xsel as fallback
    try:
        result = subprocess.run(
            ['xsel', '--clipboard', '--output'], 
            capture_output=True, 
            check=True
        )
        return result.stdout.decode('utf-8')
    except Exception as e:
        logger.error(f"Linux clipboard get failed: {e}")
        return None


def is_clipboard_available() -> bool:
    """
    Check if clipboard access is available on this system.
    
    Returns:
        True if clipboard access is available, False otherwise
    """
    try:
        # Test by trying to get clipboard content
        content = get_clipboard()
        return content is not None
    except Exception:
        return False


def get_clipboard_info() -> dict:
    """
    Get information about clipboard capabilities.
    
    Returns:
        Dictionary with clipboard information
    """
    return {
        'platform': SYSTEM,
        'pyperclip_available': PYPERCLIP_AVAILABLE,
        'clipboard_available': is_clipboard_available(),
        'method': 'pyperclip' if PYPERCLIP_AVAILABLE else 'platform-specific'
    }