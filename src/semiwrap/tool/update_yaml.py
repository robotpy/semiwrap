import os
import pathlib
import sys
import traceback
import tempfile
import typing as T
import shutil
import difflib
import dictdiffer
import dictdiffer.utils
from io import StringIO
from ruamel.yaml import YAML

from ..cmd.header2dat import make_argparser, generate_wrapper, format_missing
from ..makeplan import InputFile, makeplan, BuildTarget, CompilerInfo


class YamlUpdater:
    """
    This class will parse the headers for a semiwrap project and create or update their corresponding yaml files.

    The process for doing this goes as such:
        1. Copy backups of the yaml files into a temporary directory
        2. Make a temporary directory where the headers will be parsed from scratch
        3. Merge the additions / deletions from the fresh generation with the backups, and place them into the desired output folder

    It is made to handle custom output directories, but by default it will behave as if it was run "in place"

    This process will keep hand edited values like "ignore", "extra_includes", etc, but should be smart enough to delete config
    items that no longer exist.
    """

    @classmethod
    def add_subparser(cls, parent_parser, subparsers):
        parser = subparsers.add_parser(
            "update-yaml",
            help="Updates YAML files from parsed header files",
            parents=[parent_parser],
        )
        parser.add_argument(
            "--project_file",
            help="The path to the pyproject.toml file",
            type=pathlib.Path,
            default=pathlib.Path("./pyproject.toml"),
        )
        parser.add_argument(
            "--output_directory",
            help="Where the updated yaml files will be written",
            type=pathlib.Path,
            default=pathlib.Path("semiwrap"),
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
            is_dirty = self._run(args)
            if is_dirty:
                print(
                    "Changes have been detected in the yaml files. Run again and add --write to fix"
                )
            return not is_dirty
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
        project_root = args.project_file.parent.absolute()

        output_directory = args.output_directory.absolute()

        tmp_backup_dir = tempfile.TemporaryDirectory()
        backup_dir = pathlib.Path(tmp_backup_dir.name)
        shutil.copytree(project_root / "semiwrap", backup_dir / "semiwrap")

        tmp_generated_dir = tempfile.TemporaryDirectory()
        generated_dir = pathlib.Path(tmp_generated_dir.name)
        os.chdir(generated_dir)

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

            if sargs.cpp:
                sargs.defines.append(f"__cplusplus {sargs.cpp}")

            missing = generate_wrapper(
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
                report_only=True,
            )

            if missing:
                report = format_missing(missing)
                name = sargs.src_yml

                name.parent.mkdir(parents=True, exist_ok=True)
                with open(name, "w") as fp:
                    fp.write(report)

        is_dirty = self.merge_data(
            args.write, generated_dir, backup_dir, output_directory
        )

        # Windows can freak out if you are in a temp directory when it tries to get deleted, so just move elsewhere
        os.chdir("..")

        return is_dirty

    def merge_data(
        self,
        write: bool,
        generated_directory: pathlib.Path,
        backup_directory: pathlib.Path,
        output_directory: pathlib.Path,
    ):
        is_dirty = False

        if not write:
            print("\n\n" + "*" * 20 + "\nDry Run Results\n" + "*" * 20)
        generated_files = set()
        for root, _, files in os.walk(generated_directory):
            for f in files:
                generated_files.add(
                    (pathlib.Path(root) / f).relative_to(generated_directory)
                )

        backup_files = set()
        for root, _, files in os.walk(backup_directory):
            for f in files:
                backup_files.add((pathlib.Path(root) / f).relative_to(backup_directory))

        # In the event that the output directory is the same as the project directory, explicit delete files that are
        # no longer used in generation
        deleted_files = backup_files.difference(generated_files)
        for f in deleted_files:
            if f.suffix == ".yml":
                file_to_delete = output_directory / f
                if write:
                    print(f"Deleting unused file {file_to_delete}")
                    # It will only exist if the output directory is the same as the original directory.
                    # This would be true in the default case, but not if the tool is invoked from bazel
                    if file_to_delete.exists():
                        os.unlink(file_to_delete)
                else:
                    is_dirty = True
                    print(f"Would delete {file_to_delete}")

        # Add new files
        added_files = generated_files.difference(backup_files)
        for f in added_files:
            output_file = output_directory / f
            if write:
                output_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(f, output_file)
                print(f"Added new file {output_file}")
            else:
                is_dirty = True
                print(f"Would add this following file {output_file}")
                print(f.read_text())

        # Setup the yaml parser with some default arguments
        yaml_ = YAML()
        yaml_.default_flow_style = False
        yaml_.preserve_quotes = True
        yaml_.width = 4096  # Super long width to prevent line wrapping

        GENERATED_KEYWORDS = [
            "enums",
            "functions",
            "classes",
            "methods",
            "attributes",
            "overloads",
        ]

        common_files = backup_files.intersection(generated_files)
        for f in common_files:
            with open(generated_directory / f) as fp:
                generated = yaml_.load(fp)
            with open(backup_directory / f) as fp:
                original = yaml_.load(fp)

            diffs = dictdiffer.diff(original, generated)

            additions = []

            for diff in diffs:
                action = diff[0]
                # The freshly generated version has added something. We will track a list and apply it at the end, in case that chunk is "ignored"
                if action == "add":
                    additions.append(diff)

                elif action == "change":
                    old_value, new_value = diff[2]
                    # When the new value is None, it is basically equivalent to a deletion, which we don't want to do.
                    if new_value is not None:
                        original = dictdiffer.patch([diff], original)

                # The freshly generated version has removed something. This might be a legitimate removal, like a function being deleted, or it might be deleting some hand tweaked code that we want to keep.
                elif action == "remove":
                    removals = diff[2]
                    for removal in removals:
                        # Make a patch that contains just this one removal
                        modified_diff = [(diff[0], diff[1], [removal])]

                        # Check if the removal is a full deletion of one of the keywords
                        #
                        # i.e. [('remove', 'classes.frc::Encoder', [('enums', {'IndexingType': None})])]
                        # indicates that the enum block was completely removed
                        if removal[0] in GENERATED_KEYWORDS:
                            original = dictdiffer.patch(modified_diff, original)
                            continue

                        # Check if this removal is a sub-change of one of the keywords
                        #
                        # i.e. [('remove', 'classes.frc::Encoder.methods', [('PIDGet', {'rename': 'pidGet'})])]
                        # indicates that the PIDGet function was removed, while other Encoder.methods remain.
                        for item in GENERATED_KEYWORDS:
                            if diff[1].endswith(item):
                                original = dictdiffer.patch(modified_diff, original)
                                break

            # Patch all of the additions while being aware of if the file / class / etc has been marked as "ignore"
            if not original.get("defaults", {}).get("ignore", False):
                for addition in additions:
                    original_contents = dictdiffer.utils.dot_lookup(
                        original, addition[1]
                    )
                    if original_contents.get("ignore", False):
                        continue
                    original = dictdiffer.patch(additions, original)

            output_file = output_directory / f.relative_to("semiwrap")

            if write:
                output_file.parent.mkdir(parents=True, exist_ok=True)

                with open(output_file, "w") as f:
                    yaml_.dump(original, f)
            else:
                # Original dir might be the same as the output dir, so we have to dump it into a string
                # rather than risk writing the file and doing a simpler diff.
                strbuff = StringIO()
                yaml_.dump(original, strbuff)
                strbuff.seek(0)
                merged_lines = strbuff.readlines()

                with open(output_file, "r") as of:
                    output_lines = of.readlines()

                differences = difflib.unified_diff(
                    output_lines,
                    merged_lines,
                    fromfile=str(f),
                    tofile=str(f),
                )
                differences = list(differences)

                if differences:
                    is_dirty = True
                    print("Diff for ", output_file)
                    for difference in differences:
                        print(difference.rstrip())
                    print()

        return is_dirty
