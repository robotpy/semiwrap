from pathlib import Path
from types import SimpleNamespace

import pytest

from semiwrap.autowrap.render_wrapped import _resolve_inline_code_namespace


def test_inline_code_requires_namespace_for_multiple_targets():
    hctx = SimpleNamespace(
        inline_code='m.def("custom", []() {});',
        inline_code_namespace=None,
        enums=[SimpleNamespace(namespace="alpha")],
        classes=[SimpleNamespace(namespace="beta")],
        template_instances=[],
        functions=[],
        orig_yaml=Path("mixed.yml"),
    )

    with pytest.raises(ValueError) as exc_info:
        _resolve_inline_code_namespace(hctx)

    assert str(exc_info.value) == (
        "mixed.yml: inline_code has multiple target namespaces "
        "('alpha', 'beta'); specify inline_code_namespace"
    )
