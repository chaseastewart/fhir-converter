from __future__ import annotations

from collections.abc import Callable, Mapping, MutableMapping
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
from fhir_converter.loaders import TemplateSystemLoader, get_resource_loader, read_text
from fhir_converter.tags import all_tags, register_tags
from fhir_converter.utils import apply_dir, mkdir, parse_xml, rm_empty_dirs, rm_path

DataInput = Union[str, IO]
DataOutput = TextIO
DataRenderer = Callable[[DataInput, DataOutput, str], None]
RenderErrorHandler = Callable[[Exception], None]


class RenderingError(Exception):
    def __init__(self, msg: str, cause: Exception) -> None:
        super().__init__(msg)
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
            env = get_environment()
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
        """
        encode_io(
            self.render_to_fhir(template_name, xml_in, encoding),
            fp=fhir_out,  # type: ignore
            supply_bytes=False,
        )

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
        """
        template = self.env.get_template(template_name, globals=self.template_globals)
        return parse_fhir(
            json_input=template.render({"msg": parse_xml(xml_input, encoding)}),
        )


def get_environment(
    auto_reload: bool = False,
    cache_size: int = 300,
    loader: Optional[BaseLoader] = None,
    defaults_loader: Optional[BaseLoader] = None,
    **kwargs,
) -> Environment:
    """Factory for creating rendering environments with builtin configurations.
    Keyword arguments will be forwarded to the rendering environment

    Args:
        auto_reload (bool, optional): If `True`, loaders that have an `uptodate`
            callable will reload template source data automatically. Defaults to False.
        cache_size (int, optional): The capacity of the template cache in number of
            templates. cache_size is None or less than 1 disables caching.
            Defaults to 300.
        loader (Optional[BaseLoader], optional): The loader to use when loading the
            reandering temples. Templates will be loaded from the default loader when
            loader is None. Defaults to None.
        defaults_loader (Optional[BaseLoader], optional): The default loader to use
            when a template can not be resolved by the loader. Defaults will be loaded
            from the module when defaults_loader is None. Defaults to None.

    Returns:
        Environment: the rendering environment
    """
    if not defaults_loader:
        defaults_loader = get_resource_loader(
            search_package="fhir_converter.templates.ccda"
        )
    if not loader:
        loader, defaults_loader = defaults_loader, None
    return Environment(
        loader=TemplateSystemLoader(
            loader=loader,
            auto_reload=auto_reload,
            cache_size=cache_size,
            defaults_loader=defaults_loader,
        ),
        auto_reload=auto_reload,
        cache_size=cache_size,
        **kwargs,
    )


def fail(e: Exception) -> NoReturn:
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
    def render_files(root: Path, _, filenames: list[str]) -> None:
        for file_path in filter(path_filter, map(Path, filenames)):
            from_file = root.joinpath(file_path)
            if not flatten and from_dir != root:
                to_file_dir = to_dir.joinpath(
                    *[p for p in from_file.parts[:-1] if p not in from_dir.parts]
                )
                mkdir(to_file_dir, parents=True, exist_ok=True)
            else:
                to_file_dir = to_dir
            render_to_dir(render, from_file, to_file_dir, extension, encoding, onerror)

    try:
        apply_dir(render_files, from_dir)
    except Exception as e:
        onerror(RenderingError(f"Failed to render {from_dir}", e))
    finally:
        if not flatten:
            rm_empty_dirs(to_dir)


def render_to_dir(
    render: DataRenderer,
    from_file: Path,
    to_dir: Path,
    extension: str = ".json",
    encoding: str = "utf-8",
    onerror: RenderErrorHandler = fail,
) -> None:
    try:
        with open(from_file, "r", encoding=encoding) as data_in:
            out_path = to_dir.joinpath(from_file.with_suffix(extension).name)
            try:
                with open(out_path, "w", encoding=encoding) as data_out:
                    render(data_in, data_out, encoding)
            except Exception as e:
                rm_path(out_path)
                raise e
    except Exception as e:
        onerror(RenderingError(f"Failed to render {from_file}", e))
