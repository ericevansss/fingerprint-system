"""API routes for fingerprint analysis."""
from __future__ import annotations

import time
from typing import List, Tuple

import cv2
from fastapi import APIRouter, File, HTTPException, UploadFile

from app.schemas.response_schema import FingerprintAnalyzeResponse
from app.services.core_delta_detection import compute_orientation, orientation_to_image
from app.services.fingernet_service import infer_fingerprint
from app.services.preprocessing import preprocess_fingerprint
from app.services.ridge_count_service import analyze_ridges
from app.services.result_fusion import fuse_results
from app.utils.file_utils import is_allowed_file
from app.utils.image_utils import decode_image_from_bytes, encode_image_to_base64

router = APIRouter(tags=["fingerprint"])


def _draw_core_delta_line(image: cv2.Mat, core: tuple[int, int], delta: tuple[int, int]) -> cv2.Mat:
    annotated = image.copy()
    cv2.line(annotated, core, delta, (0, 0, 255), 2)
    cv2.rectangle(annotated, (core[0] - 6, core[1] - 6), (core[0] + 6, core[1] + 6), (0, 0, 255), 2)
    cv2.rectangle(
        annotated, (delta[0] - 6, delta[1] - 6), (delta[0] + 6, delta[1] + 6), (0, 0, 255), 2
    )
    return annotated


def _visualize_skeleton(skeleton: cv2.Mat) -> cv2.Mat:
    """Render skeleton with black ridges on white background."""
    if skeleton.max() <= 1:
        skeleton_u8 = (skeleton * 255).astype("uint8")
    else:
        skeleton_u8 = skeleton.astype("uint8")
    return cv2.bitwise_not(skeleton_u8)


def _draw_minutiae(image: cv2.Mat, minutiae: List[Tuple[int, int, str]]) -> cv2.Mat:
    if image.ndim == 2:
        colored = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    else:
        colored = image.copy()

    for x, y, kind in minutiae:
        color = (0, 200, 0) if kind == "ending" else (0, 0, 255)
        cv2.circle(colored, (x, y), 6, color, 2)
    return colored


def _scale_point(point: Tuple[int, int], scale_x: float, scale_y: float) -> Tuple[int, int]:
    return (int(round(point[0] * scale_x)), int(round(point[1] * scale_y)))


def _visualize_core_delta(
    skeleton: np.ndarray,
    core: Tuple[int, int] | None,
    delta: Tuple[int, int] | None,
    ridge_count: int,
) -> np.ndarray:
    """Visualize core/delta on top of skeleton with ridge count label."""
    base = _visualize_skeleton(skeleton)
    if base.ndim == 2:
        base = cv2.cvtColor(base, cv2.COLOR_GRAY2BGR)
    if core and delta:
        cv2.line(base, core, delta, (0, 200, 0), 2)
    if core:
        cv2.circle(base, core, 6, (0, 0, 255), 2)
    if delta:
        cv2.circle(base, delta, 6, (255, 0, 0), 2)
    cv2.putText(
        base,
        f"Ridge Count: {ridge_count}",
        (12, 28),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 180, 255),
        2,
        cv2.LINE_AA,
    )
    return base


@router.post("/api/fingerprint/analyze", response_model=FingerprintAnalyzeResponse)
@router.post("/api/analyze", response_model=FingerprintAnalyzeResponse)
@router.post("/analyze", response_model=FingerprintAnalyzeResponse)
async def analyze_fingerprint(
    file: UploadFile = File(...),
    return_images: bool = True,
) -> FingerprintAnalyzeResponse:
    """Analyze a fingerprint image.

    Args:
        file: Uploaded fingerprint image.
        return_images: Whether to include processed images as base64.

    Returns:
        FingerprintAnalyzeResponse containing type, confidence, ridge metrics, and time.
    """
    if not is_allowed_file(file.filename):
        raise HTTPException(status_code=400, detail="Unsupported file type.")

    try:
        data = await file.read()
        image = decode_image_from_bytes(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    start = time.perf_counter()
    preprocess_result = preprocess_fingerprint(image)
    fingernet_result = infer_fingerprint(preprocess_result.model_input)
    ridge_result = analyze_ridges(
        preprocess_result.enhanced,
        preprocess_result.mask,
        orientation_source=preprocess_result.normalized,
    )
    elapsed = time.perf_counter() - start

    original = preprocess_result.original
    orig_h, orig_w = original.shape[:2]
    proc_h, proc_w = preprocess_result.enhanced.shape[:2]
    scale_x = orig_w / float(proc_w)
    scale_y = orig_h / float(proc_h)

    annotated_original = original.copy()
    core_scaled = None
    delta_scaled = None
    if ridge_result.core and ridge_result.delta:
        core_scaled = _scale_point((ridge_result.core.x, ridge_result.core.y), scale_x, scale_y)
        delta_scaled = _scale_point((ridge_result.delta.x, ridge_result.delta.y), scale_x, scale_y)
        annotated_original = _draw_core_delta_line(annotated_original, core_scaled, delta_scaled)

    skeleton_viz = _visualize_skeleton(ridge_result.skeleton)
    skeleton_viz = cv2.resize(skeleton_viz, (orig_w, orig_h), interpolation=cv2.INTER_NEAREST)
    ridge_map_viz = cv2.resize(ridge_result.ridge_map, (orig_w, orig_h), interpolation=cv2.INTER_NEAREST)

    scaled_minutiae: List[Tuple[int, int, str]] = []
    for x, y, kind in ridge_result.minutiae:
        scaled = _scale_point((x, y), scale_x, scale_y)
        scaled_minutiae.append((scaled[0], scaled[1], kind))

    enhanced_with_minutiae = _draw_minutiae(skeleton_viz, scaled_minutiae)

    orientation_field = compute_orientation(
        preprocess_result.normalized, block_size=16, smooth=True
    )
    orientation_viz = orientation_to_image(
        orientation_field,
        block_size=16,
        target_shape=(orig_h, orig_w),
        mask=preprocess_result.mask,
    )

    core_delta_viz = _visualize_core_delta(
        ridge_result.skeleton,
        (ridge_result.core.x, ridge_result.core.y) if ridge_result.core else None,
        (ridge_result.delta.x, ridge_result.delta.y) if ridge_result.delta else None,
        ridge_result.ridge_count,
    )
    core_delta_viz = cv2.resize(core_delta_viz, (orig_w, orig_h), interpolation=cv2.INTER_NEAREST)

    images = None
    if return_images:
        images = {
            "original_image": encode_image_to_base64(annotated_original),
            "enhanced_image": encode_image_to_base64(orientation_viz),
            "skeleton_image": encode_image_to_base64(skeleton_viz),
            "ridge_map_image": encode_image_to_base64(ridge_map_viz),
            "visualization_image": encode_image_to_base64(core_delta_viz),
        }

    response = fuse_results(fingernet_result, ridge_result, elapsed, images)
    if core_scaled:
        response["core_point"] = {"x": core_scaled[0], "y": core_scaled[1]}
        response["core"] = [core_scaled[0], core_scaled[1]]
    if delta_scaled:
        response["delta_point"] = {"x": delta_scaled[0], "y": delta_scaled[1]}
        response["delta"] = [delta_scaled[0], delta_scaled[1]]
    return FingerprintAnalyzeResponse(**response)
