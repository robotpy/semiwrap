import dataclasses
import functools
import importlib
import re
import typing

NameKind = typing.Literal["function", "method", "attribute", "enum_value", "parameter"]
NameTransform = typing.Callable[[str, NameKind], str]
KnownWords = typing.Sequence[str]


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

    #: Transform applied to function and method parameter names.
    parameter: typing.Optional[str] = None

    #: Case-sensitive known words used by built-in case transforms when splitting words.
    known_words: typing.Optional[typing.List[str]] = None


NameTransformSpec = typing.Optional[typing.Union[str, NameTransformConfig]]


@dataclasses.dataclass(frozen=True)
class NameTransforms:
    function: NameTransform
    method: NameTransform
    attribute: NameTransform
    enum_value: NameTransform
    parameter: NameTransform


_WORD_RE = re.compile(r"[A-Z]+(?=[A-Z][a-z]|[0-9]|_|$)|[A-Z]?[a-z]+|[0-9]+|[A-Z]+")


def _split_underscore_affixes(name: str) -> typing.Tuple[str, str, str]:
    leading_len = len(name) - len(name.lstrip("_"))
    if leading_len == len(name):
        return name, "", ""

    trailing_len = len(name) - len(name.rstrip("_"))
    prefix = name[:leading_len]
    suffix = name[len(name) - trailing_len :] if trailing_len else ""
    core = name[leading_len : len(name) - trailing_len if trailing_len else len(name)]
    return prefix, core, suffix


def _transform_underscore_core(
    name: str, transform: typing.Callable[[str], str]
) -> str:
    prefix, core, suffix = _split_underscore_affixes(name)
    if not core:
        return name
    return f"{prefix}{transform(core)}{suffix}"


def _normalize_known_words(
    known_words: typing.Optional[KnownWords],
) -> typing.Tuple[str, ...]:
    if not known_words:
        return ()
    return tuple(sorted({a for a in known_words if a}, key=len, reverse=True))


def _split_words_no_known_words(name: str) -> typing.List[str]:
    words: typing.List[str] = []
    for part in name.replace("-", "_").split("_"):
        if not part:
            continue
        words.extend(m.group(0) for m in _WORD_RE.finditer(part))
    return words or [name]


def _is_known_word_boundary_match(part: str, known_word: str, pos: int) -> bool:
    if not part.startswith(known_word, pos):
        return False

    start_ok = pos == 0 or not part[pos - 1].isupper()
    if not start_ok:
        return False

    end = pos + len(known_word)
    if end == len(part):
        return True

    next_char = part[end]
    if not next_char.isupper():
        return True

    return end + 1 < len(part) and part[end + 1].islower()


def _known_word_match_word(
    part: str, known_word: str, pos: int
) -> typing.Optional[str]:
    if not _is_known_word_boundary_match(part, known_word, pos):
        return None

    end = pos + len(known_word)
    if (
        end < len(part)
        and part[end] == "s"
        and (end + 1 == len(part) or not part[end + 1].islower())
    ):
        return part[pos : end + 1]

    return known_word


def _split_part_with_known_words(
    part: str, known_words: typing.Tuple[str, ...]
) -> typing.List[str]:
    words: typing.List[str] = []
    pos = 0
    segment_start = 0

    while pos < len(part):
        match = None
        for known_word in known_words:
            match = _known_word_match_word(part, known_word, pos)
            if match is not None:
                break

        if match is None:
            pos += 1
            continue

        if segment_start < pos:
            words.extend(_split_words_no_known_words(part[segment_start:pos]))
        words.append(match)
        pos += len(match)
        segment_start = pos

    if segment_start < len(part):
        words.extend(_split_words_no_known_words(part[segment_start:]))

    return words


def _strip_k_camel_prefix(name: str) -> str:
    if len(name) >= 2 and name[0] == "k" and name[1].isupper():
        return name[1:]
    return name


def _split_words(
    name: str, known_words: typing.Optional[KnownWords] = None
) -> typing.List[str]:
    name = _strip_k_camel_prefix(name)
    normalized_known_words = _normalize_known_words(known_words)
    if not normalized_known_words:
        return _split_words_no_known_words(name)

    words: typing.List[str] = []
    for part in name.replace("-", "_").split("_"):
        if not part:
            continue
        words.extend(_split_part_with_known_words(part, normalized_known_words))
    return words or [name]


def _cap(word: str) -> str:
    if not word:
        return word
    return word[:1].upper() + word[1:].lower()


def none_transform(
    name: str, kind: NameKind, known_words: typing.Optional[KnownWords] = None
) -> str:
    return name


