from __future__ import annotations

from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import Optional

from importlib_resources import Package, files
from liquid import BoundTemplate, Context, Environment
from liquid.exceptions import TemplateNotFound
from liquid.loaders import BaseLoader, ChoiceLoader, TemplateNamespace, TemplateSource
from liquid.utils import LRUCache


class CachedChoiceLoader(ChoiceLoader):
    """A choice loader that caches parsed templates in memory

    Args:
        loaders: A list of loaders implementing `liquid.loaders.BaseLoader`
        auto_reload (bool, optional): If `True`, automatically reload a cached template
            if it has been updated. Defaults to True
        cache_size (int, optional): The maximum number of templates to hold in the cache
            before removing the least recently used template. Defaults to 300
    """

    caching_loader = True

    def __init__(
        self,
        loaders: list[BaseLoader],
        auto_reload: bool = True,
        cache_size: int = 300,
    ) -> None:
        super().__init__(loaders)
        self.auto_reload = auto_reload
        self.is_caching = cache_size > 0
        self.cache = LRUCache(capacity=cache_size) if self.is_caching else {}

    def load(
        self, env: Environment, name: str, globals: Optional[TemplateNamespace] = None
    ) -> BoundTemplate:
        return self._check_cache(
            cache_key=name,
            globals=globals,
            load_func=partial(super().load, env, name, globals),
        )

    def load_with_args(
        self,
        env: Environment,
        name: str,
        globals: Optional[TemplateNamespace] = None,
        **kwargs: object,
    ) -> BoundTemplate:
        return self._check_cache(
            cache_key=name,
            globals=globals,
            load_func=partial(super().load_with_args, env, name, globals, **kwargs),
        )

    def load_with_context(
        self, context: Context, name: str, **kwargs: str
    ) -> BoundTemplate:
        return self._check_cache(
            cache_key=name,
            globals=context.globals,
            load_func=partial(
                super().load_with_context, context=context, name=name, **kwargs
            ),
        )

    def _check_cache(
        self,
        cache_key: str,
        globals: TemplateNamespace,
        load_func: Callable[[], BoundTemplate],
    ) -> BoundTemplate:
        try:
            cached_template = self.cache[cache_key]
            if self.auto_reload and not cached_template.is_up_to_date:
                template = load_func()
                self.cache[cache_key] = template
                return template

            if globals:
                cached_template.globals.update(globals)
            return cached_template
        except KeyError:
            template = load_func()
            if self.is_caching:
                self.cache[cache_key] = template
            return template


class ResourceLoader(BaseLoader):
    """A template loader that will load templates from the package resources

    Args:
        search_package (Package): The package to load templates from
        encoding (str, optional): The encoding to use loading the template source
                Defaults to "utf-8".
        ext (str, optional): The extension to use when one isn't provided
                Defaults to ".liquid".
    """

    def __init__(
        self,
        search_package: Package,
        encoding: str = "utf-8",
        ext: str = ".liquid",
    ) -> None:
        super().__init__()
        self.search_package = search_package
        self.encoding = encoding
        self.ext = ext

    def get_source(self, _: Environment, template_name: str) -> TemplateSource:
        template_path = Path(template_name)
        if not template_path.suffix:
            template_path = template_path.with_suffix(self.ext)
        try:
            resource_path = files(self.search_package).joinpath(template_path)
            return TemplateSource(
                source=resource_path.read_text(self.encoding),
                filename=str(resource_path),
                uptodate=lambda: True,
            )
        except (ModuleNotFoundError, FileNotFoundError):
            raise TemplateNotFound(template_name)


class TemplateSystemLoader(CachedChoiceLoader):
    """TemplateSystemLoader allows templates to be loaded from a primary and optionally secondary
    location(s). This allows templates to include / render templates from the other location(s)

    Template Names Resolution:
    Any template (non json file) that is in a subdirectory will have _ prepended to the name
    Ex: Section/Immunization -> Section/_Immunization

    See ``CachedChoiceLoader`` for more information
    """

    def get_source(
        self,
        env: Environment,
        name: str,
    ) -> TemplateSource:
        return super().get_source(env, self._resolve_template_name(name))

    def _resolve_template_name(self, template_name: str) -> str:
        template_path = Path(template_name)
        parts = template_path.parts
        if len(parts) > 1:
            tail = parts[-1]
            if not tail.endswith(".json") and not tail.startswith("_"):
                template_path = template_path.with_name("_" + tail)
        return str(template_path)


def read_text(env: Environment, filename: str) -> str:
    """read_text Reads the text from the given filename using the Environment's
    loader to retrieve the file's contents

    Args:
        env (Environment): the rendering environment
        filename (str): the name of the file

    Returns:
        str: the contents of the file if the file could be found

    Raises:
        FileNotFoundError: when the file could not be found
    """
    try:
        return env.loader.get_source(env, filename).source
    except TemplateNotFound:
        raise FileNotFoundError(f"File not found {filename}")
