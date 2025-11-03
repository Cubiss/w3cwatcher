# console_log.py
import ctypes, sys, os
from ctypes import wintypes

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32   = ctypes.WinDLL("user32",   use_last_error=True)

GetConsoleWindow      = kernel32.GetConsoleWindow
AllocConsole          = kernel32.AllocConsole
FreeConsole           = kernel32.FreeConsole
SetConsoleTitleW      = kernel32.SetConsoleTitleW
SetConsoleCtrlHandler = kernel32.SetConsoleCtrlHandler
ShowWindow            = user32.ShowWindow
SetForegroundWindow   = user32.SetForegroundWindow

SW_RESTORE = 9
CTRL_CLOSE_EVENT   = 2
CTRL_LOGOFF_EVENT  = 5
CTRL_SHUTDOWN_EVENT= 6

HANDLER_ROUTINE = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.DWORD)
_handler_ref = None  # keep a reference so it doesn't get GC'd


def _bind_streams():
    sys.stdout = open("CONOUT$", "w", buffering=1, encoding="utf-8", errors="replace")
    sys.stderr = open("CONOUT$", "w", buffering=1, encoding="utf-8", errors="replace")


def _unbind_streams():
    try:
        try:
            sys.stdout.flush(); sys.stderr.flush()
        except Exception:
            pass
        try:
            if not getattr(sys.stdout, "closed", True): sys.stdout.close()
            if not getattr(sys.stderr, "closed", True): sys.stderr.close()
        except Exception:
            pass
    finally:
        sys.stdout = open(os.devnull, "w", buffering=1, encoding="utf-8", errors="ignore")
        sys.stderr = open(os.devnull, "w", buffering=1, encoding="utf-8", errors="ignore")


def _detach_console():
    _unbind_streams()
    FreeConsole()


@HANDLER_ROUTINE
def _console_ctrl_handler(ctrl_type):
    # Detach (and keep app alive) if the console is being closed/logged off/shut down.
    if ctrl_type in (CTRL_CLOSE_EVENT, CTRL_LOGOFF_EVENT, CTRL_SHUTDOWN_EVENT):
        _detach_console()
        return True
    return False


def _ensure_handler_installed():
    global _handler_ref
    if _handler_ref is None:
        _handler_ref = _console_ctrl_handler
        if not SetConsoleCtrlHandler(_handler_ref, True):
            raise ctypes.WinError(ctypes.get_last_error())


def is_console_open() -> bool:
    return bool(GetConsoleWindow())


def open_console(title: str = "PixelWatcher Log", bring_to_front: bool = True):
    # Install handler early so it’s in place even if the user closes fast.
    _ensure_handler_installed()

    hwnd = GetConsoleWindow()
    if not hwnd:
        if not AllocConsole():
            raise ctypes.WinError(ctypes.get_last_error())
        SetConsoleTitleW(title)
        _bind_streams()
        hwnd = GetConsoleWindow()

    if bring_to_front and hwnd:
        ShowWindow(hwnd, SW_RESTORE)
        SetForegroundWindow(hwnd)

    print("Your log is here.")
    return hwnd


def close_console():
    if is_console_open():
        _detach_console()
