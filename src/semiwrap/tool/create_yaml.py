import os
import pathlib
import sys
import traceback
import typing as T

from ..autowrap.generator_data import MissingReporter
from ..cmd.header2dat import make_argparser, generate_wrapper
from ..makeplan import InputFile, makeplan, BuildTarget, CompilerInfo


class GenCreator:
    @classmethod
    def add_subparser(cls, parent_parser, subparsers):
        parser = subparsers.add_parser(
            "create-yaml",
            help="Create YAML files from parsed header files",
            parents=[parent_parser],
        )
        parser.add_argument(
            "--write", help="Write to files if they don't exist", action="store_true"
        )
        parser.add_argument(
            "-v", "--verbose", help="Show full traceback", action="store_true"
        )

        return parser

    def run(self, args):
        try:
            self._run(args)
        except Exception as e:
            # Reading the stack trace is annoying, most of the time the exception content
            # is enough to figure out what you did wrong.
            if args.verbose:
                raise

            msg = [
                "ERROR: exception occurred when generating YAML from `pyproject.toml` config\n\n",
            ]

            msg += traceback.format_exception_only(type(e), e)
            cause = e.__context__
            while cause is not None:

                el = traceback.format_exception_only(type(cause), cause)
                el[0] = f"- caused by {el[0]}"
                msg += el

                if cause.__suppress_context__:
                    break

                cause = cause.__context__

            msg.append("\nUse -v/--verbose option for stacktrace")

            print("".join(msg), file=sys.stderr)
            sys.exit(1)

    def _run(self, args):
        project_root = pathlib.Path.cwd()

        # Problem: if another hatchling plugin sets PKG_CONFIG_PATH to include a .pc
        # file, makeplan() will fail to find it, which prevents a semiwrap program
        # from consuming those .pc files.
        #
        # We search for .pc files in the project root by default and add anything found
        # to the PKG_CONFIG_PATH to allow that to work. Probably won't hurt anything?

        pcpaths: T.Set[str] = set()
        for pcfile in project_root.glob("**/*.pc"):
            pcpaths.add(str(pcfile.parent))

        if pcpaths:
            # Add to PKG_CONFIG_PATH so that it can be resolved by other hatchling
            # plugins if desired
            pkg_config_path = os.environ.get("PKG_CONFIG_PATH")
            if pkg_config_path is not None:
                os.environ["PKG_CONFIG_PATH"] = os.pathsep.join(
                    (pkg_config_path, *pcpaths)
                )
            else:
                os.environ["PKG_CONFIG_PATH"] = os.pathsep.join(pcpaths)

        plan = makeplan(project_root, missing_yaml_ok=True)

        for item in plan:
            if not isinstance(item, BuildTarget) or item.command != "header2dat":
                continue

            # convert args to string so we can parse it
            # .. this is weird, but less annoying than other alternatives
            #    that I can think of?
            argv = []
            for arg in item.args:
                if isinstance(arg, str):
                    argv.append(arg)
                elif isinstance(arg, InputFile):
                    argv.append(str(arg.path.absolute()))
                elif isinstance(arg, pathlib.Path):
                    argv.append(str(arg.absolute()))
                elif isinstance(arg, CompilerInfo):
                    argv += ["pcpp", "ignored", "ignored"]
                else:
                    # anything else shouldn't matter
                    argv.append("ignored")

            sparser = make_argparser()
            sargs = sparser.parse_args(argv)

            reporter = MissingReporter()

            if sargs.cpp:
                sargs.defines.append(f"__cplusplus {sargs.cpp}")

            generate_wrapper(
                name=sargs.name,
                src_yml=sargs.src_yml,
                src_h=sargs.src_h,
                src_h_root=sargs.src_h_root,
                dst_dat=None,
                dst_depfile=None,
                include_paths=sargs.include_paths,
                compiler_flavor="pcpp",
                compiler_args=[],
                casters={},
                pp_defines=sargs.defines,
                missing_reporter=reporter,
                report_only=True,
            )

            if reporter:
                for name, report in reporter.as_yaml():
                    report = f"---\n\n{report}"

                    if args.write:
                        if not name.exists():
                            name.parent.mkdir(parents=True, exist_ok=True)
                            print("Writing", name)
                            with open(name, "w") as fp:
                                fp.write(report)
                        else:
                            print(name, "already exists!")

                    print("===", name, "===")
                    print(report)
