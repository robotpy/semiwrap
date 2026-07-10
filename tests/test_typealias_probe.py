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


def test_probe_alias_name_distinguishes_namespaces_from_templates():
    assert probe_alias_name("A::B") != probe_alias_name("A<B>")


def test_probe_alias_name_distinguishes_general_sanitizer_collisions():
    assert probe_alias_name("A<B>") != probe_alias_name("A_B")


def test_helper_uses_deferred_annotations_for_python_38_runtime_compatibility():
    source = Path(typealias_probe.__file__).read_text()
    assert source.startswith("from __future__ import annotations\n")


import pathlib

from cxxheaderparser.options import ParserOptions

from semiwrap.autowrap.cxxparser import parse_header
from semiwrap.autowrap.generator_data import GeneratorData
from semiwrap.config.autowrap_yml import AutowrapConfigYaml


def parse_fixture_header(header_name: str, yaml_name: str):
    root = pathlib.Path("tests/cpp/sw-test/src/swtest/ft/include")
    yml = pathlib.Path("tests/cpp/sw-test/semiwrap/ft") / yaml_name
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


def test_parse_header_collects_global_function_typealias_probe():
    hctx = parse_fixture_header("using.h", "using.yml")
    assert "AlsoCantResolve" in hctx.typealias_probes


def test_parse_header_collects_class_constructor_typealias_probe():
    hctx = parse_fixture_header("using.h", "using.yml")
    cls = next(c for c in hctx.classes if c.cpp_name == "ProtectedUsing")
    assert "CantResolve" in cls.typealias_probes


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
