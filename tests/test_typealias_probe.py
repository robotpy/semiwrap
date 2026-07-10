from __future__ import annotations

from pathlib import Path

from cxxheaderparser.simple import parse_typename

from semiwrap.autowrap import typealias_probe
from semiwrap.autowrap.buffer import RenderBuffer
from semiwrap.autowrap.typealias_probe import (
    add_typealias_probe,
    collect_typealias_probes,
    probe_alias_name,
    render_typealias_probes,
)
from semiwrap.autowrap.render_wrapped import render_wrapped_cpp
from semiwrap.autowrap.render_cls_trampoline_hpp import render_cls_trampoline_hpp


def probes_for(type_text: str) -> list[str]:
    return collect_typealias_probes(parse_typename(type_text))


def test_collects_unqualified_alias_from_decorated_type():
    assert probes_for("const CantResolve&") == ["CantResolve"]


def test_collects_template_alias_and_inner_alias_sorted():
    assert probes_for("fancy_list<CantResolve>") == [
        "CantResolve",
        "fancy_list<CantResolve>",
    ]


def test_skips_builtin_std_and_global_root_targets_but_collects_template_args():
    assert probes_for("int") == []
    assert probes_for("std::vector<CantResolve>") == ["CantResolve"]
    assert probes_for("::AlreadyQualified") == []


def test_add_typealias_probe_deduplicates_and_sorts():
    probes: list[str] = []
    add_typealias_probe(probes, "CantResolve")
    add_typealias_probe(probes, "AlsoCantResolve")
    add_typealias_probe(probes, "CantResolve")
    assert probes == ["AlsoCantResolve", "CantResolve"]


def test_probe_alias_name_is_deterministic_and_descriptive():
    assert probe_alias_name("CantResolve") == (
        "semiwrap_typealias_probe_CantResolve__add_typealias_to_yaml"
    )
    assert probe_alias_name("fancy_list<CantResolve>") == (
        "semiwrap_typealias_probe_fancy_u_list_lt_CantResolve_gt___add_typealias_to_yaml"
    )


def test_render_typealias_probes_emits_comment_and_sorted_using_lines():
    r = RenderBuffer()
    render_typealias_probes(r, ["CantResolve", "AlsoCantResolve"])
    out = r.getvalue()
    assert "semiwrap diagnostic" in out
    assert "add a typealias entry" in out
    assert out.index(
        "using semiwrap_typealias_probe_AlsoCantResolve__add_typealias_to_yaml"
    ) < out.index("using semiwrap_typealias_probe_CantResolve__add_typealias_to_yaml")
    assert (
        "using semiwrap_typealias_probe_CantResolve__add_typealias_to_yaml "
        "[[maybe_unused]] = CantResolve;"
    ) in out


def test_render_typealias_probes_deduplicates_duplicate_input():
    r = RenderBuffer()
    render_typealias_probes(r, ["CantResolve", "CantResolve"])
    out = r.getvalue()
    assert out.count(
        "using semiwrap_typealias_probe_CantResolve__add_typealias_to_yaml"
    ) == 1


def test_probe_alias_name_distinguishes_namespaces_from_templates():
    assert probe_alias_name("A::B") != probe_alias_name("A<B>")


def test_probe_alias_name_distinguishes_general_sanitizer_collisions():
    assert probe_alias_name("A<B>") != probe_alias_name("A_B")


def test_helper_uses_deferred_annotations_for_python_38_runtime_compatibility():
    source = Path(typealias_probe.__file__).read_text()
    assert source.startswith("from __future__ import annotations\n")


import pathlib

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]

from cxxheaderparser.options import ParserOptions

from semiwrap.autowrap.cxxparser import parse_header
from semiwrap.autowrap.generator_data import GeneratorData
from semiwrap.autowrap.context import ClassTemplateData
from semiwrap.config.autowrap_yml import AutowrapConfigYaml


def parse_fixture_header(header_name: str, yaml_name: str):
    root = PROJECT_ROOT / "tests/cpp/sw-test/src/swtest/ft/include"
    yml = PROJECT_ROOT / "tests/cpp/sw-test/semiwrap/ft" / yaml_name
    cfg = AutowrapConfigYaml.from_file(yml)
    return parse_header(
        pathlib.Path(header_name).stem,
        root / header_name,
        root,
        GeneratorData(cfg, yml),
        ParserOptions(),
        {},
        False,
    )


