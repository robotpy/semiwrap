import pytest
from cxxheaderparser.options import ParserOptions
from semiwrap.autowrap.cxxparser import parse_header
from semiwrap.autowrap.generator_data import GeneratorData
from semiwrap.autowrap.render_wrapped import render_wrapped_cpp
from semiwrap.config.autowrap_yml import AutowrapConfigYaml, EnumData


@pytest.mark.parametrize(
    "arithmetic,is_flag,base",
    [
        (False, False, "Enum"),
        (True, False, "IntEnum"),
        (False, True, "Flag"),
        (True, True, "IntFlag"),
    ],
)
def test_native_builder(tmp_path, arithmetic, is_flag, base):
    header = tmp_path / "enums.h"
    header.write_text("enum Color { Red };")
    config = AutowrapConfigYaml(
        enums={
            "Color": EnumData(
                arithmetic=arithmetic,
                is_flag=is_flag,
                inline_code='.value("Alias", ::Color::Red)\n.export_values()',
            )
        }
    )
    ctx = parse_header(
        "enums",
        header,
        tmp_path,
        GeneratorData(config, tmp_path / "enums.yml"),
        ParserOptions(),
        {},
        False,
    )
    rendered = render_wrapped_cpp(ctx)
    assert "py::native_enum<::Color>" in rendered
    assert f'"enum.{base}"' in rendered
    assert (
        rendered.index('.value("Alias"')
        < rendered.index(".export_values()")
        < rendered.index(".finalize()")
    )
    assert "py::arithmetic()" not in rendered
    assert rendered.count(".finalize()") == 1


@pytest.mark.parametrize("template", [False, True])
def test_deeply_nested_enum_finalized_once(tmp_path, template):
    from semiwrap.autowrap.render_cls_trampoline_hpp import render_cls_trampoline_hpp
    from semiwrap.config.autowrap_yml import ClassData

    header = tmp_path / "nested.h"
    header.write_text(
        ("template<class T> " if template else "")
        + "struct Outer { enum Color { Red }; struct Inner { enum Color { Red }; struct Deep { enum Color { Red }; }; }; };"
    )
    config = AutowrapConfigYaml(
        classes={
            "Outer": ClassData(template_params=["T"] if template else None),
            "Outer::Inner": ClassData(),
            "Outer::Inner::Deep": ClassData(),
        }
    )
    ctx = parse_header(
        "nested",
        header,
        tmp_path,
        GeneratorData(config, tmp_path / "nested.yml"),
        ParserOptions(),
        {},
        False,
    )
    outer = ctx.classes[0]
    rendered = (
        render_cls_trampoline_hpp(ctx, outer) if template else render_wrapped_cpp(ctx)
    )
    for cls in (outer, outer.child_classes[0], outer.child_classes[0].child_classes[0]):
        assert rendered.count(f"{cls.var_name}_enum1.finalize();") == 1


@pytest.mark.parametrize("native", [True, False])
@pytest.mark.parametrize(
    "body", ["", "enum Color { Red };", "struct Inner { enum Color { Red }; };"]
)
def test_template_header_native_include(tmp_path, native, body):
    from semiwrap.autowrap.render_cls_trampoline_hpp import render_cls_trampoline_hpp
    from semiwrap.config.autowrap_yml import ClassData

    header = tmp_path / "template.h"
    from semiwrap.config.autowrap_yml import Defaults

    header.write_text("template<class T> struct Container { " + body + " };")
    config = AutowrapConfigYaml(
        defaults=Defaults(enum_native=native),
        classes={
            "Container": ClassData(template_params=["T"]),
            "Container::Inner": ClassData(),
        },
    )
    ctx = parse_header(
        "template",
        header,
        tmp_path,
        GeneratorData(config, tmp_path / "template.yml"),
        ParserOptions(),
        {},
        False,
    )
    rendered = render_cls_trampoline_hpp(ctx, ctx.classes[0])
    assert ("#include <pybind11/native_enum.h>" in rendered) is (native and bool(body))


@pytest.mark.parametrize("native", [True, False])
@pytest.mark.parametrize(
    "source",
    [
        "",
        "enum Color { Red };",
        "struct Outer { struct Inner { enum Color { Red }; }; };",
    ],
)
def test_cpp_native_include(tmp_path, native, source):
    from semiwrap.config.autowrap_yml import Defaults

    header = tmp_path / "enums.h"
    header.write_text(source)
    from semiwrap.config.autowrap_yml import ClassData

    config = AutowrapConfigYaml(
        defaults=Defaults(enum_native=native),
        classes={"Outer": ClassData(), "Outer::Inner": ClassData()},
    )
    ctx = parse_header(
        "enums",
        header,
        tmp_path,
        GeneratorData(config, tmp_path / "enums.yml"),
        ParserOptions(),
        {},
        False,
    )
    rendered = render_wrapped_cpp(ctx)
    assert ("#include <pybind11/native_enum.h>" in rendered) is (
        native and bool(source)
    )
