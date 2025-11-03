from __future__ import annotations
import time
from typing import Optional
from .config import Settings
from .window_utils import set_dpi_awareness, find_window_by_keyword, bring_to_foreground, point_belongs_to_window, \
    get_window_image, draw_rectangle
import win32gui
import win32con
from .utils import get_pixel_screen_xy, grab_pixel_rgb, within_tolerance
from .notifier import send_discord_webhook
from .color_names import name_color
from .config import config_file_path

class PixelWatcher:
    def __init__(self, settings: Settings, check_only: bool = False):
        self.s = settings
        self._stop = False
        self._was_in_queue: Optional[bool] = False
        self._last_sent_ts: float = 0.0
        self.check_only = check_only

    def stop(self):
        self._stop = True

    def run(self):
        set_dpi_awareness()

        if not self.s.discord_webhook_url:
            print(f"[!] No webhook URL. Put it in {config_file_path()}")
            return

        hwnd = find_window_by_keyword(self.s.window_title_keyword)
        if not hwnd:
            print(f"[!] Could not find window with title containing '{self.s.window_title_keyword}'.")
            return

        print(
            f"[i] Monitoring '{self.s.window_title_keyword}' at offsets "
            f"({self.s.x_offset_pct}, {self.s.y_offset_pct}) for In Queue Color = {self.s.in_queue_color} ..."
        )

        while not self._stop:
            try:
                (sx, sy), (x_off, y_off) = get_pixel_screen_xy(hwnd, self.s.x_offset_pct, self.s.y_offset_pct,
                                             self.s.inner_rectangle_aspect_ratio)

                if (sx, sy) == (0, 0):
                    print(f'{self.s.window_title_keyword} window is not visible.')
                    time.sleep(self.s.poll_s)
                    continue

                # verify pixel belongs to window
                if not point_belongs_to_window(hwnd, sx, sy):
                    try:
                        under = win32gui.WindowFromPoint((sx, sy))
                        title = win32gui.GetWindowText(win32gui.GetAncestor(under, win32con.GA_ROOT))
                        print(f"[skip] ({sx},{sy}) belongs to '{title}', not {self.s.window_title_keyword}")
                    except Exception as ex:
                        print(f"[skip] ({sx},{sy}) could not check pixel ownership:")
                        print(ex)

                    time.sleep(self.s.poll_s)
                    continue

                rgb = grab_pixel_rgb(sx, sy)

                color_name = name_color(*rgb)

                in_queue = color_name == self.s.in_queue_color

                print(f"RGB={rgb} ({color_name}) -> in_queue={in_queue}")

                if self.check_only:
                    img = get_window_image(hwnd, self.s.inner_rectangle_aspect_ratio)
                    img = draw_rectangle(img, (x_off, y_off), size=10, outline='red', width=2)
                    img = draw_rectangle(img, (x_off, y_off), size=30, outline='blue', width=4)
                    img = draw_rectangle(img, (x_off, y_off), size=60, outline='yellow', width=8)
                    print(f'size = {img.size}')
                    print(f'pos = {(x_off, y_off)}')
                    img.show()
                    self.check_only = False
                    return

                now = time.time()
                should_notify = False

                if self._was_in_queue and not in_queue:
                    should_notify = True

                if should_notify and now - self._last_sent_ts >= self.s.debounce_seconds:
                    print('Sending notification.')
                    embed = {
                        "title": "Pixel Watch Trigger",
                        "description": f"Pixel at offsets ({self.s.x_offset_pct}, {self.s.y_offset_pct}) matched target.",
                        "fields": [
                            {"name": "Observed RGB", "value": str(rgb), "inline": True},
                            {"name": "Approx Color", "value": color_name, "inline": True},
                        ],
                    }
                    send_discord_webhook(self.s.discord_webhook_url, self.s.discord_message, embed_fields=embed)
                    self._last_sent_ts = now

                self._was_in_queue = in_queue
                time.sleep(self.s.poll_s)

            except KeyboardInterrupt:
                print("\n[+] Stopped by user.")
                break
            except Exception as e:
                print(f"[!] Error: {e}")
                time.sleep(self.s.poll_s)
