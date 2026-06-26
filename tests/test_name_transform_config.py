import dataclasses
import pathlib

from cxxheaderparser.options import ParserOptions

from semiwrap.autowrap.cxxparser import parse_header
from semiwrap.autowrap.generator_data import GeneratorData
from semiwrap.config.autowrap_yml import AutowrapConfigYaml, EnumData, EnumValue
from semiwrap.config.pyproject_toml import ExtensionModuleConfig, SemiwrapToolConfig
from semiwrap.makeplan import BuildTarget, makeplan
from semiwrap.name_transform import (
    NameTransformConfig,
    merge_name_transform_configs,
    name_transform_config_to_args,
    resolve_name_transforms,
)


def test_autowrap_yaml_accepts_name_transform(tmp_path):
    yml = tmp_path / "x.yml"
    yml.write_text("name_transform: snake_case\n")
    cfg = AutowrapConfigYaml.from_file(yml)
    assert cfg.name_transform == "snake_case"


def test_pyproject_configs_accept_name_transform():
    tool = SemiwrapToolConfig(name_transform="snake_case")
    ext = ExtensionModuleConfig(name_transform="PascalCase")
    assert tool.name_transform == "snake_case"
    assert ext.name_transform == "PascalCase"


def test_makeplan_passes_pyproject_name_transform_to_header2dat_not_yaml():
    project_root = pathlib.Path(__file__).parent / "cpp" / "sw-test"
    targets = [
        item
        for item in makeplan(project_root)
        if isinstance(item, BuildTarget) and item.command == "header2dat"
    ]

    # name_transform for these headers is configured in YAML only. header2dat
    # reads the YAML itself, so makeplan should pass only pyproject-derived
    # inherited configuration.
    for header_name in (
        "name_transform_snake",
        "name_transform_camel",
        "name_transform_pascal",
    ):
        target = next(t for t in targets if header_name in t.args)
        args = list(target.args)
        assert not any(str(arg).startswith("--name-transform") for arg in args)


def test_autowrap_yaml_accepts_name_transform_mapping(tmp_path):
    yml = tmp_path / "x.yml"
    yml.write_text(
        "name_transform:\n"
        "  default: snake_case\n"
        "  method: camelCase\n"
        "  enum_value: PascalCase\n"
    )
    cfg = AutowrapConfigYaml.from_file(yml)
    assert cfg.name_transform == NameTransformConfig(
        default="snake_case",
        method="camelCase",
        enum_value="PascalCase",
    )


def test_pyproject_configs_accept_name_transform_mapping():
    tool = SemiwrapToolConfig(
        name_transform=NameTransformConfig(
            default="snake_case", enum_value="PascalCase"
        )
    )
    ext = ExtensionModuleConfig(name_transform=NameTransformConfig(method="camelCase"))
    assert tool.name_transform == NameTransformConfig(
        default="snake_case", enum_value="PascalCase"
    )
    assert ext.name_transform == NameTransformConfig(method="camelCase")


def test_name_transform_config_expands_to_command_line_flags():
    cfg = NameTransformConfig(
        default="snake_case", method="camelCase", enum_value="PascalCase"
    )
    assert name_transform_config_to_args(cfg) == [
        "--name-transform-default",
        "snake_case",
        "--name-transform-method",
        "camelCase",
        "--name-transform-enum-value",
        "PascalCase",
    ]


def test_name_transform_string_command_flags_apply_to_all_kinds():
    assert name_transform_config_to_args("snake_case") == [
        "--name-transform-default",
        "snake_case",
        "--name-transform-function",
        "snake_case",
        "--name-transform-method",
        "snake_case",
        "--name-transform-attribute",
        "snake_case",
        "--name-transform-enum-value",
        "snake_case",
    ]


def test_name_transform_precedence_merge_example():
    top = NameTransformConfig(default="snake_case", enum_value="PascalCase")
    ext = NameTransformConfig(method="camelCase")
    yml = NameTransformConfig(attribute="none")
    merged = merge_name_transform_configs(merge_name_transform_configs(top, ext), yml)
    assert merged == NameTransformConfig(
        default="snake_case",
        method="camelCase",
        attribute="none",
        enum_value="PascalCase",
    )


def test_makeplan_does_not_encode_yaml_name_transform_mapping(monkeypatch):
    project_root = pathlib.Path(__file__).parent / "cpp" / "sw-test"

    original_from_file = AutowrapConfigYaml.from_file

    def fake_from_file(path):
        cfg = original_from_file(path)
        if path.name == "name_transform_snake.yml":
            cfg = dataclasses.replace(
                cfg,
                name_transform=NameTransformConfig(method="camelCase"),
            )
        return cfg

    monkeypatch.setattr(AutowrapConfigYaml, "from_file", staticmethod(fake_from_file))

    target = next(
        item
        for item in makeplan(project_root)
        if isinstance(item, BuildTarget)
        and item.command == "header2dat"
        and "name_transform_snake" in item.args
    )
    args = list(target.args)
    assert not any(str(arg).startswith("--name-transform") for arg in args)


def test_parse_header_transforms_enum_values_after_prefix_stripping(tmp_path):
    header = tmp_path / "x.h"
    header.write_text("enum Color { Color_Red, ColorHTTPServer };\n")
    cfg = AutowrapConfigYaml(enums={"Color": EnumData()})
    gendata = GeneratorData(cfg, tmp_path / "x.yml")

    hctx = parse_header(
        "x",
        header,
        tmp_path,
        gendata,
        ParserOptions(),
        {},
        False,
        name_transforms=resolve_name_transforms("snake_case"),
    )

    enum = hctx.enums[0]
    assert [v.py_name for v in enum.values] == ["red", "http_server"]


def test_parse_header_does_not_transform_enum_value_rename(tmp_path):
    header = tmp_path / "x.h"
    header.write_text("enum Color { Color_Red };\n")
    cfg = AutowrapConfigYaml(
        enums={"Color": EnumData(values={"Color_Red": EnumValue(rename="BrightRed")})}
    )
    gendata = GeneratorData(cfg, tmp_path / "x.yml")

    hctx = parse_header(
        "x",
        header,
        tmp_path,
        gendata,
        ParserOptions(),
        {},
        False,
        name_transforms=resolve_name_transforms("snake_case"),
    )

    assert hctx.enums[0].values[0].py_name == "BrightRed"
