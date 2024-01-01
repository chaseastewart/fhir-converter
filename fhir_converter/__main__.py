import argparse
import sys
import textwrap
from collections.abc import Callable, Sequence
from functools import partial
from pathlib import Path
from typing import Optional

from fhir_converter import renderers


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
        required=True,
    )
    parser.add_argument(
        "--template-name",
        metavar="<str>",
        help="The liquid template to use when rendering the file",
        required=True,
    )
    parser.set_defaults(func=render)

    return parser


def absolute_path(path: str) -> Path:
    return Path(path).absolute()


def render_ccda(args: argparse.Namespace) -> None:
    renderer = renderers.CcdaRenderer()
    renderers.render_to_dir(
        render=partial(renderer.render_to_json_string, args.template_name),
        from_file=args.from_file,
        to_dir=args.to_dir,
    )


file_type_renderers: dict[str, Callable[[argparse.Namespace], None]] = {
    ".ccda": render_ccda,
    ".xml": render_ccda,
}


def render(args: argparse.Namespace) -> None:
    try:
        file_type_renderers[args.from_file.suffix](args)
    except KeyError:
        raise ValueError(f"Unknown file ext[{args.from_file.suffix}]")


def entrypoint() -> None:
    main(sys.argv[1:])


if __name__ == "__main__":
    main(sys.argv[1:], "python -m fhir-converter")
