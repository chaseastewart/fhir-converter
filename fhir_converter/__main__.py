import argparse
import os
import sys
from datetime import datetime
from enum import StrEnum
from functools import partial
from pathlib import Path
from shutil import get_terminal_size
from textwrap import dedent, indent
from time import time
from traceback import print_exception
from typing import Any, Final, List, Mapping, Optional, Type

from frozendict import frozendict
from liquid import Environment, FileExtensionLoader
from psutil import Process

from fhir_converter.renderers import (
    BaseFhirRenderer,
    CcdaRenderer,
    DataRenderer,
    RenderErrorHandler,
    Stu3FhirRenderer,
    fail,
    get_environment,
    render_files_to_dir,
    render_to_dir,
)
from fhir_converter.utils import del_path_quietly, mkdir


class RenderSourceFormat(StrEnum):
    """RenderSourceFormat The source format to render"""

    STU3 = "STU3"
    CCDA = "CCDA"


render_map: Final[Mapping[RenderSourceFormat, Type[BaseFhirRenderer]]] = frozendict(
    {
        RenderSourceFormat.STU3: Stu3FhirRenderer,
        RenderSourceFormat.CCDA: CcdaRenderer,
    }
)
"""Mapping[RenderSourceFormat, Type[BaseFhirRenderer]]: Source format to render mappings"""


def main(argv: List[str], prog: Optional[str] = None) -> None:
    argparser = get_argparser(prog)
    try:
        args = parse_args(argparser, argv)
        render(get_renderer(args), args)
    except Exception as e:
        print_exception(type(e), e, e.__traceback__)
        print_summary(success=False)
        sys.exit(1)
    else:
        print_summary(success=True)
        sys.exit(0)


def print_summary(success: bool) -> None:
    banner_bar = "-" * get_terminal_size().columns
    process = Process(os.getpid())

    summary = f"""
    {banner_bar}
    RENDER {"SUCCESS" if success else "FAILURE"}
    {banner_bar}
    Total time: {time() - process.create_time():.2f}s
    Finished at: {datetime.now()}
    Final Memory: {process.memory_info().rss / (1024 * 1024):.0f}M
    {banner_bar}
    """
    print(dedent(summary).strip())


def get_renderer(args: argparse.Namespace) -> DataRenderer:
    renderer = render_map[args.source_format]
    return partial(
        renderer(get_user_defined_environment(args, renderer.defaults())).render_fhir,
        args.template_name,
    )


def get_user_defined_environment(
    args: argparse.Namespace, defaults: Mapping[str, Any]
) -> Optional[Environment]:
    if args.template_dir:
        return get_environment(
            loader=FileExtensionLoader(search_path=args.template_dir),
            additional_loaders=[defaults["loader"]],
        )
    return None


def render(render: DataRenderer, args: argparse.Namespace) -> None:
    dir_created = mkdir(args.to_dir)
    try:
        if args.from_dir:
            render_files_to_dir(
                render,
                from_dir=args.from_dir,
                to_dir=args.to_dir,
                flatten=args.flatten_to_dir,
                onerror=get_onerror(args),
                path_filter=is_ccda_file,
            )
        else:
            render_to_dir(
                render,
                from_file=args.from_file,
                to_dir=args.to_dir,
                onerror=get_onerror(args),
            )
    finally:
        if dir_created:
            del_path_quietly(args.to_dir)


def get_onerror(args: argparse.Namespace) -> RenderErrorHandler:
    if args.continue_on_error:
        return lambda e: print_exception(type(e), e, e.__traceback__)
    return fail


def is_ccda_file(path: Path) -> bool:
    return path.suffix in (".ccda", ".xml")


def get_argparser(prog: Optional[str] = None) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=prog,
        description=indent(
            dedent(
                """
            Render data formats to FHIR v4

            Formats include:

               Consolidated CDA (.xml|.ccda) documents
               STU3 FHIR (.json) resources or bundles
            """
            ).strip(),
            "    ",
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--from-file",
        type=absolute_path,
        metavar="<Path>",
        help="The file to render. Superseded by --from-dir",
    )
    parser.add_argument(
        "--from-dir",
        type=absolute_path,
        metavar="<Path>",
        help="The directory to render. Supersedes --from-file",
    )
    parser.add_argument(
        "--to-dir",
        type=absolute_path,
        metavar="<Path>",
        help="The directory to store the rendered output",
        required=True,
    )
    parser.add_argument(
        "--template-dir",
        type=absolute_path,
        metavar="<Path>",
        help="The user defined liquid template directory",
    )
    parser.add_argument(
        "--template-name",
        metavar="<str>",
        help="The liquid template to use when rendering the file",
        required=True,
    )
    parser.add_argument(
        "--source-format",
        metavar="<RenderSourceFormat>",
        type=RenderSourceFormat,
        help="The source format to render. aka STU3 or CCDA",
        required=True,
    )
    parser.add_argument(
        "--continue_on_error",
        action="store_true",
        help="Prevent the render from failing when rendering a file fails.",
    )
    parser.add_argument(
        "--flatten_to_dir",
        action="store_true",
        help="Ignore the nested file system structure in --from-dir.",
    )
    return parser


def absolute_path(path: str) -> Path:
    return Path(path).absolute()


def parse_args(argparser: argparse.ArgumentParser, argv: List[str]) -> argparse.Namespace:
    args = argparser.parse_args(argv)
    if not args.from_dir and not args.from_file:
        argparser.error("Either --from-file or --from-dir must be specified.")
    return args


def entrypoint() -> None:
    main(sys.argv[1:])


if __name__ == "__main__":
    main(sys.argv[1:], "python -m fhir-converter")