def parse_fixture_header_with_yaml(header_name: str, yml: pathlib.Path):
    root = PROJECT_ROOT / "tests/cpp/sw-test/src/swtest/ft/include"
    cfg = AutowrapConfigYaml.from_file(yml)
    return parse_header(
        pathlib.Path(header_name).stem,
        root / header_name,
        root,
        GeneratorData(cfg, yml),
        ParserOptions(),
        {},
        False,
    )


def parse_tmp_header(tmp_path: pathlib.Path, name: str, header: str, yaml: str):
    header_path = tmp_path / f"{name}.h"
    yaml_path = tmp_path / f"{name}.yml"
    header_path.write_text(header)
    yaml_path.write_text(yaml)
    cfg = AutowrapConfigYaml.from_file(yaml_path)
    return parse_header(
        name,
        header_path,
        tmp_path,
        GeneratorData(cfg, yaml_path),
        ParserOptions(),
        {},
        False,
    )


def test_parse_header_collects_global_function_typealias_probe():
    hctx = parse_fixture_header("using.h", "using.yml")
    assert "AlsoCantResolve" in hctx.typealias_probes


def test_parse_header_collects_class_constructor_typealias_probe():
    hctx = parse_fixture_header("using.h", "using.yml")
    cls = next(c for c in hctx.classes if c.cpp_name == "ProtectedUsing")
    assert "CantResolve" in cls.typealias_probes


def test_parse_header_skips_autogenerated_inner_alias_typealias_probes():
    hctx = parse_fixture_header("retval.h", "retval.yml")
    cls = next(c for c in hctx.classes if c.cpp_name == "RetvalClass")
    assert cls.typealias_probes == []


def test_parse_header_skips_embedded_using_alias_typealias_probes():
    hctx = parse_fixture_header("using2.h", "using2.yml")
    cls = next(c for c in hctx.classes if c.cpp_name == "Using1")
    assert cls.typealias_probes == []


def test_parse_header_skips_local_user_alias_template_typealias_probes():
    hctx = parse_fixture_header("using2.h", "using2.yml")
    cls = next(c for c in hctx.classes if c.cpp_name == "Using3")
    assert "fancy_list<int>" not in cls.typealias_probes


def test_parse_header_suppresses_class_template_parameter_probe():
    hctx = parse_fixture_header("templates/tvchild.h", "tvchild.yml")
    cls = next(c for c in hctx.classes if c.cpp_name == "TVChild")
    assert "N" not in cls.typealias_probes


def test_parse_header_collects_missing_yaml_typealias_probes(tmp_path):
    yml = tmp_path / "using_missing_typealias.yml"
    yml.write_text(
        """
classes:
  cr::inner::ProtectedUsing:
    methods:
      ProtectedUsing:
        overloads:
          "":
          CantResolve:
  u::FwdDecl:
    attributes:
      x:
functions:
  fn_using:
    overloads:
      AlsoCantResolve:
      std::string:
"""
    )

    hctx = parse_fixture_header_with_yaml("using.h", yml)
    cls = next(c for c in hctx.classes if c.cpp_name == "ProtectedUsing")

    assert "AlsoCantResolve" in hctx.typealias_probes
    assert "CantResolve" in cls.typealias_probes


def test_parse_header_preserves_dependent_missing_alias_probe(tmp_path):
    hctx = parse_tmp_header(
        tmp_path,
        "dependent_alias",
        """
#pragma once

template <typename N>
struct DependentAliasHolder {
    DependentAliasHolder(MissingAlias<N> value);
};
""",
        """
classes:
  DependentAliasHolder:
    template_params:
    - typename N
    methods:
      DependentAliasHolder:
        overloads:
          MissingAlias<N>:
""",
    )

    cls = next(c for c in hctx.classes if c.cpp_name == "DependentAliasHolder")
    assert cls.typealias_probes == ["MissingAlias<N>"]


def test_parse_header_suppresses_non_type_function_template_parameter_probe(tmp_path):
    hctx = parse_tmp_header(
        tmp_path,
        "non_type_template_param",
        """
#pragma once

template <int N>
void takes_value_template(TVParam<N> value);
""",
        """
functions:
  takes_value_template:
    cpp_code: "[](auto) {}"
""",
    )

    assert "N" not in hctx.typealias_probes
    assert "TVParam<N>" not in hctx.typealias_probes


