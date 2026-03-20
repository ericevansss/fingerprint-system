"""Fingerprint alignment utilities adapted from mehmetaydar/fingerprint-alignment.

This module provides orientation estimation, Poincare-based singularity detection
(core/delta), skeletonization, minutiae extraction, and ridge counting along a
core-delta line.
"""
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


@dataclass
class CoreDeltaResult:
    core: Optional[Singularity]
    delta: Optional[Singularity]


def _get_angle(left: float, right: float) -> float:
    angle = left - right
    if abs(angle) > 180:
        angle = -1 * np.sign(angle) * (360 - abs(angle))
    return angle


def compute_orientation(image: np.ndarray, block_size: int = 16, smooth: bool = True) -> np.ndarray:
    """Compute orientation field using a Sobel-based approach."""
    h, w = image.shape
    gx = cv2.Sobel(image, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(image, cv2.CV_32F, 0, 1, ksize=3)

    angles = []
    for i in range(0, h - block_size + 1, block_size):
        row = []
        for j in range(0, w - block_size + 1, block_size):
            block_gx = gx[i : i + block_size, j : j + block_size]
            block_gy = gy[i : i + block_size, j : j + block_size]
            nominator = np.sum(2 * block_gx * block_gy)
            denominator = np.sum(block_gx ** 2 - block_gy ** 2)
            angle = 0.5 * (np.pi + np.arctan2(nominator, denominator))
            row.append(angle)
        angles.append(row)

    angles = np.array(angles, dtype=np.float32)

    if smooth:
        angles = smooth_angles(angles)

    return angles


def smooth_angles(angles: np.ndarray) -> np.ndarray:
    cos2 = np.cos(2 * angles)
    sin2 = np.sin(2 * angles)
    cos2 = cv2.GaussianBlur(cos2, (5, 5), 0)
    sin2 = cv2.GaussianBlur(sin2, (5, 5), 0)
    return 0.5 * np.arctan2(sin2, cos2)


def poincare_index_at(i: int, j: int, angles: np.ndarray, tolerance: int) -> str:
    cells = [(-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]
    deg_angles = [np.degrees(angles[i - k][j - l]) % 180 for k, l in cells]
    index = 0.0
    for k in range(0, 8):
        if abs(_get_angle(deg_angles[k], deg_angles[k + 1])) > 90:
            deg_angles[k + 1] += 180
        index += _get_angle(deg_angles[k], deg_angles[k + 1])

    if 180 - tolerance <= index <= 180 + tolerance:
        return "loop"
    if -180 - tolerance <= index <= -180 + tolerance:
        return "delta"
    if 360 - tolerance <= index <= 360 + tolerance:
        return "whorl"
    return "none"


def find_singularities(angles: np.ndarray, block_size: int, tolerance: int) -> List[Singularity]:
    singularities: List[Singularity] = []
    rows, cols = angles.shape

    for i in range(1, rows - 1):
        for j in range(1, cols - 1):
            kind = poincare_index_at(i, j, angles, tolerance)
            if kind == "none":
                continue
            x = int(j * block_size + block_size / 2)
            y = int(i * block_size + block_size / 2)
            singularities.append(Singularity(kind=kind, x=x, y=y))

    return singularities


def select_core_delta(
    singularities: List[Singularity], image_shape: Tuple[int, int]
) -> CoreDeltaResult:
    h, w = image_shape
    center = np.array([w / 2.0, h / 2.0])

    loops = [s for s in singularities if s.kind in {"loop", "whorl"}]
    deltas = [s for s in singularities if s.kind == "delta"]

    core = None
    delta = None

    if loops:
        core = min(loops, key=lambda s: np.linalg.norm(np.array([s.x, s.y]) - center))
    if deltas:
        delta = min(deltas, key=lambda s: np.linalg.norm(np.array([s.x, s.y]) - center))

    return CoreDeltaResult(core=core, delta=delta)


def binarize_image(image: np.ndarray, mask: Optional[np.ndarray] = None) -> np.ndarray:
    if image.max() <= 1.0:
        src = (image * 255).astype(np.uint8)
    else:
        src = image.astype(np.uint8)

    unique_vals = np.unique(src)
    if len(unique_vals) <= 2 and set(unique_vals.tolist()) <= {0, 1, 255}:
        binary = (src > 0).astype(np.uint8) * 255
    else:
        binary = cv2.adaptiveThreshold(
            src,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            21,
            7,
        )

    if mask is not None:
        binary = binary * mask.astype(np.uint8)

    return binary


def _neighbours(x: int, y: int, image: np.ndarray) -> List[int]:
    return [
        image[x - 1][y],
        image[x - 1][y + 1],
        image[x][y + 1],
        image[x + 1][y + 1],
        image[x + 1][y],
        image[x + 1][y - 1],
        image[x][y - 1],
        image[x - 1][y - 1],
    ]


def _transitions(neighbours: List[int]) -> int:
    n = neighbours + neighbours[0:1]
    return sum((n1, n2) == (0, 1) for n1, n2 in zip(n, n[1:]))


def _zhang_suen_thinning(image: np.ndarray) -> np.ndarray:
    """Zhang-Suen thinning algorithm adapted from linbojin repo."""
    img = (image > 0).astype(np.uint8)
    changing1 = changing2 = [(-1, -1)]
    rows, columns = img.shape
    while changing1 or changing2:
        changing1 = []
        for x in range(1, rows - 1):
            for y in range(1, columns - 1):
                p2, p3, p4, p5, p6, p7, p8, p9 = n = _neighbours(x, y, img)
                if (
                    img[x][y] == 1
                    and 2 <= sum(n) <= 6
                    and _transitions(n) == 1
                    and p2 * p4 * p6 == 0
                    and p4 * p6 * p8 == 0
                ):
                    changing1.append((x, y))
        for x, y in changing1:
            img[x][y] = 0

        changing2 = []
        for x in range(1, rows - 1):
            for y in range(1, columns - 1):
                p2, p3, p4, p5, p6, p7, p8, p9 = n = _neighbours(x, y, img)
                if (
                    img[x][y] == 1
                    and 2 <= sum(n) <= 6
                    and _transitions(n) == 1
                    and p2 * p4 * p8 == 0
                    and p2 * p6 * p8 == 0
                ):
                    changing2.append((x, y))
        for x, y in changing2:
            img[x][y] = 0
    return img


def skeletonize_image(binary: np.ndarray) -> np.ndarray:
    skeleton = _zhang_suen_thinning(binary)
    return skeleton.astype(np.uint8)


def extract_minutiae(skeleton: np.ndarray) -> List[Tuple[int, int, str]]:
    minutiae: List[Tuple[int, int, str]] = []
    h, w = skeleton.shape

    cells = [(-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]

    for y in range(1, h - 1):
        for x in range(1, w - 1):
            if skeleton[y, x] == 0:
                continue
            values = [skeleton[y + dy, x + dx] for dy, dx in cells]
            crossings = 0
            for k in range(0, 8):
                crossings += abs(int(values[k]) - int(values[k + 1]))
            crossings //= 2
            if crossings == 1:
                minutiae.append((x, y, "ending"))
            elif crossings == 3:
                minutiae.append((x, y, "bifurcation"))

    return minutiae


def filter_minutiae(
    minutiae: List[Tuple[int, int, str]],
    mask: Optional[np.ndarray] = None,
    min_dist: int = 10,
    margin: int = 12,
    max_points: int = 200,
) -> List[Tuple[int, int, str]]:
    """Filter minutiae points to remove noise and border artifacts."""
    if not minutiae:
        return []

    allowed = None
    distance = None
    if mask is not None:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (17, 17))
        allowed = cv2.erode(mask.astype(np.uint8), kernel, iterations=1)
        distance = cv2.distanceTransform(mask.astype(np.uint8), cv2.DIST_L2, 3)

    kept: List[Tuple[int, int, str]] = []
    min_dist_sq = float(min_dist * min_dist)

    for x, y, kind in minutiae:
        if x < margin or y < margin:
            continue
        if mask is not None:
            h, w = mask.shape
            if x >= w - margin or y >= h - margin:
                continue
        if allowed is not None and allowed[y, x] == 0:
            continue
        if distance is not None:
            dist_val = float(distance[y, x])
            if kind == "ending" and dist_val > 18:
                continue
            if kind == "bifurcation" and dist_val < 6:
                continue
        if any((x - kx) ** 2 + (y - ky) ** 2 < min_dist_sq for kx, ky, _ in kept):
            continue
        kept.append((x, y, kind))
        if len(kept) >= max_points:
            break

    return kept


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


def _fill_small_gaps(values: List[int], max_gap: int = 2) -> List[int]:
    filled = values[:]
    i = 0
    n = len(filled)
    while i < n:
        if filled[i] == 0:
            j = i
            while j < n and filled[j] == 0:
                j += 1
            gap = j - i
            if i > 0 and j < n and filled[i - 1] == 1 and filled[j] == 1 and gap <= max_gap:
                for k in range(i, j):
                    filled[k] = 1
            i = j
        else:
            i += 1
    return filled


def count_ridges_along_line(
    skeleton: np.ndarray, core: Singularity, delta: Singularity, max_gap: int = 2
) -> int:
    line_points = _bresenham((core.x, core.y), (delta.x, delta.y))
    values = []
    h, w = skeleton.shape

    for x, y in line_points:
        if 0 <= x < w and 0 <= y < h:
            values.append(1 if skeleton[y, x] > 0 else 0)

    values = _fill_small_gaps(values, max_gap=max_gap)

    count = 0
    prev = 0
    for val in values:
        if val == 1 and prev == 0:
            count += 1
        prev = val

    return count
