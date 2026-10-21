import pytest
from cxxheaderparser.options import ParserOptions

from semiwrap.autowrap.buffer import RenderBuffer
from semiwrap.autowrap.cxxparser import parse_header
from semiwrap.autowrap.generator_data import GeneratorData
from semiwrap.autowrap.render_pybind11 import genmethod
from semiwrap.config.autowrap_yml import AutowrapConfigYaml


@pytest.mark.parametrize("return_type", ["void", "int"])
@pytest.mark.parametrize("buffer_type", ["IN", "OUT"])
@pytest.mark.parametrize("no_release", [None, False, True])
def test_buffer_gil_scope(tmp_path, return_type, buffer_type, no_release):
    header = tmp_path / "buffers.h"
    header.write_text(f"{return_type} process(char *data, int size);")
    yml = tmp_path / "buffers.yml"
    gil_setting = (
        "" if no_release is None else f"    no_release_gil: {str(no_release).lower()}\n"
    )
    yml.write_text(
        f"functions:\n  process:\n{gil_setting}"
        f"    buffers:\n    - {{type: {buffer_type}, src: data, len: size}}\n"
    )
    cfg = AutowrapConfigYaml.from_file(yml)
    hctx = parse_header(
        "buffers",
        header,
        tmp_path,
        GeneratorData(cfg, tmp_path / "buffers.yml"),
        ParserOptions(),
        {},
        False,
    )
    r = RenderBuffer()
    genmethod(r, "m", None, hctx.functions[0], None)
    code = r.getvalue()
    assert "release_gil()" not in code
    if no_release:
        assert "py::gil_scoped_release" not in code
    else:
        assert code.index(".request(") < code.index("py::gil_scoped_release")
        assert code.index("py::gil_scoped_release") < code.index("return ::process(")
        assert "return ::process((char*)__data.ptr, size);\n  }();" in code
        if return_type == "int":
            assert "auto __ret = [&]()" in code
            assert code.index("}();") < code.index("return __ret;")
