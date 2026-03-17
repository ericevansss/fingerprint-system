"""Fingerprint image preprocessing pipeline."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import cv2
import numpy as np

from app.config import (
    CLAHE_CLIP_LIMIT,
    CLAHE_TILE_GRID_SIZE,
    GABOR_GAMMA,
    GABOR_KERNEL_SIZE,
    GABOR_LAMBDA,
    GABOR_SIGMA,
    IMAGE_SIZE,
)


@dataclass
class PreprocessResult:
    """Container for preprocessing outputs."""

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


def _gabor_kernels() -> Tuple[np.ndarray, ...]:
    """Create a bank of Gabor kernels for ridge enhancement."""
    kernels = []
    for theta in np.linspace(0, np.pi, 8, endpoint=False):
        kernel = cv2.getGaborKernel(
            (GABOR_KERNEL_SIZE, GABOR_KERNEL_SIZE),
            GABOR_SIGMA,
            theta,
            GABOR_LAMBDA,
            GABOR_GAMMA,
            psi=0,
            ktype=cv2.CV_32F,
        )
        kernels.append(kernel)
    return tuple(kernels)


def _enhance_with_gabor(image: np.ndarray) -> np.ndarray:
    """Enhance ridge structures using a Gabor filter bank."""
    responses = []
    for kernel in _gabor_kernels():
        filtered = cv2.filter2D(image, cv2.CV_32F, kernel)
        responses.append(filtered)
    response = np.max(np.stack(responses, axis=0), axis=0)
    response = cv2.normalize(response, None, 0, 1.0, cv2.NORM_MINMAX)
    return response.astype(np.float32)


def _segment_fingerprint(image: np.ndarray) -> np.ndarray:
    """Extract segmentation mask for fingerprint foreground."""
    img_u8 = np.clip(image * 255.0, 0, 255).astype(np.uint8)
    blurred = cv2.GaussianBlur(img_u8, (5, 5), 0)
    _, mask = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # Ensure foreground is white
    if mask.mean() > 127:
        mask = cv2.bitwise_not(mask)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)

    # Keep the largest connected component
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
    gray = _to_gray(image)
    normalized = _normalize(gray)
    clahe = _apply_clahe(normalized)
    enhanced = _enhance_with_gabor(clahe)
    mask = _segment_fingerprint(clahe)

    enhanced = enhanced * mask.astype(np.float32)

    enhanced_resized = _resize(enhanced, IMAGE_SIZE)
    mask_resized = _resize(mask, IMAGE_SIZE, is_mask=True)
    model_input = enhanced_resized.astype(np.float32)

    return PreprocessResult(
        gray=gray,
        normalized=normalized,
        clahe=clahe,
        enhanced=enhanced_resized,
        mask=mask_resized,
        model_input=model_input,
    )
