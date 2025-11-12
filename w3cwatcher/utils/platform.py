import os
import subprocess
import sys
import ctypes
from pathlib import Path
from typing import Optional
import tkinter as tk
from tkinter import messagebox


_IS_WINDOWS = os.name == "nt"


if _IS_WINDOWS:
    from win32com.client import Dispatch
    from win32com.shell import shell, shellcon

    # GetAncestor flags (not all exposed in win32con)
    GA_PARENT = 1
    GA_ROOT = 2
    GA_ROOTOWNER = 3

    DPI_RESULT_OK = 0
    DPI_RESULT_ALREADY_SET = 0x5
    PROCESS_PER_MONITOR_DPI_AWARE = 2


def ensure_windows() -> None:
    if not _IS_WINDOWS:
        raise NotImplementedError("This function is only supported on Windows.")


def set_dpi_awareness() -> None:
    if not _IS_WINDOWS:
        return

    # noinspection PyBroadException
    try:
        # noinspection PyUnresolvedReferences
        hr = ctypes.windll.shcore.SetProcessDpiAwareness(PROCESS_PER_MONITOR_DPI_AWARE)
        if hr in (DPI_RESULT_OK, DPI_RESULT_ALREADY_SET):
            return
    except Exception:
        pass


def get_app_name() -> str:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).stem

    main_module = sys.modules.get("__main__")
    if main_module is not None:
        if hasattr(main_module, "__spec__") and main_module.__spec__ is not None:
            return main_module.__spec__.name

        if hasattr(main_module, "__file__") and main_module.__file__:
            return Path(main_module.__file__).stem

    return Path(sys.argv[0]).stem or "app"


def open_file(file: Path | str) -> None:
    if os.name == "nt":
        os.startfile(file)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(file)])
    else:
        subprocess.Popen(["xdg-open", str(file)])

def show_error(message: str) -> None:
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("W3CWatcher Error", message)
    root.destroy()
