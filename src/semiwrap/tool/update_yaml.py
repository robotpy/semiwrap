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
from ..pyproject import PyProject


class YamlUpdater:
    """
    This class will parse the headers for a semiwrap project and create or update their corresponding yaml files.

    The process for doing this goes as such:
        1. Parse the headers and generate .yml files into a temporary directory
        2. Merge the additions / deletions from the fresh generation with the backups
        3. Output the differences
        4. Optionally write the changes to the files

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
            "--write", help="Write to files if they don't exist", action="store_true"
        )
        parser.add_argument(
            "-v", "--verbose", help="Show full traceback", action="store_true"
        )

        return parser

    def run(self, args):
        try:
            with tempfile.TemporaryDirectory() as gendir:
                return self._run(args, pathlib.Path(gendir))
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

    def _run(self, args, generated_dir: pathlib.Path):
        project_root = args.project_file.parent

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
                    # Causes missing content to be written to generated directory
                    if arg.path.name.endswith(".yml"):
                        argv.append(str(generated_dir / arg.path))
                    else:
                        argv.append(str(arg.path))
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
                warn_on_missing_header=False,
            )

            if missing:
                report = format_missing(missing)
                name = sargs.src_yml

                name.parent.mkdir(parents=True, exist_ok=True)
                with open(name, "w") as fp:
                    fp.write(report)

        files_updated = self.merge_data(args.write, project_root, generated_dir)

        if args.write:
            print(files_updated, "files were updated")
            return True

        # When not writing, return True if no changes needed, False otherwise

        if files_updated == 0:
            print("All files up to date")
        else:
            print(
                files_updated,
                "files need to be updated (use --write to apply the changes)",
            )

        return files_updated == 0

    def merge_data(
        self,
        write: bool,
        project_root: pathlib.Path,
        generated_directory: pathlib.Path,
    ):
        files_updated = 0

        if not write:
            print("\n\n" + "*" * 20 + "\nDry Run Results\n" + "*" * 20)

        # Collect original YAML files for diff
        original_files = set()
        pyproject = PyProject(project_root)
        for extcfg in pyproject.project.extension_modules.values():
            original_files |= set(
                pyproject.get_extension_yaml_path(extcfg).glob("**/*.yml")
            )

        generated_files = set()
        for f in generated_directory.glob("**/*.yml"):
            generated_files.add(f.relative_to(generated_directory))

        # Delete files that are no longer used in generation
        deleted_files = original_files.difference(generated_files)
        for file_to_delete in deleted_files:
            files_updated += 1
            if write:
                print(f"Deleting unused file {file_to_delete}")
                os.unlink(file_to_delete)
            else:
                print(f"Would delete {file_to_delete}")

        # Add new files
        added_files = generated_files.difference(original_files)
        for f in added_files:
            files_updated += 1
            output_file = project_root / f
            if write:
                output_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(generated_directory / f, output_file)
                print(f"Added new file {output_file}")
            else:
                print(f"Would create {output_file}")

            print((generated_directory / f).read_text())

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

        common_files = original_files.intersection(generated_files)
        for f in sorted(common_files):
            with open(generated_directory / f) as fp:
                generated = yaml_.load(fp)
            with open(project_root / f) as fp:
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

            # Output a diff
            output_file = project_root / f

            with open(output_file, "r") as of:
                output_lines = of.readlines()

            strbuff = StringIO()
            yaml_.dump(original, strbuff)
            strbuff.seek(0)
            merged_lines = strbuff.readlines()

            differences = difflib.unified_diff(
                output_lines,
                merged_lines,
                fromfile=str(f),
                tofile=str(f),
            )
            differences = list(differences)

            if differences:
                files_updated += 1

                print("Diff for", output_file)
                for difference in differences:
                    print(difference.rstrip())
                print()

                if write:
                    with open(output_file, "w") as fp:
                        strbuff.seek(0)
                        shutil.copyfileobj(strbuff, fp)

        return files_updated
