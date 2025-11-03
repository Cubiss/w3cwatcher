from __future__ import annotations
import ctypes
from typing import Optional, Tuple, Union
import win32gui
import win32con
from PIL import ImageGrab, Image, ImageDraw

from w3cwatcher.utils import get_relevant_rectangle

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


def point_belongs_to_window(hwnd: int, sx: int, sy: int) -> bool:
    under = win32gui.WindowFromPoint((sx, sy))
    if not under:
        return False
    if win32gui.GetAncestor(under, GA_ROOT) != win32gui.GetAncestor(hwnd, GA_ROOT):
        return False
    cx, cy = win32gui.ScreenToClient(hwnd, (sx, sy))
    left, top, right, bottom = win32gui.GetClientRect(hwnd)
    return left <= cx < right and top <= cy < bottom


def get_window_image(hwnd: int, aspect_ratio: float) -> Image.Image:
    l, t, r, b = win32gui.GetClientRect(hwnd)
    if r - l <= 0 or b - t <= 0:
        raise RuntimeError("Window has no client area to capture")

    # Convert client (0,0) and (r,b) to screen coords
    pt_tl = win32gui.ClientToScreen(hwnd, (l, t))
    pt_br = win32gui.ClientToScreen(hwnd, (r, b))

    # bbox = (left, top, right, bottom) in screen coords
    bbox = (pt_tl[0], pt_tl[1], pt_br[0], pt_br[1])
    bbox = get_relevant_rectangle(bbox, aspect_ratio)

    # Grab what's currently visible on screen
    return ImageGrab.grab(bbox=bbox)


def draw_rectangle(
    image: Image.Image,
    location: Tuple[int, int],
    size: Union[int, Tuple[int, int]] = 10,
    width: int = 2,
    outline: str = "red",
) -> Image.Image:
    if isinstance(size, int):
        w = h = size
    else:
        w, h = size

    x, y = location
    x0 = int(round(x - w / 2))
    y0 = int(round(y - h / 2))
    x1 = int(round(x + w / 2))
    y1 = int(round(y + h / 2))

    # Clip to image bounds
    x0 = max(0, min(x0, image.width - 1))
    y0 = max(0, min(y0, image.height - 1))
    x1 = max(0, min(x1, image.width - 1))
    y1 = max(0, min(y1, image.height - 1))

    width = max(1, int(width))

    draw = ImageDraw.Draw(image)
    draw.rectangle([x0, y0, x1, y1], outline=outline, width=width)

    return image
