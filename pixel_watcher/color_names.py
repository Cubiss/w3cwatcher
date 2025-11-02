from __future__ import annotations


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
