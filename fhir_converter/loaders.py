from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Sequence

from liquid import ChoiceLoader, Context, Environment
from liquid.builtin.loaders.mixins import CachingLoaderMixin
from liquid.exceptions import TemplateNotFound
from liquid.loaders import BaseLoader, TemplateSource


class TemplateSystemLoader(ChoiceLoader):
    """TemplateSystemLoader allows templates to be loaded from a primary and optionally secondary
    location(s). This allows templates to include / render templates from the other location(s)

    Template Names Resolution:
    Any template (non json file) that is in a subdirectory will have _ prepended to the name
    Ex: Section/Immunization -> Section/_Immunization

    See `ChoiceLoader` for more information
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


class CachingTemplateSystemLoader(CachingLoaderMixin, TemplateSystemLoader):
    """TemplateSystemLoader that caches parsed templates in memory.

    See `TemplateSystemLoader` for more information
    """

    def __init__(
        self,
        loaders: List[BaseLoader],
        *,
        auto_reload: bool = True,
        namespace_key: str = "",
        cache_size: int = 300,
    ) -> None:
        super().__init__(
            auto_reload=auto_reload,
            namespace_key=namespace_key,
            cache_size=cache_size,
        )

        TemplateSystemLoader.__init__(self, loaders)


def make_template_system_loader(
    loader: BaseLoader,
    *,
    auto_reload: bool = True,
    namespace_key: str = "",
    cache_size: int = 300,
    additional_loaders: Optional[Sequence[BaseLoader]] = None,
) -> BaseLoader:
    """make_template_system_loader A `TemplateSystemLoader` factory

    Args:
        loader (BaseLoader): The loader to use when loading the rendering temples
        auto_reload (bool, optional): If `True`, loaders that have an `uptodate`
            callable will reload template source data automatically. Defaults to False
        namespace_key (str, optional): The name of a global render context variable or loader
            keyword argument that resolves to the current loader "namespace" or
            "scope". Defaults to ""
        cache_size (int, optional): The capacity of the template cache in number of
            templates. cache_size less than 1 disables caching. Defaults to 300
        additional_loaders (Optional[Sequence[BaseLoader]], optional): The additional
            loaders to use when a template is not found by the loader. Defaults to None

    Returns:
        BaseLoader: `CachingTemplateSystemLoader` if cache_size > 0 else `TemplateSystemLoader`
    """
    loaders = [loader]
    if additional_loaders:
        loaders += additional_loaders
    if cache_size > 0:
        return CachingTemplateSystemLoader(
            loaders=loaders,
            auto_reload=auto_reload,
            namespace_key=namespace_key,
            cache_size=cache_size,
        )

    return TemplateSystemLoader(loaders=loaders)


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
