from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass, asdict, fields, is_dataclass
from pathlib import Path
from platformdirs import user_config_dir
from dataclasses import field as dc_field


def field(*, arg=None, help_text=None, serialize=True, **kwargs):
    """
    Custom field() wrapper that allows top-level 'arg', 'help_text',
    and 'serialize' parameters instead of putting them inside metadata.
    """
    metadata = kwargs.pop("metadata", {}) or {}
    # Merge the custom params into metadata
    if arg is not None:
        metadata["arg"] = arg
    if help_text is not None:
        metadata["help_text"] = help_text
    if serialize is not None:
        metadata["serialize"] = serialize

    return dc_field(metadata=metadata, **kwargs)


@dataclass
class UnifiedConfig:
    config_path: (Path | str) = field(default=None, metadata={
        "serialize": False,  # should be serialized into file
        "arg": None,         # should have a command line argument '--serialize'
        "help_text": "Source of the config."
    })

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not is_dataclass(cls):
            # tune these flags as you prefer
            dataclass(eq=True, repr=False)(cls)

    def __init__(self, config_path: (Path | str) = None, user_config: bool = False, app_name: str = None):
        app_name = app_name or _get_app_name()

        if config_path is not None:
            self.config_path = config_path
        elif user_config:
            self.config_path = Path(user_config_dir(app_name, appauthor=False)) / "config.json"
        else:
            self.config_path = Path('./') / f'{app_name}.config.json'

    def __str__(self):
        serializable = {}
        for f in fields(self):
            if f.metadata.get("serialize", True):
                serializable[f.name] = getattr(self, f.name)
        return json.dumps(serializable, indent=2)

    @classmethod
    def get_argument_parser(cls, *args, **kwargs) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(*args, **kwargs)

        for f in fields(cls):
            if not (arg := f.metadata.get("arg")):
                continue

            help_text = f.metadata.get("help_text", "")
            arg_type = f.type

            if arg_type is bool:
                parser.add_argument(arg, dest=f.name, action='store_true', help=help_text)
            else:
                parser.add_argument(arg, dest=f.name, type=arg_type, default=None, help=help_text)

        return parser

    @staticmethod
    def from_args(argv: list[str] = None, parser: argparse.Namespace = None) -> UnifiedConfig:
        argv = argv or sys.argv
        parser = parser or UnifiedConfig.get_argument_parser()
        cfg = UnifiedConfig()
        for f in fields(UnifiedConfig):
            if hasattr(parser, f.name):
                val = getattr(parser, f.name)
                if val is not None:
                    setattr(cfg, f.name, val)

        return cfg

    @staticmethod
    def from_file(file: (Path | str)):
        cfg = UnifiedConfig()
        loaded = json.loads(UnifiedConfig.get_config_file(file).read_text(encoding="utf-8"))
        for f in fields(UnifiedConfig):
            if f.name in loaded:
                setattr(cfg, f.name, f.type(loaded[f.name]))
        cfg.config_path = file
        return cfg

    @staticmethod
    def get_config_file(path: (Path | str)):
        file = Path(path)
        file.parent.mkdir(parents=True, exist_ok=True)
        if not file.exists():
            file.write_text(json.dumps(asdict(UnifiedConfig()), indent=2), encoding="utf-8")
        return file

    def show(self):
        if os.name == "nt":
            os.startfile(self.config_path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(self.config_path)])
        else:
            subprocess.Popen(["xdg-open", str(self.config_path)])


def _get_app_name():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).stem

    main_module = sys.modules.get('__main__')
    if main_module is not None:
        if hasattr(main_module, '__spec__') and main_module.__spec__ is not None:
            return main_module.__spec__.name

        if hasattr(main_module, '__file__') and main_module.__file__:
            return Path(main_module.__file__).stem

    return Path(sys.argv[0]).stem or "app"
