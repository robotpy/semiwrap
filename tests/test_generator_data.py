from cxxheaderparser.options import ParserOptions

from semiwrap.autowrap.cxxparser import parse_header
from semiwrap.autowrap.generator_data import GeneratorData
from semiwrap.autowrap.render_cls_trampoline_hpp import render_cls_trampoline_hpp
from semiwrap.autowrap.render_wrapped import render_wrapped_cpp
from semiwrap.config.autowrap_yml import (
    AutowrapConfigYaml,
    ClassData,
    FunctionData,
    TemplateData,
)


def test_ignored_overloaded_function_is_not_reported_missing(tmp_path):
    header = tmp_path / "x.h"
    header.write_text("int add(int x);\nint add(int x, int y);\n")
    config = AutowrapConfigYaml(functions={"add": FunctionData(ignore=True)})
    gendata = GeneratorData(config, tmp_path / "x.yml")

    hctx = parse_header(
        "x",
        header,
        tmp_path,
        gendata,
        ParserOptions(),
        {},
        False,
    )

    assert hctx.functions == []
    assert gendata.get_missing() == {}


def _parse_nested_class_template(tmp_path):
    header = tmp_path / "nested.h"
    header.write_text(
        "template <typename T> struct Outer { "
        "template <typename U> struct Inner {}; "
        "};\n"
    )
    config = AutowrapConfigYaml(
        classes={
            "Outer": ClassData(template_params=["T"]),
            "Outer::Inner": ClassData(template_params=["U"]),
        },
        templates={
            "InnerIntDouble": TemplateData(
                qualname="Outer::Inner", params=["int", "double"]
            )
        },
    )

    return parse_header(
        "nested",
        header,
        tmp_path,
        GeneratorData(config, tmp_path / "nested.yml"),
        ParserOptions(),
        {},
        False,
    )


def test_render_wrapped_emits_nested_instance_beneath_class_template(tmp_path):
    hctx = _parse_nested_class_template(tmp_path)

    rendered = render_wrapped_cpp(hctx)

    declaration = "::semiwrap_generated::bind___Outer_T___Inner_0 tmplCls0;"
    initializer = 'tmplCls0(m, "InnerIntDouble"),'
    assert rendered.count(declaration) == 1
    assert rendered.count(initializer) == 1


def test_nested_template_binder_includes_enclosing_template_parameters(tmp_path):
    hctx = _parse_nested_class_template(tmp_path)
    inner = hctx.classes[0].child_classes[0]

    rendered = render_cls_trampoline_hpp(hctx, inner)

    assert "template <typename T, typename U>" in rendered
    assert "::Outer<T>::template Inner<U>" in rendered
