"""Result fusion service."""
from __future__ import annotations

from dataclasses import asdict
from typing import Dict, Optional

from app.services.fingernet_service import FingerNetResult
from app.services.ridge_count_service import RidgeCountResult


def fuse_results(
    fingernet_result: FingerNetResult,
    ridge_result: RidgeCountResult,
    processing_time: float,
    images: Optional[Dict[str, str]] = None,
) -> Dict[str, object]:
    """Fuse results into a unified response dict.

    Args:
        fingernet_result: FingerNet output.
        ridge_result: Ridge counting output.
        processing_time: Processing time in seconds.
        images: Optional base64-encoded images to include in response.

    Returns:
        Dictionary formatted for API response.
    """
    result = asdict(fingernet_result)

    result["minutiae_points"] = [
        {"x": x, "y": y, "kind": kind} for x, y, kind in ridge_result.minutiae
    ]

    result.update(
        {
            "ridge_count": ridge_result.ridge_count,
            "ridge_density": ridge_result.ridge_density,
            "processing_time": f"{processing_time:.2f}s",
        }
    )

    if ridge_result.core:
        result["core_point"] = {"x": ridge_result.core.x, "y": ridge_result.core.y}
    if ridge_result.delta:
        result["delta_point"] = {"x": ridge_result.delta.x, "y": ridge_result.delta.y}
    if ridge_result.core:
        result["core"] = [ridge_result.core.x, ridge_result.core.y]
    if ridge_result.delta:
        result["delta"] = [ridge_result.delta.x, ridge_result.delta.y]

    result.pop("orientation_field", None)
    result.pop("segmentation_mask", None)
    result.pop("enhancement_map", None)
    result.pop("minutiae_map", None)

    if images:
        result.update(images)

    return result
