"""FingerNet inference service."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
from torchvision.models import ResNet18_Weights, resnet18

from app.config import DEVICE_PREFERENCE, FINGERNET_CLASSES, RESNET_WEIGHTS_PATH

LOGGER = logging.getLogger(__name__)


@dataclass
class FingerNetResult:
    """FingerNet inference result."""

    fingerprint_type: str
    confidence: float
    minutiae_points: List[object]
    orientation_field: np.ndarray
    segmentation_mask: np.ndarray
    enhancement_map: np.ndarray
    minutiae_map: np.ndarray


_MODEL: Optional[nn.Module] = None
_DEVICE: Optional[torch.device] = None


def _get_device() -> torch.device:
    if DEVICE_PREFERENCE == "cuda" and torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def _init_resnet(num_classes: int) -> nn.Module:
    model = resnet18(weights=ResNet18_Weights.IMAGENET1K_V1)
    # Adapt first conv to 1-channel input
    old_conv = model.conv1
    new_conv = nn.Conv2d(1, old_conv.out_channels, kernel_size=7, stride=2, padding=3, bias=False)
    with torch.no_grad():
        new_conv.weight.copy_(old_conv.weight.mean(dim=1, keepdim=True))
    model.conv1 = new_conv
    model.fc = nn.Linear(model.fc.in_features, num_classes)
    return model


def load_fingernet_model() -> Tuple[nn.Module, torch.device]:
    """Load ResNet-18 classifier once at startup."""
    global _MODEL, _DEVICE
    if _MODEL is not None and _DEVICE is not None:
        return _MODEL, _DEVICE

    device = _get_device()
    model = _init_resnet(num_classes=len(FINGERNET_CLASSES))
    if RESNET_WEIGHTS_PATH.exists() and RESNET_WEIGHTS_PATH.stat().st_size > 0:
        state = torch.load(RESNET_WEIGHTS_PATH, map_location=device)
        incompatible = model.load_state_dict(state, strict=False)
        if incompatible.missing_keys:
            LOGGER.warning(
                "Missing keys when loading ResNet weights: %s", incompatible.missing_keys
            )
        if incompatible.unexpected_keys:
            LOGGER.warning(
                "Unexpected keys when loading ResNet weights: %s",
                incompatible.unexpected_keys,
            )
        LOGGER.info("Loaded ResNet weights from %s", RESNET_WEIGHTS_PATH)
    else:
        LOGGER.warning("ResNet weights not found; using randomly initialized model.")

    model.to(device)
    model.eval()
    _MODEL = model
    _DEVICE = device
    return model, device


def infer_fingerprint(image: np.ndarray) -> FingerNetResult:
    """Run ResNet-18 fingerprint classification.

    Args:
        image: Preprocessed grayscale image in [0, 1], shape (H, W).

    Returns:
        FingerNetResult containing classification and feature maps.
    """
    model, device = load_fingernet_model()

    tensor = torch.from_numpy(image).unsqueeze(0).unsqueeze(0).float().to(device)
    with torch.no_grad():
        logits = model(tensor)
        probs = F.softmax(logits, dim=1).cpu().numpy()[0]

    idx = int(np.argmax(probs))
    fingerprint_type = FINGERNET_CLASSES[idx]
    confidence = float(probs[idx])

    return FingerNetResult(
        fingerprint_type=fingerprint_type,
        confidence=confidence,
        minutiae_points=[],
        orientation_field=np.zeros_like(image, dtype=np.float32),
        segmentation_mask=np.zeros_like(image, dtype=np.float32),
        enhancement_map=np.zeros_like(image, dtype=np.float32),
        minutiae_map=np.zeros_like(image, dtype=np.float32),
    )
