import ctypes
import sys
import os
from ctypes import wintypes

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32   = ctypes.WinDLL("user32",   use_last_error=True)

GetConsoleWindow       = kernel32.GetConsoleWindow
AllocConsole           = kernel32.AllocConsole
FreeConsole            = kernel32.FreeConsole
SetConsoleTitleW       = kernel32.SetConsoleTitleW
SetConsoleCtrlHandler  = kernel32.SetConsoleCtrlHandler
ShowWindow             = user32.ShowWindow
SetForegroundWindow    = user32.SetForegroundWindow

SW_RESTORE = 9

CTRL_C_EVENT        = 0
CTRL_BREAK_EVENT    = 1
CTRL_CLOSE_EVENT    = 2
CTRL_LOGOFF_EVENT   = 5
CTRL_SHUTDOWN_EVENT = 6

HANDLER_ROUTINE = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.DWORD)
_ctrl_handler_ref = None  # keep a ref so it isn't GC'd


def _bind_streams_to_console():
    # Rebind stdout/stderr to the console; line-buffered, tolerant encoding.
    sys.stdout = open("CONOUT$", "w", buffering=1, encoding="utf-8", errors="replace")
    sys.stderr = open("CONOUT$", "w", buffering=1, encoding="utf-8", errors="replace")


def _unbind_streams_to_devnull():
    # Flush/close current streams and point to NUL so prints won't crash after detach.
    try:
        try:
            sys.stdout.flush()
            sys.stderr.flush()
        except Exception:
            pass
        try:
            if getattr(sys.stdout, "closed", False) is False:
                sys.stdout.close()
            if getattr(sys.stderr, "closed", False) is False:
                sys.stderr.close()
        except Exception:
            pass
    finally:
        sys.stdout = open(os.devnull, "w", buffering=1, encoding="utf-8", errors="ignore")
        sys.stderr = open(os.devnull, "w", buffering=1, encoding="utf-8", errors="ignore")


def _detach_console():
    _unbind_streams_to_devnull()
    FreeConsole()


@HANDLER_ROUTINE
def _console_ctrl_handler(ctrl_type):
    if ctrl_type in (CTRL_CLOSE_EVENT, CTRL_LOGOFF_EVENT, CTRL_SHUTDOWN_EVENT):
        _detach_console()
        return True  # tell Windows we handled it
    return False


def _ensure_ctrl_handler():
    global _ctrl_handler_ref
    if _ctrl_handler_ref is None:
        _ctrl_handler_ref = _console_ctrl_handler
        if not SetConsoleCtrlHandler(_ctrl_handler_ref, True):
            raise ctypes.WinError(ctypes.get_last_error())


def is_console_open() -> bool:
    return bool(GetConsoleWindow())


def open_console(title: str = "PixelWatcher Log", bring_to_front: bool = True):
    """
    Ensure a console exists, attach stdout/stderr, and register a close handler
    so closing the console window doesn't kill the app.
    """
    hwnd = GetConsoleWindow()
    if not hwnd:
        # Create a new console and wire up streams & handler.
        if not AllocConsole():
            raise ctypes.WinError(ctypes.get_last_error())
        SetConsoleTitleW(title)
        _bind_streams_to_console()
        _ensure_ctrl_handler()
        hwnd = GetConsoleWindow()

    if bring_to_front and hwnd:
        ShowWindow(hwnd, SW_RESTORE)
        SetForegroundWindow(hwnd)

    return hwnd


def close_console():
    """Manually detach from the console (safe to call even if none is open)."""
    if is_console_open():
        _detach_console()


# --- Optional demo
if __name__ == "__main__":
    open_console()
    print("Test line. Close the console window and the process will keep running.")
