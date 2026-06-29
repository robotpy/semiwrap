from __future__ import annotations

import os
import pathlib
import re
import subprocess
import sys

from semiwrap.cmd import make_pyi

SRC_DIR = pathlib.Path(__file__).resolve().parents[1] / "src"


def _pythonpath(*paths: pathlib.Path) -> str:
    entries = [str(SRC_DIR), *(str(path) for path in paths)]
    existing = os.environ.get("PYTHONPATH")
    if existing:
        entries.append(existing)
    return os.pathsep.join(entries)


def _run_make_pyi(
    tmp_path: pathlib.Path,
    package_name: str,
    input_pyi: str,
    output: pathlib.Path,
    *module_map: tuple[str, pathlib.Path],
):
    args = [
        sys.executable,
        "-m",
        "semiwrap.cmd.make_pyi",
        package_name,
        input_pyi,
        str(output),
        "--",
    ]
    for module_name, module_path in module_map:
        args.extend([module_name, str(module_path)])

    proc = subprocess.run(
        args,
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": _pythonpath(tmp_path)},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )

    assert proc.returncode == 0, (
        f"make_pyi failed with exit code {proc.returncode}\n"
        f"command: {' '.join(args)}\n"
        f"stdout:\n{proc.stdout}\n"
        f"stderr:\n{proc.stderr}"
    )


def _assert_generated_name(output: pathlib.Path):
    generated = output.read_text()
    assert re.search(r"^new_name: int(?: = 1)?$", generated, re.MULTILINE)


def test_make_pyi_treats_extension_suffix_mappings_as_importable():
    extension_path = f"provider{make_pyi._EXTENSION_SUFFIXES[0]}"

    assert make_pyi._is_importable_mapped_module(extension_path)


def test_make_pyi_imports_extension_without_executing_stale_parent_init(tmp_path):
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()
    parent_init = pkg_dir / "__init__.py"
    parent_init.write_text("from .compiled import old_name\n")

    compiled = tmp_path / "compiled.py"
    compiled.write_text("new_name = 1\n")

    output = tmp_path / "out.pyi"

    _run_make_pyi(
        tmp_path,
        "pkg.compiled",
        "pkg/compiled.pyi",
        output,
        ("pkg", parent_init),
        ("pkg.compiled", compiled),
    )

    _assert_generated_name(output)


def test_make_pyi_exposes_parent_init_aliases_without_executing_stale_imports(
    tmp_path,
):
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()
    parent_init = pkg_dir / "__init__.py"
    parent_init.write_text("Alias = int\nfrom .compiled import old_name\n")

    compiled = tmp_path / "compiled.py"
    compiled.write_text(
        "import pkg\n"
        "if pkg.Alias is not int:\n"
        "    raise ImportError('parent Alias was not replayed')\n"
        "new_name = 1\n"
    )

    output = tmp_path / "out.pyi"

    _run_make_pyi(
        tmp_path,
        "pkg.compiled",
        "pkg/compiled.pyi",
        output,
        ("pkg", parent_init),
        ("pkg.compiled", compiled),
    )

    _assert_generated_name(output)


def test_make_pyi_imports_parent_init_absolute_dependencies_without_stale_imports(
    tmp_path,
):
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()
    parent_init = pkg_dir / "__init__.py"
    parent_init.write_text("import dependency\nfrom .compiled import old_name\n")

    dependency = tmp_path / "dependency.py"
    dependency.write_text(
        "import builtins\nbuiltins._semiwrap_test_dependency_loaded = True\n"
    )

    compiled = tmp_path / "compiled.py"
    compiled.write_text(
        "import builtins\n"
        "if not getattr(builtins, '_semiwrap_test_dependency_loaded', False):\n"
        "    raise ImportError('dependency module was not imported')\n"
        "new_name = 1\n"
    )

    output = tmp_path / "out.pyi"

    _run_make_pyi(
        tmp_path,
        "pkg.compiled",
        "pkg/compiled.pyi",
        output,
        ("pkg", parent_init),
        ("pkg.compiled", compiled),
    )

    _assert_generated_name(output)


def test_make_pyi_replays_aliases_using_package_globals_before_builtins(tmp_path):
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()
    parent_init = pkg_dir / "__init__.py"
    parent_init.write_text("int = str\nAlias = int\nfrom .compiled import old_name\n")

    compiled = tmp_path / "compiled.py"
    compiled.write_text(
        "import pkg\n"
        "if pkg.Alias is not str:\n"
        "    raise ImportError('parent Alias did not use package globals')\n"
        "new_name = 1\n"
    )

    output = tmp_path / "out.pyi"

    _run_make_pyi(
        tmp_path,
        "pkg.compiled",
        "pkg/compiled.pyi",
        output,
        ("pkg", parent_init),
        ("pkg.compiled", compiled),
    )

    _assert_generated_name(output)


def test_make_pyi_replays_dotted_import_binding_like_python(tmp_path):
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()
    parent_init = pkg_dir / "__init__.py"
    parent_init.write_text(
        "import dependency_pkg.sub\nfrom .compiled import old_name\n"
    )

    dependency_pkg = tmp_path / "dependency_pkg"
    dependency_pkg.mkdir()
    (dependency_pkg / "__init__.py").write_text("")
    (dependency_pkg / "sub.py").write_text("")

    compiled = tmp_path / "compiled.py"
    compiled.write_text(
        "import sys\n"
        "import pkg\n"
        "if pkg.dependency_pkg is not sys.modules['dependency_pkg']:\n"
        "    raise ImportError('dotted import did not bind the top-level package')\n"
        "new_name = 1\n"
    )

    output = tmp_path / "out.pyi"

    _run_make_pyi(
        tmp_path,
        "pkg.compiled",
        "pkg/compiled.pyi",
        output,
        ("pkg", parent_init),
        ("pkg.compiled", compiled),
    )

    _assert_generated_name(output)


def test_make_pyi_imports_mapped_modules_before_stubgen(tmp_path):
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()
    parent_init = pkg_dir / "__init__.py"
    parent_init.write_text("# synthetic package should not execute this\n")

    marker = tmp_path / "provider-loaded"

    provider = tmp_path / "provider.py"
    provider.write_text(
        "import pathlib\n" f"pathlib.Path({str(marker)!r}).write_text('loaded')\n"
    )

    consumer = tmp_path / "consumer.py"
    consumer.write_text(
        "import pathlib\n"
        f"if not pathlib.Path({str(marker)!r}).exists():\n"
        "    raise ImportError('provider module was not imported')\n"
        "new_name = 1\n"
    )

    output = tmp_path / "out.pyi"

    _run_make_pyi(
        tmp_path,
        "pkg.consumer",
        "pkg/consumer.pyi",
        output,
        ("pkg", parent_init),
        ("pkg.provider", provider),
        ("pkg.consumer", consumer),
    )

    _assert_generated_name(output)
    assert marker.read_text() == "loaded"


def test_make_pyi_imports_mapped_libinit_module_before_extension(tmp_path):
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir()
    parent_init = pkg_dir / "__init__.py"
    parent_init.write_text("from . import load_deps\nfrom .compiled import old_name\n")

    marker = tmp_path / "init-ran"

    init_module = tmp_path / "load_deps.py"
    init_module.write_text(
        "import pathlib\n" f"pathlib.Path({str(marker)!r}).write_text('loaded')\n"
    )

    compiled = tmp_path / "compiled.py"
    compiled.write_text(
        "import pathlib\n"
        f"if not pathlib.Path({str(marker)!r}).exists():\n"
        "    raise ImportError('init module was not imported')\n"
        "new_name = 1\n"
    )

    output = tmp_path / "out.pyi"

    _run_make_pyi(
        tmp_path,
        "pkg.compiled",
        "pkg/compiled.pyi",
        output,
        ("pkg", parent_init),
        ("pkg.load_deps", init_module),
        ("pkg.compiled", compiled),
    )

    _assert_generated_name(output)
    assert marker.read_text() == "loaded"
