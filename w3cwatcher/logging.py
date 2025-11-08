from __future__ import annotations

import logging

import os
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional, Dict

from platformdirs import user_log_dir

from w3cwatcher.config import APP_NAME, Config

ALLOWED_LOG_LEVELS = (
    'CRITICAL',
    'FATAL',
    'ERROR',
    'WARN',
    'WARNING',
    'INFO',
    'DEBUG'
)


class RedactingFormatter(logging.Formatter):
    """
    Wraps another formatter; post-processes the rendered string with a redactor.
    """
    def __init__(self, base_formatter: logging.Formatter, redactor: Callable[[str], str]):
        super().__init__(fmt=base_formatter._fmt, datefmt=base_formatter.datefmt)
        self._base = base_formatter
        self._redact = redactor

    def format(self, record: logging.LogRecord) -> str:
        # noinspection PyBroadException
        try:
            rendered = self._base.format(record)
            return self._redact(rendered)
        except Exception:
            return "[log redaction failed: sensitive data suppressed]"


class Logger:
    _instances: Dict[str, Logger] = {}

    def __init__(
        self,
        app_name: str = APP_NAME,
        log_level: str = "INFO",
        keep: int = 10,
        log_dir: Optional[Path] = None,
    ) -> None:
        self.app_name = app_name
        self.keep = keep
        self.log_dir = Path(log_dir) if log_dir else Path(user_log_dir(appname=app_name, appauthor=False))
        self.log_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        pid = os.getpid()
        self.file_path = self.log_dir / f"{self.app_name}_{ts}_{pid}.log"
        self.latest_path = self.log_dir / "latest.log"

        self.logger = logging.getLogger(self.app_name)
        self.logger.setLevel(log_level or logging.INFO)
        self.logger.propagate = False

        self._base_fmt = logging.Formatter(
            fmt="%(asctime)s.%(msecs)03d [%(levelname)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Idempotent: only add our file handlers once per process
        if not any(isinstance(h, logging.FileHandler) and getattr(h, "_w3cwatcher_file", False)
                   for h in self.logger.handlers):
            self._add_file_handlers()

        self._prune_old_logs()

        self.logger.debug(f"Logging initialized -> {self.file_path}")

    # ---------- public helpers ----------

    @classmethod
    def from_config(cls, config: Config, app_name: str = APP_NAME) -> "Logger":
        """
        Build from your existing Config (expects .log_level and .log_keep).
        """
        key = f"{app_name}"
        if key in cls._instances:
            inst = cls._instances[key]
            inst.set_level(getattr(config, "log_level", "INFO"))
            return inst
        inst = cls(
            app_name=app_name,
            log_level=getattr(config, "log_level", "INFO"),
            keep=getattr(config, "log_keep", 10),
        )
        cls._instances[key] = inst
        return inst

    def get_logger(self) -> logging.Logger:
        return self.logger

    def set_level(self, level: str | int) -> None:
        lvl = getattr(logging, str(level).upper(), level)
        self.logger.setLevel(lvl)
        for h in self.logger.handlers:
            h.setLevel(logging.DEBUG if isinstance(h, logging.FileHandler) else lvl)

    def add_console(self, level: str | int = "INFO") -> None:
        """
        Add a console (stream) handler if not already present.
        """
        if not any(isinstance(h, logging.StreamHandler) and getattr(h, "_w3cwatcher_console", False)
                   for h in self.logger.handlers):
            ch = logging.StreamHandler()
            ch.setFormatter(self._base_fmt)
            ch.setLevel(getattr(logging, str(level).upper(), level))
            ch._w3cwatcher_console = True
            self.logger.addHandler(ch)

    def add_redactor(self, redactor: Callable[[str], str]) -> None:
        """
        Apply a redactor on top of each handler's formatter.
        """
        for handler in self.logger.handlers:
            base = handler.formatter or self._base_fmt
            handler.setFormatter(RedactingFormatter(base, redactor))

    # ---------- internals ----------

    def _add_file_handlers(self) -> None:
        """
        Two file handlers:
          • append to the per-run file
          • overwrite 'latest.log'
        """
        for path, mode in [(self.file_path, "a"), (self.latest_path, "w")]:
            fh = logging.FileHandler(path, encoding="utf-8", mode=mode)
            fh.setFormatter(self._base_fmt)
            fh.setLevel(logging.DEBUG)  # capture everything to disk
            fh._w3cwatcher_file = True  # marker to avoid duplicates
            self.logger.addHandler(fh)

    def _prune_old_logs(self) -> None:
        """
        Keep the newest `keep` matching '{APP_NAME}_*.log' in the same directory.
        """
        if self.keep <= 0:
            return
        pattern = f"{self.app_name}_*.log"
        files = sorted(
            self.log_dir.glob(pattern),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        for old in files[self.keep:]:
            # noinspection PyBroadException
            try:
                old.unlink(missing_ok=True)
            except Exception:
                # Best-effort; ignore locked files
                pass

    # Delegate logging methods to the wrapped logger
    def debug(self, msg, *args, **kwargs):
        self.logger.debug(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.logger.error(msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        self.logger.critical(msg, *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        self.logger.exception(msg, *args, **kwargs)

    def log(self, level, msg, *args, **kwargs):
        self.logger.log(level, msg, *args, **kwargs)
