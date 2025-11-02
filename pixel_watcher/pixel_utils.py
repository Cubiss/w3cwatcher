from __future__ import annotations
from typing import Tuple
from PIL import ImageGrab
import pyautogui
import win32gui

def get_pixel_screen_xy(hwnd: int, x_off: int, y_off: int) -> Tuple[int, int]:
    cx, cy = win32gui.ClientToScreen(hwnd, (0, 0))
    return cx + x_off, cy + y_off


def grab_pixel_rgb(screen_x: int, screen_y: int) -> Tuple[int, int, int]:
    # Grab a 1x1 region
    bbox = (screen_x, screen_y, screen_x + 1, screen_y + 1)
    img = ImageGrab.grab(bbox=bbox, all_screens=True)
    return img.getpixel((0, 0))


def within_tolerance(rgb: Tuple[int, int, int], target: Tuple[int, int, int], tol: int) -> bool:
    return all(abs(a - b) <= tol for a, b in zip(rgb, target))


def calibrate_offsets(hwnd: int) -> tuple[int, int]:
    print("\n[Calibrate] Focus the target window. Move your mouse to the pixel and press ENTER here...")
    input()
    mx, my = pyautogui.position()
    cx, cy = win32gui.ClientToScreen(hwnd, (0, 0))
    xo, yo = mx - cx, my - cy
    print(f"[Calibrate] Suggested X_OFFSET={xo}, Y_OFFSET={yo}")
    return xo, yo
