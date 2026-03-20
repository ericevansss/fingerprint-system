"""Core and delta detection using Poincare index with block-wise orientation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import cv2
import numpy as np


@dataclass
class Singularity:
    kind: str
    x: int
    y: int


def _normalize_image(image: np.ndarray) -> np.ndarray:
    if image.max() <= 1.0:
        img = (image * 255.0).astype(np.float32)
    else:
        img = image.astype(np.float32)
    img = cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX)
    return img.astype(np.float32)


def _smooth_orientation(angles: np.ndarray) -> np.ndarray:
    cos2 = np.cos(2 * angles)
    sin2 = np.sin(2 * angles)
    cos2 = cv2.GaussianBlur(cos2, (5, 5), 0)
    sin2 = cv2.GaussianBlur(sin2, (5, 5), 0)
    return 0.5 * np.arctan2(sin2, cos2)


def compute_orientation(image: np.ndarray, block_size: int = 16, smooth: bool = True) -> np.ndarray:
    """Compute block-wise ridge orientation field."""
    img = _normalize_image(image)
    h, w = img.shape
    gx = cv2.Sobel(img, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(img, cv2.CV_32F, 0, 1, ksize=3)

    angles = []
    for i in range(0, h - block_size + 1, block_size):
        row = []
        for j in range(0, w - block_size + 1, block_size):
            block_gx = gx[i : i + block_size, j : j + block_size]
            block_gy = gy[i : i + block_size, j : j + block_size]
            nom = np.sum(2 * block_gx * block_gy)
            den = np.sum(block_gx ** 2 - block_gy ** 2)
            angle = 0.5 * (np.pi + np.arctan2(nom, den))
            row.append(angle)
        angles.append(row)

    angles = np.array(angles, dtype=np.float32)
    if smooth:
        angles = _smooth_orientation(angles)
    return angles


def _angle_diff(left: float, right: float) -> float:
    diff = left - right
    if abs(diff) > 180:
        diff = -1 * np.sign(diff) * (360 - abs(diff))
    return diff


def poincare_index_at(i: int, j: int, angles: np.ndarray, tolerance: int) -> str:
    cells = [(-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]
    deg_angles = [np.degrees(angles[i - k][j - l]) % 180 for k, l in cells]
    index = 0.0
    for k in range(0, 8):
        if abs(_angle_diff(deg_angles[k], deg_angles[k + 1])) > 90:
            deg_angles[k + 1] += 180
        index += _angle_diff(deg_angles[k], deg_angles[k + 1])

    if 180 - tolerance <= index <= 180 + tolerance:
        return "core"
    if -180 - tolerance <= index <= -180 + tolerance:
        return "delta"
    if 360 - tolerance <= index <= 360 + tolerance:
        return "core"
    return "none"


def find_singularities(
    angles: np.ndarray,
    block_size: int,
    tolerance: int,
    valid_blocks: Optional[np.ndarray] = None,
) -> List[Singularity]:
    singularities: List[Singularity] = []
    rows, cols = angles.shape
    for i in range(1, rows - 1):
        for j in range(1, cols - 1):
            if valid_blocks is not None and not valid_blocks[i, j]:
                continue
            kind = poincare_index_at(i, j, angles, tolerance)
            if kind == "none":
                continue
            x = int(j * block_size + block_size / 2)
            y = int(i * block_size + block_size / 2)
            singularities.append(Singularity(kind=kind, x=x, y=y))
    return singularities


def detect_core_delta(
    image: np.ndarray,
    mask: Optional[np.ndarray] = None,
    block_size: int = 16,
    tolerance: int = 8,
    min_block_fg: float = 0.6,
) -> Tuple[Optional[Tuple[int, int]], Optional[Tuple[int, int]]]:
    """Detect core and delta points using Poincare index."""
    orientation = compute_orientation(image, block_size=block_size, smooth=True)
    valid_blocks = None
    center = None
    if mask is not None:
        mask_u8 = (mask > 0).astype(np.uint8)
        h, w = mask_u8.shape
        rows, cols = orientation.shape
        valid_blocks = np.zeros((rows, cols), dtype=bool)
        for i in range(rows):
            for j in range(cols):
                y0 = i * block_size
                x0 = j * block_size
                y1 = min(h, y0 + block_size)
                x1 = min(w, x0 + block_size)
                block = mask_u8[y0:y1, x0:x1]
                if block.size == 0:
                    continue
                valid_blocks[i, j] = (float(np.mean(block)) >= min_block_fg)
        ys, xs = np.where(mask_u8 > 0)
        if ys.size > 0:
            center = np.array([float(np.mean(xs)), float(np.mean(ys))])

    singularities = find_singularities(
        orientation, block_size=block_size, tolerance=tolerance, valid_blocks=valid_blocks
    )
    if not singularities:
        return None, None

    h, w = image.shape
    if center is None:
        center = np.array([w / 2.0, h / 2.0])
    cores = [s for s in singularities if s.kind == "core"]
    deltas = [s for s in singularities if s.kind == "delta"]

    core = None
    delta = None
    if cores:
        core = min(cores, key=lambda s: np.linalg.norm(np.array([s.x, s.y]) - center))
    if deltas:
        delta = min(deltas, key=lambda s: np.linalg.norm(np.array([s.x, s.y]) - center))

    core_point = (core.x, core.y) if core else None
    delta_point = (delta.x, delta.y) if delta else None
    return core_point, delta_point


def orientation_to_image(
    angles: np.ndarray, block_size: int, target_shape: Tuple[int, int], mask: Optional[np.ndarray] = None
) -> np.ndarray:
    """Render orientation field as an HSV-colored image."""
    angle_deg = (np.degrees(angles) % 180.0).astype(np.float32)
    rows, cols = angle_deg.shape
    h, w = target_shape
    hue = np.clip(angle_deg / 180.0 * 179.0, 0, 179).astype(np.uint8)
    hsv = np.zeros((rows, cols, 3), dtype=np.uint8)
    hsv[..., 0] = hue
    hsv[..., 1] = 255
    hsv[..., 2] = 200
    bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    bgr = cv2.resize(bgr, (w, h), interpolation=cv2.INTER_NEAREST)
    if mask is not None:
        mask_u8 = (mask > 0).astype(np.uint8)
        if mask_u8.shape != (h, w):
            mask_u8 = cv2.resize(mask_u8, (w, h), interpolation=cv2.INTER_NEAREST)
        bgr[mask_u8 == 0] = 0
    return bgr


def _bresenham(p0: Tuple[int, int], p1: Tuple[int, int]) -> List[Tuple[int, int]]:
    x0, y0 = p0
    x1, y1 = p1
    points: List[Tuple[int, int]] = []
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        points.append((x0, y0))
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy
    return points


def count_ridges(
    skeleton: np.ndarray, core: Tuple[int, int], delta: Tuple[int, int]
) -> int:
    """Count ridge crossings along the line between core and delta."""
    line_points = _bresenham(core, delta)
    values = []
    h, w = skeleton.shape
    for x, y in line_points:
        if 0 <= x < w and 0 <= y < h:
            values.append(1 if skeleton[y, x] > 0 else 0)

    count = 0
    prev = 0
    for val in values:
        if val == 1 and prev == 0:
            count += 1
        prev = val
    return count
