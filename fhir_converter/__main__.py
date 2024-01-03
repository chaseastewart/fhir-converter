import argparse
import sys
import textwrap
from collections.abc import Sequence
from functools import partial
from pathlib import Path
from typing import Optional

from liquid import Environment

from fhir_converter import loaders, renderers


def main(argv: Sequence[str], prog: Optional[str] = None) -> None:
    argparser = get_argparser(prog)
    args = argparser.parse_args(argv)
    if not args.from_dir and not args.from_file:
        argparser.error("Either --from-file or --from-dir must be specified.")
    if not args.to_dir.is_dir():
        args.to_dir.mkdir()

    render = partial(
        renderers.CcdaRenderer(env=get_user_defined_environment(args)).render_fhir,
        args.template_name,
    )
    if args.from_dir:
        renderers.render_files_to_dir(
            render,
            from_dir=args.from_dir,
            to_dir=args.to_dir,
            filter_func=lambda p: p.suffix in (".ccda", ".xml"),
            **get_user_defined_options(args),
        )
    else:
        renderers.render_to_dir(
            render,
            from_file=args.from_file,
            to_dir=args.to_dir,
            **get_user_defined_options(args),
        )


def get_argparser(prog: Optional[str] = None) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=prog,
        description=textwrap.indent(
            textwrap.dedent(
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
        help="The file to render",
    )
    parser.add_argument(
        "--from-dir",
        type=absolute_path,
        metavar="<Path>",
        help="The directory to render",
    )
    parser.add_argument(
        "--to-dir",
        type=absolute_path,
        metavar="<Path>",
        help="The directory to store the rendered file(s)",
        required=True,
    )
    parser.add_argument(
        "--template-dir",
        type=absolute_path,
        metavar="<Path>",
        help="The liquid template directory",
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
        help="The indentation amount",
    )
    return parser


def absolute_path(path: str) -> Path:
    return Path(path).absolute()


def get_user_defined_environment(args: argparse.Namespace) -> Optional[Environment]:
    if args.template_dir:
        return renderers.get_environment(
            loader=loaders.get_file_system_loader(search_path=args.template_dir)
        )
    return None


def get_user_defined_options(args: argparse.Namespace) -> dict:
    options = {}
    if args.indent:
        options["indent"] = args.indent
    return options


def entrypoint() -> None:
    main(sys.argv[1:])


if __name__ == "__main__":
    main(sys.argv[1:], "python -m fhir-converter")
