import ast
from pathlib import Path

from cxxheaderparser.options import ParserOptions

from semiwrap.autowrap.cxxparser import parse_header
from semiwrap.autowrap.generator_data import GeneratorData
from semiwrap.autowrap.render_cls_trampoline_hpp import render_cls_trampoline_hpp
from semiwrap.autowrap.render_tmpl_inst import (
    render_template_inst_cpp,
    render_template_inst_hpp,
)
from semiwrap.autowrap.render_wrapped import render_wrapped_cpp
from semiwrap.config.autowrap_yml import (
    AutowrapConfigYaml,
    ClassData,
    EnumData,
    FunctionData,
    PropData,
    TemplateData,
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
    assert_rendered_suppression(
        rendered,
        'value.value("OldGlobalValue", ::OldGlobalEnum::OldGlobalValue);',
        True,
    )
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


def test_enum_suppression_preserves_inline_code_statement_termination(tmp_path):
    source = r"""
enum class [[deprecated("Use CurrentEnum.")]] OldEnum {
    Value,
};
"""
    config = AutowrapConfigYaml(
        enums={
            "OldEnum": EnumData(
                inline_code=(
                    '.value("Alias", ::OldEnum::Value);\n'
                    'm.attr("enum_marker") = py::none()'
                )
            )
        }
    )

    rendered = render_wrapped_cpp(parse_deprecated_header(tmp_path, source, config))

    assert 'm.attr("enum_marker") = py::none()\n    ;' in rendered


def test_render_suppresses_deprecated_class_and_generated_constexpr_alias(tmp_path):
    source = r"""
class [[deprecated("Use CurrentWidget.")]] OldWidget {
public:
    OldWidget();
    void old_widget_method();
    int old_widget_field;
    static constexpr int OldWidgetConstant = 1;
    enum {
        OldWidgetUnnamed,
    };
};
"""
    config = AutowrapConfigYaml(
        classes={
            "OldWidget": ClassData(
                methods={
                    "OldWidget": FunctionData(),
                    "old_widget_method": FunctionData(),
                },
                attributes={
                    "old_widget_field": PropData(),
                    "OldWidgetConstant": PropData(),
                },
                inline_code="/* OLD_WIDGET_INLINE_MARKER */",
            )
        }
    )

    rendered = render_wrapped_cpp(parse_deprecated_header(tmp_path, source, config))

    assert_rendered_suppression(rendered, "py::class_<typename ::OldWidget", True)
    assert_rendered_suppression(rendered, "return new ::OldWidget()", True)
    assert "cls_OldWidget.def(py::init<>()" not in rendered
    assert_rendered_suppression(rendered, 'cls_OldWidget.def("old_widget_method"', True)
    assert_rendered_suppression(
        rendered, 'cls_OldWidget.def_readwrite("old_widget_field"', True
    )
    assert_rendered_suppression(
        rendered,
        "static constexpr auto OldWidgetConstant [[maybe_unused]] = "
        "::OldWidget::OldWidgetConstant",
        True,
    )
    assert_rendered_suppression(
        rendered, 'cls_OldWidget.attr("OldWidgetUnnamed")', True
    )
    assert_rendered_suppression(rendered, "OLD_WIDGET_INLINE_MARKER", False)


def test_render_suppresses_only_deprecated_nested_classes_and_enums(tmp_path):
    source = r"""
struct Parent {
    struct [[deprecated("Use CurrentChild.")]] OldChild {
        void old_child_method();
        static constexpr int OldChildConstant = 1;
    };
    struct CurrentChild {
        void current_child_method();
        static constexpr int CurrentChildConstant = 2;
    };

    enum class [[deprecated("Use CurrentNestedEnum.")]] OldNestedEnum {
        OldNestedValue,
    };
    enum class CurrentNestedEnum {
        CurrentNestedValue,
    };
};
"""
    config = AutowrapConfigYaml(
        classes={
            "Parent": ClassData(
                enums={
                    "OldNestedEnum": EnumData(),
                    "CurrentNestedEnum": EnumData(),
                }
            ),
            "Parent::OldChild": ClassData(
                methods={"old_child_method": FunctionData()},
                attributes={"OldChildConstant": PropData()},
            ),
            "Parent::CurrentChild": ClassData(
                methods={"current_child_method": FunctionData()},
                attributes={"CurrentChildConstant": PropData()},
            ),
        }
    )

    rendered = render_wrapped_cpp(parse_deprecated_header(tmp_path, source, config))

    assert_rendered_suppression(rendered, "py::class_<typename ::Parent,", False)
    assert_rendered_suppression(
        rendered, "py::class_<typename ::Parent::OldChild,", True
    )
    assert_rendered_suppression(
        rendered, "py::class_<typename ::Parent::CurrentChild,", False
    )
    assert_rendered_suppression(rendered, 'cls_OldChild.def("old_child_method"', True)
    assert_rendered_suppression(
        rendered, 'cls_CurrentChild.def("current_child_method"', False
    )
    assert_rendered_suppression(
        rendered,
        "using OldChild [[maybe_unused]] = typename ::Parent::OldChild",
        True,
    )
    assert_rendered_suppression(
        rendered,
        "using CurrentChild [[maybe_unused]] = typename ::Parent::CurrentChild",
        False,
    )
    assert_rendered_suppression(
        rendered,
        "static constexpr auto OldChildConstant [[maybe_unused]] = "
        "::Parent::OldChild::OldChildConstant",
        True,
    )
    assert_rendered_suppression(
        rendered,
        "static constexpr auto CurrentChildConstant [[maybe_unused]] = "
        "::Parent::CurrentChild::CurrentChildConstant",
        False,
    )
    assert_rendered_suppression(
        rendered,
        "py::enum_<::Parent::OldNestedEnum> cls_Parent_enum1",
        True,
    )
    assert_rendered_suppression(
        rendered,
        "py::enum_<::Parent::CurrentNestedEnum> cls_Parent_enum2",
        False,
    )
    assert_rendered_suppression(
        rendered,
        "using OldNestedEnum [[maybe_unused]] = typename ::Parent::OldNestedEnum",
        True,
    )
    assert_rendered_suppression(
        rendered,
        "using CurrentNestedEnum [[maybe_unused]] = typename ::Parent::CurrentNestedEnum",
        False,
    )


def test_trampoline_suppresses_deprecated_class_and_method_references(tmp_path):
    source = r"""
class [[deprecated("Use CurrentVirtual.")]] OldVirtual {
public:
    virtual int public_old_virtual();
protected:
    OldVirtual(int value);
    virtual int protected_old_virtual();
    void old_protected_method();
    int old_protected_property;
};

class CurrentVirtual {
public:
    [[deprecated("Use current_virtual().")]] virtual int old_virtual();
    virtual int current_virtual();
};
"""
    config = AutowrapConfigYaml(
        classes={
            "OldVirtual": ClassData(
                methods={
                    "OldVirtual": FunctionData(),
                    "public_old_virtual": FunctionData(),
                    "protected_old_virtual": FunctionData(),
                    "old_protected_method": FunctionData(),
                },
                attributes={"old_protected_property": PropData()},
                trampoline_inline_code="/* OLD_TRAMPOLINE_INLINE_MARKER */",
            ),
            "CurrentVirtual": ClassData(
                methods={
                    "old_virtual": FunctionData(
                        cpp_code="[](CurrentVirtual *) -> int { return 1; }"
                    ),
                    "current_virtual": FunctionData(),
                }
            ),
        }
    )
    hctx = parse_deprecated_header(tmp_path, source, config)
    classes = {cls.cpp_name: cls for cls in hctx.classes}

    old_rendered = render_cls_trampoline_hpp(hctx, classes["OldVirtual"])
    assert_rendered_suppression(old_rendered, "using Base = ::OldVirtual;", True)
    assert_rendered_suppression(
        old_rendered,
        "struct PyTrampoline_OldVirtual : PyTrampolineBase",
        True,
    )
    assert_rendered_suppression(
        old_rendered, "PyTrampoline_OldVirtual(int value) :", True
    )
    assert_rendered_suppression(
        old_rendered, "return CxxCallBase::protected_old_virtual()", True
    )
    assert_rendered_suppression(
        old_rendered, "using ::OldVirtual::old_protected_method;", True
    )
    assert_rendered_suppression(
        old_rendered, "using ::OldVirtual::old_protected_property;", True
    )
    assert_rendered_suppression(old_rendered, "OLD_TRAMPOLINE_INLINE_MARKER", False)

    current_rendered = render_cls_trampoline_hpp(hctx, classes["CurrentVirtual"])
    assert_rendered_suppression(
        current_rendered, "return CxxCallBase::old_virtual()", True
    )
    assert_rendered_suppression(
        current_rendered, "return CxxCallBase::current_virtual()", False
    )

    wrapped = render_wrapped_cpp(hctx)
    assert_rendered_suppression(
        wrapped,
        "auto vcheck = [](CurrentVirtual *) -> int { return 1; };",
        True,
    )


def test_render_uses_local_callables_for_deprecated_constructor_and_operator(tmp_path):
    source = r"""
struct Widget {
    [[deprecated("Use create().")]] Widget();
    [[deprecated("Use is_same().")]] bool operator==(const Widget &other) const;
};
"""
    config = AutowrapConfigYaml(
        classes={
            "Widget": ClassData(
                methods={
                    "Widget": FunctionData(),
                    "operator==": FunctionData(),
                }
            )
        }
    )

    rendered = render_wrapped_cpp(parse_deprecated_header(tmp_path, source, config))

    assert_rendered_suppression(rendered, "return new ::Widget()", True)
    assert_rendered_suppression(
        rendered,
        'cls_Widget.def("__eq__", [](const ::Widget &self',
        True,
    )
    assert_rendered_suppression(rendered, "return self ==", True)
    assert "cls_Widget.def(py::init<>()" not in rendered
    assert "cls_Widget.def(py::self == py::self" not in rendered


def test_render_preserves_custom_cpp_code_for_deprecated_operator(tmp_path):
    source = r"""
struct [[deprecated("Use CurrentWidget.")]] Widget {
    bool operator==(const Widget &other) const;
};
"""
    config = AutowrapConfigYaml(
        classes={
            "Widget": ClassData(
                methods={
                    "operator==": FunctionData(cpp_code="py::self != py::self"),
                }
            )
        }
    )

    rendered = render_wrapped_cpp(parse_deprecated_header(tmp_path, source, config))

    assert_rendered_suppression(rendered, "cls_Widget.def(py::self != py::self", True)
    assert 'cls_Widget.def("__eq__", [](' not in rendered


def test_deprecated_class_template_suppresses_generated_binder_references(tmp_path):
    source = r"""
template <typename T>
struct [[deprecated("Use CurrentTemplate.")]] OldTemplate {
    T get();
};
"""
    config = AutowrapConfigYaml(
        classes={
            "OldTemplate": ClassData(
                template_params=["T"],
                methods={"get": FunctionData()},
                inline_code="/* OLD_TEMPLATE_CLASS_INLINE_MARKER */",
                template_inline_code="/* OLD_TEMPLATE_INLINE_MARKER */",
            )
        },
        templates={
            "OldTemplateInt": TemplateData(qualname="OldTemplate", params=["int"])
        },
    )
    hctx = parse_deprecated_header(tmp_path, source, config)
    tmpl_data = hctx.template_instances[0]

    binder = render_cls_trampoline_hpp(hctx, hctx.classes[0])
    assert_rendered_suppression(binder, "py::class_<typename ::OldTemplate<T>", True)
    assert_rendered_suppression(binder, 'cls_OldTemplate.def("get"', True)
    assert_rendered_suppression(binder, "OLD_TEMPLATE_CLASS_INLINE_MARKER", False)
    assert_rendered_suppression(binder, "OLD_TEMPLATE_INLINE_MARKER", False)

    inst_hpp = render_template_inst_hpp(hctx)
    assert_rendered_suppression(inst_hpp, f"struct {tmpl_data.binder_typename}", True)

    inst_cpp = render_template_inst_cpp(hctx, tmpl_data)
    assert_rendered_suppression(inst_cpp, "using BindType =", True)
    assert_rendered_suppression(inst_cpp, "inst = std::make_unique<BindType>", True)
    assert_rendered_suppression(inst_cpp, "inst->finish(set_doc, add_doc);", True)
    assert_rendered_suppression(inst_cpp, "inst.reset();", True)

    wrapped = render_wrapped_cpp(hctx)
    assert (
        "SEMIWRAP_SUPPRESS_DEPRECATED_BEGIN\n"
        "  semiwrap_deprecated_initializer(py::module &m) :" in wrapped
    )
    assert_rendered_suppression(
        wrapped, f"::{tmpl_data.binder_full_cpp_name} {tmpl_data.var_name};", True
    )
    assert_rendered_suppression(
        wrapped, f'{tmpl_data.var_name}(m, "OldTemplateInt"),', True
    )
    assert_rendered_suppression(wrapped, f"{tmpl_data.var_name}.finish(", True)


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
