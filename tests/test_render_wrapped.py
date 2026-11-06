from pathlib import Path
from types import SimpleNamespace

import pytest
from cxxheaderparser.options import ParserOptions

from semiwrap.autowrap.cxxparser import parse_header
from semiwrap.autowrap.generator_data import GeneratorData
from semiwrap.autowrap.render_wrapped import (
    _resolve_inline_code_namespace,
    render_wrapped_cpp,
)
from semiwrap.config.autowrap_yml import AutowrapConfigYaml, EnumData


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


def _render_enums(tmp_path, hname, source):
    header = tmp_path / f"{hname}.h"
    header.write_text(source)
    config = AutowrapConfigYaml(enums={"FieldId": EnumData(rename="Field")})
    hctx = parse_header(
        hname,
        header,
        tmp_path,
        GeneratorData(config, tmp_path / f"{hname}.yml"),
        ParserOptions(),
        {},
        False,
    )
    return render_wrapped_cpp(hctx)


@pytest.mark.parametrize("enum_kind", ["enum", "enum class"])
@pytest.mark.parametrize(
    "namespace,identifier,qualifier,cpp_name",
    [
        ("", "__FieldId", "::", "::FieldId"),
        (
            "wpi::fields",
            "wpi__fields__FieldId",
            "::wpi::fields::",
            "wpi::fields::FieldId",
        ),
    ],
)
def test_named_enum_helpers_are_stable(
    tmp_path, enum_kind, namespace, identifier, qualifier, cpp_name
):
    source = f"{enum_kind} FieldId {{ Value = 1 }};"
    if namespace:
        source = f"namespace {namespace} {{ {source} }}"

    # Neither the header name, declaration order, nor Python rename should
    # change the C++ names available to handwritten bindings.
    for hname, prefix in [("fields", ""), ("renamed", "enum Other { OtherValue };\n")]:
        rendered = _render_enums(tmp_path, hname, prefix + source)
        helper = f"semiwrap_enum_{identifier}"
        helper_var = f"semiwrap_enum_helper_{identifier}"
        assert f"struct {helper} {{" in rendered
        assert f"{qualifier}{helper} {helper_var};" in rendered
        assert f"py::enum_<{cpp_name}> enum_FieldId;" in rendered
        assert f"decltype({helper_var}.enum_FieldId) &enum_FieldId;" in rendered
        assert f"{helper_var}(m, m)," in rendered
        assert f"enum_FieldId({helper_var}.enum_FieldId)," in rendered
        assert 'enum_FieldId(scope, "Field")' in rendered
        assert f"{helper_var}.finish();" in rendered
        assert 'enum_FieldId\n      .value("Value",' in rendered


def test_anonymous_enum_helpers_keep_indexed_names(tmp_path):
    rendered = _render_enums(
        tmp_path, "anonymous", "enum { First = 1 }; enum { Second = 2 };"
    )
    for index in (1, 2):
        assert f"struct semiwrap_enum_anonymous_{index} {{" in rendered
        assert f"::semiwrap_enum_anonymous_{index} enum{index};" in rendered
        assert f"enum{index}(m, m)," in rendered
        assert f"enum{index}.finish();" in rendered
