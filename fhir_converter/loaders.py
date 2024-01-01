from __future__ import annotations

from collections.abc import Callable, Iterable
from functools import partial
from pathlib import Path
from typing import Optional, Union

from importlib_resources import Package, files
from importlib_resources.abc import Traversable
from liquid import BoundTemplate, Context, Environment
from liquid.exceptions import TemplateNotFound
from liquid.loaders import (
    BaseLoader,
    CachingFileSystemLoader,
    TemplateNamespace,
    TemplateSource,
    UpToDate,
)
from liquid.utils import LRUCache


class TemplateFileSystemLoader(CachingFileSystemLoader):
    def resolve_path(self, template_name: str) -> Path:
        return super().resolve_path(str(normalize_path(template_name)))


class TemplateResourceLoader(BaseLoader):
    caching_loader = True

    def __init__(
        self,
        search_package: Union[Package, Iterable[Package]],
        encoding: str = "utf-8",
        ext: str = ".liquid",
        cache_size: int = 300,
    ) -> None:
        if not isinstance(search_package, Iterable) or isinstance(
            search_package, Package
        ):
            search_package = [search_package]

        self.search_package = [package for package in search_package]
        self.encoding = encoding
        self.ext = ext
        self.cache = LRUCache(capacity=cache_size)

    def load(
        self,
        env: Environment,
        name: str,
        globals: Optional[TemplateNamespace] = None,
    ) -> BoundTemplate:
        return self.check_cache(
            env,
            name,
            globals,
            partial(super().load, env, name, globals),
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
            name,
            globals,
            partial(super().load_with_args, env, name, globals, **kwargs),
        )

    def load_with_context(
        self, context: Context, name: str, **kwargs: str
    ) -> BoundTemplate:
        return self.check_cache(
            context.env,
            name,
            context.globals,
            partial(super().load_with_context, context=context, name=name, **kwargs),
        )

    def check_cache(
        self,
        _: Environment,
        cache_key: str,
        globals: TemplateNamespace,
        load_func: Callable[[], BoundTemplate],
    ) -> BoundTemplate:
        try:
            cached_template = self.cache[cache_key]
        except KeyError:
            template = load_func()
            self.cache[cache_key] = template
            return template

        if globals:
            cached_template.globals.update(globals)
        return cached_template

    def get_source(self, _: Environment, template_name: str) -> TemplateSource:
        template_path = Path(template_name)
        if not template_path.suffix:
            template_path = template_path.with_suffix(self.ext)

        cause = None
        for package in self.search_package:
            try:
                return get_template_source(
                    files(package), normalize_path(template_path), self.encoding
                )
            except (ModuleNotFoundError, FileNotFoundError) as e:
                cause = e
        raise TemplateNotFound(template_name) from cause


def get_template_source(
    package_files: Traversable,
    template_path: Union[str, Path],
    encoding: Optional[str] = None,
    uptodate: UpToDate = lambda: True,
) -> TemplateSource:
    resource_path = package_files.joinpath(template_path)
    return TemplateSource(
        source=resource_path.read_text(encoding),
        filename=str(resource_path),
        uptodate=uptodate,
    )


def read_text(env: Environment, filename: str) -> str:
    return env.loader.get_source(env, filename).source


def normalize_path(template_path: Union[str, Path]) -> Path:
    if isinstance(template_path, str):
        template_path = Path(template_path)

    parts = template_path.parts
    if len(parts) > 1:
        tail = parts[-1]
        if not tail.endswith(".json") and not tail.startswith("_"):
            template_path = template_path.with_name("_" + tail)
    return template_path


def get_file_system_loader(
    search_path: Union[str, Path, Iterable[Union[str, Path]]],
    auto_reload=False,
    **kwargs,
) -> TemplateFileSystemLoader:
    return TemplateFileSystemLoader(
        search_path=search_path, auto_reload=auto_reload, **kwargs
    )


def get_resource_loader(
    search_package: Union[Package, Iterable[Package]],
    **kwargs,
) -> TemplateResourceLoader:
    return TemplateResourceLoader(search_package=search_package, **kwargs)