def default_transform(
    name: str, kind: NameKind, known_words: typing.Optional[KnownWords] = None
) -> str:
    def transform_core(core: str) -> str:
        if kind in ("function", "method") and not core[:2].isupper():
            return f"{core[0].lower()}{core[1:]}"
        return core

    return _transform_underscore_core(name, transform_core)


def camel_case_transform(
    name: str, kind: NameKind, known_words: typing.Optional[KnownWords] = None
) -> str:
    def transform_core(core: str) -> str:
        words = _split_words(core, known_words)
        return words[0].lower() + "".join(_cap(w) for w in words[1:])

    return _transform_underscore_core(name, transform_core)


def snake_case_transform(
    name: str, kind: NameKind, known_words: typing.Optional[KnownWords] = None
) -> str:
    return _transform_underscore_core(
        name, lambda core: "_".join(w.lower() for w in _split_words(core, known_words))
    )


def pascal_case_transform(
    name: str, kind: NameKind, known_words: typing.Optional[KnownWords] = None
) -> str:
    return _transform_underscore_core(
        name, lambda core: "".join(_cap(w) for w in _split_words(core, known_words))
    )


def k_camel_case_transform(
    name: str, kind: NameKind, known_words: typing.Optional[KnownWords] = None
) -> str:
    return _transform_underscore_core(
        name,
        lambda core: "k" + "".join(_cap(w) for w in _split_words(core, known_words)),
    )


def caps_case_transform(
    name: str, kind: NameKind, known_words: typing.Optional[KnownWords] = None
) -> str:
    return _transform_underscore_core(
        name, lambda core: "_".join(w.upper() for w in _split_words(core, known_words))
    )


_BUILTINS: typing.Dict[str, NameTransform] = {
    "none": none_transform,
    "default": default_transform,
    "camelCase": camel_case_transform,
    "snake_case": snake_case_transform,
    "PascalCase": pascal_case_transform,
    "kCamelCase": k_camel_case_transform,
    "CAPS_CASE": caps_case_transform,
}


_NAME_TRANSFORM_FIELDS = ("function", "method", "attribute", "enum_value", "parameter")


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
            parameter=spec,
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
        parameter=(
            higher_cfg.parameter
            if higher_cfg.parameter is not None
            else lower_cfg.parameter
        ),
        known_words=(
            higher_cfg.known_words
            if higher_cfg.known_words is not None
            else lower_cfg.known_words
        ),
    )


def resolve_name_transforms(
    spec: NameTransformSpec,
    known_words: typing.Optional[KnownWords] = None,
) -> NameTransforms:
    cfg = normalize_name_transform_config(spec)
    default_spec = cfg.default or "default"
    selected_known_words = known_words if known_words is not None else cfg.known_words

    function_spec = cfg.function or default_spec
    method_spec = cfg.method or default_spec
    attribute_spec = cfg.attribute or default_spec
    enum_value_spec = cfg.enum_value or default_spec
    parameter_spec = cfg.parameter or default_spec

    return NameTransforms(
        function=resolve_name_transform(function_spec, selected_known_words),
        method=resolve_name_transform(method_spec, selected_known_words),
        attribute=resolve_name_transform(attribute_spec, selected_known_words),
        enum_value=resolve_name_transform(enum_value_spec, selected_known_words),
        parameter=resolve_name_transform(parameter_spec, selected_known_words),
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
    if cfg.parameter is not None:
        args.extend(["--name-transform-parameter", cfg.parameter])
    if cfg.known_words is not None:
        for known_word in cfg.known_words:
            args.extend(["--name-transform-known-word", known_word])
    return args


@functools.lru_cache(maxsize=None)
def _resolve_name_transform(spec: str) -> NameTransform:
    try:
        return _BUILTINS[spec]
    except KeyError:
        pass

    if spec.startswith("custom:"):
        return _resolve_custom_name_transform(spec)

    raise ValueError(f"unknown name_transform {spec!r}")


def resolve_name_transform(
    spec: str, known_words: typing.Optional[KnownWords] = None
) -> NameTransform:
    transform = _resolve_name_transform(spec)
    normalized_known_words = _normalize_known_words(known_words)
    if not normalized_known_words or spec not in _BUILTINS:
        return transform

    def wrapper(name: str, kind: NameKind) -> str:
        result = transform(name, kind, normalized_known_words)  # type: ignore[misc]
        if not isinstance(result, str):
            raise TypeError(
                f"name_transform {spec!r} returned {type(result).__name__}, expected str"
            )
        return result

    return wrapper


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
