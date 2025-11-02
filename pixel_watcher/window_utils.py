from __future__ import annotations
import ctypes
from typing import Optional, Tuple
import win32gui
import win32con

# new helper to normalize hwnd to root
GA_ROOT = win32con.GA_ROOT


def set_dpi_awareness() -> None:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def find_window_by_keyword(keyword: str) -> Optional[int]:
    target_hwnd = None

    def _enum_cb(hwnd, _):
        nonlocal target_hwnd
        if not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd)
        if keyword == title:
            target_hwnd = hwnd
    win32gui.EnumWindows(_enum_cb, None)
    return target_hwnd


def get_client_top_left_screen(hwnd: int) -> Tuple[int, int]:
    return win32gui.ClientToScreen(hwnd, (0, 0))


def bring_to_foreground(hwnd: int) -> None:
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        pass

# NEW: verify pixel belongs to window

def point_belongs_to_window(hwnd: int, sx: int, sy: int) -> bool:
    under = win32gui.WindowFromPoint((sx, sy))
    if not under:
        return False
    if win32gui.GetAncestor(under, GA_ROOT) != win32gui.GetAncestor(hwnd, GA_ROOT):
        return False
    cx, cy = win32gui.ScreenToClient(hwnd, (sx, sy))
    left, top, right, bottom = win32gui.GetClientRect(hwnd)
    return left <= cx < right and top <= cy < bottom
