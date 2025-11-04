from __future__ import annotations

import os
import sys
import ctypes
import threading
from typing import Optional

import win32api
import win32event
import winerror
from PIL import Image, ImageDraw
import pystray
from pathlib import Path
import win32com.client
from .config import Settings, open_user_config, APP_NAME
from .watcher import PixelWatcher

_mutex_name = "W3CWatcherSingletonMutex"
_singleton_mutex_handle = None

class TrayApp:
    def __init__(self, settings: Settings):
        self.s = settings

        # store icons
        self._icon_red = self._icon_image(color=(200, 60, 60))
        self._icon_green = self._icon_image(color=(60, 200, 60))

        self._icon = pystray.Icon(APP_NAME, self._icon_red, APP_NAME)
        self._worker: Optional[threading.Thread] = None
        self._watcher: Optional[PixelWatcher] = None

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
        if self._worker and self._worker.is_alive():
            return

        def run_and_reset():
            print('Starting watcher.')
            self._watcher.run()
            print('Watcher finished.')
            self._icon.icon = self._icon_red

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
            print('Starting watcher.')
            self._watcher.run()
            print('Watcher finished.')
            self._icon.icon = self._icon_red


        self._watcher = PixelWatcher(self.s, check_only=True)
        self._worker = threading.Thread(target=run_and_reset, daemon=True)
        self._worker.start()

        self._icon.icon = self._icon_green


    def _log(self, _):
        # os.startfile(self.s.logfile)
        os.system(f'start powershell -command "Get-Content \'{self.s.logfile}\' -Wait -Tail 40"')

    def _settings(self, _):
        open_user_config()

    def run(self):
        self._icon.run()


def _detach_console() -> None:
    try:
        ctypes.windll.kernel32.FreeConsole()
    except Exception:
        pass


def _ensure_single_instance() -> bool:
    global _singleton_mutex_handle
    _singleton_mutex_handle = win32event.CreateMutex(None, False, _mutex_name)
    return win32api.GetLastError() != winerror.ERROR_ALREADY_EXISTS


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


def run_tray(settings: Settings) -> None:
    _detach_console()
    if not (settings.allow_multiple_instances or _ensure_single_instance()):
        return _show_multiple_instances_error()

    print('Starting W3CWatcher Tray app')
    return TrayApp(settings).run()


def create_tray_shortcut():
    shell = win32com.client.Dispatch("WScript.Shell")
    desktop = Path(shell.SpecialFolders("Desktop"))

    shortcut_path = desktop / "W3CWatcher.lnk"

    exe = Path(sys.executable)
    pythonw = exe if exe.name.lower() == "pythonw.exe" else exe.with_name("pythonw.exe")
    if not pythonw.exists():
        pythonw = exe

    arguments = "-m w3cwatcher --tray"
    working_dir = Path.cwd()

    shortcut = shell.CreateShortcut(str(shortcut_path))
    shortcut.Targetpath = str(pythonw)
    shortcut.Arguments = arguments
    shortcut.WorkingDirectory = str(working_dir)
    shortcut.IconLocation = str(pythonw)
    shortcut.Description = "Launch PixelWatcher in tray mode"
    shortcut.Save()

    print(f"Created desktop shortcut: {shortcut_path}")
    return str(shortcut_path)
