import argparse
import shutil
import sys
import textwrap
from functools import partial
from pathlib import Path
from typing import Optional, Sequence

from fhir_converter.processors import Processor


def make_parser(prog: Optional[str] = None) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=prog,
        description=textwrap.indent(
            textwrap.dedent(
                """
            Convert legacy data formats to FHIR v4

            Legacy formats include:

               Consolidated CDA (.xml|.ccda) documents
            """
            ).strip(),
            "    ",
        ),
        formatter_class=partial(
            argparse.RawDescriptionHelpFormatter,
            width=min(shutil.get_terminal_size().columns - 2, 127),
        ),
    )

    parser.add_argument(
        "--from-file",
        type=_absolute_path,
        metavar="<Path>",
        help="The file to convert",
        required=True,
    )
    parser.add_argument(
        "--to-dir",
        type=_absolute_path,
        metavar="<Path>",
        help="The directory to store the converted file to",
        required=True,
    )
    parser.add_argument(
        "--template-dir",
        type=_absolute_path,
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
    parser.set_defaults(func=convert)

    return parser


def _absolute_path(path: str) -> Path:
    return Path(path).absolute()


def convert(args: argparse.Namespace) -> None:
    processor = Processor.resolve(from_file=args.from_file).from_template_dir(
        template_dir=args.template_dir
    )
    processor.convert_to_dir(
        from_file=args.from_file, to_dir=args.to_dir, template_name=args.template_name
    )


def main(argv: Sequence[str], prog: Optional[str] = None) -> None:
    args = make_parser(prog).parse_args(argv)
    args.func(args)


def entrypoint() -> None:
    main(sys.argv[1:])


if __name__ == "__main__":
    main(sys.argv[1:], "python -m fhir-converter")
