from __future__ import annotations
import time
from datetime import datetime
from typing import Optional
from .config import Settings
from .window_utils import (set_dpi_awareness, find_window_by_keyword, point_belongs_to_window,
                           get_window_image, draw_rectangle)
import win32gui
import win32con
from .utils import get_pixel_screen_xy, grab_pixel_rgb
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

        print(
            f"[i] Monitoring '{self.s.w3champions_window_title}' at offsets "
            f"({self.s.x_offset_pct}, {self.s.y_offset_pct}) for In Queue Color = {self.s.in_queue_color} ..."
        )



        while not self._stop:
            try:
                hwnd_w3c = find_window_by_keyword(self.s.w3champions_window_title)
                if not hwnd_w3c:
                    print(f"[!] Could not find window with title containing '{self.s.w3champions_window_title}'.")
                    time.sleep(self.s.poll_s)
                    continue

                (sx, sy), (x_off, y_off) = get_pixel_screen_xy(hwnd_w3c, self.s.x_offset_pct, self.s.y_offset_pct,
                                             self.s.inner_rectangle_aspect_ratio)

                if (sx, sy) == (0, 0):
                    print(f'{self.s.w3champions_window_title} window is not visible.')
                    time.sleep(self.s.poll_s)
                    continue


                if not point_belongs_to_window(hwnd_w3c, sx, sy):
                    try:
                        under = win32gui.WindowFromPoint((sx, sy))
                        title = win32gui.GetWindowText(win32gui.GetAncestor(under, win32con.GA_ROOT))
                        print(f"[skip] ({sx},{sy}) belongs to '{title}', not {self.s.w3champions_window_title}")
                    except Exception as ex:
                        print(f"[skip] ({sx},{sy}) could not check pixel ownership:")
                        print(ex)

                    time.sleep(self.s.poll_s)
                    continue


                rgb = grab_pixel_rgb(sx, sy)
                color_name = name_color(*rgb)
                in_queue = color_name == self.s.in_queue_color

                if not self._was_in_queue:
                    queue_start = datetime.now()

                print(f"RGB={rgb} ({color_name}) -> in_queue={in_queue}")

                if self.check_only:
                    img = get_window_image(hwnd_w3c, self.s.inner_rectangle_aspect_ratio)
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
                    time_in_queue = datetime.now() - queue_start
                    time_in_queue_str = (datetime.min + time_in_queue).strftime("%H:%M:%S")
                    print("Match started after:", time_in_queue_str)

                    embed = {
                        "title": "W3CWatcher",
                        "description": f"Pixel at offsets ({self.s.x_offset_pct}, {self.s.y_offset_pct}) matched target.",
                        "fields": [
                            {"name": "Time in Queue", "value": str(time_in_queue_str), "inline": True},
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
