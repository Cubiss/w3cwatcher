from __future__ import annotations

import argparse
import sys

import tomlkit
from dataclasses import dataclass, fields, Field, MISSING
from pathlib import Path
from dataclasses import field as dc_field
from typing import (
    Any,
    Callable,
    Self,
    Dict,
    Union,
    List,
    get_type_hints,
    Set,
    Tuple,
    Literal,
    Optional,
    Iterable,
    Iterator,
    ClassVar,
)

from platformdirs import user_config_dir

VALIDATION_ERRORS_ON_SETATTR = True

FIELD_ARG = "arg"
FIELD_HELP_TEXT = "help_text"
FIELD_SERIALIZER = "serializer"
FIELD_MODIFIABLE = "modifiable"
FIELD_VALIDATORS = "validator"

AUTO_ARG = -1

DEFAULT_SOURCE = "default"

NodeKind = Literal["scalar", "table"]


@dataclass(frozen=True)
class ScalarNode:
    name: str
    value: Any
    help_text: Optional[str] = None
    source: Optional[str] = None
    kind: NodeKind = dc_field(default="scalar", init=False)


@dataclass(frozen=True)
class TableNode:
    name: str
    children: Iterable[Node]
    help_text: Optional[str] = None
    kind: NodeKind = dc_field(default="table", init=False)


Node = Union[ScalarNode, TableNode]


class TDoNotSerialize:
    pass


DO_NOT_SERIALIZE = TDoNotSerialize()

Serializable = Union[
    TDoNotSerialize,
    None,
    bool,
    int,
    float,
    str,
    List["Serializable"],
    Dict[str, "Serializable"],
]
SerializerFunc = Callable[[Any], Serializable]


ValidationError = Union[List[str], Dict[str, "ValidationError"]]
ValidatorFunc = Callable[[Any], ValidationError]


def default_serializer(value: Any) -> Serializable:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [default_serializer(v) for v in value]
    if isinstance(value, dict):
        return {k: default_serializer(v) for k, v in value.items()}
    return str(value)


def do_not_serialize_serializer(_) -> Serializable:
    return DO_NOT_SERIALIZE


def get_allowed_values_validator(*values) -> Callable[[Any], ValidationError]:
    def validator(value):
        if value in values:
            return []
        return [f"Must be one of: {values}"]

    return validator


def get_allowed_range_validator(lower_boundary, upper_boundary) -> Callable[[Any], ValidationError]:
    def validator(value):
        if lower_boundary < value < upper_boundary:
            return []
        return [f"Must be between {lower_boundary} and {upper_boundary}"]

    return validator


def field(
    *,
    arg: str = AUTO_ARG,
    help_text: str = None,
    modifiable: bool = True,
    serialize: bool = True,
    serializer: SerializerFunc = default_serializer,
    validators: ValidatorFunc | List[ValidatorFunc] | None = None,
    **kwargs,
):
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

    if validators is None:
        metadata[FIELD_VALIDATORS] = []
    elif isinstance(validators, list):
        metadata[FIELD_VALIDATORS] = validators
    elif callable(validators):
        metadata[FIELD_VALIDATORS] = [validators]
    else:
        raise ValueError("validators must be callable")

    return dc_field(metadata=metadata, **kwargs)


