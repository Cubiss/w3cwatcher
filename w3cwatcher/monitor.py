from __future__ import annotations
import time
from dataclasses import dataclass

import win32gui
import win32con

from . import utils
from datetime import datetime
from logging import Logger
from .config import MonitorConfig
from .notifier import Notifier
from .utils import Point
from .utils.platform import set_dpi_awareness


class Monitor:
    def __init__(self, logger: Logger, config: MonitorConfig, notifier: Notifier):
        self.config = config
        self.logger = logger
        self._stop = False
        self.notifier = notifier

    def stop(self):
        self._stop = True


    def show_debug_image(self):
        self.logger.info("Gathering debug info:")
        set_dpi_awareness()
        self._stop = False
        window_info = self._wait_for_window(self.config.poll_s)
        if window_info is None:
            self.logger.error('Failed to get W3C window info.')
            return

        in_game = window_info.hwnd_warcraft3
        rgb = utils.grab_pixel_rgb(*window_info.watched_screen_pos)
        color_name = utils.name_color(*rgb)
        in_queue = color_name == self.config.in_queue_color
        self.logger.debug(f"RGB={rgb} ({color_name}) -> in_queue={in_queue}, in_game={in_game}")

        img = utils.get_window_image(window_info.hwnd_w3c, self.config.enforced_window_aspect_ratio)
        img = utils.draw_rectangle(img, window_info.watched_window_pos, size=60, outline='yellow', width=8)

        self.logger.info(f"""
            size = {img.size}
            abs_pos = {window_info.watched_window_pos}
            rel_pos = {(self.config.x_offset_pct, self.config.y_offset_pct)}
            RGB={rgb}
            color_name={color_name}
            in_queue={in_queue}
            in_game={in_game}
        """)

        img.show()
        


    def run(self):
        set_dpi_awareness()
        self._stop = False

        self.logger.info(f"Monitoring started")

        queue_start = None
        was_in_queue = False

        poll_rate_s = self.config.poll_s

        while not self._stop:
            try:
                window_info = self._wait_for_window(poll_rate_s)
                if window_info is None:
                    time.sleep(poll_rate_s)
                    continue

                in_game = window_info.hwnd_warcraft3
                rgb = utils.grab_pixel_rgb(*window_info.watched_screen_pos)
                color_name = utils.name_color(*rgb)
                in_queue = color_name == self.config.in_queue_color

                self.logger.debug(f"RGB={rgb} ({color_name}) -> in_queue={in_queue}, in_game={in_game}")

                if not was_in_queue and in_queue:
                    queue_start = datetime.now()
                    self.logger.info('Detected queue.')

                if was_in_queue and in_game:
                    self.logger.info("Notifying Match Start")
                    self.notifier.notify_match_started(
                        queue_duration=datetime.now() - queue_start
                    )

                was_in_queue = in_queue and not in_game
                poll_rate_s = self.config.reduced_poll_s if in_game else self.config.poll_s
                time.sleep(poll_rate_s)

            except KeyboardInterrupt:
                self.logger.info("\n[+] Stopped by user.")
                break
            except Exception as e:
                self.logger.error(f"[!] Error: {e}")
                time.sleep(poll_rate_s)

    @dataclass
    class _WindowInfo:
        hwnd_w3c: int
        hwnd_warcraft3: int | None
        watched_screen_pos: Point
        watched_window_pos: Point

    def _wait_for_window(self, poll_rate_s: float) -> (_WindowInfo | None):
        while not self._stop:
            hwnd_w3c = utils.find_window_by_title(self.config.w3champions_window_title)
            hwnd_warcraft3 = utils.find_window_by_title(self.config.warcraft3_window_title)

            if not hwnd_w3c:
                self.logger.debug(
                    f"[!] Could not find window with title containing '{self.config.w3champions_window_title}'.")
                time.sleep(poll_rate_s)
                continue

            screen_pos, window_pos = utils.hwnd_relative_to_screen_xy(hwnd_w3c, self.config.x_offset_pct,
                                                                  self.config.y_offset_pct,
                                                                  self.config.enforced_window_aspect_ratio)

            if screen_pos == (0, 0):
                self.logger.debug(f'{self.config.w3champions_window_title} window is not visible.')
                time.sleep(poll_rate_s)
                continue

            if not utils.point_belongs_to_window(hwnd_w3c, screen_pos):
                try:
                    under = win32gui.WindowFromPoint(screen_pos)
                    title = win32gui.GetWindowText(win32gui.GetAncestor(under, win32con.GA_ROOT))
                    self.logger.debug(
                        f"[skip] {screen_pos} belongs to '{title}', not {self.config.w3champions_window_title}")
                except Exception as ex:
                    self.logger.debug(f"[skip] {screen_pos} could not check pixel ownership: {ex}")

                time.sleep(self.config.poll_s)
                continue

            return Monitor._WindowInfo(
                hwnd_w3c=hwnd_w3c,
                hwnd_warcraft3=hwnd_warcraft3,
                watched_screen_pos=screen_pos,
                watched_window_pos=window_pos
            )

        return None
