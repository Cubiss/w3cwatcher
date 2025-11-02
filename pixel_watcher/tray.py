from __future__ import annotations
import threading
from typing import Optional

from PIL import Image, ImageDraw
import pystray

from .config import Settings
from .utils import calibrate_offsets
from .watcher import PixelWatcher


class TrayApp:
    def __init__(self, settings: Settings):
        self.s = settings
        self._icon = pystray.Icon("PixelWatcher", self._icon_image(), "Pixel Watcher")
        self._worker: Optional[threading.Thread] = None
        self._watcher: Optional[PixelWatcher] = None

        self._icon.menu = pystray.Menu(
            pystray.MenuItem("Start", self._start),
            pystray.MenuItem("Stop", self._stop),
            pystray.MenuItem("Calibrate", self._calibrate),
            pystray.MenuItem("Quit", self._quit)
        )

    def _icon_image(self) -> Image.Image:
        # simple dot icon
        img = Image.new("RGB", (64, 64), color=(40, 40, 40))
        d = ImageDraw.Draw(img)
        d.ellipse((16, 16, 48, 48), fill=(200, 60, 60))
        return img

    def _start(self, _):
        if self._worker and self._worker.is_alive():
            return
        self._watcher = PixelWatcher(self.s)
        self._worker = threading.Thread(target=self._watcher.run, daemon=True)
        self._worker.start()

    def _stop(self, _):
        if self._watcher:
            self._watcher.stop()
        self._watcher = None
        self._worker = None

    def _calibrate(self, _):
        hwnd = find_window_by_keyword(self.s.window_title_keyword)
        if not hwnd:
            print(f"[!] Window not found: {self.s.window_title_keyword}")
            return
        xo, yo = calibrate_offsets(hwnd)
        self.s.x_offset = xo
        self.s.y_offset = yo

    def _quit(self, _):
        self._stop(_)
        self._icon.stop()

    def run(self):
        self._icon.run()