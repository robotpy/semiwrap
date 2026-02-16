import codecs
import pathlib
import re
import typing as T

from .util import relpath_walk_up

# String escaping stolen from meson source code, Apache 2.0 license
# This is the regex for the supported escape sequences of a regular string
# literal, like 'abc\x00'
ESCAPE_SEQUENCE_SINGLE_RE = re.compile(
    r"""
    ( \\U[A-Fa-f0-9]{8}   # 8-digit hex escapes
    | \\u[A-Fa-f0-9]{4}   # 4-digit hex escapes
    | \\x[A-Fa-f0-9]{2}   # 2-digit hex escapes
    | \\[0-7]{1,3}        # Octal escapes
    | \\N\{[^}]+\}        # Unicode characters by name
    | \\[\\'abfnrtv]      # Single-character escapes
    )""",
    re.UNICODE | re.VERBOSE,
)


def _decode_match(match: T.Match[str]) -> str:
    return codecs.decode(match.group(0).encode(), "unicode_escape")


def make_meson_string(s: str) -> str:
    s = ESCAPE_SEQUENCE_SINGLE_RE.sub(_decode_match, s)
    return f"'{s}'"


def make_include_path_str(
    pth: pathlib.Path, meson_build_path: T.Optional[pathlib.Path]
) -> str:
    """
    Returns a string containing a path suitable for use with include_directories
    """
    # meson wants these to be relative to meson.build
    # - only can do that if we're writing an output file
    if meson_build_path:
        pth = relpath_walk_up(pth, meson_build_path.parent)

    return make_meson_string(pth.as_posix())
