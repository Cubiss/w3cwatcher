from __future__ import annotations

import os
import ctypes
import threading
from logging import Logger
from typing import Optional
import win32api
import win32event
import winerror
from PIL import Image, ImageDraw
import pystray

from .config import Config, APP_NAME, TrayConfig
from .monitor import Monitor
from .notifier import Notifier


class TrayApp:
    _mutex_name = "W3CWatcherSingletonMutex"
    _singleton_mutex_handle = None

    def __init__(self, logger: Logger, config: TrayConfig, monitor: Monitor):
        self.logger = logger
        self.config = config
        self.monitor = monitor

        self._icon_red = self._icon_image(color=(200, 60, 60))
        self._icon_green = self._icon_image(color=(60, 200, 60))

        self._icon = pystray.Icon(APP_NAME, self._icon_red, APP_NAME)
        self._worker: Optional[threading.Thread] = None
        self._monitor: Optional[Monitor] = None

        self._icon.menu = pystray.Menu(
            pystray.MenuItem("Start", self._start),
            pystray.MenuItem("Stop", self._stop),
            pystray.MenuItem(
                "Tools",
                pystray.Menu(
                    pystray.MenuItem("Check", self._check),
                    pystray.MenuItem("Log", self._log),
                    pystray.MenuItem("Settings", self._settings),
                )
            ),
            pystray.MenuItem("Quit", self._quit)
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
            print('Already running.')
            return

        print('Init for start.')

        def run_and_reset():
            print('Starting watcher.')
            self._monitor.run()
            print('Watcher finished.')
            self._icon.icon = self._icon_red

        self._monitor = Monitor(self.logger, self.config, self.notifier)
        self._worker = threading.Thread(target=run_and_reset, daemon=True)
        self._worker.start()

        # set icon green
        self._icon.icon = self._icon_green

    def _stop(self, _):
        if self._monitor:
            self._monitor.stop()
        self._monitor = None
        self._worker = None

        # set icon red
        self._icon.icon = self._icon_red

    def _quit(self, _):
        self._stop(_)
        self._icon.stop()

    def _check(self, _):
        self._stop(_)

        # wrapper so we know when finished
        def run_and_reset():
            print('Starting watcher.')
            self._monitor.run()
            print('Watcher finished.')
            self._icon.icon = self._icon_red


        self._monitor = Monitor(self.logger, self.config, self.notifier, check_only=True)
        self._worker = threading.Thread(target=run_and_reset, daemon=True)
        self._worker.start()

        self._icon.icon = self._icon_green


    def _log(self, _):
        # os.startfile(self.s.logfile)
        os.system(f'start powershell -command "Get-Content \'{self.config.logfile}\' -Wait -Tail 40"')

    def _settings(self, _):
        self.config.show()

    def run(self):
        self.start()
        self._icon.run()


    def _ensure_single_instance(self) -> bool:
        self._singleton_mutex_handle = win32event.CreateMutex(None, False, self._mutex_name)
        return win32api.GetLastError() != winerror.ERROR_ALREADY_EXISTS

    @staticmethod
    def _show_multiple_instances_error() -> None:
        message = f"{APP_NAME} is already running.\n\n" \
                   "Check your system tray, or start with --allow-multiple-instances if you really need another copy."
        print(message)
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
    def create(logger: Logger, config: Config, notifier: Notifier) -> (TrayApp | None):
        if not (config.allow_multiple_instances or TrayApp._ensure_single_instance()):
            TrayApp._show_multiple_instances_error()
            return None

        return TrayApp(logger, config, notifier)

