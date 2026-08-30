import contextlib
import typing

from .buffer import RenderBuffer

GENERATED_NAMESPACE = "semiwrap_generated"


def normalize_namespace(namespace: str) -> str:
    return namespace.strip(":")


def generated_namespace(namespace: str) -> str:
    namespace = normalize_namespace(namespace)
    if namespace:
        return f"{namespace}::{GENERATED_NAMESPACE}"
    return GENERATED_NAMESPACE


def generated_qualname(namespace: str, name: str) -> str:
    return f"{generated_namespace(namespace)}::{name}"


@contextlib.contextmanager
def namespace_scope(
    r: RenderBuffer,
    namespace: str,
    *,
    generated: bool = False,
    anonymous: bool = False,
) -> typing.Iterator[None]:
    namespace = normalize_namespace(namespace)
    opened = []
    if namespace:
        r.writeln(f"namespace {namespace} {{")
        opened.append(namespace)
    if generated:
        r.writeln(f"namespace {GENERATED_NAMESPACE} {{")
        opened.append(GENERATED_NAMESPACE)
    if anonymous:
        r.writeln("namespace {")
        opened.append("")
    try:
        if opened:
            r.writeln()
            yield
            r.writeln()
        else:
            yield
    finally:
        for name in reversed(opened):
            if name:
                r.writeln(f"}} // namespace {name}")
            else:
                r.writeln("} // namespace")
