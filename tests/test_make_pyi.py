import builtins
import importlib
import pathlib
import sys
import types

from semiwrap.cmd import make_pyi


def test_make_pyi_imports_extension_without_executing_stale_parent_init(
    tmp_path, monkeypatch
):
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()
    parent_init = pkg_dir / "__init__.py"
    parent_init.write_text("from .compiled import old_name\n")

    compiled = tmp_path / "compiled.py"
    compiled.write_text("new_name = 1\n")

    output = tmp_path / "out.pyi"

    def fake_stubgen_main():
        module_name = sys.argv[-1]
        module = importlib.import_module(module_name)
        assert module.new_name == 1

        outdir = pathlib.Path(sys.argv[sys.argv.index("-o") + 1])
        stub = outdir / "pkg" / "compiled.pyi"
        stub.parent.mkdir(parents=True, exist_ok=True)
        stub.write_text("new_name: int\n")

    monkeypatch.setattr(make_pyi.pybind11_stubgen, "main", fake_stubgen_main)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "make_pyi",
            "pkg.compiled",
            "pkg/compiled.pyi",
            str(output),
            "--",
            "pkg",
            str(parent_init),
            "pkg.compiled",
            str(compiled),
        ],
    )

    old_meta_path = list(sys.meta_path)
    try:
        make_pyi._PackageFinder.mapping.clear()
        make_pyi.main()
    finally:
        make_pyi._PackageFinder.mapping.clear()
        make_pyi._PackageFinder.packages.clear()
        sys.meta_path[:] = old_meta_path
        sys.modules.pop("pkg.compiled", None)
        sys.modules.pop("pkg", None)

    assert output.read_text() == "new_name: int\n"


def test_make_pyi_imports_mapped_extension_modules_before_stubgen(
    tmp_path, monkeypatch
):
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()
    parent_init = pkg_dir / "__init__.py"
    parent_init.write_text("# synthetic package should not execute this\n")

    provider = tmp_path / f"provider{make_pyi._EXTENSION_SUFFIXES[0]}"
    provider.write_bytes(b"")

    consumer = tmp_path / "consumer.py"
    consumer.write_text(
        "import builtins\n"
        "if not getattr(builtins, '_semiwrap_test_provider_loaded', False):\n"
        "    raise ImportError('provider extension was not imported')\n"
        "new_name = 1\n"
    )

    output = tmp_path / "out.pyi"
    real_import_module = importlib.import_module

    def fake_import_module(module_name, package=None):
        if module_name == "pkg.provider":
            builtins._semiwrap_test_provider_loaded = True
            module = types.ModuleType(module_name)
            sys.modules[module_name] = module
            return module
        return real_import_module(module_name, package)

    def fake_stubgen_main():
        module_name = sys.argv[-1]
        module = importlib.import_module(module_name)
        assert module.new_name == 1

        outdir = pathlib.Path(sys.argv[sys.argv.index("-o") + 1])
        stub = outdir / "pkg" / "consumer.pyi"
        stub.parent.mkdir(parents=True, exist_ok=True)
        stub.write_text("new_name: int\n")

    monkeypatch.delattr("builtins._semiwrap_test_provider_loaded", raising=False)
    monkeypatch.setattr(importlib, "import_module", fake_import_module)
    monkeypatch.setattr(make_pyi.pybind11_stubgen, "main", fake_stubgen_main)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "make_pyi",
            "pkg.consumer",
            "pkg/consumer.pyi",
            str(output),
            "--",
            "pkg",
            str(parent_init),
            "pkg.provider",
            str(provider),
            "pkg.consumer",
            str(consumer),
        ],
    )

    old_meta_path = list(sys.meta_path)
    try:
        make_pyi._PackageFinder.mapping.clear()
        make_pyi.main()
    finally:
        make_pyi._PackageFinder.mapping.clear()
        make_pyi._PackageFinder.packages.clear()
        sys.meta_path[:] = old_meta_path
        sys.modules.pop("pkg.consumer", None)
        sys.modules.pop("pkg.provider", None)
        sys.modules.pop("pkg", None)
        monkeypatch.delattr("builtins._semiwrap_test_provider_loaded", raising=False)

    assert output.read_text() == "new_name: int\n"


def test_make_pyi_imports_mapped_libinit_module_before_extension(tmp_path, monkeypatch):
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()
    parent_init = pkg_dir / "__init__.py"
    parent_init.write_text("from . import load_deps\nfrom .compiled import old_name\n")

    init_module = tmp_path / "load_deps.py"
    init_module.write_text("import builtins\nbuiltins._semiwrap_test_init_ran = True\n")

    compiled = tmp_path / "compiled.py"
    compiled.write_text(
        "import builtins\n"
        "if not getattr(builtins, '_semiwrap_test_init_ran', False):\n"
        "    raise ImportError('init module was not imported')\n"
        "new_name = 1\n"
    )

    output = tmp_path / "out.pyi"

    def fake_stubgen_main():
        module_name = sys.argv[-1]
        module = importlib.import_module(module_name)
        assert module.new_name == 1

        outdir = pathlib.Path(sys.argv[sys.argv.index("-o") + 1])
        stub = outdir / "pkg" / "compiled.pyi"
        stub.parent.mkdir(parents=True, exist_ok=True)
        stub.write_text("new_name: int\n")

    monkeypatch.delattr("builtins._semiwrap_test_init_ran", raising=False)
    monkeypatch.setattr(make_pyi.pybind11_stubgen, "main", fake_stubgen_main)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "make_pyi",
            "pkg.compiled",
            "pkg/compiled.pyi",
            str(output),
            "--",
            "pkg",
            str(parent_init),
            "pkg.load_deps",
            str(init_module),
            "pkg.compiled",
            str(compiled),
        ],
    )

    old_meta_path = list(sys.meta_path)
    try:
        make_pyi._PackageFinder.mapping.clear()
        make_pyi.main()
    finally:
        make_pyi._PackageFinder.mapping.clear()
        make_pyi._PackageFinder.packages.clear()
        sys.meta_path[:] = old_meta_path
        sys.modules.pop("pkg.compiled", None)
        sys.modules.pop("pkg.load_deps", None)
        sys.modules.pop("pkg", None)

    assert output.read_text() == "new_name: int\n"
