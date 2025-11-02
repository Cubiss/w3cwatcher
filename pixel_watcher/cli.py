from __future__ import annotations
import argparse
from .config import Settings, get_webhook_url
from .watcher import PixelWatcher
from .tray import TrayApp
from .pixel_utils import calibrate_offsets


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
    p.add_argument('--x', type=int, default=None, help='Client X offset (pixels)')
    p.add_argument('--y', type=int, default=None, help='Client Y offset (pixels)')
    p.add_argument('--target', type=parse_rgb, default=None, help='Target RGB as R,G,B')
    p.add_argument('--tol', type=int, default=None, help='Tolerance per channel (0..255)')
    p.add_argument('--poll', type=int, default=None, help='Polling rate (Hz)')
    p.add_argument('--debounce', type=int, default=None, help='Minimum seconds between webhooks')
    p.add_argument('--change-only', action='store_true', help='Trigger only on false->true changes')
    p.add_argument('--message', default=None, help='Discord message content')
    p.add_argument('--webhook', default=None, help='Discord webhook URL (overrides env/file)')
    p.add_argument('--tray', action='store_true', help='Run as a Windows system tray app')
    p.add_argument('--calibrate', action='store_true', help='Calibrate offsets and exit')

    return p

def settings_from_args(args: argparse.Namespace) -> Settings:
    s = Settings()
    if args.title is not None:
        s.window_title_keyword = args.title
    if args.x is not None:
        s.x_offset = args.x
    if args.y is not None:
        s.y_offset = args.y
    if args.target is not None:
        s.target_rgb = args.target
    if args.tol is not None:
        s.tolerance = args.tol
    if args.poll is not None:
        s.poll_s = args.poll
    if args.debounce is not None:
        s.debounce_seconds = args.debounce
    if args.change_only:
        s.trigger_on_change_only = True
    if args.message is not None:
        s.discord_message = args.message
    if args.webhook is not None:
        s.webhook_url = args.webhook
    else:
        # refresh in case env/file changed since import
        s.webhook_url = get_webhook_url()
    return s


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.calibrate:
        # Find window and run one-off calibration
        title = args.title or Settings().window_title_keyword
        hwnd = find_window_by_keyword(title)
        if not hwnd:
            print(f"[!] Could not find window with title containing '{title}'.")
            return
        calibrate_offsets(hwnd)
        return

    s = settings_from_args(args)

    if args.tray:
        app = TrayApp(s)
        app.run()
    else:
        PixelWatcher(s).run()