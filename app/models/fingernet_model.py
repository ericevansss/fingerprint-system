"""FingerNet-style model for fingerprint analysis.

This implementation follows the typical FingerNet pipeline:
- normalization
- orientation estimation
- segmentation
- enhancement
- minutiae extraction

The model is a multi-head CNN that produces orientation bins, segmentation mask,
image enhancement, minutiae heatmap, and classification logits.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import torch
from torch import nn
from torch.nn import functional as F

from app.config import ORIENTATION_BINS


class ImageNormalization(nn.Module):
    """Per-sample normalization layer used by FingerNet.

    This layer normalizes each input image to zero mean and unit variance.
    """

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        mean = x.mean(dim=(2, 3), keepdim=True)
        std = x.std(dim=(2, 3), keepdim=True) + 1e-5
        return (x - mean) / std


class ConvBlock(nn.Module):
    """A simple conv-batchnorm-relu block."""

    def __init__(self, in_channels: int, out_channels: int) -> None:
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.block(x)


@dataclass
class FingerNetOutputs:
    """Structured outputs from the FingerNet model."""

    orientation_logits: torch.Tensor
    segmentation_logits: torch.Tensor
    enhancement_logits: torch.Tensor
    minutiae_logits: torch.Tensor
    class_logits: torch.Tensor

    def as_dict(self) -> Dict[str, torch.Tensor]:
        return {
            "orientation_logits": self.orientation_logits,
            "segmentation_logits": self.segmentation_logits,
            "enhancement_logits": self.enhancement_logits,
            "minutiae_logits": self.minutiae_logits,
            "class_logits": self.class_logits,
        }


class FingerNetModel(nn.Module):
    """FingerNet-style multi-head CNN.

    The model uses a shared encoder and multiple task-specific heads:
    - Orientation estimation (orientation bins)
    - Segmentation (foreground mask)
    - Enhancement (ridge enhancement)
    - Minutiae detection (heatmap)
    - Classification (arch/loop/whorl)
    """

    def __init__(self, num_classes: int = 4, orientation_bins: int = ORIENTATION_BINS) -> None:
        super().__init__()
        self.normalization = ImageNormalization()

        self.encoder = nn.Sequential(
            ConvBlock(1, 16),
            ConvBlock(16, 16),
            nn.MaxPool2d(2),
            ConvBlock(16, 32),
            ConvBlock(32, 32),
            nn.MaxPool2d(2),
            ConvBlock(32, 64),
            ConvBlock(64, 64),
        )

        self.orientation_head = nn.Sequential(
            ConvBlock(64, 64),
            nn.Conv2d(64, orientation_bins, kernel_size=1),
        )
        self.segmentation_head = nn.Sequential(
            ConvBlock(64, 32),
            nn.Conv2d(32, 1, kernel_size=1),
        )
        self.enhancement_head = nn.Sequential(
            ConvBlock(64, 32),
            nn.Conv2d(32, 1, kernel_size=1),
        )
        self.minutiae_head = nn.Sequential(
            ConvBlock(64, 32),
            nn.Conv2d(32, 1, kernel_size=1),
        )

        self.classifier = nn.Sequential(
            nn.AdaptiveAvgPool2d((1, 1)),
            nn.Flatten(),
            nn.Linear(64, num_classes),
        )

    def forward(self, x: torch.Tensor) -> FingerNetOutputs:
        """Forward pass.

        Args:
            x: Input tensor of shape (N, 1, H, W) with values in [0, 1].

        Returns:
            FingerNetOutputs containing task logits.
        """
        x = self.normalization(x)
        features = self.encoder(x)

        orientation_logits = self.orientation_head(features)
        segmentation_logits = self.segmentation_head(features)
        enhancement_logits = self.enhancement_head(features)
        minutiae_logits = self.minutiae_head(features)
        class_logits = self.classifier(features)

        target_size = x.shape[-2:]
        orientation_logits = F.interpolate(
            orientation_logits, size=target_size, mode="bilinear", align_corners=False
        )
        segmentation_logits = F.interpolate(
            segmentation_logits, size=target_size, mode="bilinear", align_corners=False
        )
        enhancement_logits = F.interpolate(
            enhancement_logits, size=target_size, mode="bilinear", align_corners=False
        )
        minutiae_logits = F.interpolate(
            minutiae_logits, size=target_size, mode="bilinear", align_corners=False
        )

        return FingerNetOutputs(
            orientation_logits=orientation_logits,
            segmentation_logits=segmentation_logits,
            enhancement_logits=enhancement_logits,
            minutiae_logits=minutiae_logits,
            class_logits=class_logits,
        )
