"""Fingerprint ridge counting service."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np
from skimage.morphology import skeletonize


@dataclass
class RidgeCountResult:
    """Container for ridge counting outputs."""

    ridge_count: int
    ridge_density: float
    skeleton: np.ndarray
    ridge_map: np.ndarray


def _binarize(image: np.ndarray, mask: Optional[np.ndarray] = None) -> np.ndarray:
    """Binarize image using adaptive thresholding.

    Args:
        image: Grayscale image in [0, 1] or [0, 255].
        mask: Optional foreground mask (0/1).

    Returns:
        Binary image with values 0 or 255.
    """
    if image.max() <= 1.0:
        src = (image * 255).astype(np.uint8)
    else:
        src = image.astype(np.uint8)

    src = cv2.GaussianBlur(src, (5, 5), 0)
    binary = cv2.adaptiveThreshold(
        src,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        21,
        7,
    )

    if mask is not None:
        binary = (binary * mask.astype(np.uint8))

    return binary


def _skeletonize(binary: np.ndarray) -> np.ndarray:
    """Skeletonize a binary ridge image."""
    skeleton = skeletonize(binary > 0)
    return (skeleton.astype(np.uint8) * 255)


def _count_centerline_ridges(skeleton: np.ndarray) -> int:
    """Count ridge transitions along the horizontal center line.

    Args:
        skeleton: Skeletonized binary image (0 or 255).

    Returns:
        Number of ridge transitions along the center line.
    """
    h = skeleton.shape[0]
    center_line = skeleton[h // 2, :]
    binary = (center_line > 0).astype(np.uint8)
    transitions = np.diff(binary)
    return int(np.sum(transitions == 1))


def _ridge_density(skeleton: np.ndarray, mask: Optional[np.ndarray]) -> float:
    """Compute ridge density as skeleton pixels per foreground area."""
    ridge_pixels = float(np.sum(skeleton > 0))
    if mask is None:
        area = float(skeleton.size)
    else:
        area = float(np.sum(mask > 0))
    if area <= 0:
        return 0.0
    return ridge_pixels / area


def count_ridges(image: np.ndarray, mask: Optional[np.ndarray] = None) -> RidgeCountResult:
    """Estimate ridge count using skeletonization and center-line tracing.

    Pipeline:
        1. Binarize enhanced image
        2. Skeletonize ridge map
        3. Count ridge transitions along center line
        4. Compute ridge density

    Args:
        image: Enhanced grayscale image in [0, 1].
        mask: Optional segmentation mask (0/1).

    Returns:
        RidgeCountResult containing ridge count, density, skeleton, and ridge map.
    """
    ridge_map = _binarize(image, mask)
    skeleton = _skeletonize(ridge_map)
    ridge_count = _count_centerline_ridges(skeleton)
    ridge_density = _ridge_density(skeleton, mask)

    return RidgeCountResult(
        ridge_count=ridge_count,
        ridge_density=ridge_density,
        skeleton=skeleton,
        ridge_map=ridge_map,
    )
