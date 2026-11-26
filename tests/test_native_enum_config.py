import pytest
from cxxheaderparser.options import ParserOptions
from semiwrap.autowrap.cxxparser import parse_header
from semiwrap.autowrap.generator_data import GeneratorData
from semiwrap.config.autowrap_yml import (
    AutowrapConfigYaml,
    Defaults,
    EnumData,
    ClassData,
)


@pytest.mark.parametrize("project", [False, True])
@pytest.mark.parametrize("yaml", [None, False, True])
@pytest.mark.parametrize("native", [None, False, True])
def test_native_precedence(tmp_path, project, yaml, native):
    header = tmp_path / "enums.h"
    header.write_text(
        "enum Color { Red }; struct Box { enum Color { Red }; enum Other { Blue }; };"
    )
    config = AutowrapConfigYaml(
        classes={"Box": ClassData(enums={"Color": EnumData(native=native)})},
        defaults=Defaults(enum_native=yaml),
        enums={"Color": EnumData(native=native)},
    )
    ctx = parse_header(
        "enums",
        header,
        tmp_path,
        GeneratorData(config, tmp_path / "enums.yml", enum_native=project),
        ParserOptions(),
        {},
        False,
    )
    assert ctx.classes[0].enums[0].native is ctx.enums[0].native
    assert ctx.classes[0].enums[1].native is (yaml if yaml is not None else project)
    assert ctx.enums[0].native is (
        native if native is not None else yaml if yaml is not None else project
    )


def test_project_and_yaml_loading(tmp_path):
    from semiwrap.pyproject import PyProject

    project = tmp_path / "pyproject.toml"
    project.write_text("[tool.semiwrap.defaults]\nenum_native = false\n")
    assert PyProject(project).project.defaults.enum_native is False
    yml = tmp_path / "enums.yml"
    yml.write_text(
        "defaults:\n  enum_native: true\nenums:\n  Color:\n    native: false\n"
    )
    cfg = AutowrapConfigYaml.from_file(yml)
    assert cfg.defaults.enum_native is True
    assert cfg.enums["Color"].native is False


def test_legacy_flags_rejected(tmp_path):
    header = tmp_path / "enums.h"
    header.write_text("enum Color { Red };")
    config = AutowrapConfigYaml(enums={"Color": EnumData(native=False, is_flag=True)})
    from cxxheaderparser.errors import CxxParseError

    with pytest.raises(CxxParseError) as exc:
        parse_header(
            "enums",
            header,
            tmp_path,
            GeneratorData(config, tmp_path / "enums.yml"),
            ParserOptions(),
            {},
            False,
        )
    assert "is_flag requires native" in str(exc.value.__cause__)
