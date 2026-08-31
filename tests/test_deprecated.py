import ast
from pathlib import Path

from cxxheaderparser.options import ParserOptions

from semiwrap.autowrap.cxxparser import parse_header
from semiwrap.autowrap.generator_data import GeneratorData
from semiwrap.config.autowrap_yml import (
    AutowrapConfigYaml,
    ClassData,
    EnumData,
    FunctionData,
    PropData,
)


def parse_deprecated_header(tmp_path: Path, source: str, config: AutowrapConfigYaml):
    header = tmp_path / "deprecated.h"
    header.write_text(source)
    return parse_header(
        "deprecated",
        header,
        tmp_path,
        GeneratorData(config, tmp_path / "deprecated.yml"),
        ParserOptions(),
        {},
        False,
    )


def unquote_doc(doc):
    return "".join(ast.literal_eval(line) for line in doc or [])


def test_parses_supported_deprecated_function_attributes(tmp_path):
    source = r"""
[[deprecated]] int old_plain();
[[deprecated("Use " "new_free().")]] int old_free();
__attribute__((__deprecated__("Use new_gnu()."))) int old_gnu();
__declspec(deprecated("Use new_msvc().")) int old_msvc();
__attribute__((deprecated("Use new_clang().", "new_clang"))) int old_clang();
"""
    config = AutowrapConfigYaml(
        functions={
            "old_plain": FunctionData(),
            "old_free": FunctionData(),
            "old_gnu": FunctionData(),
            "old_msvc": FunctionData(),
            "old_clang": FunctionData(),
        }
    )

    hctx = parse_deprecated_header(tmp_path, source, config)
    functions = {fn.cpp_name: fn for fn in hctx.functions}

    assert all(fn.deprecated is True for fn in functions.values())
    assert functions["old_plain"].doc == [
        '".. warning::\\n"',
        '"   Deprecated."',
    ]
    assert "Deprecated: Use new_free()." in unquote_doc(functions["old_free"].doc)
    assert "Deprecated: Use new_gnu()." in unquote_doc(functions["old_gnu"].doc)
    assert "Deprecated: Use new_msvc()." in unquote_doc(functions["old_msvc"].doc)
    assert unquote_doc(functions["old_clang"].doc) == (
        ".. warning::\n   Deprecated: Use new_clang()."
    )


def test_decodes_escaped_newline_in_deprecation_message(tmp_path):
    source = r'[[deprecated("line\nnext")]] int old_lines();'
    config = AutowrapConfigYaml(functions={"old_lines": FunctionData()})

    hctx = parse_deprecated_header(tmp_path, source, config)

    assert unquote_doc(hctx.functions[0].doc) == (
        ".. warning::\n   Deprecated: line\n   next"
    )


def test_concatenates_multiline_adjacent_deprecation_literals(tmp_path):
    source = r"""
[[deprecated(
    "Use "
    "new_multiline()."
)]] int old_multiline();
"""
    config = AutowrapConfigYaml(functions={"old_multiline": FunctionData()})

    hctx = parse_deprecated_header(tmp_path, source, config)

    assert unquote_doc(hctx.functions[0].doc) == (
        ".. warning::\n   Deprecated: Use new_multiline()."
    )


def test_marks_each_supported_declaration_kind(tmp_path):
    source = r"""
class [[deprecated("Use NewThing.")]] OldThing {
public:
    [[deprecated("Use another constructor.")]] OldThing();
    [[deprecated("Use new_method().")]] void old_method();
    [[deprecated("Use new_field.")]] int old_field;

    enum class [[deprecated("Use NewEnum.")]] OldEnum {
        OldValue [[deprecated("Use NewValue.")]],
        NewValue,
    };

    /** Current documentation. */
    void current_method();
};
"""
    config = AutowrapConfigYaml(
        classes={
            "OldThing": ClassData(
                methods={
                    "OldThing": FunctionData(),
                    "old_method": FunctionData(),
                    "current_method": FunctionData(),
                },
                attributes={"old_field": PropData()},
                enums={"OldEnum": EnumData()},
            )
        }
    )

    hctx = parse_deprecated_header(tmp_path, source, config)
    cls = hctx.classes[0]
    methods = {method.cpp_name: method for method in cls.wrapped_public_methods}
    enum = cls.enums[0]
    values = {value.py_name: value for value in enum.values}

    assert cls.deprecated is True
    assert methods["OldThing"].deprecated is True
    assert methods["old_method"].deprecated is True
    assert cls.public_properties[0].deprecated is True
    assert enum.deprecated is True
    assert values["OldValue"].deprecated is True

    assert methods["current_method"].deprecated is False
    assert unquote_doc(methods["current_method"].doc) == "Current documentation."
    assert values["NewValue"].deprecated is False
    assert values["NewValue"].doc is None


