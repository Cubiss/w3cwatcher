from __future__ import annotations
import time
from dataclasses import dataclass

import win32gui
import win32con

from . import utils
from .logging import Logger
from .config import MonitorConfig
from .state_manager import StateManager, STATE_WAITING, STATE_IN_QUEUE, STATE_IN_GAME, STATE_DISABLED
from .utils import Point, show_error
from .utils.platform import set_dpi_awareness


class Monitor:
    def __init__(self, logger: Logger, config: MonitorConfig, state_manager: StateManager):
        self.config = config
        self.logger = logger
        self._stop = False
        self.state_manager = state_manager

    def stop(self):
        self._stop = True

    def show_debug_image(self):
        self.logger.info("Gathering debug info:")
        set_dpi_awareness()
        self._stop = False
        window_info = self._wait_for_window(self.config.poll_s)
        if window_info is None:
            self.logger.error("Failed to get W3C window info.")
            return

        in_game = window_info.hwnd_warcraft3
        rgb = utils.grab_pixel_rgb(*window_info.watched_screen_pos)
        color_name = utils.name_color(*rgb)
        in_queue = color_name == self.config.in_queue_color
        self.logger.debug(f"RGB={rgb} ({color_name}) -> in_queue={in_queue}, in_game={in_game}")

        img = utils.get_window_image(window_info.hwnd_w3c, self.config.enforced_window_aspect_ratio)
        img = utils.draw_rectangle(img, window_info.watched_window_pos, size=30, outline="yellow", width=5)

        self.logger.info(
            f"""
            size = {img.size}
            Point: 
                screen_pos = {window_info.watched_screen_pos}
                window_pos = {window_info.watched_window_pos}
                %_pos = {(self.config.x_offset_pct, self.config.y_offset_pct)}
            RGB={rgb}
            color_name={color_name}
            in_queue={in_queue}
            in_game={in_game}
        """
        )

        img.show()

    def run(self):
        try:
            self.config.validate_all()
        except Exception as ex:
            self.logger.error(ex)
            show_error(str(ex))
            return

        set_dpi_awareness()
        self._stop = False

        self.logger.info(f"Monitoring started")
        self.state_manager.update_state(STATE_WAITING)
        was_in_queue = False

        poll_rate_s = self.config.poll_s

        while not self._stop:
            try:
                window_info = self._wait_for_window(poll_rate_s)
                if window_info is None:
                    time.sleep(poll_rate_s)
                    continue

                in_game = window_info.hwnd_warcraft3 is not None
                rgb = utils.grab_pixel_rgb(*window_info.watched_screen_pos)
                color_name = utils.name_color(*rgb)
                in_queue = color_name == self.config.in_queue_color

                self.logger.debug(f"RGB={rgb} ({color_name}) -> in_queue={in_queue}, in_game={in_game}")

                if in_queue and not was_in_queue:
                    self.state_manager.update_state(STATE_IN_QUEUE)

                if in_game and was_in_queue:
                    self.state_manager.update_state(STATE_IN_GAME)

                if was_in_queue and not in_queue and not in_game:
                    self.state_manager.update_state(STATE_WAITING)

                was_in_queue = in_queue and not in_game
                poll_rate_s = self.config.reduced_poll_s if in_game else self.config.poll_s
                time.sleep(poll_rate_s)
            except Exception as e:
                self.logger.error(e)
                self._stop = True
                break

        self.state_manager.update_state(STATE_DISABLED)

    @dataclass
    class _WindowInfo:
        hwnd_w3c: int
        hwnd_warcraft3: int | None
        watched_screen_pos: Point
        watched_window_pos: Point

    def _wait_for_window(self, poll_rate_s: float) -> _WindowInfo | None:
        waiting = False

        def _wait():
            nonlocal waiting
            if not waiting:
                self.logger.info("Waiting for W3C window...")
                waiting = True
            time.sleep(poll_rate_s)

        while not self._stop:
            hwnd_w3c = utils.find_window_by_title(self.config.w3champions_window_title)
            hwnd_warcraft3 = utils.find_window_by_title(self.config.warcraft3_window_title)

            if not hwnd_w3c:
                self.logger.debug(
                    f"[!] Could not find window with title containing '{self.config.w3champions_window_title}'."
                )
                _wait()
                continue

            point_screen_pos, point_window_pos = utils.hwnd_relative_to_screen_xy(
                hwnd_w3c,
                self.config.x_offset_pct,
                self.config.y_offset_pct,
                self.config.enforced_window_aspect_ratio,
            )

            if point_screen_pos == (0, 0):
                self.logger.debug(f"{self.config.w3champions_window_title} window is not visible.")
                _wait()
                continue

            if not utils.point_belongs_to_window(hwnd_w3c, point_screen_pos):
                try:
                    under = win32gui.WindowFromPoint(point_screen_pos)
                    title = win32gui.GetWindowText(win32gui.GetAncestor(under, win32con.GA_ROOT))
                    self.logger.debug(
                        f"[skip] {point_screen_pos} belongs to '{title}', not {self.config.w3champions_window_title}"
                    )
                except Exception as ex:
                    self.logger.debug(f"[skip] {point_screen_pos} could not check pixel ownership: {ex}")

                _wait()
                continue

            if waiting:
                self.logger.info("W3C Window detected.")

            return Monitor._WindowInfo(
                hwnd_w3c=hwnd_w3c,
                hwnd_warcraft3=hwnd_warcraft3,
                watched_screen_pos=point_screen_pos,
                watched_window_pos=point_window_pos,
            )

        return None
