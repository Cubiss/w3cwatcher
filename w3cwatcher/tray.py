from __future__ import annotations

import os
import ctypes
import threading
from .logging import Logger
from typing import Optional
import win32api
import win32event
import winerror
from PIL import Image, ImageDraw
import pystray

from .config import APP_NAME, TrayConfig
from .monitor import Monitor
from .state_manager import STATE_WAITING, STATE_DISABLED, STATE_IN_QUEUE, STATE_IN_GAME
from .utils import open_file
from .utils.config_base import get_config_file


class TrayApp:
    _mutex_name = "W3CWatcherSingletonMutex"
    _singleton_mutex_handle = None

    def __init__(self, logger: Logger, config: TrayConfig, monitor: Monitor):
        self.logger = logger
        self.config = config
        self.monitor: Optional[Monitor] = monitor

        self._icon_red = self._icon_image(color=(200, 60, 60))
        self._icon_green = self._icon_image(color=(60, 200, 60))
        self._icon_grey = self._icon_image(color=(120, 120, 120))
        self._icon_blue = self._icon_image(color=(60, 60, 200))

        self._icon = pystray.Icon(APP_NAME, self._icon_grey, APP_NAME)
        self._worker: Optional[threading.Thread] = None

        self._icon.menu = pystray.Menu(
            pystray.MenuItem("Start", self._start),
            pystray.MenuItem("Stop", self._stop),
            pystray.MenuItem(
                "Tools",
                pystray.Menu(
                    pystray.MenuItem("Check capture area", self._check),
                    pystray.MenuItem("Test game start", self._mock_game_start),
                    pystray.MenuItem("Log", self._log),
                    pystray.MenuItem("Settings", self._settings),
                ),
            ),
            pystray.MenuItem("Quit", self._quit),
        )

        self.monitor.state_manager.add_state_change_listener(self.on_monitor_state_change)

    @staticmethod
    def _icon_image(color=(200, 60, 60)) -> Image.Image:
        img = Image.new("RGB", (64, 64), color=(40, 40, 40))
        d = ImageDraw.Draw(img)
        d.ellipse((16, 16, 48, 48), fill=color)
        return img

    def _start(self, _):
        self.start()

    def start(self):
        if self._worker and self._worker.is_alive():
            self.logger.info("Already running.")
            return

        self._worker = threading.Thread(target=self.monitor.run, daemon=True)
        self._worker.start()

    def _stop(self, _):
        self.monitor.stop()
        self._worker = None

    def _quit(self, _):
        self._stop(_)
        self._icon.stop()

    def _check(self, _):
        self._stop(_)
        self._worker = threading.Thread(target=self.monitor.show_debug_image, daemon=True)
        self._worker.start()

    def _log(self, _):
        # os.startfile(self.s.logfile)
        os.system(f"start powershell -command \"Get-Content '{self.logger.latest_path}' -Wait -Tail 40\"")

    def _settings(self, _):
        path = get_config_file(path=self.config.get_file_path(), user_config=True, app_name=APP_NAME)
        self.logger.info(f"Opening {path}")
        open_file(path)

    def _mock_game_start(self, _):
        #
        self.monitor.state_manager.update_state(STATE_IN_GAME)

    def run(self):
        if self.config.autostart:
            self.start()
        self._icon.run()

    @staticmethod
    def _ensure_single_instance() -> bool:
        # noinspection PyTypeChecker
        TrayApp._singleton_mutex_handle = win32event.CreateMutex(None, False, TrayApp._mutex_name)
        return win32api.GetLastError() != winerror.ERROR_ALREADY_EXISTS

    def on_monitor_state_change(self, new_state, _after):
        if new_state == STATE_WAITING:
            self._icon.icon = self._icon_green
        elif new_state == STATE_IN_QUEUE:
            self._icon.icon = self._icon_red
        elif new_state == STATE_DISABLED:
            self._icon.icon = self._icon_grey
        else:
            self._icon.icon = self._icon_blue
        self._icon.title = f'{APP_NAME} - {new_state}'

    # noinspection PyPep8Naming,SpellCheckingInspection,PyUnresolvedReferences
    @staticmethod
    def _show_multiple_instances_error(logger) -> None:
        message = (
            f"{APP_NAME} is already running.\n\n"
            "Check your system tray, or start with --allow-multiple-instances if you really need another copy."
        )
        logger.warning(message)
        MB_OK = 0x00000000
        MB_ICONWARNING = 0x00000030
        MB_SYSTEMMODAL = 0x00001000  # ensure it shows even if no foreground window
        ctypes.windll.user32.MessageBoxW(
            None,
            message,
            APP_NAME,
            MB_OK | MB_ICONWARNING | MB_SYSTEMMODAL,
        )
        return

    @staticmethod
    def create_singleton(logger: Logger, config: TrayConfig, monitor: Monitor) -> TrayApp | None:
        if not (config.allow_multiple_instances or TrayApp._ensure_single_instance()):
            TrayApp._show_multiple_instances_error(logger)
            return None

        return TrayApp(logger, config, monitor)