@dataclass
class ConfigBase:
    # Shared across all instances
    _initialized: ClassVar[Set] = set()

    # Unique per instance
    _source: Dict[str, str] = field(default_factory=dict)
    _modified: Set[str] = field(default_factory=set)
    _validation_errors: Dict[str, "ValidationError"] = field(default_factory=dict)
    _file_path: Path | None = None

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls not in ConfigBase._initialized:
            ConfigBase._initialized.add(cls)
            dataclass()(cls)

    def __post__init__(self):
        self._init_tracking()

    def __setattr__(self, name, value):
        # noinspection PyTypeChecker
        matching_fields = list(f for f in fields(self) if name == f.name)
        if len(matching_fields) == 0:
            return super().__setattr__(name, value)
        fld = matching_fields[0]

        if not hasattr(self, name) or value == getattr(self, name):
            return super().__setattr__(name, value)

        if not fld.metadata.get(FIELD_MODIFIABLE, True):
            raise AttributeError(f"Field '{name}' is not modifiable")

        errors = self.validate_field(fld, value)
        self._validation_errors[fld.name] = errors
        if VALIDATION_ERRORS_ON_SETATTR and len(errors):
            msg = "\n".join(f"- {m}" for m in errors)
            raise ValueError(f"Validation failed:\n{msg}")

        old = getattr(self, name, None)
        if old != value:
            self._modified.add(name)

        return super().__setattr__(name, value)

    @staticmethod
    def validate_field(fld: Field[Any], value: Any, raise_error=False) -> List[str]:
        validators = fld.metadata.get(FIELD_VALIDATORS, [])
        errors = []
        for v in validators:
            errors += v(value)
        if raise_error and len(errors):
            msg = "\n".join(f"- {m}" for m in errors)
            raise ValueError(f"Validation failed:\n{msg}")

        return errors

    def _set_silently(self, name: str, value):
        object.__setattr__(self, name, value)

    def _init_tracking(self):
        # noinspection PyTypeChecker
        for f in fields(self):
            if f.name.startswith("_"):
                continue
            self._source.setdefault(f.name, DEFAULT_SOURCE)

    @classmethod
    def _get_field_type(cls, f: Field[Any]):
        cls_types = get_type_hints(cls)
        if isinstance(f.type, str):
            return cls_types.get(f.name, str)
        return f.type

    @staticmethod
    def _is_config(f: Field[Any]):
        return f.default_factory != MISSING and issubclass(f.default_factory, ConfigBase)

    @classmethod
    def add_argument_group(
        cls,
        parser: argparse.ArgumentParser,
        namespace: str = "",
        description: str = None,
    ):
        group = parser
        if namespace:
            group = parser.add_argument_group(title=namespace, description=description)

        # noinspection PyTypeChecker
        for f in fields(cls):
            help_text = f.metadata.get(FIELD_HELP_TEXT, None)
            arg = f.metadata.get(FIELD_ARG, None)

            name = f.name

            if name.startswith("_"):
                continue

            if not arg:
                continue

            if arg == AUTO_ARG:
                arg = "--" + name.replace("_", "-")

            name = name
            f_type = cls._get_field_type(f)

            if cls._is_config(f):
                f.default_factory.add_argument_group(
                    group,
                    namespace=f"{namespace}.{name}" if arg == AUTO_ARG else arg,
                    description=help_text,
                )
            elif f_type is bool:
                parser.add_argument(
                    arg, dest=name, action="store_true", default=argparse.SUPPRESS, help=help_text
                )
            else:
                parser.add_argument(arg, dest=name, type=f_type, default=argparse.SUPPRESS, help=help_text)

    @classmethod
    def get_argument_parser(cls, *args, **kwargs) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(*args, **kwargs)
        cls.add_argument_group(parser)
        return parser

    def _iter_fields(self, include_defaults: bool, only_serializable: bool = False):
        for f in fields(self):
            name = f.name
            if name.startswith("_"):
                continue

            source = self._source.get(name, DEFAULT_SOURCE)
            if not include_defaults and source == DEFAULT_SOURCE:
                continue

            value = getattr(self, name)
            comment = f.metadata.get(FIELD_HELP_TEXT)
            serializer = f.metadata.get(FIELD_SERIALIZER, do_not_serialize_serializer)
            if only_serializable and serializer == do_not_serialize_serializer:
                continue
            yield name, f, value, comment, serializer, source

    def _walk(self, include_defaults: bool) -> Iterator[Node]:
        for name, f, value, comment, serializer, source in self._iter_fields(include_defaults):
            if self._is_config(f):
                # recurse into child config
                value: ConfigBase
                yield TableNode(
                    name=name,
                    help_text=comment,
                    children=value._walk(include_defaults),
                )
            else:
                serialized = serializer(value)
                if serialized is not DO_NOT_SERIALIZE:
                    yield ScalarNode(name=name, value=serialized, help_text=comment, source=source)

    def as_dict(self, include_defaults: bool = False) -> dict:
        def build(nodes: Iterable[Node]) -> dict:
            out: dict[str, Any] = {}
            for node in nodes:
                if isinstance(node, TableNode):
                    out[node.name] = build(node.children)
                else:  # ScalarNode
                    out[node.name] = node.value
            return out

        return build(self._walk(include_defaults))

    def as_toml(
        self, include_defaults: bool, comment: Literal[None, "help_text", "source"] = None, _table=None
    ):
        def fill(table, nodes: Iterable[Node]) -> None:
            for node in nodes:
                if isinstance(node, TableNode):
                    node: TableNode
                    sub = tomlkit.table()
                    fill(sub, node.children)
                    table.add(node.name, sub)

                    if comment == "help_text" and node.help_text:
                        table[node.name].comment(node.help_text)
                else:
                    node: ScalarNode
                    item = tomlkit.item("" if node.value is None else node.value)
                    if comment == "help_text" and node.help_text:
                        item.comment(node.help_text)
                    elif comment == "source":
                        item.comment(str(node.source))

                    table.add(node.name, item)

        doc = _table or tomlkit.document()
        fill(doc, self._walk(include_defaults))
        return doc

    @classmethod
    def from_args(cls, args: argparse.Namespace = None, argv: list[str] = None):
        if args is None:
            parser = cls.get_argument_parser()
            args = parser.parse_args(argv or None)

        cfg = cls()
        # noinspection PyTypeChecker
        for f in fields(cls):
            if cls._is_config(f):
                val = f.default_factory.from_args(args, argv)
                setattr(cfg, f.name, val)
                cfg._source[f.name] = "arg"
            elif hasattr(args, f.name):
                val = getattr(args, f.name)
                if val is not None:
                    setattr(cfg, f.name, val)
                    cfg._source[f.name] = "arg"

        return cfg

    @classmethod
    def from_file(cls, file: Path | str) -> Self:
        loaded = tomlkit.loads(file.read_text(encoding="utf-8"))
        cfg = cls.from_dict(loaded, source=file)
        cfg._file_path = file
        return cfg

    def get_file_path(self) -> Path | None:
        return self._file_path

    @classmethod
    def from_dict(cls, loaded: Serializable, validate: bool = False, source: Any = "from_dict") -> Self:
        cfg = cls()
        # noinspection PyTypeChecker
        for fld in fields(cls):
            name = fld.name
            if name in loaded:
                if cls._is_config(fld):
                    instance: ConfigBase = cls._get_field_type(fld).from_dict(loaded[name], source=source)
                    setattr(cfg, name, instance)
                    if len(instance._modified) > 0:
                        cfg._modified.add(name)
                else:
                    setattr(cfg, name, cls._get_field_type(fld)(loaded[name]))
                    cfg._modified.add(name)

                cfg._source[name] = source
        return cfg

    def save(self, path: Path | str = None, include_defaults=False, include_comments=True):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        doc = self.as_toml(include_defaults=include_defaults, include_comments=include_comments)

        path.write_text(tomlkit.dumps(doc), encoding="utf-8")

    def update_from(self: Self, other: Self) -> Self:
        if not isinstance(other, type(self)):
            raise TypeError(f"'other' must be {type(self).__name__}")

        for f in fields(self):
            name = f.name

            my_val = getattr(self, name)
            their_val = getattr(other, name, None)

            if name == "discord_webhook_url":
                pass

            if self._is_config(f):
                if their_val is not None:
                    my_val.update_from(their_val)
                continue

            if name.startswith("_"):
                continue

            if not f.metadata.get(FIELD_MODIFIABLE, True):
                continue

            if name not in other._modified:
                continue

            if my_val != their_val:
                self._set_silently(name, their_val)
            self._source[name] = other._source.get(name, "merge")
            self._modified.add(name)

        return self

    def validate_all(self, raise_error: bool = True) -> Tuple[ValidationError, str]:
        # noinspection PyTypeChecker
        for f in fields(self):
            if self._is_config(f):
                cfg: ConfigBase = getattr(self, f.name)
                self._validation_errors[f.name], _ = cfg.validate_all(raise_error=False)

            self._validation_errors[f.name] = self.validate_field(
                f, getattr(self, f.name, None), raise_error=False
            )

        if validation_message := self._get_validation_message(self._validation_errors):
            if raise_error:
                raise ValueError(validation_message)

        return self._validation_errors, validation_message

    @staticmethod
    def _get_validation_message(
        validation_errors: Dict[str, ValidationError], prefix: str = ""
    ) -> str | None:
        message = ""
        for name, errors in validation_errors.items():
            if len(errors) == 0:
                continue
            message += f"{prefix}{name}:\n"
            if isinstance(errors, list):
                for error in errors:
                    message += f"{prefix}  - {error}\n"
            elif isinstance(errors, dict):
                message += ConfigBase._get_validation_message(validation_errors, prefix=prefix + "  ")
            else:
                raise ValueError(
                    f"Unexpected type: ({type(errors)}) '{errors}'",
                )

        if message:
            return "There are some validation errors:\n" + message

        return None


def get_config_file(
    path: Path | str = None, filename: str = "config.toml", user_config: bool = False, app_name: str = None
) -> Path:
    app_name = app_name or get_app_name()
    if path is not None:
        file = Path(path)
    elif user_config:
        file = Path(user_config_dir(app_name, appauthor=False)) / filename
    else:
        file = Path("../") / f"{app_name}.{filename}"

    file.parent.mkdir(parents=True, exist_ok=True)
    return file


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
