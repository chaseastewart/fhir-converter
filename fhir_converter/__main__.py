import argparse
import sys
import textwrap
from collections.abc import Callable, Sequence
from functools import partial
from pathlib import Path
from typing import Optional

from liquid import Environment

from fhir_converter import loaders, renderers


def main(argv: Sequence[str], prog: Optional[str] = None) -> None:
    args = make_parser(prog).parse_args(argv)
    args.func(args)


def make_parser(prog: Optional[str] = None) -> argparse.ArgumentParser:
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
        required=True,
    )
    parser.add_argument(
        "--to-dir",
        type=absolute_path,
        metavar="<Path>",
        help="The directory to store the rendered file to",
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
    parser.set_defaults(func=render)

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


def render_ccda(args: argparse.Namespace) -> None:
    renderers.render_to_dir(
        partial(
            renderers.CcdaRenderer(env=get_user_defined_environment(args)).render_fhir,
            args.template_name,
        ),
        args.from_file,
        args.to_dir,
        **get_user_defined_options(args),
    )


file_type_renderers: dict[str, Callable[[argparse.Namespace], None]] = {
    ".ccda": render_ccda,
    ".xml": render_ccda,
}


def render(args: argparse.Namespace) -> None:
    try:
        file_type_renderers[args.from_file.suffix](args)
    except KeyError:
        raise ValueError(f"Unsupported file ext[{args.from_file.suffix}]")


def entrypoint() -> None:
    main(sys.argv[1:])


if __name__ == "__main__":
    main(sys.argv[1:], "python -m fhir-converter")
