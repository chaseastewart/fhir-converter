from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, MutableMapping, Sequence
from io import StringIO
from pathlib import Path
from typing import IO, Any, NoReturn, Optional, TextIO, Union

from frozendict import frozendict
from liquid import Environment
from liquid.loaders import BaseLoader
from pyjson5 import encode_io
from pyjson5 import loads as json_loads

from fhir_converter.filters import all_filters, register_filters
from fhir_converter.hl7 import parse_fhir
from fhir_converter.loaders import ResourceLoader, TemplateSystemLoader, read_text
from fhir_converter.tags import all_tags, register_tags
from fhir_converter.utils import (
    del_empty_dirs_quietly,
    del_path_quietly,
    join_subpath,
    mkdir,
    parse_xml,
    walk_path,
)

DataInput = Union[str, IO]
""" Union[str, IO]: The rendering data input types"""

DataOutput = TextIO
"""TextIO: The rendering data output type"""

DataRenderer = Callable[[DataInput, DataOutput, str], None]
"""Callable[[DataInput, DataOutput, str], None]: Data renderer function"""

RenderErrorHandler = Callable[[Exception], None]
"""Callable[[Exception], None]: Rendering error handling function"""

ccda_default_loader = ResourceLoader(search_package="fhir_converter.templates.ccda")
"""ResourceLoader: The default loader for the ccda templates"""


class RenderingError(Exception):
    """Raised when there is a rendering error"""

    def __init__(self, msg: str, cause: Optional[Exception] = None) -> None:
        super().__init__(msg)
        if cause:
            self.__cause__ = cause


class CcdaRenderer:
    """Consolidated CDA document renderer. Supports rendering the documents to FHIR

    Filters:
        The module provides builtin filters to support the default templates provided
        within the module. Custom filters may be added for user defined templates.
        Consumers must provide the rendering environment with the custom filters
        registered. The builtin filters will be added unless a filter with the same
        name has already been registered.

    Tags:
        The module provides builtin tags to support the default templates provided
        within the module. Custom tags may be added for user defined templates.
        Consumers must provide the rendering environment with the custom tag(s)
        registered. The builtin tag(s) will be added unless a tag with the same name
        has already been registered.

    Args:
        env (Environment, optional): Optional rendering environment. A rendering
            environment will be constructed with builtin defaults when env is None.
            Defaults to None.
        template_globals (Mapping, optional): Optional mapping that will be added to
            the render context. Code mappings from ValueSet/ValueSet.json will be
            loaded from the module when template_globals is None. Defaults to None.
    """

    def __init__(
        self,
        env: Optional[Environment] = None,
        template_globals: Optional[Mapping[str, Any]] = None,
    ) -> None:
        if not env:
            env = get_environment(loader=ccda_default_loader)
        register_filters(env, all_filters)
        register_tags(env, all_tags)

        self.env = env
        self.template_globals = self._make_globals(template_globals)

    def _make_globals(self, globals: Optional[Mapping[str, Any]]) -> Mapping[str, Any]:
        template_globals = dict(globals or {})
        if "code_mapping" not in template_globals:
            value_set = json_loads(read_text(self.env, filename="ValueSet/ValueSet.json"))
            template_globals["code_mapping"] = frozendict(value_set.get("Mapping", {}))
        return frozendict(template_globals)

    def render_fhir_string(
        self, template_name: str, xml_in: DataInput, encoding: str = "utf-8"
    ) -> str:
        with StringIO() as buffer:
            self.render_fhir(template_name, xml_in, buffer, encoding)
            return buffer.getvalue()

    def render_fhir(
        self,
        template_name: str,
        xml_in: DataInput,
        fhir_out: DataOutput,
        encoding: str = "utf-8",
    ) -> None:
        """Renders the XML to FHIR writing the generated output to the supplied file
        like object

        Args:
            template_name (str): The rendering template
            xml_in (DataInput): The XML input. Either a string or file like object
            fhir_out (DataOutput): The file like object to write the rendered output
            encoding (str, optional): The encoding to use when parsing the XML input.
                Defaults to "utf-8".

        Raises:
            RenderingError: when an error occurs while rendering the input
        """
        fhir = self.render_to_fhir(template_name, xml_in, encoding)
        try:
            encode_io(
                fhir,
                fp=fhir_out,  # type: ignore
                supply_bytes=False,
            )
        except Exception as e:
            raise RenderingError("Failed to serialize FHIR", e)

    def render_to_fhir(
        self, template_name: str, xml_input: DataInput, encoding: str = "utf-8"
    ) -> MutableMapping:
        """Renders the XML to FHIR

        Args:
            template_name (str): The rendering template
            xml_in (DataInput): The XML input. Either a string or file like object
            encoding (str, optional): The encoding to use when parsing the XML input.
                Defaults to "utf-8".

        Returns:
            dict: The rendered FHIR bundle

        Raises:
            RenderingError: when an error occurs while rendering the input
        """
        try:
            template = self.env.get_template(template_name, globals=self.template_globals)
            return parse_fhir(
                json_input=template.render({"msg": parse_xml(xml_input, encoding)}),
            )
        except Exception as e:
            raise RenderingError("Failed to render FHIR", e)


