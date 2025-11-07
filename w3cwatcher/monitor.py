from __future__ import annotations
import time
from datetime import datetime
from logging import Logger
from .config import Config
from .window_utils import (set_dpi_awareness, find_window_by_keyword, point_belongs_to_window,
                           get_window_image, draw_rectangle)
import win32gui
import win32con
from .utils import get_pixel_screen_xy, grab_pixel_rgb
from .notifier import Notifier
from .color_names import name_color

class Monitor:
    def __init__(self, logger: Logger, config: Config, notifier: Notifier, check_only: bool = False):
        self.s = config
        self.l = logger
        self._stop = False
        self._last_sent_ts: float = 0.0
        self.check_only = check_only
        self.notifier = notifier

    def stop(self):
        self._stop = True

    def run(self):
        set_dpi_awareness()
        self._stop = False

        self.l.info(f"Monitoring started")

        queue_start = None
        was_in_queue = False

        while not self._stop:
            try:
                hwnd_w3c = find_window_by_keyword(self.s.w3champions_window_title)
                hwnd_warcraft3 = find_window_by_keyword(self.s.warcraft3_window_title)
                in_game = hwnd_warcraft3 is not None
                sleep_s = self.s.reduced_poll_s if in_game else self.s.poll_s

                if not hwnd_w3c:
                    self.l.debug(f"[!] Could not find window with title containing '{self.s.w3champions_window_title}'.")
                    time.sleep(sleep_s)
                    continue

                (sx, sy), (x_off, y_off) = get_pixel_screen_xy(hwnd_w3c, self.s.x_offset_pct, self.s.y_offset_pct,
                                             self.s.inner_rectangle_aspect_ratio)

                if (sx, sy) == (0, 0):
                    self.l.debug(f'{self.s.w3champions_window_title} window is not visible.')
                    time.sleep(sleep_s)
                    continue

                if not point_belongs_to_window(hwnd_w3c, sx, sy):
                    try:
                        under = win32gui.WindowFromPoint((sx, sy))
                        title = win32gui.GetWindowText(win32gui.GetAncestor(under, win32con.GA_ROOT))
                        self.l.debug(f"[skip] ({sx},{sy}) belongs to '{title}', not {self.s.w3champions_window_title}")
                    except Exception as ex:
                        self.l.debug(f"[skip] ({sx},{sy}) could not check pixel ownership:")
                        print(ex)

                    time.sleep(self.s.poll_s)
                    continue


                rgb = grab_pixel_rgb(sx, sy)
                color_name = name_color(*rgb)
                in_queue = color_name == self.s.in_queue_color

                self.l.debug(f"RGB={rgb} ({color_name}) -> in_queue={in_queue}, in_game={in_game}")

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

                if not was_in_queue and in_queue:
                    queue_start = datetime.now()
                    self.l.info('Detected queue.')

                now = time.time()

                if was_in_queue and in_game:
                    self.l.info('Detected game start.')

                    if now - self._last_sent_ts < self.s.debounce_seconds:
                        self.l.info(f'Not pinging, pinged {now - self._last_sent_ts}')
                    else:
                        time_in_queue = datetime.now() - queue_start
                        time_in_queue_str = (datetime.min + time_in_queue).strftime("%H:%M:%S")
                        self.l.info(f"Match started after: {time_in_queue_str}")

                        embed = {
                            "title": "W3CWatcher",
                            "description": f"Pixel at offsets ({self.s.x_offset_pct}, {self.s.y_offset_pct}) matched target.",
                            "fields": [
                                {"name": "Time in Queue", "value": str(time_in_queue_str), "inline": True},
                            ],
                        }
                        self.notifier.notify(self.s.discord_webhook_url, self.s.discord_message, embed_fields=embed)
                        self._last_sent_ts = now


                was_in_queue = in_queue and not in_game
                time.sleep(sleep_s)

            except KeyboardInterrupt:
                self.l.info("\n[+] Stopped by user.")
                break
            except Exception as e:
                self.l.error(f"[!] Error: {e}")
                time.sleep(self.s.poll_s)
