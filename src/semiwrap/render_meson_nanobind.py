#
# The generated meson.build contents are mostly copied from
# https://github.com/mesonbuild/wrapdb/blob/master/subprojects/packagefiles/nanobind/meson.build
# which is covered by an MIT license
#
#
# Copyright (c) 2021 The Meson development team
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import pathlib
import textwrap
import sys
import typing as T

import nanobind

from .autowrap.buffer import RenderBuffer
from .render_meson_util import make_include_path_str, make_meson_string


def render_nanobind_dep(
    r: RenderBuffer,
    meson_build_path: T.Optional[pathlib.Path],
):
    nb_cmake_dir = pathlib.Path(nanobind.cmake_dir()).as_posix()
    nb_include_dir = pathlib.Path(nanobind.include_dir()).resolve().as_posix()

    # Nanobind depends on robin-map, and embeds it in its wheel (but doesn't
    # explicitly expose it), so we cheat here
    rm_include_dir = (
        pathlib.Path(nanobind.__file__).parent.resolve()
        / "ext"
        / "robin_map"
        / "include"
    ).as_posix()

    # Both nb_include_dir and rm_include_dir are included via -I instead of
    # include_directories because on Windows they may be on different drives,
    # and include_directories only accepts relative paths

    r.writeln()
    r.write_trim(
        f"""
        #
        # meson magic for linking to nanobind instead of using WrapDB
        #

        meson.override_dependency(
            'robin-map',
            declare_dependency(
                compile_args: [{make_meson_string('-I' + rm_include_dir)}]
            ),
        )

        # Arguments are derived from nanobind_build_library() in CMake configuration.
        _sw_nb_dep_compile_args = [{make_meson_string('-I' + nb_include_dir)}]
        _sw_nb_dep_link_args = []

        if meson.get_compiler('cpp').get_argument_syntax() == 'msvc'
            _sw_nb_dep_compile_args += ['/D_CRT_SECURE_NO_WARNINGS']
        endif

        # Discussion in WrapDB PR #1556 as to whether or not the following is necessary:
        # _sw_nb_dep_compile_args += ['-fno-strict-aliasing']

        if sw_py.get_variable('Py_GIL_DISABLED', 0) != 0
            _sw_nb_dep_compile_args += ['-DNB_FREE_THREADED']
        endif

        if not get_option('debug')
            _sw_nb_dep_compile_args += ['-DNB_COMPACT_ASSERTIONS']

            # The following, from nanobind_strip(), applies both to the nanobind shared
            # library (if it's built) and to the developer's extension:
            if host_machine.system() == 'darwin'
                _sw_nb_dep_link_args += ['-Wl,-dead_strip', '-Wl,-x', '-Wl,-S']
            elif host_machine.system() != 'windows'
                _sw_nb_dep_link_args += ['-Wl,-s']
            endif
        endif

        if host_machine.system() == 'darwin'
            if sw_py.get_variable('SOABI').startswith('cp')
                _sw_nb_resp_file = {make_meson_string(nb_cmake_dir)} / 'darwin-ld-cpython.sym'
            else
                _sw_nb_resp_file = {make_meson_string(nb_cmake_dir)} / 'darwin-ld-pysw_py.sym'
            endif
            _sw_nb_dep_link_args += ['-Wl,@' + _sw_nb_resp_file]
        endif

        # We always link statically
        #if get_option('default_library') == 'shared'
        #    _sw_nb_dep_compile_args += ['-DNB_SHARED']
        #endif

        if host_machine.system() != 'windows' and host_machine.system() != 'darwin'
            _sw_nb_dep_compile_args += ['-ffunction-sections', '-fdata-sections']
            _sw_nb_dep_link_args += ['-Wl,--gc-sections']
        endif

        # meson won't build something out of tree, so generate a file and ask it
        # to build that instead
        _sw_nb_src = custom_target(
            command: [sw_py, '-m', 'semiwrap.render_meson_nanobind', '@OUTPUT@'],
            output: 'sw_nb_combined.cpp',
        )

        meson.override_dependency(
            'nanobind',
            declare_dependency(
                sources: [_sw_nb_src],
                dependencies: [dependency('robin-map')],
                compile_args: _sw_nb_dep_compile_args,
                link_args: _sw_nb_dep_link_args,
                version: {make_meson_string(nanobind.__version__)}
            )
        )
        """
    )


if __name__ == "__main__":
    _, out = sys.argv

    nb_sourcedir = pathlib.Path(nanobind.source_dir())

    with open(out, "w") as fp:
        fp.write(
            textwrap.dedent(
                f"""
            // This file is automatically generated, DO NOT EDIT

            #include <{nb_sourcedir.as_posix()}/nb_combined.cpp>
            """
            )
        )
