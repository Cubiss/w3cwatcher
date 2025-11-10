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

from .config import Config, APP_NAME, TrayConfig
from .monitor import Monitor
from .notifier import Notifier
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

        self._icon = pystray.Icon(APP_NAME, self._icon_red, APP_NAME)
        self._worker: Optional[threading.Thread] = None

        self._icon.menu = pystray.Menu(
            pystray.MenuItem("Start", self._start),
            pystray.MenuItem("Stop", self._stop),
            pystray.MenuItem(
                "Tools",
                pystray.Menu(
                    pystray.MenuItem("Check", self._check),
                    pystray.MenuItem("Log", self._log),
                    pystray.MenuItem("Settings", self._settings),
                ),
            ),
            pystray.MenuItem("Quit", self._quit),
        )

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

        self.logger.info("Init for start.")

        def run_and_reset():
            self.logger.info("Starting watcher.")
            self.monitor.run()
            self.logger.info("Watcher finished.")
            self._icon.icon = self._icon_red

        self._worker = threading.Thread(target=run_and_reset, daemon=True)
        self._worker.start()
        self._icon.icon = self._icon_green

    def _stop(self, _):
        self.monitor.stop()
        self._worker = None

    def _quit(self, _):
        self._stop(_)
        self._icon.stop()

    def _check(self, _):
        self._stop(_)

        def run_and_reset():
            self.monitor.show_debug_image()
            self._icon.icon = self._icon_red

        self._worker = threading.Thread(target=run_and_reset, daemon=True)
        self._worker.start()

        self._icon.icon = self._icon_green

    def _log(self, _):
        # os.startfile(self.s.logfile)
        os.system(f"start powershell -command \"Get-Content '{self.logger.latest_path}' -Wait -Tail 40\"")

    def _settings(self, _):
        path = get_config_file(path=self.config.get_file_path(), user_config=True, app_name=APP_NAME)
        self.logger.info("Opening ", path)
        open_file(path)

    def run(self):
        self.start()
        self._icon.run()

    def _ensure_single_instance(self) -> bool:
        self._singleton_mutex_handle = win32event.CreateMutex(None, False, self._mutex_name)
        return win32api.GetLastError() != winerror.ERROR_ALREADY_EXISTS

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
    def create(logger: Logger, config: Config, notifier: Notifier) -> TrayApp | None:
        if not (config.tray.allow_multiple_instances or TrayApp._ensure_single_instance()):
            TrayApp._show_multiple_instances_error(logger)
            return None

        return TrayApp(logger, config, notifier)
