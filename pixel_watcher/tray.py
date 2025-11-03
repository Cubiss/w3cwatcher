from __future__ import annotations
import sys
import ctypes
import threading
from typing import Optional
from PIL import Image, ImageDraw
import pystray

from .config import Settings
from .watcher import PixelWatcher


class TrayApp:
    def __init__(self, settings: Settings):
        self.s = settings

        # store icons
        self._icon_red = self._icon_image(color=(200, 60, 60))
        self._icon_green = self._icon_image(color=(60, 200, 60))

        self._icon = pystray.Icon("PixelWatcher", self._icon_red, "Pixel Watcher")
        self._worker: Optional[threading.Thread] = None
        self._watcher: Optional[PixelWatcher] = None

        self._icon.menu = pystray.Menu(
            pystray.MenuItem("Start", self._start),
            pystray.MenuItem("Stop", self._stop),
            pystray.MenuItem("Check", self._check),
            pystray.MenuItem("Log", self._log),
            pystray.MenuItem("Quit", self._quit)
        )

    @staticmethod
    def _icon_image(color=(200, 60, 60)) -> Image.Image:
        img = Image.new("RGB", (64, 64), color=(40, 40, 40))
        d = ImageDraw.Draw(img)
        d.ellipse((16, 16, 48, 48), fill=color)
        return img

    def _start(self, _):
        if self._worker and self._worker.is_alive():
            return

        # wrapper so we know when finished
        def run_and_reset():
            self._watcher.run()  # run check
            self._icon.icon = self._icon_red  # back to red when done

        self._watcher = PixelWatcher(self.s)
        self._worker = threading.Thread(target=run_and_reset, daemon=True)
        self._worker.start()

        # set icon green
        self._icon.icon = self._icon_green

    def _stop(self, _):
        if self._watcher:
            self._watcher.stop()
        self._watcher = None
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
            self._watcher.run()  # run check
            self._icon.icon = self._icon_red  # back to red when done

        self._watcher = PixelWatcher(self.s, check_only=True)
        self._worker = threading.Thread(target=run_and_reset, daemon=True)
        self._worker.start()

        # green while checking
        self._icon.icon = self._icon_green


    def _log(self, _):
        # If already has console do nothing
        # Bring console to front
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if not hwnd:
            ctypes.windll.kernel32.AllocConsole()
            ctypes.windll.kernel32.SetConsoleTitleW("PixelWatcher Log")

            # Redirect stdout & stderr
            sys.stdout = open("CONOUT$", "w", buffering=1)
            sys.stderr = open("CONOUT$", "w", buffering=1)

        SW_RESTORE = 9
        ctypes.windll.user32.ShowWindow(hwnd, SW_RESTORE)
        ctypes.windll.user32.SetForegroundWindow(hwnd)

        print('Your log is here.')
        return


    def run(self):
        self._icon.run()
