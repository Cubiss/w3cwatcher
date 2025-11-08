from __future__ import annotations

from typing import Callable, Optional

from .geometry import Point, Rect

def _enum_windows(predicate: Callable[[int, str], bool]) -> Optional[int]:
    _ensure_windows()

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

    win32gui.EnumWindows(_cb, None)
    return result


def find_window_by_title(keyword: str) -> Optional[int]:
    if not keyword:
        raise ValueError("keyword must be a non-empty string")
    return _enum_windows(lambda _hwnd, title: keyword.lower() in title.lower())


def bring_to_foreground(hwnd: int) -> None:
    _ensure_windows()
    if not win32gui.IsWindow(hwnd):
        raise RuntimeError(f"Invalid window handle: {hwnd}")

    # Restore if minimized, then set foreground.
    placement = win32gui.GetWindowPlacement(hwnd)
    show_cmd = placement[1]
    if show_cmd == win32con.SW_SHOWMINIMIZED:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    win32gui.SetForegroundWindow(hwnd)


def point_belongs_to_window(hwnd: int, screen_pos: Point) -> bool:
    _ensure_windows()
    if not win32gui.IsWindow(hwnd):
        return False

    point_hwnd = win32gui.WindowFromPoint(screen_pos)
    if not point_hwnd:
        return False

    # Compare root ancestors to handle child windows.
    this_root = win32gui.GetAncestor(hwnd, GA_ROOT)
    that_root = win32gui.GetAncestor(point_hwnd, GA_ROOT)
    return this_root == that_root


def get_client_top_left_screen(hwnd: int) -> Point:
    _ensure_windows()
    if not win32gui.IsWindow(hwnd):
        raise RuntimeError(f"Invalid window handle: {hwnd}")

    # ClientToScreen converts client (0,0) to screen coords
    return win32gui.ClientToScreen(hwnd, (0, 0))


def _get_client_rect(hwnd: int) -> Rect:
    """
    Client rect in client coords (left=0, top=0, right, bottom).
    """
    _ensure_windows()
    l, t, r, b = win32gui.GetClientRect(hwnd)
    return l, t, r, b


# Expose a small helper for imaging to use without extra imports.
def get_client_bbox_in_screen(hwnd: int) -> Rect:
    """
    Return client rectangle for `hwnd` mapped to screen coordinates as (L, T, R, B).

    Raises
    ------
    RuntimeError if the client area is empty.
    """
    _ensure_windows()
    l, t = get_client_top_left_screen(hwnd)
    cl, ct, cr, cb = _get_client_rect(hwnd)
    width = cr - cl
    height = cb - ct
    if width <= 0 or height <= 0:
        raise RuntimeError("Window client area is empty (width or height is 0).")
    return l, t, l + width, t + height
