from __future__ import annotations
import os
from dataclasses import dataclass

DEFAULT_WINDOW_TITLE_KEYWORD = "W3Champions"
DEFAULT_X_OFFSET = 1960
DEFAULT_Y_OFFSET = 1358
DEFAULT_POLL_S = 5
DEFAULT_DEBOUNCE_SECONDS = 30
DEFAULT_DISCORD_MESSAGE = "Match found!"
DEFAULT_IN_QUEUE_COLOR = "red"


def get_webhook_url() -> str:
    webhook_path = os.path.expanduser('./webhook')
    webhook = ''
    if os.path.exists(webhook_path):
        try:
            with open(webhook_path, 'r', encoding='utf-8') as f:
                webhook = f.read()
        except Exception:
            webhook = ''
    return os.getenv("DISCORD_WEBHOOK_URL", webhook).strip()


@dataclass
class Settings:
    window_title_keyword: str = DEFAULT_WINDOW_TITLE_KEYWORD
    x_offset: int = DEFAULT_X_OFFSET
    y_offset: int = DEFAULT_Y_OFFSET
    in_queue_color: str = DEFAULT_IN_QUEUE_COLOR
    poll_s: int = DEFAULT_POLL_S
    debounce_seconds: int = DEFAULT_DEBOUNCE_SECONDS
    discord_message: str = DEFAULT_DISCORD_MESSAGE
    webhook_url: str = get_webhook_url()

