from contextlib import contextmanager
import typing

from .buffer import RenderBuffer


@contextmanager
def suppress_deprecated(r: RenderBuffer, enabled: bool) -> typing.Iterator[None]:
    if enabled:
        r.writeln("SEMIWRAP_SUPPRESS_DEPRECATED_BEGIN")
    try:
        yield
    finally:
        if enabled:
            r.writeln("SEMIWRAP_SUPPRESS_DEPRECATED_END")
