"""File validation utilities."""
from __future__ import annotations

from pathlib import Path
from app.config import ALLOWED_EXTENSIONS


def is_allowed_file(filename: str) -> bool:
    """Check if file extension is supported.

    Args:
        filename: Name of the uploaded file.

    Returns:
        True if allowed, otherwise False.
    """
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS
