"""Fingerprint ridge counting service using fingerprint-alignment logic."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import cv2
import numpy as np

from app.services.core_delta_detection import count_ridges, detect_core_delta
from app.services.fingerprint_alignment import (
    Singularity,
    binarize_image,
    extract_minutiae,
    filter_minutiae,
    skeletonize_image,
)


@dataclass
class RidgeCountResult:
    """Container for ridge counting outputs."""

    ridge_count: int
    ridge_density: float
    skeleton: np.ndarray
    ridge_map: np.ndarray
    core: Optional[Singularity]
    delta: Optional[Singularity]
    minutiae: List[Tuple[int, int, str]]


def _ridge_density(skeleton: np.ndarray, mask: Optional[np.ndarray]) -> float:
    ridge_pixels = float(np.sum(skeleton > 0))
    if mask is None:
        area = float(skeleton.size)
    else:
        area = float(np.sum(mask > 0))
    if area <= 0:
        return 0.0
    return ridge_pixels / area


def analyze_ridges(
    enhanced: np.ndarray,
    mask: Optional[np.ndarray] = None,
    orientation_source: Optional[np.ndarray] = None,
    block_size: int = 16,
    tolerance: int = 8,
) -> RidgeCountResult:
    """Run ridge analysis with core/delta detection and ridge counting.

    Returns ridge count along the core-delta line, skeleton image, ridge map,
    and extracted minutiae.
    """
    ridge_map = binarize_image(enhanced, mask)
    ridge_map = _remove_small_components(ridge_map, min_size=40)
    kernel = np.ones((3, 3), np.uint8)
    ridge_map = cv2.morphologyEx(ridge_map, cv2.MORPH_CLOSE, kernel, iterations=1)
    ridge_map = cv2.morphologyEx(ridge_map, cv2.MORPH_OPEN, kernel, iterations=1)
    skeleton = skeletonize_image(ridge_map)

    orientation_image = orientation_source if orientation_source is not None else enhanced
    if mask is not None and mask.shape != orientation_image.shape:
        mask = cv2.resize(mask, (orientation_image.shape[1], orientation_image.shape[0]), interpolation=cv2.INTER_NEAREST)
        mask = (mask > 0).astype(np.uint8)
    core_point, delta_point = detect_core_delta(
        orientation_image,
        mask=mask,
        block_size=block_size,
        tolerance=tolerance,
    )
    if core_point and mask is not None and mask[core_point[1], core_point[0]] == 0:
        core_point = None
    if delta_point and mask is not None and mask[delta_point[1], delta_point[0]] == 0:
        delta_point = None

    ridge_count = 0
    if core_point and delta_point:
        ridge_count = count_ridges(skeleton, core_point, delta_point)

    ridge_density = _ridge_density(skeleton, mask)
    minutiae_raw = extract_minutiae(skeleton)
    minutiae = filter_minutiae(minutiae_raw, mask)

    return RidgeCountResult(
        ridge_count=ridge_count,
        ridge_density=ridge_density,
        skeleton=skeleton,
        ridge_map=ridge_map,
        core=Singularity(kind="core", x=core_point[0], y=core_point[1]) if core_point else None,
        delta=Singularity(kind="delta", x=delta_point[0], y=delta_point[1]) if delta_point else None,
        minutiae=minutiae,
    )


def _remove_small_components(binary: np.ndarray, min_size: int = 40) -> np.ndarray:
    if binary.dtype != np.uint8:
        binary_u8 = binary.astype(np.uint8)
    else:
        binary_u8 = binary

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary_u8, connectivity=8)
    cleaned = np.zeros_like(binary_u8)
    for label in range(1, num_labels):
        area = stats[label, cv2.CC_STAT_AREA]
        if area >= min_size:
            cleaned[labels == label] = 255
    return cleaned
