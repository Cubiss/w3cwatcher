from __future__ import annotations
import argparse
from .config import Settings, load_user_config, open_user_config, config_file_path
from .log import init_logging
from .watcher import PixelWatcher
from .tray import run_tray, create_tray_shortcut


def parse_rgb(text: str) -> tuple[int, int, int]:
    try:
        parts = [int(p.strip()) for p in text.split(',')]
        if len(parts) != 3 or any(p < 0 or p > 255 for p in parts):
            raise ValueError
        return parts[0], parts[1], parts[2]
    except Exception:
        raise argparse.ArgumentTypeError("Expected R,G,B with 0-255 each")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Watch a pixel in a window and notify via Discord")
    p.add_argument('--title', default=None, help='Substring to match target window title')
    p.add_argument('--x', type=int, default=None, help='Client X offset (0.5 = middle, 1.0 = left)')
    p.add_argument('--y', type=int, default=None, help='Client Y offset (0.5 = middle), 1.0 = bottom')
    p.add_argument('--poll', type=int, default=None, help='Polling rate (s)')
    p.add_argument('--debounce', type=int, default=None, help='Minimum seconds between webhooks')
    p.add_argument('--message', default=None, help='Discord message content')
    p.add_argument('--webhook', default=None, help='Discord webhook URL')
    p.add_argument('--check', action='store_true', help='Check currently captured rectangle')
    p.add_argument('--config', action='store_true', help='Open config file')
    p.add_argument('--tray', action='store_true', help='Run as a system tray app')
    p.add_argument('--shortcut', action='store_true', help='Create a desktop shortcut for Tray')
    p.add_argument('--allow-multiple-instances', action='store_true', help='[Tray]Disable single instance check')

    return p


def load_settings(args: argparse.Namespace) -> Settings:
    s = load_user_config(create_if_missing=True)
    if args.title is not None:
        s.w3champions_window_title = args.title
    if args.x is not None:
        s.x_offset_pct = args.x
    if args.y is not None:
        s.y_offset_pct = args.y
    if args.poll is not None:
        s.poll_s = args.poll
    if args.debounce is not None:
        s.debounce_seconds = args.debounce
    if args.message is not None:
        s.discord_message = args.message
    if args.webhook is not None:
        s.discord_webhook_url = args.webhook
    if args.allow_multiple_instances:
        s.allow_multiple_instances = True
    return s


def main():
    parser = build_parser()
    args = parser.parse_args()
    s = load_settings(args)
    init_logging(s)

    print(s)

    if args.config:
        print(config_file_path())
        open_user_config()
    elif args.shortcut:
        create_tray_shortcut()
    elif args.check:
        PixelWatcher(s, check_only=True).run()
    elif args.tray:
        run_tray(s)
    else:
        PixelWatcher(s).run()