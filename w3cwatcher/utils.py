from __future__ import annotations
import sys
from pathlib import Path
import win32com.client
import ctypes
from typing import Tuple, Union
import win32gui
import win32con
from PIL import ImageGrab, Image, ImageDraw

def get_pixel_screen_xy(hwnd: int, x_pct: float, y_pct: float, aspect_ratio: float) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    rect = win32gui.GetClientRect(hwnd)

    if rect == (0,0,0,0):
        return (0,0), (0,0)

    left, top, right, bottom = get_relevant_rectangle(rect, aspect_ratio)

    width = right - left
    height = bottom - top

    x_off = int(width * x_pct)
    y_off = int(height * y_pct)

    cx, cy = win32gui.ClientToScreen(hwnd, (0, 0))
    return (cx + x_off, cy + y_off), (x_off, y_off)



def grab_pixel_rgb(screen_x: int, screen_y: int) -> Tuple[int, int, int]:
    bbox = (screen_x, screen_y, screen_x + 1, screen_y + 1)
    img = ImageGrab.grab(bbox=bbox, all_screens=True)
    return img.getpixel((0, 0))


def find_window_by_keyword(keyword: str):
    keyword = keyword.lower()
    matched_hwnd = None

    def enum_handler(hwnd, _):
        nonlocal matched_hwnd
        if matched_hwnd is not None:
            return

        title = win32gui.GetWindowText(hwnd)
        if title and keyword in title.lower() and win32gui.IsWindowVisible(hwnd):
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
        new_width = int(height * aspect_ratio)
        new_right = left + new_width
        return left, top, new_right, bottom
    else:
        new_height = int(width / aspect_ratio)
        new_bottom = top + new_height
        return left, top, right, new_bottom


def create_tray_shortcut():
    shell = win32com.client.Dispatch("WScript.Shell")
    desktop = Path(shell.SpecialFolders("Desktop"))

    shortcut_path = desktop / "W3CWatcher.lnk"

    exe = Path(sys.executable)
    pythonw = exe if exe.name.lower() == "pythonw.exe" else exe.with_name("pythonw.exe")
    if not pythonw.exists():
        pythonw = exe

    arguments = "-m w3cwatcher --tray"
    working_dir = Path.cwd()

    shortcut = shell.CreateShortcut(str(shortcut_path))
    shortcut.Targetpath = str(pythonw)
    shortcut.Arguments = arguments
    shortcut.WorkingDirectory = str(working_dir)
    shortcut.IconLocation = str(pythonw)
    shortcut.Description = "Launch PixelWatcher in tray mode"
    shortcut.Save()

    print(f"Created desktop shortcut: {shortcut_path}")
    return str(shortcut_path)

def name_color(r: int, g: int, b: int) -> str:
    """Return a coarse human-friendly color name for logging.
    Categories: black/white/gray/red/green/blue/yellow/cyan/magenta/unknown
    """
    r, g, b = [c / 255 for c in (r, g, b)]
    gray_threshold = 0.10
    brightness = (r + g + b) / 3
    max_c = max(r, g, b)
    min_c = min(r, g, b)
    saturation = max_c - min_c

    if saturation < gray_threshold:
        if brightness < 0.2:
            return "black"
        if brightness > 0.85:
            return "white"
        return "gray"

    if r > g and r > b:
        return "red"
    if g > r and g > b:
        return "green"
    if b > r and b > g:
        return "blue"

    if r > 0.5 and g > 0.5:
        return "yellow"
    if g > 0.5 and b > 0.5:
        return "cyan"
    if r > 0.5 and b > 0.5:
        return "magenta"

    return "unknown"



# new helper to normalize hwnd to root
GA_ROOT = win32con.GA_ROOT


def set_dpi_awareness() -> None:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass





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

def is_pyinstaller_bundle():
    if getattr(sys, 'frozen', False):
        print("Running in a PyInstaller bundle")
    else:
        print("Running as normal Python script")

