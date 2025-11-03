from __future__ import annotations
import argparse
import ctypes
from .config import Settings, load_user_config, open_user_config, config_file_path
from .watcher import PixelWatcher
from .tray import TrayApp


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
    p.add_argument('--tray', action='store_true', help='Run as a system tray app')
    p.add_argument('--check', action='store_true', help='Check currently captured rectangle')
    p.add_argument('--config', action='store_true', help='Opens config file')
    p.add_argument('--shortcut', action='store_true', help='Creates a desktop shortcut')

    return p


def load_settings(args: argparse.Namespace) -> Settings:
    s = load_user_config(create_if_missing=True)
    if args.title is not None:
        s.window_title_keyword = args.title
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
    return s

def detach_console():
    # Only detach if we currently have a console
    try:
        ctypes.windll.kernel32.FreeConsole()
    except Exception as ex:
        print('Detach failed: ', ex)
        pass


def main():
    parser = build_parser()
    args = parser.parse_args()
    s = load_settings(args)

    if args.config:
        print(config_file_path())
        open_user_config()
    elif args.shortcut:
        print(config_file_path())
        create_tray_shortcut()

    elif args.check:
        PixelWatcher(s, check_only=True).run()
    elif args.tray:
        detach_console()
        app = TrayApp(s)
        app.run()
    else:
        PixelWatcher(s).run()