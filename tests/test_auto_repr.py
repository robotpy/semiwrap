"""Structural eligibility must reflect C++ declarations, not filtered bindings."""

import pytest
import yaml
from cxxheaderparser.options import ParserOptions

from semiwrap.autowrap.buffer import RenderBuffer
from semiwrap.autowrap.cxxparser import parse_header
from semiwrap.autowrap.generator_data import GeneratorData
from semiwrap.autowrap.render_pybind11 import cls_def
from semiwrap.config.autowrap_yml import AutowrapConfigYaml


def _parse(tmp_path, source, settings=None):
    header = tmp_path / "repr.h"
    header.write_text(source)
    yml = tmp_path / "repr.yml"
    yml.write_text(yaml.safe_dump({"classes": {"Data": settings or {}}}))
    config = AutowrapConfigYaml.from_file(yml)
    return parse_header(
        "repr", header, tmp_path, GeneratorData(config, yml), ParserOptions(), {}, False
    ).classes[0]


@pytest.mark.parametrize(
    "source",
    [
        "struct Data { int value; };",
        "class Data { public: int value; };",
        "struct Data {};",
        "struct Data { int value = 3; static int count; };",
        "struct Data { int value; private: static int count; };",
    ],
)
@pytest.mark.parametrize("settings", [{}, {"auto_repr": None}, {"auto_repr": True}])
def test_plain_data_qualifies(tmp_path, source, settings):
    assert _parse(tmp_path, source, settings).auto_repr


@pytest.mark.parametrize(
    "member",
    [
        "void method();",
        "static void method();",
        "private: void method();",
        "protected: void method();",
        "Data() = default;",
        "Data(int);",
        "Data(const Data&) = delete;",
        "~Data() = default;",
        "operator bool() const;",
        "private: int hidden;",
        "protected: int hidden;",
    ],
)
@pytest.mark.parametrize("auto_repr", [None, False, True])
def test_auto_repr_setting_controls_non_data_declarations(tmp_path, member, auto_repr):
    ctx = _parse(
        tmp_path,
        "struct Data { int value; " + member + " };",
        {"auto_repr": auto_repr},
    )
    assert ctx.auto_repr is (auto_repr is True)


@pytest.mark.parametrize(
    "settings,expected", [({}, False), ({"auto_repr": True}, True)]
)
def test_ignored_method_respects_auto_repr_setting(tmp_path, settings, expected):
    ctx = _parse(
        tmp_path,
        "struct Data { int value; void method(); };",
        {**settings, "methods": {"method": {"ignore": True}}},
    )
    assert ctx.auto_repr is expected


@pytest.mark.parametrize("settings", [{}, {"ignored_bases": ["Base"]}])
@pytest.mark.parametrize("auto_repr", [None, False, True])
def test_bases_respect_auto_repr_setting(tmp_path, settings, auto_repr):
    ctx = _parse(
        tmp_path,
        "struct Data : Base { int value; };",
        {**settings, "auto_repr": auto_repr},
    )
    assert ctx.auto_repr is (auto_repr is True)


def test_auto_repr_can_be_disabled(tmp_path):
    assert not _parse(
        tmp_path, "struct Data { int value; };", {"auto_repr": False}
    ).auto_repr


@pytest.mark.parametrize("size", ["", "1 + 1"])
def test_repr_does_not_read_unbound_array_attributes(tmp_path, size):
    ctx = _parse(tmp_path, f"struct Data {{ int value; int samples[{size}]; }};")
    output = RenderBuffer()
    cls_def(output, ctx, ctx.var_name)
    generated = output.getvalue()
    assert 'self.attr("value")' in generated
    assert 'self.attr("samples")' not in generated


def test_default_auto_repr_does_not_force_ineligible_type(tmp_path):
    assert not _parse(tmp_path, "struct Data { void method(); };").auto_repr
