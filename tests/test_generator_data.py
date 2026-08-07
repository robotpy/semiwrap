from cxxheaderparser.options import ParserOptions

from semiwrap.autowrap.cxxparser import parse_header
from semiwrap.autowrap.generator_data import GeneratorData
from semiwrap.config.autowrap_yml import AutowrapConfigYaml, FunctionData


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
