"""
Text Utility Functions

This module provides utility functions for text processing operations.
"""

import re


def strip_ansi_codes(text: str | None) -> str:
    """
    Remove ANSI color codes from text.
    
    Args:
        text: Text containing ANSI escape sequences (or None)
    
    Returns:
        Clean text with ANSI codes removed, or empty string if text is None
    
    Example:
        >>> strip_ansi_codes("\x1B[32mSuccess\x1B[0m")
        "Success"
        >>> strip_ansi_codes(None)
        ""
    """
    if text is None:
        return ""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)
