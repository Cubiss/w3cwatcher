from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Tuple

from .utils.config_base import ConfigBase, field, get_allowed_values_validator, get_config_file

APP_NAME = "W3CWatcher"


class MonitorConfig(ConfigBase):
    w3champions_window_title: str = field(
        default="W3Champions",
        arg="--title",
        help_text="Substring to match target window title.",
    )

    warcraft3_window_title: str = field(
        default="Warcraft III",
        help_text="Default Warcraft III window title (used for fallback).",
    )

    x_offset_pct: float = field(
        default=0.755,
        arg="--x",
        help_text="Client X offset (0.5 = middle, 1.0 = right).",
    )

    y_offset_pct: float = field(
        default=0.955,
        arg="--y",
        help_text="Client Y offset (0.5 = middle, 1.0 = bottom).",
    )

    enforced_window_aspect_ratio: float = field(
        default=1846 / 1040,
        help_text="Aspect ratio for the inner rectangle of the window capture.",
    )

    in_queue_color: str = field(default="red", help_text="Color used to detect when in queue.")

    ready_color: str = field(default="green", help_text="Color used to detect when the match is ready.")

    poll_s: int = field(default=1, arg="--poll", help_text="Polling rate in seconds.")

    reduced_poll_s: int = field(default=5, help_text="Reduced polling rate when idle (seconds).")


class DiscordConfig(ConfigBase):
    @staticmethod
    def _validate_discord_webhook(url):
        if url is None:
            return ["You must set discord webhook url first."]
        elif not re.match(r"^https://(discord\.com)/api/webhooks/\d+/[\w-]+$", url):
            return ["Invalid webhook URL format."]
        else:
            return []

    enabled: bool = field(
        default=False,
        help_text="Whether to enable Discord notifications.",
    )

    match_started_message: str = field(
        default="Match found!",
        help_text="Discord message content to send on match found.",
    )

    webhook_url: str = field(
        default=None,
        help_text="Discord webhook URL for notifications.",
        validators=[_validate_discord_webhook],
    )

    debounce: int = field(
        default=60,
        arg="--debounce",
        help_text="Minimum seconds between Discord webhook notifications.",
    )



class TelegramConfig(ConfigBase):
    @staticmethod
    def _validate_telegram_token(value):
        if not value:
            return "Telegram bot token cannot be empty."
        if ":" not in value:
            return "Invalid Telegram bot token format."
        return None

    @staticmethod
    def _validate_chat_id(value):
        if not value:
            return "Telegram chat_id cannot be empty."
        try:
            int(value)
        except:
            return "Telegram chat_id must be an integer or numeric string."
        return None

    enabled: bool = field(
        default=False,
        help_text="Whether to enable Telegram notifications.",
    )

    match_started_message: str = field(
        default="Match found!",
        help_text="Telegram message content to send on match found."
    )

    bot_token: str = field(
        default=None,
        help_text="Telegram Bot API token from BotFather.",
        validators=[_validate_telegram_token],
    )

    chat_id: str = field(
        default=None,
        help_text="Telegram chat ID to send messages to.",
        validators=[_validate_chat_id],
    )

    debounce: int = field(
        default=60,
        help_text="Minimum seconds between Telegram notifications.",
    )


class LoggingConfig(ConfigBase):
    log_level: str = field(
        default="INFO",
        help_text="Logging level (DEBUG, INFO, WARNING, ERROR).",
        validators=get_allowed_values_validator(
            "CRITICAL", "FATAL", "ERROR", "WARN", "WARNING", "INFO", "DEBUG"
        ),
    )

    log_keep: int = field(default=10, help_text="Number of old log files to keep. -1 for no cleanup")

    log_dir: Path = field(default=None, help_text="Logging directory.")


class TrayConfig(ConfigBase):
    autostart: bool = field(default=False, help_text="Whether the tray app should autostart with Windows.")
    allow_multiple_instances: bool = field(
        default=False, help_text="[Tray] Disable single instance check."
    )


class NotificationsConfig(ConfigBase):
    discord: DiscordConfig = field(default_factory=DiscordConfig)
    telegram: TelegramConfig = field(default_factory=TelegramConfig)


class Config(ConfigBase):
    monitor: MonitorConfig = field(default_factory=MonitorConfig)
    notifications: NotificationsConfig = field(default_factory=NotificationsConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    tray: TrayConfig = field(default_factory=TrayConfig)


def load_config() -> Tuple[argparse.Namespace, Config]:
    # Loads config based on priority:
    # 1. shell arguments
    # 2. file provided by --config shell argument
    # 3. local file ./w3cwatcher.config.toml
    # 4. user file %localappdata%/W3CWatcher/config.toml

    config = Config()
    default_config_file = get_config_file(
        user_config=True, filename="config.default.toml", app_name=APP_NAME
    )

    # keep defaults file up to date
    config.save(default_config_file, include_defaults=True, comment='help_text')

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, help="Specify config file (defaults to user file).")
    parser.add_argument("--tray", action="store_true", help="Run as a system tray app")
    parser.add_argument("--check", action="store_true", help="Check currently captured rectangle")
    Config.fill_arg_parse(parser)
    args = parser.parse_args()

    arg_config_file = getattr(args, "config", None)
    config_files = [
        get_config_file(user_config=True, app_name=APP_NAME),
        get_config_file(user_config=False, app_name=APP_NAME),
    ]

    if arg_config_file:
        config_files.append(arg_config_file)

    for file in config_files:
        if file.exists():
            print("Loading ", file)
            args_cfg = Config.from_file(file)
            config.update_from(args_cfg)

    args_cfg = Config.from_args(args)
    config.update_from(args_cfg)

    return args, config
