import dataclasses
import functools
import importlib
import re
import typing

NameKind = typing.Literal["function", "method", "attribute", "enum_value"]
NameTransform = typing.Callable[[str, NameKind], str]


@dataclasses.dataclass(frozen=True)
class NameTransformConfig:
    """
    Per-kind ``name_transform`` mapping.

    Each field is a transform spec such as ``default``, ``snake_case``,
    ``camelCase``, or ``custom: package.name:function``. When a field is
    omitted, the next lower-precedence configuration value is used.
    """

    # Optional here preserves whether a higher-precedence mapping omitted default.
    # Final resolution treats None as "default".

    #: Transform applied to all kinds unless a kind-specific transform is set.
    default: typing.Optional[str] = None

    #: Transform applied to namespace-scope functions.
    function: typing.Optional[str] = None

    #: Transform applied to class methods.
    method: typing.Optional[str] = None

    #: Transform applied to attributes and properties.
    attribute: typing.Optional[str] = None

    #: Transform applied to enum values after semiwrap's enum prefix stripping.
    enum_value: typing.Optional[str] = None


NameTransformSpec = typing.Optional[typing.Union[str, NameTransformConfig]]


@dataclasses.dataclass(frozen=True)
class NameTransforms:
    function: NameTransform
    method: NameTransform
    attribute: NameTransform
    enum_value: NameTransform


_WORD_RE = re.compile(r"[A-Z]+(?=[A-Z][a-z]|[0-9]|_|$)|[A-Z]?[a-z]+|[0-9]+|[A-Z]+")


def _split_words(name: str) -> typing.List[str]:
    words: typing.List[str] = []
    for part in name.replace("-", "_").split("_"):
        if not part:
            continue
        words.extend(m.group(0) for m in _WORD_RE.finditer(part))
    return words or [name]


def _cap(word: str) -> str:
    if not word:
        return word
    return word[:1].upper() + word[1:].lower()


def none_transform(name: str, kind: NameKind) -> str:
    return name


def default_transform(name: str, kind: NameKind) -> str:
    if kind in ("function", "method") and not name[:2].isupper():
        return f"{name[0].lower()}{name[1:]}"
    return name


def camel_case_transform(name: str, kind: NameKind) -> str:
    words = _split_words(name)
    return words[0].lower() + "".join(_cap(w) for w in words[1:])


def snake_case_transform(name: str, kind: NameKind) -> str:
    return "_".join(w.lower() for w in _split_words(name))


def pascal_case_transform(name: str, kind: NameKind) -> str:
    return "".join(_cap(w) for w in _split_words(name))


def caps_case_transform(name: str, kind: NameKind) -> str:
    return "_".join(w.upper() for w in _split_words(name))


_BUILTINS: typing.Dict[str, NameTransform] = {
    "none": none_transform,
    "default": default_transform,
    "camelCase": camel_case_transform,
    "snake_case": snake_case_transform,
    "PascalCase": pascal_case_transform,
    "CAPS_CASE": caps_case_transform,
}


_NAME_TRANSFORM_FIELDS = ("function", "method", "attribute", "enum_value")


def normalize_name_transform_config(spec: NameTransformSpec) -> NameTransformConfig:
    if spec is None:
        return NameTransformConfig()
    if isinstance(spec, str):
        return NameTransformConfig(
            default=spec,
            function=spec,
            method=spec,
            attribute=spec,
            enum_value=spec,
        )
    if isinstance(spec, NameTransformConfig):
        return spec
    raise TypeError(f"invalid name_transform {spec!r}")


def merge_name_transform_configs(
    lower: NameTransformSpec,
    higher: NameTransformSpec,
) -> NameTransformConfig:
    lower_cfg = normalize_name_transform_config(lower)
    if higher is None:
        return lower_cfg
    higher_cfg = normalize_name_transform_config(higher)
    return NameTransformConfig(
        default=(
            higher_cfg.default if higher_cfg.default is not None else lower_cfg.default
        ),
        function=(
            higher_cfg.function
            if higher_cfg.function is not None
            else lower_cfg.function
        ),
        method=higher_cfg.method if higher_cfg.method is not None else lower_cfg.method,
        attribute=(
            higher_cfg.attribute
            if higher_cfg.attribute is not None
            else lower_cfg.attribute
        ),
        enum_value=(
            higher_cfg.enum_value
            if higher_cfg.enum_value is not None
            else lower_cfg.enum_value
        ),
    )


def resolve_name_transforms(spec: NameTransformSpec) -> NameTransforms:
    cfg = normalize_name_transform_config(spec)
    default_spec = cfg.default or "default"

    function_spec = cfg.function or default_spec
    method_spec = cfg.method or default_spec
    attribute_spec = cfg.attribute or default_spec
    enum_value_spec = cfg.enum_value or default_spec

    return NameTransforms(
        function=resolve_name_transform(function_spec),
        method=resolve_name_transform(method_spec),
        attribute=resolve_name_transform(attribute_spec),
        enum_value=resolve_name_transform(enum_value_spec),
    )


def name_transform_config_to_args(spec: NameTransformSpec) -> typing.List[str]:
    cfg = normalize_name_transform_config(spec)
    args: typing.List[str] = []
    if cfg.default is not None:
        args.extend(["--name-transform-default", cfg.default])
    if cfg.function is not None:
        args.extend(["--name-transform-function", cfg.function])
    if cfg.method is not None:
        args.extend(["--name-transform-method", cfg.method])
    if cfg.attribute is not None:
        args.extend(["--name-transform-attribute", cfg.attribute])
    if cfg.enum_value is not None:
        args.extend(["--name-transform-enum-value", cfg.enum_value])
    return args


@functools.lru_cache(maxsize=None)
def resolve_name_transform(spec: str) -> NameTransform:
    try:
        return _BUILTINS[spec]
    except KeyError:
        pass

    if spec.startswith("custom:"):
        return _resolve_custom_name_transform(spec)

    raise ValueError(f"unknown name_transform {spec!r}")


def _resolve_custom_name_transform(spec: str) -> NameTransform:
    target = spec[len("custom:") :].strip()
    module_name, sep, attr_name = target.partition(":")
    if not module_name or not sep or not attr_name:
        raise ValueError(
            f"invalid custom name_transform {spec!r}; expected custom: package.name:function"
        )

    try:
        module = importlib.import_module(module_name)
    except Exception as e:
        raise ValueError(
            f"could not import custom name_transform module {module_name!r}"
        ) from e

    try:
        obj = getattr(module, attr_name)
    except AttributeError as e:
        raise ValueError(
            f"custom name_transform {spec!r} does not define {attr_name!r}"
        ) from e

    if not callable(obj):
        raise ValueError(f"custom name_transform {spec!r} is not callable")

    def wrapper(name: str, kind: NameKind) -> str:
        result = obj(name, kind)
        if not isinstance(result, str):
            raise TypeError(
                f"custom name_transform {spec!r} returned {type(result).__name__}, expected str"
            )
        return result

    return wrapper
