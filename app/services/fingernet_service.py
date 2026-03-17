"""FingerNet inference service."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np
import torch
from torch.nn import functional as F

from app.config import (
    DEVICE_PREFERENCE,
    FINGERNET_CLASSES,
    FINGERNET_WEIGHTS_PATH,
    MINUTIAE_NMS_RADIUS,
    MINUTIAE_THRESHOLD,
    ORIENTATION_BINS,
)
from app.models.fingernet_model import FingerNetModel

LOGGER = logging.getLogger(__name__)


@dataclass
class MinutiaePoint:
    """Single minutiae detection."""

    x: int
    y: int
    score: float
    angle: float


@dataclass
class FingerNetResult:
    """FingerNet inference result."""

    fingerprint_type: str
    confidence: float
    minutiae_points: List[MinutiaePoint]
    orientation_field: np.ndarray
    segmentation_mask: np.ndarray
    enhancement_map: np.ndarray
    minutiae_map: np.ndarray


_MODEL: Optional[FingerNetModel] = None
_DEVICE: Optional[torch.device] = None


def _get_device() -> torch.device:
    if DEVICE_PREFERENCE == "cuda" and torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def load_fingernet_model() -> Tuple[FingerNetModel, torch.device]:
    """Load FingerNet model once at startup.

    Returns:
        Model and device.
    """
    global _MODEL, _DEVICE
    if _MODEL is not None and _DEVICE is not None:
        return _MODEL, _DEVICE

    device = _get_device()
    model = FingerNetModel(num_classes=len(FINGERNET_CLASSES), orientation_bins=ORIENTATION_BINS)
    if FINGERNET_WEIGHTS_PATH.exists() and FINGERNET_WEIGHTS_PATH.stat().st_size > 0:
        state = torch.load(FINGERNET_WEIGHTS_PATH, map_location=device)
        incompatible = model.load_state_dict(state, strict=False)
        if incompatible.missing_keys:
            LOGGER.warning(
                "Missing keys when loading FingerNet weights: %s", incompatible.missing_keys
            )
        if incompatible.unexpected_keys:
            LOGGER.warning(
                "Unexpected keys when loading FingerNet weights: %s",
                incompatible.unexpected_keys,
            )
        LOGGER.info("Loaded FingerNet weights from %s", FINGERNET_WEIGHTS_PATH)
    else:
        LOGGER.warning("FingerNet weights not found; using randomly initialized model.")

    model.to(device)
    model.eval()
    _MODEL = model
    _DEVICE = device
    return model, device


def _orientation_field(orientation_logits: torch.Tensor) -> np.ndarray:
    """Convert orientation logits to a dense orientation field in degrees."""
    probs = F.softmax(orientation_logits, dim=1)
    angle_step = 180.0 / ORIENTATION_BINS
    angles = torch.arange(0.0, 180.0, angle_step, device=orientation_logits.device)
    angles = angles.view(1, -1, 1, 1)
    orientation = torch.sum(probs * angles, dim=1)
    return orientation.squeeze(0).cpu().numpy()


def _extract_minutiae(
    minutiae_map: np.ndarray, orientation_field: np.ndarray
) -> List[MinutiaePoint]:
    """Extract minutiae points using thresholding and non-maximum suppression."""
    points: List[MinutiaePoint] = []
    if minutiae_map.ndim != 2:
        return points

    candidate_indices = np.argwhere(minutiae_map >= MINUTIAE_THRESHOLD)
    if candidate_indices.size == 0:
        return points

    radius = MINUTIAE_NMS_RADIUS
    for y, x in candidate_indices:
        y0 = max(0, y - radius)
        y1 = min(minutiae_map.shape[0], y + radius + 1)
        x0 = max(0, x - radius)
        x1 = min(minutiae_map.shape[1], x + radius + 1)
        window = minutiae_map[y0:y1, x0:x1]
        if minutiae_map[y, x] >= np.max(window):
            points.append(
                MinutiaePoint(
                    x=int(x),
                    y=int(y),
                    score=float(minutiae_map[y, x]),
                    angle=float(orientation_field[y, x]),
                )
            )

    return points


def infer_fingerprint(image: np.ndarray) -> FingerNetResult:
    """Run FingerNet inference.

    Args:
        image: Preprocessed grayscale image in [0, 1], shape (H, W).

    Returns:
        FingerNetResult containing classification and feature maps.
    """
    model, device = load_fingernet_model()

    tensor = torch.from_numpy(image).unsqueeze(0).unsqueeze(0).float().to(device)
    with torch.no_grad():
        outputs = model(tensor)
        class_logits = outputs.class_logits
        probs = F.softmax(class_logits, dim=1).cpu().numpy()[0]

        orientation_field = _orientation_field(outputs.orientation_logits)
        segmentation_mask = torch.sigmoid(outputs.segmentation_logits).squeeze(0).squeeze(0)
        enhancement_map = torch.sigmoid(outputs.enhancement_logits).squeeze(0).squeeze(0)
        minutiae_map = torch.sigmoid(outputs.minutiae_logits).squeeze(0).squeeze(0)

    segmentation_mask_np = segmentation_mask.cpu().numpy()
    enhancement_map_np = enhancement_map.cpu().numpy()
    minutiae_map_np = minutiae_map.cpu().numpy()

    idx = int(np.argmax(probs))
    fingerprint_type = FINGERNET_CLASSES[idx]
    confidence = float(probs[idx])

    minutiae_points = _extract_minutiae(minutiae_map_np, orientation_field)

    return FingerNetResult(
        fingerprint_type=fingerprint_type,
        confidence=confidence,
        minutiae_points=minutiae_points,
        orientation_field=orientation_field,
        segmentation_mask=segmentation_mask_np,
        enhancement_map=enhancement_map_np,
        minutiae_map=minutiae_map_np,
    )
