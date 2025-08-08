"""
Parses a header file and writes an intermediate dat file that other tools
can turn into other things
"""

import argparse
import pathlib
import pickle
import typing

from cxxheaderparser.options import ParserOptions
from cxxheaderparser import preprocessor

import yaml

from ..autowrap.cxxparser import parse_header
from ..autowrap.generator_data import GeneratorData
from ..casters import CastersData
from ..config.autowrap_yml import AutowrapConfigYaml


def format_missing(report) -> str:
    return (
        yaml.safe_dump(report, sort_keys=False)
        .replace(" {}", "")
        .replace("? ''\n          :", '"":')
        .replace("? ''\n      :", '"":')
    )


def generate_wrapper(
    *,
    name: str,
    src_yml: pathlib.Path,
    src_h: pathlib.Path,
    src_h_root: pathlib.Path,
    include_paths: typing.List[pathlib.Path],
    compiler_flavor: str,
    compiler_args: typing.List[str],
    pp_defines: typing.List[str],
    casters: CastersData,
    dst_dat: typing.Optional[pathlib.Path],
    dst_depfile: typing.Optional[pathlib.Path],
    report_only: bool,
    warn_on_missing_header: bool = True,
):

    try:
        # semiwrap requires user to create yaml files first using update-yaml
        data = AutowrapConfigYaml.from_file(src_yml)
    except FileNotFoundError:
        if not report_only:
            raise

        if warn_on_missing_header:
            print("WARNING: could not find", src_yml)

        data = AutowrapConfigYaml()

    deptarget = None
    if dst_depfile is not None:
        assert dst_dat is not None
        deptarget = [str(dst_dat)]

    if compiler_flavor == "gcc":

        def make_preprocessor(*args, **kwargs):
            return preprocessor.make_gcc_preprocessor(
                print_cmd=False, gcc_args=compiler_args, *args, **kwargs
            )

    # elif compiler_flavor == "msvc":
    #   .. cxxheaderparser's msvc support doesn't generate a depfile, so it's not usable
    #      without breaking incremental build
    else:
        make_preprocessor = preprocessor.make_pcpp_preprocessor

    popts = ParserOptions(
        preprocessor=make_preprocessor(
            defines=pp_defines,
            include_paths=include_paths,
            encoding=data.encoding,
            depfile=dst_depfile,
            deptarget=deptarget,
        )
    )

    gendata = GeneratorData(data, src_yml)

    try:
        hctx = parse_header(
            name,
            src_h,
            src_h_root,
            gendata,
            popts,
            casters,
            report_only,
        )
    except Exception as e:
        raise ValueError(f"processing {src_h}") from e

    missing = gendata.get_missing()

    if not report_only and missing and not data.defaults.ignore:
        print("WARNING: some items not in", src_yml, "for", src_h)
        print(format_missing(missing))

    if dst_dat is not None:
        with open(dst_dat, "wb") as fp:
            pickle.dump(hctx, fp)

    return missing


def make_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-I", "--include-paths", action="append", default=[])
    parser.add_argument("-D", "--defines", action="append", default=[])
    parser.add_argument("--cpp")
    parser.add_argument("name")
    parser.add_argument("src_yml", type=pathlib.Path)
    parser.add_argument("src_h", type=pathlib.Path)
    parser.add_argument("src_h_root", type=pathlib.Path)
    parser.add_argument("in_casters", type=pathlib.Path)
    parser.add_argument("dst_dat", type=pathlib.Path)
    parser.add_argument("dst_depfile", type=pathlib.Path)
    parser.add_argument("compiler_flavor")
    parser.add_argument("cpp_std")
    parser.add_argument("compiler_args", nargs="+")
    parser.add_argument("--update-yaml", action="store_true", default=False)
    return parser


def main():
    parser = make_argparser()
    args = parser.parse_args()

    if not args.update_yaml:
        dst_dat = args.dst_dat
        dst_depfile = args.dst_depfile
        report_only = False
        warn_on_missing_header = True

        with open(args.in_casters, "rb") as fp:
            casters = pickle.load(fp)
    else:
        dst_dat = None
        dst_depfile = None
        report_only = True
        warn_on_missing_header = False
        casters = {}

    compiler_args = args.compiler_args

    if args.compiler_flavor == "gcc":
        compiler_args.append(f"-std={args.cpp_std}")
    else:
        compiler_args.append(f"/std:{args.cpp_std}")

    if args.cpp and args.compiler_flavor != "gcc":
        args.defines.append(f"__cplusplus {args.cpp}")

    missing = generate_wrapper(
        name=args.name,
        src_yml=args.src_yml,
        src_h=args.src_h,
        src_h_root=args.src_h_root,
        dst_dat=dst_dat,
        dst_depfile=dst_depfile,
        include_paths=args.include_paths,
        compiler_flavor=args.compiler_flavor,
        compiler_args=compiler_args,
        casters=casters,
        pp_defines=args.defines,
        report_only=report_only,
        warn_on_missing_header=warn_on_missing_header,
    )

    if args.update_yaml:
        report = format_missing(missing)
        args.src_yml.parent.mkdir(parents=True, exist_ok=True)
        with open(args.src_yml, "w") as fp:
            fp.write(report)


if __name__ == "__main__":
    main()