def test_parse_header_suppresses_method_template_dependent_alias_probe(tmp_path):
    hctx = parse_tmp_header(
        tmp_path,
        "method_template_param",
        """
#pragma once

struct MethodTemplateProbe {
    virtual ~MethodTemplateProbe() = default;

protected:
    template <typename T>
    void hidden(Alias<T> value) {}
};
""",
        """
classes:
  MethodTemplateProbe:
    methods:
      hidden:
        cpp_code: "[](auto&, auto) {}"
""",
    )

    cls = next(c for c in hctx.classes if c.cpp_name == "MethodTemplateProbe")
    assert "T" not in cls.typealias_probes
    assert "Alias<T>" not in cls.typealias_probes


def test_parse_header_collects_public_generated_lambda_method_probe(tmp_path):
    hctx = parse_tmp_header(
        tmp_path,
        "generated_lambda_probe",
        """
#pragma once

struct GeneratedLambdaProbe {
    void needs_lambda(MissingLambdaAlias value, int* out) {}
};
""",
        """
classes:
  GeneratedLambdaProbe:
    methods:
      needs_lambda:
""",
    )

    cls = next(c for c in hctx.classes if c.cpp_name == "GeneratedLambdaProbe")
    assert "MissingLambdaAlias" in cls.typealias_probes


def test_render_wrapped_cpp_emits_global_typealias_probe_before_initializer():
    hctx = parse_fixture_header("using.h", "using.yml")
    out = render_wrapped_cpp(hctx)
    probe = "semiwrap_typealias_probe_AlsoCantResolve__add_typealias_to_yaml"
    assert probe in out
    assert out.index("using namespace u;") < out.index(probe)
    assert out.index(probe) < out.index("struct semiwrap_using_initializer")
    assert "using semiwrap_typealias_probe_AlsoCantResolve__add_typealias_to_yaml" in out
    assert "= AlsoCantResolve;" in out


def test_render_wrapped_cpp_emits_class_typealias_probe_inside_initializer():
    hctx = parse_fixture_header("using.h", "using.yml")
    out = render_wrapped_cpp(hctx)
    probe = "semiwrap_typealias_probe_CantResolve__add_typealias_to_yaml"
    assert probe in out
    assert out.index("struct semiwrap_using_initializer") < out.index(probe)
    assert out.index(probe) < out.index("py::class_<typename cr::inner::ProtectedUsing")


def test_render_wrapped_cpp_deduplicates_class_typealias_probes_in_initializer_scope():
    hctx = parse_fixture_header("using.h", "using.yml")
    fwd_decl = next(c for c in hctx.classes if c.cpp_name == "FwdDecl")
    fwd_decl.typealias_probes.append("CantResolve")
    out = render_wrapped_cpp(hctx)
    probe = "semiwrap_typealias_probe_CantResolve__add_typealias_to_yaml"
    assert out.count(f"using {probe}") == 1


def test_render_wrapped_cpp_skips_templated_child_typealias_probes():
    hctx = parse_fixture_header("using.h", "using.yml")
    parent = next(c for c in hctx.classes if c.cpp_name == "ProtectedUsing")
    child_template = next(c for c in hctx.classes if c.cpp_name == "FwdDecl")
    child_template.template = ClassTemplateData("", "", "")
    child_template.typealias_probes.append("ChildTemplateProbe")
    parent.child_classes.append(child_template)
    hctx.classes = [parent]

    out = render_wrapped_cpp(hctx)

    assert "semiwrap_typealias_probe_ChildTemplateProbe__add_typealias_to_yaml" not in out


def test_render_trampoline_hpp_emits_class_typealias_probe():
    hctx = parse_fixture_header("using.h", "using.yml")
    cls = next(c for c in hctx.classes if c.cpp_name == "ProtectedUsing")
    out = render_cls_trampoline_hpp(hctx, cls)
    probe = "semiwrap_typealias_probe_CantResolve__add_typealias_to_yaml"
    assert probe in out
    assert out.index(probe) < out.index("PyTrampoline_ProtectedUsing(CantResolve")
