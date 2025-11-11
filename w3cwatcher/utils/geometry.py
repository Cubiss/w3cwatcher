from __future__ import annotations

from typing import Tuple

Point = Tuple[int, int]
Rect = Tuple[int, int, int, int]


def crop_to_aspect_ratio(rect: Rect, aspect_ratio: float) -> Rect:
    if aspect_ratio <= 0:
        raise ValueError("aspect_ratio must be > 0")

    l, t, r, b = rect
    if r <= l or b <= t:
        raise ValueError(f"Invalid rect {rect}")

    width = r - l
    height = b - t
    current_ratio = width / height

    if current_ratio > aspect_ratio:
        new_w = int(round(height * aspect_ratio))
        new_l = l + (width - new_w) // 2
        return new_l, t, new_l + new_w, b
    else:
        new_h = int(round(width / aspect_ratio))
        new_t = t + (height - new_h) // 2
        return l, new_t, r, new_t + new_h
