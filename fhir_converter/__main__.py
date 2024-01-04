import argparse
import os
import sys
from collections.abc import Mapping, Sequence
from datetime import datetime
from functools import partial
from pathlib import Path
from shutil import get_terminal_size
from textwrap import dedent, indent
from time import time
from traceback import print_exception
from typing import Any, Optional

from liquid import Environment
from psutil import Process

from fhir_converter import loaders, renderers


def main(argv: Sequence[str], prog: Optional[str] = None) -> None:
    argparser = get_argparser(prog)
    try:
        args = parse_args(argparser, argv)
        render(get_renderer(args), args)
    except Exception as e:
        print_exception(e)
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
    Final Memory: {process.memory_info().rss / (1024*1024):.0f}M
    {banner_bar}
    """
    print(dedent(summary).strip())


def get_renderer(args: argparse.Namespace) -> renderers.DataRenderer:
    return partial(
        renderers.CcdaRenderer(get_user_defined_environment(args)).render_fhir,
        args.template_name,
        **get_user_defined_options(args),
    )


def get_user_defined_environment(args: argparse.Namespace) -> Optional[Environment]:
    if args.template_dir:
        return renderers.get_environment(
            loader=loaders.get_file_system_loader(search_path=args.template_dir)
        )
    return None


def get_user_defined_options(args: argparse.Namespace) -> Mapping[str, Any]:
    options = {}
    if args.indent:
        options["indent"] = args.indent
    return options


def render(render: renderers.DataRenderer, args: argparse.Namespace) -> None:
    if args.from_dir:
        renderers.render_files_to_dir(
            render,
            from_dir=args.from_dir,
            to_dir=args.to_dir,
            onerror=get_onerror(args),
            path_filter=lambda p: p.suffix in (".ccda", ".xml"),
        )
    else:
        renderers.render_to_dir(
            render,
            from_file=args.from_file,
            to_dir=args.to_dir,
            onerror=get_onerror(args),
        )


def get_onerror(args: argparse.Namespace) -> renderers.RenderErrorHandler:
    return print_exception if args.continue_on_error else renderers.fail


def get_argparser(prog: Optional[str] = None) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=prog,
        description=indent(
            dedent(
                """
            Render legacy data formats to FHIR v4

            Legacy formats include:

               Consolidated CDA (.xml|.ccda) documents
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
        "--indent",
        type=int,
        metavar="<int>",
        help="The indentation amount or level. 0 is none.",
    )
    parser.add_argument(
        "--continue_on_error",
        action="store_true",
        help="Prevent the render from failing when rendering a file fails. ",
    )
    return parser


def absolute_path(path: str) -> Path:
    return Path(path).absolute()


def parse_args(
    argparser: argparse.ArgumentParser, argv: Sequence[str]
) -> argparse.Namespace:
    args = argparser.parse_args(argv)
    if not args.from_dir and not args.from_file:
        argparser.error("Either --from-file or --from-dir must be specified.")
    return args


def entrypoint() -> None:
    main(sys.argv[1:])


if __name__ == "__main__":
    main(sys.argv[1:], "python -m fhir-converter")
