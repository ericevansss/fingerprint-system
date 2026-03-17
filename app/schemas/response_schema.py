"""API response schemas."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class MinutiaePointSchema(BaseModel):
    """Minutiae point schema."""

    x: int = Field(..., example=120)
    y: int = Field(..., example=80)
    score: float = Field(..., example=0.87)
    angle: float = Field(..., example=45.0)


class FingerprintAnalyzeResponse(BaseModel):
    """Response model for fingerprint analysis."""

    fingerprint_type: str = Field(..., example="whorl")
    confidence: float = Field(..., example=0.92)
    ridge_count: int = Field(..., example=17)
    ridge_density: float = Field(..., example=0.18)
    minutiae_points: List[MinutiaePointSchema]
    processing_time: str = Field(..., example="0.38s")

    enhanced_image: Optional[str] = Field(None, description="Base64-encoded PNG")
    skeleton_image: Optional[str] = Field(None, description="Base64-encoded PNG")
    ridge_map_image: Optional[str] = Field(None, description="Base64-encoded PNG")
