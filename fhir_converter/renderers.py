from __future__ import annotations

from collections.abc import Callable, Generator, Mapping
from json import dumps as json_dumps
from os import walk as os_walk
from pathlib import Path
from typing import IO, Any, Optional, Union

from frozendict import frozendict
from liquid import Environment
from liquid.loaders import BaseLoader
from pyjson5 import loads as json5_loads

from fhir_converter import filters, loaders, parsers, tags

DataT = Union[str, IO]


class CcdaRenderer:
    """Renders consolidated CDA documents

    Args:
        template_globals: A mapping of render context variables attached
            to the rendering template. Default empty
        env (Environment): The rendering `Environment`. Optional
    """

    def __init__(
        self,
        template_globals: Mapping[str, Any] = {},
        env: Optional[Environment] = None,
    ) -> None:
        if not env:
            env = get_environment()
        filters.register(env, filters.generic + filters.hl7)
        tags.register(env, tags.all)

        self.env = env
        self.template_globals = self._make_globals(template_globals)

    def _make_globals(self, globals: Mapping[str, Any]) -> Mapping[str, Any]:
        template_globals = dict(globals)
        if not "code_mapping" in template_globals:
            value_set = json5_loads(
                loaders.read_text(self.env, filename="ValueSet/ValueSet.json")
            )
            template_globals["code_mapping"] = frozendict(value_set.get("Mapping", {}))
        return frozendict(template_globals)

    def render_to_json_string(
        self, template_name: str, xml_input: DataT, encoding: str = "utf-8"
    ) -> str:
        """Render the xml input to a json string

        Args:
            template_name: The rendering template name
            xml_input: The xml input. Either a string or File-like object
            encoding: The xml encoding. Optional
        """
        return json_dumps(self.render_to_json(template_name, xml_input, encoding))

    def render_to_json(
        self, template_name: str, xml_input: DataT, encoding: str = "utf-8"
    ) -> dict:
        """Render the xml input to json

        Args:
            template_name: The rendering template name
            xml_input: The xml input. Either a string or File-like object
            encoding: The xml encoding. Optional
        """
        template = self.env.get_template(template_name, globals=self.template_globals)
        return parsers.parse_json(
            json_input=template.render({"msg": parsers.parse_xml(xml_input, encoding)}),
            encoding=encoding,
        )


def get_environment(
    auto_reload: bool = False,
    cache_size: int = 250,
    loader: Optional[BaseLoader] = None,
    defaults_loader: Optional[BaseLoader] = None,
    **kwargs,
) -> Environment:
    if not defaults_loader:
        defaults_loader = loaders.get_resource_loader(
            search_package="fhir_converter.templates.ccda"
        )
    if not loader:
        loader, defaults_loader = defaults_loader, None
    return Environment(
        loader=loaders.TemplateSystemLoader(
            loader=loader,
            auto_reload=auto_reload,
            cache_size=cache_size,
            defaults_loader=defaults_loader,
        ),
        auto_reload=auto_reload,
        cache_size=cache_size,
        **kwargs,
    )


def render_files_to_dir(
    render: Callable[[DataT, str], str],
    from_dir: Path,
    to_dir: Path,
    extension: str = ".json",
    encoding: str = "utf-8",
    filter_func: Optional[Callable[[Path], bool]] = None,
) -> None:
    def walk_dir() -> Generator[Path, Any, None]:
        for root, _, filenames in os_walk(from_dir):
            for file_path in filter(filter_func, map(Path, filenames)):
                yield Path(root).joinpath(file_path)

    for from_file in walk_dir():
        render_to_dir(render, from_file, to_dir, extension, encoding)


def render_to_dir(
    render: Callable[[DataT, str], str],
    from_file: Path,
    to_dir: Path,
    extension: str = ".json",
    encoding: str = "utf-8",
) -> None:
    with open(from_file, "r", encoding=encoding) as ccda_file:
        fhir_path = to_dir.joinpath(from_file.with_suffix(extension).name)
        with open(fhir_path, "w", encoding=encoding) as fhir_file:
            fhir_file.write(render(ccda_file, encoding))
