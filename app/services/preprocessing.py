"""Fingerprint image preprocessing pipeline."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

import cv2
import numpy as np

from app.config import CLAHE_CLIP_LIMIT, CLAHE_TILE_GRID_SIZE, IMAGE_SIZE


@dataclass
class PreprocessResult:
    """Container for preprocessing outputs."""

    original: np.ndarray
    original_resized: np.ndarray
    gray: np.ndarray
    normalized: np.ndarray
    clahe: np.ndarray
    enhanced: np.ndarray
    mask: np.ndarray
    model_input: np.ndarray


def _to_gray(image: np.ndarray) -> np.ndarray:
    """Convert BGR image to grayscale float32 in [0, 1]."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return gray.astype(np.float32) / 255.0


def _normalize(gray: np.ndarray) -> np.ndarray:
    """Normalize grayscale image to [0, 1] with contrast stretching."""
    normalized = cv2.normalize(gray, None, 0, 1.0, cv2.NORM_MINMAX)
    return normalized.astype(np.float32)


def _apply_clahe(gray: np.ndarray) -> np.ndarray:
    """Apply CLAHE for local contrast enhancement."""
    gray_u8 = np.clip(gray * 255.0, 0, 255).astype(np.uint8)
    clahe = cv2.createCLAHE(
        clipLimit=CLAHE_CLIP_LIMIT,
        tileGridSize=CLAHE_TILE_GRID_SIZE,
    )
    enhanced = clahe.apply(gray_u8)
    return enhanced.astype(np.float32) / 255.0


def _load_external_enhancer():
    base_dir = Path(__file__).resolve().parents[2]
    enhancer_path = base_dir / "external" / "Fingerprint-Enhancement-Python" / "src"
    if str(enhancer_path) not in __import__("sys").path:
        __import__("sys").path.insert(0, str(enhancer_path))
    from fingerprint_enhancer.fingerprint_image_enhancer import FingerprintImageEnhancer

    return FingerprintImageEnhancer


def _segment_fingerprint(image: np.ndarray) -> np.ndarray:
    """Extract segmentation mask for fingerprint foreground."""
    img_u8 = np.clip(image * 255.0, 0, 255).astype(np.uint8)
    blurred = cv2.GaussianBlur(img_u8, (5, 5), 0)
    _, mask = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if mask.mean() > 127:
        mask = cv2.bitwise_not(mask)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        largest = max(contours, key=cv2.contourArea)
        mask = np.zeros_like(mask)
        cv2.drawContours(mask, [largest], -1, 255, thickness=cv2.FILLED)

    return (mask > 0).astype(np.uint8)


def _resize(image: np.ndarray, size: Tuple[int, int], is_mask: bool = False) -> np.ndarray:
    """Resize image or mask to target size."""
    interpolation = cv2.INTER_NEAREST if is_mask else cv2.INTER_AREA
    resized = cv2.resize(image, size, interpolation=interpolation)
    return resized


def preprocess_fingerprint(image: np.ndarray) -> PreprocessResult:
    """Preprocess fingerprint image.

    Pipeline:
        1. Grayscale conversion
        2. Normalization
        3. CLAHE contrast enhancement
        4. Gabor ridge enhancement
        5. Segmentation mask extraction
        6. Resize to model input size

    Args:
        image: Input BGR image.

    Returns:
        PreprocessResult containing intermediate outputs and model input.
    """
    original_resized = _resize(image, IMAGE_SIZE)

    gray = _to_gray(image)
    normalized = _normalize(gray)
    clahe = _apply_clahe(normalized)

    gray_u8 = np.clip(gray * 255.0, 0, 255).astype(np.uint8)
    enhanced = None
    mask = None
    try:
        FingerprintImageEnhancer = _load_external_enhancer()
        enhancer = FingerprintImageEnhancer()
        enhanced_bin = enhancer.enhance(gray_u8, resize=False, invert_output=False)
        enhanced = enhanced_bin.astype(np.float32)
        mask = enhancer._mask.astype(np.uint8)
        normalized = enhancer._normim.astype(np.float32)
    except Exception:
        mask = _segment_fingerprint(clahe)
        enhanced = normalized * mask.astype(np.float32)

    model_input = _resize(enhanced, IMAGE_SIZE).astype(np.float32)

    return PreprocessResult(
        original=image,
        original_resized=original_resized,
        gray=gray,
        normalized=normalized,
        clahe=clahe,
        enhanced=enhanced,
        mask=mask,
        model_input=model_input,
    )
