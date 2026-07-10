from __future__ import annotations

import re
import typing as T

from cxxheaderparser.types import (
    Array,
    DecoratedType,
    FunctionType,
    FundamentalSpecifier,
    MoveReference,
    NameSpecifier,
    Pointer,
    Reference,
    TemplateArgument,
    Type,
    Value,
)

from .buffer import RenderBuffer

_INT_TYPES = frozenset(
    [
        "bool",
        "char",
        "char8_t",
        "char16_t",
        "char32_t",
        "double",
        "float",
        "int",
        "long",
        "short",
        "signed",
        "unsigned",
        "void",
        "wchar_t",
        "size_t",
        "ssize_t",
        "ptrdiff_t",
        "intmax_t",
        "uintmax_t",
    ]
    + [
        f"{prefix}{middle}{bits}_t"
        for prefix in ("int", "uint")
        for middle in ("", "_fast", "_least")
        for bits in ("8", "16", "32", "64")
    ]
)

_SANITIZE_RE = re.compile(r"[^0-9A-Za-z]+")


def _is_builtin_type(t: Type) -> bool:
    last = t.typename.segments[-1]
    if isinstance(last, FundamentalSpecifier):
        return True
    if isinstance(last, NameSpecifier) and len(t.typename.segments) == 1:
        return last.name in _INT_TYPES
    return False


def _target_from_type(t: Type) -> str | None:
    if _is_builtin_type(t):
        return None
    if not all(isinstance(seg, NameSpecifier) for seg in t.typename.segments):
        return None

    target = t.typename.format()
    if target.startswith("::"):
        return None
    if target.startswith(("std::", "py::", "pybind11::", "semiwrap::", "swgen::")):
        return None
    return target


def _collect_from_template_args(t: Type, out: list[str]) -> None:
    for segment in t.typename.segments:
        if not isinstance(segment, NameSpecifier) or segment.specialization is None:
            continue
        for arg in segment.specialization.args:
            _collect_from_template_arg(arg, out)


def _collect_from_template_arg(arg: TemplateArgument, out: list[str]) -> None:
    value = arg.arg
    if isinstance(value, Value):
        return
    collect_typealias_probes_into(value, out)


def add_typealias_probe(probes: list[str], target: str) -> None:
    if target and target not in probes:
        probes.append(target)
        probes.sort()


def collect_typealias_probes_into(
    dt: DecoratedType | FunctionType | None, out: list[str]
) -> None:
    if dt is None:
        return
    if isinstance(dt, Type):
        target = _target_from_type(dt)
        if target is not None:
            add_typealias_probe(out, target)
        _collect_from_template_args(dt, out)
    elif isinstance(dt, Pointer):
        collect_typealias_probes_into(dt.ptr_to, out)
    elif isinstance(dt, Reference):
        collect_typealias_probes_into(dt.ref_to, out)
    elif isinstance(dt, MoveReference):
        collect_typealias_probes_into(dt.moveref_to, out)
    elif isinstance(dt, Array):
        collect_typealias_probes_into(dt.array_of, out)
    elif isinstance(dt, FunctionType):
        collect_typealias_probes_into(dt.return_type, out)
        for param in dt.parameters:
            collect_typealias_probes_into(param.type, out)


def collect_typealias_probes(dt: DecoratedType | FunctionType | None) -> list[str]:
    probes: list[str] = []
    collect_typealias_probes_into(dt, probes)
    return probes


def probe_alias_name(target: str) -> str:
    safe_target = target.replace("::", "_scope_")
    safe = _SANITIZE_RE.sub("_", safe_target).strip("_")
    if not safe:
        safe = "unknown"
    return f"semiwrap_typealias_probe_{safe}__add_typealias_to_yaml"


def render_typealias_probes(
    r: RenderBuffer, probes: T.Sequence[str], *, indent: str = ""
) -> None:
    for target in sorted(probes):
        alias = probe_alias_name(target)
        r.writeln(
            f"{indent}// semiwrap diagnostic: if this line fails because `{target}` "
            "is unknown,"
        )
        r.writeln(
            f"{indent}// add a typealias entry for `{target}` to the semiwrap yaml file."
        )
        r.writeln(f"{indent}using {alias} [[maybe_unused]] = {target};")
