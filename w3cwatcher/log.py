from __future__ import annotations
import builtins
import logging
from pathlib import Path
import sys
import os
from datetime import datetime
from typing import List

from platformdirs import user_log_dir
from .config import APP_NAME, Settings


def _log_dir() -> Path:
    # e.g. %LOCALAPPDATA%\W3CWatcher\Logs
    return Path(user_log_dir(appname=APP_NAME, appauthor=False))


def _make_instance_logfile() -> Path:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    pid = os.getpid()
    return _log_dir() / f"{APP_NAME}_{ts}_{pid}.log"


def _prune_old_logs(dirpath: Path, keep: int) -> None:
    """
    Keep the newest `keep` log files that match our naming scheme; delete older ones.
    """
    if keep <= 0:
        return
    pattern = f"{APP_NAME}_*.log"
    files: List[Path] = sorted(dirpath.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in files[keep:]:
        try:
            old.unlink(missing_ok=True)
        except Exception:
            # Best-effort pruning; ignore locked files
            pass


def _formatter() -> logging.Formatter:
    # Millisecond-precision timestamps on every line
    return logging.Formatter(
        fmt="%(asctime)s.%(msecs)03d [%(levelname)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def init_logging(settings: Settings) -> tuple[logging.Logger, Path]:
    """
    Initialize per-instance file logging and redirect print/stdout/stderr.
    Safe to call once at startup; no duplicate handlers added on repeats.
    Returns (logger, logfile_path).
    """
    log_dir = _log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    logfile = _make_instance_logfile()

    logger = logging.getLogger(APP_NAME)
    level_name = getattr(settings, "log_level", "INFO") or "INFO"
    logger.setLevel(getattr(logging, level_name.upper(), logging.INFO))
    logger.propagate = False

    # Avoid duplicate file handlers if called twice
    if not any(isinstance(h, logging.FileHandler) and getattr(h, "_w3cwatcher_file", False)
               for h in logger.handlers):
        fh = logging.FileHandler(logfile, encoding="utf-8")
        fh.setFormatter(_formatter())
        fh.setLevel(logging.DEBUG)  # capture everything to file
        fh._w3cwatcher_file = True  # marker
        logger.addHandler(fh)

    # Redirect print/stdout/stderr into the logger (once)
    if not getattr(sys, "_w3cwatcher_redirected", False):
        original_print = builtins.print

        def logged_print(*args, **kwargs):
            original_print(*args, **kwargs)
            sep = kwargs.get("sep", " ")
            text = sep.join(str(a) for a in args)
            logger.info(text)

        builtins.print = logged_print
        sys._w3cwatcher_redirected = True

    # Prune old logs (keep last X instances)
    keep = int(getattr(settings, "log_keep", 10))
    _prune_old_logs(log_dir, keep)

    logger.debug(f"Logging initialized -> {logfile}")

    settings.logger = logger
    settings.logfile = logfile

    return logger, logfile
