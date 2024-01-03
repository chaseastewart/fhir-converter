from __future__ import annotations

from collections.abc import Callable, Iterable
from functools import partial
from pathlib import Path
from typing import Optional, Union

from importlib_resources import Package, files
from liquid import BoundTemplate, Context, Environment
from liquid.exceptions import TemplateNotFound
from liquid.loaders import (
    BaseLoader,
    FileExtensionLoader,
    FileSystemLoader,
    TemplateNamespace,
    TemplateSource,
)
from liquid.utils import LRUCache


class TemplateSystemLoader(BaseLoader):
    caching_loader = True

    def __init__(
        self,
        loader: BaseLoader,
        auto_reload: bool = True,
        cache_size: int = 300,
        defaults_loader: Optional[BaseLoader] = None,
    ) -> None:
        self.loader = loader
        self.defaults_loader = defaults_loader
        self.auto_reload = auto_reload
        self.is_caching = cache_size > 0
        self.cache = LRUCache(capacity=cache_size)

    def load(
        self, env: Environment, name: str, globals: TemplateNamespace = None
    ) -> BoundTemplate:
        return self.check_cache(
            env,
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
        return self.check_cache(
            env,
            cache_key=name,
            globals=globals,
            load_func=partial(super().load_with_args, env, name, globals, **kwargs),
        )

    def load_with_context(
        self, context: Context, name: str, **kwargs: str
    ) -> BoundTemplate:
        return self.check_cache(
            context.env,
            cache_key=name,
            globals=context.globals,
            load_func=partial(
                super().load_with_context, context=context, name=name, **kwargs
            ),
        )

    def check_cache(
        self,
        env: Environment,
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

    def get_source(
        self,
        env: Environment,
        name: str,
    ) -> TemplateSource:
        template_name = self.resolve_template_name(name)
        try:
            return self.loader.get_source(env, template_name)
        except TemplateNotFound as e:
            if self.defaults_loader:
                return self.defaults_loader.get_source(env, template_name)
            raise e

    def resolve_template_name(self, template_name: str) -> str:
        template_path = Path(template_name)
        parts = template_path.parts
        if len(parts) > 1:
            tail = parts[-1]
            if not tail.endswith(".json") and not tail.startswith("_"):
                template_path = template_path.with_name("_" + tail)
        return str(template_path)


class ResourceLoader(BaseLoader):
    def __init__(
        self,
        search_package: Package,
        encoding: str = "utf-8",
        ext: str = ".liquid",
    ) -> None:
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


def read_text(env: Environment, filename: str) -> str:
    return env.loader.get_source(env, filename).source


def get_file_system_loader(
    search_path: Union[str, Path, Iterable[Union[str, Path]]],
    **kwargs,
) -> FileSystemLoader:
    return FileExtensionLoader(search_path=search_path, **kwargs)


def get_resource_loader(
    search_package: Package,
    **kwargs,
) -> ResourceLoader:
    return ResourceLoader(search_package=search_package, **kwargs)
