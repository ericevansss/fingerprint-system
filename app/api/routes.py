"""API routes for fingerprint analysis."""
from __future__ import annotations

import time
from fastapi import APIRouter, File, HTTPException, UploadFile

from app.schemas.response_schema import FingerprintAnalyzeResponse
from app.services.fingernet_service import infer_fingerprint
from app.services.preprocessing import preprocess_fingerprint
from app.services.ridge_count_service import count_ridges
from app.services.result_fusion import fuse_results
from app.utils.file_utils import is_allowed_file
from app.utils.image_utils import decode_image_from_bytes, encode_image_to_base64

router = APIRouter(tags=["fingerprint"])


@router.post("/api/fingerprint/analyze", response_model=FingerprintAnalyzeResponse)
@router.post("/api/analyze", response_model=FingerprintAnalyzeResponse)
@router.post("/analyze", response_model=FingerprintAnalyzeResponse)
async def analyze_fingerprint(
    file: UploadFile = File(...),
    return_images: bool = False,
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
    ridge_result = count_ridges(preprocess_result.enhanced, preprocess_result.mask)
    elapsed = time.perf_counter() - start

    images = None
    if return_images:
        images = {
            "enhanced_image": encode_image_to_base64(preprocess_result.enhanced),
            "skeleton_image": encode_image_to_base64(ridge_result.skeleton),
            "ridge_map_image": encode_image_to_base64(ridge_result.ridge_map),
        }

    response = fuse_results(fingernet_result, ridge_result, elapsed, images)
    return FingerprintAnalyzeResponse(**response)
