import ast
from pathlib import Path

from cxxheaderparser.options import ParserOptions

from semiwrap.autowrap.cxxparser import parse_header
from semiwrap.autowrap.generator_data import GeneratorData
from semiwrap.autowrap.render_wrapped import render_wrapped_cpp
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


def assert_rendered_suppression(rendered: str, needle: str, suppressed: bool):
    depth = 0
    needle_depths = []
    for line in rendered.splitlines():
        if line.strip() == "SEMIWRAP_SUPPRESS_DEPRECATED_BEGIN":
            depth += 1
        elif line.strip() == "SEMIWRAP_SUPPRESS_DEPRECATED_END":
            assert depth > 0
            depth -= 1
        elif needle in line:
            needle_depths.append(depth)

    assert depth == 0
    assert len(needle_depths) == 1
    assert (needle_depths[0] > 0) is suppressed


def test_render_suppresses_only_deprecated_callable_property_and_enum_bindings(
    tmp_path,
):
    source = r"""
[[deprecated("Use current_free().")]] void old_free();
void current_free();

enum class [[deprecated("Use CurrentGlobalEnum.")]] OldGlobalEnum {
    OldGlobalValue,
    CurrentGlobalValue,
};
enum class MixedGlobalEnum {
    OldMixedGlobal [[deprecated("Use CurrentMixedGlobal.")]],
    CurrentMixedGlobal,
};

struct Widget {
    [[deprecated("Use current_method().")]] void old_method();
    void current_method();

    [[deprecated("Use current_field.")]] int old_field;
    int current_field;

    enum class [[deprecated("Use CurrentClassEnum.")]] OldClassEnum {
        OldClassValue,
        CurrentClassValue,
    };
    enum class MixedClassEnum {
        OldMixedClass [[deprecated("Use CurrentMixedClass.")]],
        CurrentMixedClass,
    };
    enum {
        OldUnnamed [[deprecated("Use CurrentUnnamed.")]],
        CurrentUnnamed,
    };
};
"""
    config = AutowrapConfigYaml(
        functions={
            "old_free": FunctionData(ifdef="HAS_OLD_FREE"),
            "current_free": FunctionData(),
        },
        enums={
            "OldGlobalEnum": EnumData(),
            "MixedGlobalEnum": EnumData(),
        },
        classes={
            "Widget": ClassData(
                methods={
                    "old_method": FunctionData(),
                    "current_method": FunctionData(),
                },
                attributes={
                    "old_field": PropData(),
                    "current_field": PropData(),
                },
                enums={
                    "OldClassEnum": EnumData(),
                    "MixedClassEnum": EnumData(),
                },
            )
        },
    )

    rendered = render_wrapped_cpp(parse_deprecated_header(tmp_path, source, config))

    assert_rendered_suppression(rendered, 'scope.def("old_free"', True)
    assert_rendered_suppression(rendered, "#ifdef HAS_OLD_FREE", True)
    assert_rendered_suppression(rendered, "#endif // HAS_OLD_FREE", True)
    assert_rendered_suppression(rendered, 'scope.def("current_free"', False)

    assert_rendered_suppression(rendered, 'cls_Widget.def("old_method"', True)
    assert_rendered_suppression(rendered, 'cls_Widget.def("current_method"', False)
    assert_rendered_suppression(rendered, 'cls_Widget.def_readwrite("old_field"', True)
    assert_rendered_suppression(
        rendered, 'cls_Widget.def_readwrite("current_field"', False
    )

    assert_rendered_suppression(rendered, "py::enum_<::OldGlobalEnum> value;", True)
    assert_rendered_suppression(rendered, '.value("OldGlobalValue"', True)
    assert_rendered_suppression(rendered, '.value("CurrentGlobalValue"', True)
    assert_rendered_suppression(rendered, "py::enum_<::MixedGlobalEnum> value;", False)
    assert_rendered_suppression(rendered, '.value("OldMixedGlobal"', True)
    assert_rendered_suppression(rendered, '.value("CurrentMixedGlobal"', False)

    assert_rendered_suppression(
        rendered, "py::enum_<::Widget::OldClassEnum> cls_Widget_enum1;", True
    )
    assert_rendered_suppression(rendered, '.value("OldClassValue"', True)
    assert_rendered_suppression(rendered, '.value("CurrentClassValue"', True)
    assert_rendered_suppression(
        rendered, "py::enum_<::Widget::MixedClassEnum> cls_Widget_enum2;", False
    )
    assert_rendered_suppression(rendered, '.value("OldMixedClass"', True)
    assert_rendered_suppression(rendered, '.value("CurrentMixedClass"', False)
    assert_rendered_suppression(rendered, 'cls_Widget.attr("OldUnnamed")', True)
    assert_rendered_suppression(rendered, 'cls_Widget.attr("CurrentUnnamed")', False)

    assert rendered.count("SEMIWRAP_SUPPRESS_DEPRECATED_BEGIN") == rendered.count(
        "SEMIWRAP_SUPPRESS_DEPRECATED_END"
    )


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
