"""Image utilities for decoding, encoding, and validation."""
from __future__ import annotations

import base64
from typing import Optional

import cv2
import numpy as np


def decode_image_from_bytes(data: bytes) -> np.ndarray:
    """Decode image bytes into a BGR OpenCV image.

    Args:
        data: Raw image bytes.

    Returns:
        OpenCV BGR image as a NumPy array.

    Raises:
        ValueError: If the image cannot be decoded.
    """
    array = np.frombuffer(data, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Failed to decode image bytes.")
    return image


def encode_image_to_base64(image: np.ndarray, ext: str = ".png") -> Optional[str]:
    """Encode an image array to base64 string.

    Args:
        image: Image array (grayscale or BGR) in uint8 or float.
        ext: Image extension for encoding.

    Returns:
        Base64-encoded string without metadata prefix.
    """
    if image is None:
        return None

    if image.dtype != np.uint8:
        img = np.clip(image * 255.0, 0, 255).astype(np.uint8)
    else:
        img = image

    success, buffer = cv2.imencode(ext, img)
    if not success:
        return None
    return base64.b64encode(buffer.tobytes()).decode("utf-8")
