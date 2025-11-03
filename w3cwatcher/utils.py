from __future__ import annotations
from typing import Tuple
from PIL import ImageGrab
import pyautogui
import win32gui


def get_pixel_screen_xy(hwnd: int, x_pct: float, y_pct: float, aspect_ratio: float) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    # Get client rect relative to client area (0,0)-(width,height)
    rect = win32gui.GetClientRect(hwnd)

    if rect == (0,0,0,0):
        return (0,0), (0,0)

    left, top, right, bottom = get_relevant_rectangle(rect, aspect_ratio)

    width = right - left
    height = bottom - top

    # Convert percent offset to client pixel positions
    x_off = int(width * x_pct)
    y_off = int(height * y_pct)

    # Convert to screen coordinates
    cx, cy = win32gui.ClientToScreen(hwnd, (0, 0))
    return (cx + x_off, cy + y_off), (x_off, y_off)



def grab_pixel_rgb(screen_x: int, screen_y: int) -> Tuple[int, int, int]:
    # Grab a 1x1 region
    bbox = (screen_x, screen_y, screen_x + 1, screen_y + 1)
    img = ImageGrab.grab(bbox=bbox, all_screens=True)
    return img.getpixel((0, 0))


def within_tolerance(rgb: Tuple[int, int, int], target: Tuple[int, int, int], tol: int) -> bool:
    return all(abs(a - b) <= tol for a, b in zip(rgb, target))


def find_window_by_keyword(keyword: str):
    keyword = keyword.lower()
    matched_hwnd = None

    def enum_handler(hwnd, _):
        nonlocal matched_hwnd
        if matched_hwnd is not None:
            return  # already found, skip further checks

        # Get window title
        title = win32gui.GetWindowText(hwnd)
        if keyword in title.lower() and win32gui.IsWindowVisible(hwnd):
            matched_hwnd = hwnd

    win32gui.EnumWindows(enum_handler, None)
    return matched_hwnd

def get_relevant_rectangle(
    rect: Tuple[int, int, int, int],
    aspect_ratio: float
) -> Tuple[int, int, int, int]:
    left, top, right, bottom = rect

    width  = right - left
    height = bottom - top

    current_ratio = width / height

    if current_ratio > aspect_ratio:
        # Too wide — trim right side instead of left
        new_width = int(height * aspect_ratio)
        new_right = left + new_width
        return left, top, new_right, bottom
    else:
        # Too tall — trim bottom
        new_height = int(width / aspect_ratio)
        new_bottom = top + new_height
        return left, top, right, new_bottom
