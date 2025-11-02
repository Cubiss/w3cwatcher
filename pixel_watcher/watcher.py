from __future__ import annotations
import time
from typing import Optional
from .config import Settings
from .window_utils import set_dpi_awareness, find_window_by_keyword, bring_to_foreground, point_belongs_to_window
import win32gui
import win32con
from .utils import get_pixel_screen_xy, grab_pixel_rgb, within_tolerance
from .notifier import send_discord_webhook
from .color_names import name_color


class PixelWatcher:
    def __init__(self, settings: Settings):
        self.s = settings
        self._stop = False
        self._was_in_queue: Optional[bool] = False
        self._last_sent_ts: float = 0.0

    def stop(self):
        self._stop = True

    def run(self):
        set_dpi_awareness()

        if not self.s.webhook_url:
            print("[!] No webhook URL. Set DISCORD_WEBHOOK_URL or put it in ~/webhook.")
            return

        hwnd = find_window_by_keyword(self.s.window_title_keyword)
        if not hwnd:
            print(f"[!] Could not find window with title containing '{self.s.window_title_keyword}'.")
            return

        print(
            f"[i] Monitoring '{self.s.window_title_keyword}' at offsets "
            f"({self.s.x_offset}, {self.s.y_offset}) for Color≈{self.s.in_queue_color} ..."
        )

        while not self._stop:
            try:
                sx, sy = get_pixel_screen_xy(hwnd, self.s.x_offset, self.s.y_offset)
                # verify pixel belongs to window
                if not point_belongs_to_window(hwnd, sx, sy):
                    try:
                        under = win32gui.WindowFromPoint((sx, sy))
                        title = win32gui.GetWindowText(win32gui.GetAncestor(under, win32con.GA_ROOT))
                        print(f"[skip] ({sx},{sy}) belongs to '{title}', not target window")
                    except Exception:
                        print(f"[skip] ({sx},{sy}) not on target window")
                    time.sleep(self.s.poll_s)
                    continue

                rgb = grab_pixel_rgb(sx, sy)

                color_name = name_color(*rgb)

                in_queue = color_name == self.s.in_queue_color

                print(f"RGB={rgb} ({color_name}) -> in_queue={in_queue}")

                now = time.time()
                should_notify = False

                if self._was_in_queue and not in_queue:
                    should_notify = True

                if should_notify and now - self._last_sent_ts >= self.s.debounce_seconds:
                    embed = {
                        "title": "Pixel Watch Trigger",
                        "description": f"Pixel at offsets ({self.s.x_offset}, {self.s.y_offset}) matched target.",
                        "fields": [
                            {"name": "Observed RGB", "value": str(rgb), "inline": True},
                            {"name": "Approx Color", "value": color_name, "inline": True},
                        ],
                    }
                    send_discord_webhook(self.s.webhook_url, self.s.discord_message, embed_fields=embed)
                    self._last_sent_ts = now

                self._was_in_queue = in_queue
                time.sleep(self.s.poll_s)

            except KeyboardInterrupt:
                print("\n[+] Stopped by user.")
                break
            except Exception as e:
                print(f"[!] Error: {e}")
                time.sleep(0.5)
