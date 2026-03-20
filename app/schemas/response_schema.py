"""API response schemas."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class MinutiaePointSchema(BaseModel):
    """Minutiae point schema."""

    x: int = Field(..., example=120)
    y: int = Field(..., example=80)
    kind: str = Field(..., example="ending")


class PointSchema(BaseModel):
    """Core/Delta point schema."""

    x: int
    y: int


class FingerprintAnalyzeResponse(BaseModel):
    """Response model for fingerprint analysis."""

    fingerprint_type: str = Field(..., example="whorl")
    confidence: float = Field(..., example=0.92)
    ridge_count: int = Field(..., example=17)
    ridge_density: float = Field(..., example=0.18)
    minutiae_points: List[MinutiaePointSchema]
    processing_time: str = Field(..., example="0.38s")

    core_point: Optional[PointSchema] = None
    delta_point: Optional[PointSchema] = None

    original_image: Optional[str] = Field(None, description="Base64-encoded PNG")
    enhanced_image: Optional[str] = Field(None, description="Base64-encoded PNG")
    skeleton_image: Optional[str] = Field(None, description="Base64-encoded PNG")
    ridge_map_image: Optional[str] = Field(None, description="Base64-encoded PNG")
    visualization_image: Optional[str] = Field(None, description="Base64-encoded PNG")

    core: Optional[List[int]] = None
    delta: Optional[List[int]] = None
