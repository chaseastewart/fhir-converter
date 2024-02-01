from __future__ import annotations

from pathlib import Path
from typing import Callable, List

from importlib_resources import Package, files
from liquid import BoundTemplate, ChoiceLoader, Context, Environment
from liquid.builtin.loaders.mixins import CachingLoaderMixin
from liquid.exceptions import TemplateNotFound
from liquid.loaders import BaseLoader, TemplateNamespace, TemplateSource
from typing_extensions import deprecated


@deprecated(
    "ResourceLoader is deprecated and scheduled for removal "
    "in a future version. Use PackageLoader instead"
)
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
        if ".." in template_path.parts:
            raise TemplateNotFound(template_name)

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


@deprecated(
    "CachedChoiceLoader is deprecated and scheduled for removal "
    "in a future version. Use CachingChoiceLoader instead"
)
class CachedChoiceLoader(CachingLoaderMixin, ChoiceLoader):
    """A choice loader that caches parsed templates in memory
    Args:
        loaders: A list of loaders implementing `liquid.loaders.BaseLoader`
        auto_reload (bool, optional): If `True`, automatically reload a cached template
            if it has been updated. Defaults to True
        cache_size (int, optional): The maximum number of templates to hold in the cache
            before removing the least recently used template. Defaults to 300
        namespace_key (str, optional): The name of a global render context variable or
            loader keyword argument that resolves to the current loader "namespace" or
            "scope". Defaults to ""
    """

    def __init__(
        self,
        loaders: List[BaseLoader],
        auto_reload: bool = True,
        cache_size: int = 300,
        namespace_key: str = "",
    ) -> None:
        super().__init__(
            auto_reload=auto_reload,
            namespace_key=namespace_key,
            cache_size=cache_size,
        )
        ChoiceLoader.__init__(self, loaders)
        self.is_caching = cache_size > 0

    def _check_cache(
        self,
        env: Environment,  # noqa: ARG002
        cache_key: str,
        globals: TemplateNamespace,  # noqa: A002
        load_func: Callable[[], BoundTemplate],
    ) -> BoundTemplate:
        if self.is_caching:
            return super()._check_cache(env, cache_key, globals, load_func)
        return load_func()


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
        template_name: str,
    ) -> TemplateSource:
        return super().get_source(env, self._resolve_template_name(template_name))

    async def get_source_async(
        self,
        env: Environment,
        template_name: str,
    ) -> TemplateSource:
        return await super().get_source_async(
            env, self._resolve_template_name(template_name)
        )

    def get_source_with_args(
        self,
        env: Environment,
        template_name: str,
        **kwargs: object,
    ) -> TemplateSource:
        return super().get_source_with_args(
            env, self._resolve_template_name(template_name), **kwargs
        )

    async def get_source_with_args_async(
        self,
        env: Environment,
        template_name: str,
        **kwargs: object,
    ) -> TemplateSource:
        return await super().get_source_with_args_async(
            env, self._resolve_template_name(template_name), **kwargs
        )

    def get_source_with_context(
        self, context: Context, template_name: str, **kwargs: str
    ) -> TemplateSource:
        return super().get_source_with_context(
            context, self._resolve_template_name(template_name), **kwargs
        )

    async def get_source_with_context_async(
        self, context: Context, template_name: str, **kwargs: str
    ) -> TemplateSource:
        return await super().get_source_with_context_async(
            context, self._resolve_template_name(template_name), **kwargs
        )

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
