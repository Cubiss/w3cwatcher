from __future__ import annotations
import sys

from w3cwatcher.unified_config import UnifiedConfig, field

APP_NAME = "W3CWatcher"

class Config(UnifiedConfig):
    def __init__(self):
        super().__init__(app_name=APP_NAME, user_config=not getattr(sys, 'frozen', False))

    w3champions_window_title: str = field(
        default="W3Champions",
        arg="--title",
        help_text="Substring to match target window title."
    )

    warcraft3_window_title: str = field(
        default="Warcraft III",
        help_text="Default Warcraft III window title (used for fallback)."
    )

    x_offset_pct: float = field(
        default=0.755,
        arg="--x",
        help_text="Client X offset (0.5 = middle, 1.0 = right)."
    )

    y_offset_pct: float = field(
        default=0.955,
        arg="--y",
        help_text="Client Y offset (0.5 = middle, 1.0 = bottom)."
    )

    in_queue_color: str = field(
        default="red",
        help_text="Color used to detect when in queue."
    )

    ready_color: str = field(
        default="green",
        help_text="Color used to detect when the match is ready."
    )

    poll_s: int = field(
        default=1,
        arg="--poll",
        help_text="Polling rate in seconds."
    )

    reduced_poll_s: int = field(
        default=5,
        help_text="Reduced polling rate when idle (seconds)."
    )

    debounce_seconds: int = field(
        default=60,
        arg="--debounce",
        help_text="Minimum seconds between Discord webhook notifications."
    )

    discord_message: str = field(
        default="Match found!",
        arg="--message",
        help_text="Discord message content to send on match found."
    )

    inner_rectangle_aspect_ratio: float = field(
        default=1846 / 1040,
        help_text="Aspect ratio for the inner rectangle of the window capture."
    )

    allow_multiple_instances: bool = field(
        default=False,
        arg="--allow-multiple-instances",
        help_text="[Tray] Disable single instance check."
    )

    log_level: str = field(
        default="INFO",
        help_text="Logging level (DEBUG, INFO, WARNING, ERROR)."
    )

    log_keep: int = field(
        default=10,
        help_text="Number of old log files to keep."
    )

    autostart: bool = field(
        default=False,
        help_text="Whether the tray app should autostart with Windows."
    )

    # cli-only args
    discord_webhook_url: str = field(
        default="",
        serialize=False,
        arg="--webhook",
        help_text="Discord webhook URL for notifications."
    )
