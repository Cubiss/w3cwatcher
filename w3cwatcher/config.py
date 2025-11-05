from __future__ import annotations

import logging
import os
import json
import subprocess
import sys
from dataclasses import dataclass, asdict, fields, field
from typing import Any, Dict
from pathlib import Path
from platformdirs import user_config_dir

APP_NAME = "W3CWatcher"

@dataclass
class Settings:
    w3champions_window_title: str = "W3Champions"
    warcraft3_window_title: str = "Warcraft III"
    x_offset_pct: float = 0.755
    y_offset_pct: float = 0.955
    in_queue_color: str = "red"
    ready_color: str = "green"
    poll_s: int = 1
    reduced_poll_s: int = 5
    debounce_seconds: int = 60
    discord_message: str = "Match found!"
    discord_webhook_url: str = field(default='', metadata={"serialize": False})
    inner_rectangle_aspect_ratio: float = 1846 / 1040
    allow_multiple_instances: bool = False
    log_level: str = "INFO"
    log_keep: int = 10
    logfile: Path = field(default=None, metadata={"serialize": False})
    logger: logging.Logger = field(default=None, metadata={"serialize": False})

    def __str__(self):
        serializable = {}
        for f in fields(self):
            if f.metadata.get("serialize", True):
                serializable[f.name] = getattr(self, f.name)
        return json.dumps(serializable, indent=2)


def _config_file_dir() -> Path:
    return Path(user_config_dir(APP_NAME, appauthor=False))


def config_file_path() -> Path:
    return _config_file_dir() / "config.json"


def _coerce_types_into_settings(data: Dict[str, Any]) -> Settings:
    """Create a Settings instance from a dict, coercing basic types where sensible."""
    field_types = {f.name: f.type for f in fields(Settings)}
    kwargs: Dict[str, Any] = {}
    for name, tp in field_types.items():
        if name in data:
            val = data[name]
            if tp is float:
                try:
                    val = float(val)
                except Exception:
                    pass
            elif tp is int:
                try:
                    val = int(val)
                except Exception:
                    pass
            elif tp is str and val is not None:
                val = str(val)
            kwargs[name] = val
    return Settings(**{**asdict(Settings()), **kwargs})


def ensure_user_config() -> Path:
    cfg_dir = _config_file_dir()
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg_file = config_file_path()

    if not cfg_file.exists():
        defaults = asdict(Settings())
        cfg_file.write_text(json.dumps(defaults, indent=2), encoding="utf-8")

    return cfg_file


def load_user_config(create_if_missing: bool = True) -> Settings:
    if create_if_missing:
        ensure_user_config()

    cfg_file = config_file_path()
    loaded: Dict[str, Any] = {}
    if cfg_file.exists():
        try:
            loaded = json.loads(cfg_file.read_text(encoding="utf-8"))
        except Exception as ex:
            print("ERROR: Could not load config file:", ex)
            loaded = {}

    # Merge file values into defaults
    settings = _coerce_types_into_settings(loaded)

    return settings


def open_user_config():
    cfg_path = ensure_user_config()

    try:
        if os.name == "nt":  # Windows
            os.startfile(cfg_path)  # type: ignore[attr-defined]
        else:
            opener = "open" if sys.platform == "darwin" else "xdg-open"
            subprocess.Popen([opener, str(cfg_path)])
    except Exception as e:
        print(f"Could not open config file automatically: {e}")
        print(f"Config file path: {cfg_path}")
