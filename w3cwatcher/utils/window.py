from __future__ import annotations

from typing import Callable, Optional

import win32con
import win32gui

from .geometry import Point, Rect, crop_to_aspect_ratio
from .platform import ensure_windows, GA_ROOT


def _enum_windows(predicate: Callable[[int, str], bool]) -> Optional[int]:
    ensure_windows()

    result: Optional[int] = None

    def _cb(hwnd, _param):
        nonlocal result
        if not win32gui.IsWindowVisible(hwnd):
            return True  # continue
        title = win32gui.GetWindowText(hwnd) or ""
        try:
            if predicate(hwnd, title):
                result = hwnd
                return False  # stop
        except Exception:
            # keep enumerating if predicate raised
            return True
        return True

    try:
        win32gui.EnumWindows(_cb, None)
    except Exception as ex:
        print(ex)
    return result


def find_window_by_title(keyword: str) -> Optional[int]:
    if not keyword:
        raise ValueError("keyword must be a non-empty string")
    return _enum_windows(lambda _hwnd, title: keyword.lower() in title.lower())


def bring_to_foreground(hwnd: int) -> None:
    ensure_windows()
    if not win32gui.IsWindow(hwnd):
        raise RuntimeError(f"Invalid window handle: {hwnd}")

    placement = win32gui.GetWindowPlacement(hwnd)
    show_cmd = placement[1]
    if show_cmd == win32con.SW_SHOWMINIMIZED:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    win32gui.SetForegroundWindow(hwnd)


def point_belongs_to_window(hwnd: int, screen_pos: Point) -> bool:
    ensure_windows()
    if not win32gui.IsWindow(hwnd):
        return False

    point_hwnd = win32gui.WindowFromPoint(screen_pos)
    if not point_hwnd:
        return False

    this_root = win32gui.GetAncestor(hwnd, GA_ROOT)
    that_root = win32gui.GetAncestor(point_hwnd, GA_ROOT)
    return this_root == that_root


def get_client_bbox_in_screen(hwnd: int, aspect_ratio: float = None) -> Rect:
    ensure_windows()
    l, t = win32gui.ClientToScreen(hwnd, (0, 0))
    _, _, width, height = win32gui.GetClientRect(hwnd)
    if width <= 0 or height <= 0:
        raise RuntimeError("Window client area is empty (width or height is 0).")

    client_bbox = l, t, l + width, t + height

    if aspect_ratio is not None:
        client_bbox = crop_to_aspect_ratio(client_bbox, aspect_ratio)
        pass

    return client_bbox
