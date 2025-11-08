from __future__ import annotations
import argparse
import json
import sys
from dataclasses import dataclass, fields, is_dataclass
from pathlib import Path
from dataclasses import field as dc_field
from typing import Any, Callable, Self, Dict, Union, List

FIELD_ARG = "arg"
FIELD_HELP_TEXT = "help_text"
FIELD_SERIALIZER = "serializer"
FIELD_MODIFIABLE = "modifiable"
FIELD_VALIDATORS = "validator"

AUTO_ARG = -1

DEFAULT_SOURCE = "default"


Serializable = Union[
    None,
    bool,
    int,
    float,
    str,
    List["JsonSerializable"],
    Dict[str, "JsonSerializable"],
]


def default_serializer(value: Any) -> Serializable:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [default_serializer(v) for v in value]
    if isinstance(value, dict):
        return {k: default_serializer(v) for k, v in value.items()}
    return str(value)

def do_not_serialize_serializer(_) -> (str | None):
    return None

def get_allowed_values_validator(*values) -> Callable[[Any], (str | None)]:
    def validator(value):
        if value in values:
            return None
        return f"Must be one of: {values}"
    return validator

def get_allowed_range_validator(lower_boundary, upper_boundary) -> Callable[[Any], (str | None)]:
    def validator(value):
        if lower_boundary < value < upper_boundary:
            return None
        return f"Must be between {lower_boundary} and {upper_boundary}"
    return validator

def field(*, arg: str = AUTO_ARG,
          help_text: str=None,
          modifiable: bool=True,
          serialize: bool=True,
          serializer: Callable[[Any], (str | None)]=default_serializer,
          validator: Callable[[Any], (str | None)]=None,
          **kwargs):
    metadata = kwargs.pop("metadata", {}) or {}
    if arg is not None:
        metadata[FIELD_ARG] = arg
    if help_text is not None:
        metadata[FIELD_HELP_TEXT] = help_text
    if modifiable is not None:
        metadata[FIELD_MODIFIABLE] = modifiable
    if not serialize or serializer is None:
        metadata[FIELD_SERIALIZER] = do_not_serialize_serializer
    else:
        metadata[FIELD_SERIALIZER] = serializer

    if validator is not None:
        metadata[FIELD_VALIDATORS] = [validator]


    return dc_field(metadata=metadata, **kwargs)


@dataclass
class ConfigBase:
    _source: dict[str, str] = dc_field(default_factory=dict, init=False, repr=False, compare=False)
    _modified: set[str] = dc_field(default_factory=set, init=False, repr=False, compare=False)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not is_dataclass(cls):
            dataclass()(cls)

    def __post__init__(self):
        self._init_tracking()

    def __str__(self):
        return json.dumps(self.as_dict(include_defaults=True), indent=2)

    def as_dict(self, serialize: bool=True, recursive: bool=True, include_defaults=False) -> Dict[str, (str, Any)]:
        retval = {}
        for f in fields(self):
            if not include_defaults and self._source[f.name] == DEFAULT_SOURCE:
                continue

            value = getattr(self, f.name)
            if recursive and issubclass(f.type, ConfigBase):
                retval[f.name] = value.to_dict(serializable=serialize, recursive=recursive)

            if serialize:
                serializer = f.metadata.get(FIELD_SERIALIZER, do_not_serialize_serializer)
                serialized_val = serializer(value)
                if serialized_val is not None:
                    retval[f.name] = serialized_val
            else:
                retval[f.name] = value
        return retval

    def __setattr__(self, name, value):
        matching_fields = list(f for f in fields(self) if name == f.name)
        if len(matching_fields) == 0:
            return super().__setattr__(name, value)

        if value == getattr(self, name):
            return super().__setattr__(name, value)

        fld = matching_fields[0]

        if not fld.metadata.get(FIELD_MODIFIABLE, True):
            raise AttributeError(f"Field '{name}' is not modifiable")

        if validator := fld.metadata.get(FIELD_VALIDATORS, None):
            error = validator(value)
            if error is not None:
                raise ValueError(error)

        old = getattr(self, name, None)
        if old != value:
            self._modified.add(name)

        return super().__setattr__(name, value)

    def _set_silently(self, name: str, value):
        object.__setattr__(self, name, value)

    def _init_tracking(self):
        for f in fields(self):
            if f.name.startswith("_"):
                continue
            self._source.setdefault(f.name, DEFAULT_SOURCE)


    @classmethod
    def add_argument_group(cls, parser: argparse.ArgumentParser, namespace: str='', description: str=None):
        group = parser
        if namespace:
            group = parser.add_argument_group(title=namespace, description=description)

        for f in fields(cls):
            arg_type = f.type
            help_text = f.metadata.get(FIELD_HELP_TEXT, None)
            arg = f.metadata.get(FIELD_ARG, None)

            if not arg:
                continue

            if issubclass(arg_type, ConfigBase):
                arg_type.add_argument_group(group, namespace=f'{namespace}.{f.name}' if arg == AUTO_ARG else arg,
                                                   description=help_text)
            elif arg_type is bool:
                parser.add_argument(arg, dest=f.name, action='store_true', help=help_text)
            else:
                parser.add_argument(arg, dest=f.name, type=arg_type, default=None, help=help_text)


    @classmethod
    def get_argument_parser(cls, *args, **kwargs) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(*args, **kwargs)
        cls.add_argument_group(parser)
        return parser

    @classmethod
    def from_args(cls, args: argparse.Namespace = None, argv: list[str] = None):
        if args is None:
            if argv is None:
                argv = sys.argv
            parser = cls.get_argument_parser()
            args = parser.parse_args(argv)

        cfg = cls()
        for f in fields(cls):
            if issubclass(f.type, ConfigBase):
                val = f.type.from_args(args, argv)
                setattr(cfg, f.name, val)
                cfg._source[f.name] = "arg"

            if hasattr(args, f.name):
                val = getattr(args, f.name)
                if val is not None:
                    setattr(cfg, f.name, val)
                    cfg._source[f.name] = "arg"

        return cfg

    @classmethod
    def from_file(cls, file: (Path | str)):
        loaded = json.loads(file.read_text(encoding="utf-8"))
        return cls.from_dict(loaded, source=file)

    @classmethod
    def from_dict(cls, loaded, source='from_dict'):
        cfg = cls()
        for f in fields(cls):
            if f.name in loaded:
                if issubclass(f.type, ConfigBase):
                    setattr(cfg, f.name, f.type.from_dict(loaded[f.name], source))
                else:
                    setattr(cfg, f.name, f.type(loaded[f.name]))
                cfg._source[f.name] = source

    def save(self, path: (Path | str) = None, include_defaults=False):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                self.as_dict(serialize=True, include_defaults=include_defaults), indent=2
            ),encoding="utf-8")

    def update(self,
               other: Self,
              ):
        if not issubclass(other, ConfigBase):
            return

        for f in fields(self):
            name = f.name
            my_val = getattr(other, name)
            their_val = getattr(self, name, None)

            if issubclass(f.type, ConfigBase):
                if their_val is not None:
                    my_val.update(their_val)
                continue

            if name.startswith("_"):
                continue

            if not f.metadata.get(FIELD_MODIFIABLE, True):
                continue

            if name not in other._modified:
                continue

            if my_val != their_val:
                self._set_silently(name, my_val)
            self._source[name] = other._source.get(name, 'merge')
            self._modified.add(name)
