from __future__ import annotations

from typing import Optional, Tuple

from PIL import Image, ImageGrab, ImageDraw

from .geometry import crop_to_aspect_ratio, Point
from .window import get_client_bbox_in_screen

def hwnd_relative_to_screen_xy(
    hwnd: int,
    x_relative_ltr: float,
    y_relative_ttb: float,
    aspect_ratio: float=None,
) -> Tuple[Point, Point]:
    if not (0.0 <= x_relative_ltr <= 100.0 and 0.0 <= y_relative_ttb <= 100.0):
        raise ValueError("x_relative_ltr and y_relative_ttb must be in the 0..100 range")

    client_bbox = get_client_bbox_in_screen(hwnd)
    if aspect_ratio is not None:
        client_bbox = crop_to_aspect_ratio(client_bbox, aspect_ratio)

    left, top, right, bottom = client_bbox
    width = right - left
    height = bottom - top

    x_pixel_offset = int(round((x_relative_ltr / 100.0) * width))
    y_pixel_offset = int(round((y_relative_ttb / 100.0) * height))
    screen_x = left + x_pixel_offset
    screen_y = top + y_pixel_offset
    return (screen_x, screen_y), (x_pixel_offset, y_pixel_offset)


def grab_pixel_rgb(screen_x: int, screen_y: int) -> Tuple[int, int, int]:
    box = (screen_x, screen_y, screen_x + 1, screen_y + 1)
    img = ImageGrab.grab(bbox=box, include_layered_windows=True, all_screens=True)
    # noinspection PyTypeChecker
    return img.getpixel((0, 0))


def get_window_image(hwnd: int, aspect_ratio: Optional[float] = None) -> Image.Image:
    client_bbox = get_client_bbox_in_screen(hwnd)

    bbox = client_bbox
    if aspect_ratio is not None:
        bbox = crop_to_aspect_ratio(client_bbox, aspect_ratio)

    img = ImageGrab.grab(bbox=bbox, include_layered_windows=True, all_screens=True)
    return img


def draw_rectangle(
    image: Image.Image,
    location: Point,
    size: int = 10,
    width: int = 2,
    outline: str = "red",
) -> Image.Image:
    x, y = location
    left = x - size
    top = y - size
    right = x + size
    bottom = y + size
    draw = ImageDraw.Draw(image)
    draw.rectangle((left, top, right, bottom), outline=outline, width=width)
    return image


def name_color(r: int, g: int, b: int) -> str:
    max_c = max(r, g, b)
    min_c = min(r, g, b)
    if max_c - min_c < 15:
        if max_c < 40:
            return "black"
        if max_c > 215:
            return "white"
        return "gray"

    if r > 200 and g < 80 and b < 80:
        return "red"
    if g > 200 and r < 80 and b < 80:
        return "green"
    if b > 200 and r < 80 and g < 80:
        return "blue"
    if r > 200 and g > 200 and b < 80:
        return "yellow"
    if r > 200 and b > 200 and g < 80:
        return "magenta"
    if g > 200 and b > 200 and r < 80:
        return "cyan"

    if r > g and r > b:
        return "orange" if g > 100 else "red-ish"
    if g > r and g > b:
        return "lime" if r > 100 else "green-ish"
    if b > r and b > g:
        return "purple" if r > 100 else "blue-ish"

    return "unknown"
