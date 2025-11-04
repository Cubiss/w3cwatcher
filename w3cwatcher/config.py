from __future__ import annotations
import os
import json
import subprocess
import sys
from dataclasses import dataclass, asdict, fields
from typing import Any, Dict
from pathlib import Path
from platformdirs import user_config_dir

# ---- App identity (used for config path) ----
APP_NAME = "W3CWatcher"

# ---- Defaults (unchanged) ----
DEFAULT_WINDOW_TITLE_KEYWORD = "W3Champions"
DEFAULT_X_OFFSET_PCT = 0.755
DEFAULT_Y_OFFSET_PCT = 0.955
DEFAULT_POLL_S = 5
DEFAULT_DEBOUNCE_SECONDS = 60
DEFAULT_DISCORD_MESSAGE = "Match found!"
DEFAULT_IN_QUEUE_COLOR = "red"
DEFAULT_INNER_RECTANGLE_ASPECT_RATIO = 1846 / 1040
DEFAULT_DISCORD_WEBHOOK_URL = ""
DEFAULT_ALLOW_MULTIPLE_INSTANCES = True

@dataclass
class Settings:
    window_title_keyword: str = DEFAULT_WINDOW_TITLE_KEYWORD
    x_offset_pct: float = DEFAULT_X_OFFSET_PCT
    y_offset_pct: float = DEFAULT_Y_OFFSET_PCT
    in_queue_color: str = DEFAULT_IN_QUEUE_COLOR
    poll_s: int = DEFAULT_POLL_S
    debounce_seconds: int = DEFAULT_DEBOUNCE_SECONDS
    discord_message: str = DEFAULT_DISCORD_MESSAGE
    discord_webhook_url: str = DEFAULT_DISCORD_WEBHOOK_URL
    inner_rectangle_aspect_ratio: float = DEFAULT_INNER_RECTANGLE_ASPECT_RATIO
    allow_multiple_instances: bool = DEFAULT_ALLOW_MULTIPLE_INSTANCES


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
