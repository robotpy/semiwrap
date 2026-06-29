"""
Creates an output .pyi file from a given python module.

Arguments are:
    package outpath [subpackage outpath...] -- package mapped_file
"""

import ast
import builtins
import importlib
import importlib.abc
import importlib.machinery
import importlib.util
import inspect
import os
from os.path import dirname, join
import pathlib
import shutil
import sys
import tempfile
import typing as T

import pybind11_stubgen


def _safe_eval_package_alias_expr(expr: ast.expr, module) -> T.Any:
    if isinstance(expr, ast.Constant):
        return expr.value
    if isinstance(expr, ast.Name):
        if hasattr(module, expr.id):
            return getattr(module, expr.id)
        if hasattr(builtins, expr.id):
            return getattr(builtins, expr.id)
    raise ValueError


def _is_self_package_import(module_name: str, import_name: str) -> bool:
    return import_name == module_name or import_name.startswith(f"{module_name}.")


def _populate_safe_package_members(module, filename: str):
    try:
        source = pathlib.Path(filename).read_text()
        tree = ast.parse(source, filename=filename)
    except (OSError, SyntaxError, UnicodeDecodeError):
        return

    for stmt in tree.body:
        if isinstance(stmt, ast.Import):
            for alias in stmt.names:
                if _is_self_package_import(module.__name__, alias.name):
                    continue
                imported = importlib.import_module(alias.name)
                if alias.asname:
                    setattr(module, alias.asname, imported)
                else:
                    attr_name = alias.name.split(".", 1)[0]
                    setattr(module, attr_name, importlib.import_module(attr_name))
        elif isinstance(stmt, ast.ImportFrom):
            if stmt.level != 0 or stmt.module is None:
                continue
            if _is_self_package_import(module.__name__, stmt.module):
                continue
            imported = importlib.import_module(stmt.module)
            for alias in stmt.names:
                if alias.name == "*":
                    continue
                setattr(
                    module, alias.asname or alias.name, getattr(imported, alias.name)
                )
        elif isinstance(stmt, ast.Assign):
            try:
                value = _safe_eval_package_alias_expr(stmt.value, module)
            except ValueError:
                continue
            for target in stmt.targets:
                if isinstance(target, ast.Name):
                    setattr(module, target.id, value)
        elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
            if stmt.value is None:
                continue
            try:
                value = _safe_eval_package_alias_expr(stmt.value, module)
            except ValueError:
                continue
            setattr(module, stmt.target.id, value)


class _PackageLoader(importlib.abc.Loader):
    def __init__(self, filename: str):
        self.filename = filename

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        module.__file__ = self.filename
        module.__path__ = [dirname(self.filename)]
        _populate_safe_package_members(module, self.filename)


class _PackageFinder:
    """
    Custom loader to allow loading built modules from their location
    in the build directory (as opposed to their install location)
    """

    # Set these to mappings returned from main()
    mapping: T.Dict[str, str] = {}
    packages: T.Set[str] = set()

    @classmethod
    def find_spec(cls, fullname, path, target=None):
        m = cls.mapping.get(fullname)
        if m:
            if fullname in cls.packages:
                return importlib.util.spec_from_loader(
                    fullname, _PackageLoader(m), origin=m, is_package=True
                )
            return importlib.util.spec_from_file_location(fullname, m)


_EXTENSION_SUFFIXES = tuple(importlib.machinery.EXTENSION_SUFFIXES)


def _is_importable_mapped_module(module_path: str) -> bool:
    path = pathlib.Path(module_path)
    return path.suffix == ".py" or path.name.endswith(_EXTENSION_SUFFIXES)


def _import_mapped_modules(
    package_name: str, package_map: T.Dict[str, str], package_pkgs: T.Set[str]
):
    for module_name, module_path in package_map.items():
        if module_name == package_name or module_name in package_pkgs:
            continue
        if not _is_importable_mapped_module(module_path):
            continue
        importlib.import_module(module_name)


def _write_pyi(
    package_name, generated_pyi: T.Dict[pathlib.PurePosixPath, pathlib.Path]
):

    # We can't control where stubgen writes files, so tell it to output
    # to a temporary directory and then we copy the files from there to
    # our desired location
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_pth = pathlib.Path(tmpdir)

        # Call pybind11-stubgen
        sys.argv = [
            "<dummy>",
            "--exit-code",
            "--ignore-invalid-expressions=<.*>",
            "--root-suffix=",
            "-o",
            tmpdir,
            package_name,
        ]

        # Create the parent directories in the temporary directory
        for infile in generated_pyi.keys():
            (tmpdir_pth / infile).parent.mkdir(parents=True, exist_ok=True)

        # Fix typing.Annotated bug in < 3.8
        # - the Right Fix would be to emit typing_extensions.Annotated in pybind11,
        #   but Python 3.8 support will go away soon so not worth it
        if sys.version_info < (3, 9):
            import typing_extensions

            T.Annotated = typing_extensions.Annotated

        pybind11_stubgen.main()

        # stubgen doesn't take a direct output filename, so move the file
        # to our desired location
        for infile, output in generated_pyi.items():
            output.unlink(missing_ok=True)
            shutil.move(tmpdir_pth / infile, output)


def main():

    generated_pyi: T.Dict[pathlib.PurePosixPath, pathlib.Path] = {}
    argv = sys.argv

    if len(argv) < 3:
        print(inspect.cleandoc(__doc__ or ""), file=sys.stderr)
        sys.exit(1)

    # Package name first
    package_name = argv[1]

    # Output file map: input output
    idx = 2
    while idx < len(argv):
        if argv[idx] == "--":
            idx += 1
            break

        generated_pyi[pathlib.PurePosixPath(argv[idx])] = pathlib.Path(argv[idx + 1])
        idx += 2

    # Arguments are used to set up the package map
    package_map = _PackageFinder.mapping
    for i in range(idx, len(argv), 2):
        # python 3.9 requires paths to be resolved
        package_map[argv[i]] = os.fspath(pathlib.Path(argv[i + 1]).resolve())

    # Add parent packages too. These are synthesized as package modules instead
    # of executing their source __init__.py files; the source package can contain
    # stale autogenerated imports while make_pyi is regenerating stubs after a
    # name transform change.
    package_pkgs = _PackageFinder.packages
    package_pkgs.clear()
    for pkg in list(package_map.keys()):
        while True:
            idx = pkg.rfind(".")
            if idx == -1:
                break
            ppkg = pkg[:idx]
            if ppkg not in package_map:
                package_map[ppkg] = join(
                    dirname(dirname(package_map[pkg])), "__init__.py"
                )
                package_pkgs.add(ppkg)
            elif pathlib.Path(package_map[ppkg]).name == "__init__.py":
                package_pkgs.add(ppkg)
            pkg = ppkg

    sys.meta_path.insert(0, _PackageFinder)

    _import_mapped_modules(package_name, package_map, package_pkgs)
    _write_pyi(package_name, generated_pyi)


if __name__ == "__main__":
    main()