def get_environment(
    loader: BaseLoader,
    auto_reload: bool = False,
    cache_size: int = 300,
    additional_loaders: Optional[Sequence[BaseLoader]] = None,
    **kwargs,
) -> Environment:
    """Factory for creating rendering environments with builtin configurations.
    Keyword arguments will be forwarded to the rendering environment

    Args:
        loader (BaseLoader): The loader to use when loading the rendering temples
        auto_reload (bool, optional): If `True`, loaders that have an `uptodate`
            callable will reload template source data automatically. Defaults to False
        cache_size (int, optional): The capacity of the template cache in number of
            templates. cache_size is None or less than 1 disables caching.
            Defaults to 300
        additional_loaders (Optional[Sequence[BaseLoader]], optional): The additional
            loaders to use when a template is not found by the loader. Defaults to None

    Returns:
        Environment: the rendering environment
    """
    loaders = [loader]
    if additional_loaders:
        loaders += additional_loaders
    return Environment(
        loader=TemplateSystemLoader(
            loaders,
            auto_reload=auto_reload,
            cache_size=cache_size,
        ),
        **kwargs,
    )


def fail(e: Exception) -> NoReturn:
    """fail Raises the provided exception

    Args:
        e (Exception): the exception / failure reason

    Raises:
        Exception: the provided exception
    """
    raise e


def render_files_to_dir(
    render: DataRenderer,
    from_dir: Path,
    to_dir: Path,
    flatten: bool = False,
    extension: str = ".json",
    encoding: str = "utf-8",
    onerror: RenderErrorHandler = fail,
    path_filter: Optional[Callable[[Path], bool]] = None,
) -> None:
    """render_files_to_dir Renders the files from the given directory to the specified output
    directory using the supplied data renderer.

    Args:
        render (DataRenderer): the renderer to use
        from_dir (Path): the directory to render
        to_dir (Path): the output directory
        flatten (bool, optional): whether to flatten, ignore, the source directory structure and write
            all files to the root of the output directory. Defaults to False.
        extension (str, optional): the file extension for the rendered output file. Defaults to ".json".
        encoding (str, optional): the character encoding to use. Defaults to "utf-8".
        onerror (RenderErrorHandler, optional): the error handler. Defaults to fail.
        path_filter (Optional[Callable[[Path], bool]], optional): the filter to use when scaning the
            source directory. Defaults to None.
    """
    try:
        for dir, _, filenames in walk_path(from_dir):
            files: Iterable[Path] = map(lambda fn: dir.joinpath(fn), filenames)
            if path_filter:
                files = filter(path_filter, files)
            for file in files:
                if not flatten and from_dir != dir:
                    to_file_dir = join_subpath(to_dir, parent=from_dir, child=file)
                    mkdir(to_file_dir, parents=True, exist_ok=True)
                else:
                    to_file_dir = to_dir
                render_to_dir(render, file, to_file_dir, extension, encoding, onerror)
    except Exception as e:
        onerror(RenderingError(f"Failed to render {from_dir}", e))
    finally:
        if not flatten:
            del_empty_dirs_quietly(to_dir)


def render_to_dir(
    render: DataRenderer,
    from_file: Path,
    to_dir: Path,
    extension: str = ".json",
    encoding: str = "utf-8",
    onerror: RenderErrorHandler = fail,
) -> None:
    """render_to_dir Renders the given file to the specified output directory using the
    supplied data renderer.

    Args:
        render (DataRenderer): the renderer to use
        from_file (Path): the file to render
        to_dir (Path): the output directory
        extension (str, optional): the file extension for the rendered output file. Defaults to ".json".
        encoding (str, optional): the character encoding to use. Defaults to "utf-8".
        onerror (RenderErrorHandler, optional): the error handler. Defaults to fail.

    Raises:
        Exception: when the error handler determines an exception should be raised. By default
        all exceptions are raised. See fail
    """
    try:
        with from_file.open(encoding=encoding) as data_in:
            to_file: Path = to_dir.joinpath(from_file.with_suffix(extension).name)
            try:
                with to_file.open("w", encoding=encoding) as data_out:
                    render(data_in, data_out, encoding)
            except Exception as e:
                del_path_quietly(to_file)
                raise e
    except Exception as e:
        onerror(RenderingError(f"Failed to render {from_file}", e))
