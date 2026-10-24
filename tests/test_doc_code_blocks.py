"""Errors that prevent generating bindings; successful cases live in test_ft_docs."""

import pytest
import yaml
from cxxheaderparser.errors import CxxParseError
from cxxheaderparser.options import ParserOptions

from semiwrap.autowrap.cxxparser import parse_header
from semiwrap.autowrap.generator_data import GeneratorData
from semiwrap.config.autowrap_yml import AutowrapConfigYaml
from semiwrap.config.util import ValidationError


def _parse(tmp_path, source, config):
    header = tmp_path / "examples.h"
    header.write_text(source)
    yml = tmp_path / "examples.yml"
    yml.write_text(yaml.safe_dump(config))
    data = AutowrapConfigYaml.from_file(yml)
    return parse_header(
        "examples",
        header,
        tmp_path,
        GeneratorData(data, yml),
        ParserOptions(),
        {},
        False,
    )


@pytest.mark.parametrize("configured,found", [(1, 2), (2, 1), (1, 0)])
def test_replacement_count_mismatch(tmp_path, configured, found):
    comment = "/**\n" + "@code\nf();\n@endcode\n" * found + "*/\n" if found else ""
    with pytest.raises(CxxParseError) as exc:
        _parse(
            tmp_path,
            comment + "int example(int x);",
            {"functions": {"example": {"doc_code_blocks": ["f()"] * configured}}},
        )
    assert isinstance(exc.value.__cause__, ValueError)
    message = str(exc.value.__cause__)
    for fragment in [
        "examples.h",
        "example(int)",
        "configured {}".format(configured),
        "found {}".format(found),
    ]:
        assert fragment in message


@pytest.mark.parametrize("replacement", ["", " \n\t"])
def test_blank_replacement_rejected(tmp_path, replacement):
    with pytest.raises(CxxParseError) as exc:
        _parse(
            tmp_path,
            "/** @code f(); @endcode */ int example();",
            {"functions": {"example": {"doc_code_blocks": [replacement]}}},
        )
    assert isinstance(exc.value.__cause__, ValueError)
    assert "nonempty" in str(exc.value.__cause__)


@pytest.mark.parametrize(
    "function_config",
    [
        {"doc": "Override", "doc_code_blocks": ["f()"]},
        {"doc": "Override", "overloads": {"int": {"doc_code_blocks": ["f()"]}}},
        {"doc_code_blocks": ["f()"], "overloads": {"int": {"doc": "Override"}}},
    ],
)
def test_doc_conflict_including_inherited_settings(tmp_path, function_config):
    with pytest.raises(CxxParseError) as exc:
        _parse(
            tmp_path,
            "/** @code f(); @endcode */ int example(int x);",
            {"functions": {"example": function_config}},
        )
    assert isinstance(exc.value.__cause__, ValueError)
    assert "doc and doc_code_blocks" in str(exc.value.__cause__)


@pytest.mark.parametrize("name", ["First", "Second"])
def test_error_identifies_qualified_method(tmp_path, name):
    with pytest.raises(CxxParseError) as exc:
        _parse(
            tmp_path,
            "struct First { int f(int x); }; struct Second { int f(int x); };",
            {
                "classes": {
                    "First": {},
                    "Second": {},
                    name: {"methods": {"f": {"doc_code_blocks": ["f()"]}}},
                }
            },
        )
    assert isinstance(exc.value.__cause__, ValueError)
    assert name + "::f(int)" in str(exc.value.__cause__)


def test_unterminated_block_has_declaration_context(tmp_path):
    with pytest.raises(CxxParseError) as exc:
        _parse(
            tmp_path,
            "/** @code f(); */ int example();",
            {"functions": {"example": {"doc_code_blocks": ["f()"]}}},
        )
    for fragment in ["examples.h", "example()", "Unterminated", "doxygen", "0"]:
        assert fragment in str(exc.value.__cause__)


@pytest.mark.parametrize("invalid", [[1], [["x"]], [{"python": "x"}], "x", {"0": "x"}])
def test_invalid_yaml_replacements(tmp_path, invalid):
    yml = tmp_path / "invalid.yml"
    yml.write_text(
        yaml.safe_dump({"functions": {"example": {"doc_code_blocks": invalid}}})
    )
    with pytest.raises(ValidationError, match="doc_code_blocks"):
        AutowrapConfigYaml.from_file(yml)


def test_template_instance_replacement_is_not_supported(tmp_path):
    yml = tmp_path / "invalid.yml"
    yml.write_text(
        "templates:\n  ExampleInt:\n    qualname: Example\n    params: [int]\n    doc_code_blocks: ['f()']\n"
    )
    with pytest.raises(ValidationError, match="doc_code_blocks"):
        AutowrapConfigYaml.from_file(yml)