def test_doxygen_message_prevents_duplicate_deprecation_warning(tmp_path):
    source = r"""
/** Use new_doxygen(). */
[[deprecated("Use new_doxygen().")]] int old_doxygen();
"""
    config = AutowrapConfigYaml(functions={"old_doxygen": FunctionData()})

    hctx = parse_deprecated_header(tmp_path, source, config)
    doc = unquote_doc(hctx.functions[0].doc)

    assert doc.count("Use new_doxygen().") == 1
    assert ".. warning::" not in doc


def test_yaml_message_prevents_duplicate_deprecation_warning(tmp_path):
    source = '[[deprecated("Use new_yaml().")]] int old_yaml();'
    config = AutowrapConfigYaml(
        functions={
            "old_yaml": FunctionData(doc="Use new_yaml()."),
        }
    )

    hctx = parse_deprecated_header(tmp_path, source, config)
    doc = unquote_doc(hctx.functions[0].doc)

    assert doc.count("Use new_yaml().") == 1
    assert ".. warning::" not in doc


def test_existing_deprecated_text_prevents_generic_warning(tmp_path):
    source = "[[deprecated]] int old_documented();"
    config = AutowrapConfigYaml(
        functions={
            "old_documented": FunctionData(doc="This API is DEPRECATED already."),
        }
    )

    hctx = parse_deprecated_header(tmp_path, source, config)
    doc = unquote_doc(hctx.functions[0].doc)

    assert hctx.functions[0].deprecated is True
    assert doc == "This API is DEPRECATED already."
    assert ".. warning::" not in doc


def test_doxygen_and_similar_attribute_names_do_not_mark_declarations(tmp_path):
    source = r"""
/** @deprecated Use replacement(). */
int docs_only();
[[vendor::not_deprecated("Still current.")]] int similar_attribute();
"""
    config = AutowrapConfigYaml(
        functions={
            "docs_only": FunctionData(),
            "similar_attribute": FunctionData(),
        }
    )

    hctx = parse_deprecated_header(tmp_path, source, config)
    functions = {fn.cpp_name: fn for fn in hctx.functions}

    assert functions["docs_only"].deprecated is False
    assert functions["similar_attribute"].deprecated is False
    assert functions["similar_attribute"].doc is None


def test_decodes_supported_cpp_string_prefixes(tmp_path):
    source = r"""
[[deprecated(u8"UTF-8 message")]] int old_u8();
[[deprecated(u"UTF-16 message")]] int old_u();
[[deprecated(U"UTF-32 message")]] int old_U();
[[deprecated(L"wide message")]] int old_L();
"""
    config = AutowrapConfigYaml(
        functions={
            "old_u8": FunctionData(),
            "old_u": FunctionData(),
            "old_U": FunctionData(),
            "old_L": FunctionData(),
        }
    )

    hctx = parse_deprecated_header(tmp_path, source, config)
    docs = {fn.cpp_name: unquote_doc(fn.doc) for fn in hctx.functions}

    assert "Deprecated: UTF-8 message" in docs["old_u8"]
    assert "Deprecated: UTF-16 message" in docs["old_u"]
    assert "Deprecated: UTF-32 message" in docs["old_U"]
    assert "Deprecated: wide message" in docs["old_L"]


def test_non_string_attribute_argument_falls_back_to_generic_warning(tmp_path):
    source = "[[deprecated(DEPRECATION_MESSAGE)]] int old_macro_message();"
    config = AutowrapConfigYaml(functions={"old_macro_message": FunctionData()})

    hctx = parse_deprecated_header(tmp_path, source, config)

    assert hctx.functions[0].deprecated is True
    assert unquote_doc(hctx.functions[0].doc) == ".. warning::\n   Deprecated."
