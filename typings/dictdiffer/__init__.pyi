from collections.abc import Iterable, Iterator, Mapping
from typing import Any, TypeVar

_T = TypeVar("_T")
Diff = tuple[str, str, Any]

def diff(
    first: Mapping[str, Any],
    second: Mapping[str, Any],
    node: str | None = ...,
    ignore: Iterable[str] | None = ...,
    path_limit: Any = ...,
    expand: bool = ...,
    tolerance: float = ...,
    absolute_tolerance: float | None = ...,
    dot_notation: bool = ...,
) -> Iterator[Diff]: ...
def patch(diff_result: Iterable[Diff], destination: _T, in_place: bool = ...) -> _T: ...
