"""
Creates an output .pyi file from a given python module.

Arguments are:
    package outpath [subpackage outpath...] -- package mapped_file
"""

import importlib.util
import inspect
import os
from os.path import dirname, join
import pathlib
import shutil
import sys
import tempfile
import typing as T

import nanobind.stubgen


class _PackageFinder:
    """
    Custom loader to allow loading built modules from their location
    in the build directory (as opposed to their install location)
    """

    # Set this to mapping returned from _BuiltEnv.setup_built_env
    mapping: T.Dict[str, str] = {}

    @classmethod
    def find_spec(cls, fullname, path, target=None):
        m = cls.mapping.get(fullname)
        if m:
            return importlib.util.spec_from_file_location(fullname, m)


def main():

    argv = sys.argv

    if len(argv) < 3:
        print(inspect.cleandoc(__doc__ or ""), file=sys.stderr)
        sys.exit(1)

    # Package name first
    package_name = argv[1]
    output_file = argv[2]

    # Arguments are used to set up the package map
    package_map = _PackageFinder.mapping
    for i in range(3, len(argv), 2):
        # python 3.9 requires paths to be resolved
        package_map[argv[i]] = os.fspath(pathlib.Path(argv[i + 1]).resolve())

    # Add parent packages too
    # .. assuming there are __init__.py in each package
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
            pkg = ppkg

    sys.meta_path.insert(0, _PackageFinder)

    # TODO: use the stubgen API directly? This seems easier.
    nanobind.stubgen.main(["-m", package_name, "-o", output_file])


if __name__ == "__main__":
    main()
