from liquid import CachingFileSystemLoader, Environment
from liquid.exceptions import TemplateNotFound
from liquid.loaders import TemplateSource


def get_template_resource(env: Environment, resource_name: str) -> str:
    return env.loader.get_source(env, resource_name).source


class TemplateLoader(CachingFileSystemLoader):
    def _normalize_name(self, template_name: str) -> str:
        idx = template_name.rfind("/") + 1
        if idx:
            tail = template_name[idx:]
            if not tail.startswith("_"):
                return template_name[:idx] + "_" + tail
        return template_name

    def get_source(self, env: Environment, template_name: str) -> TemplateSource:
        func = super().get_source
        try:
            return func(env, self._normalize_name(template_name))
        except TemplateNotFound:
            return func(env, template_name)

    async def get_source_async(
        self, env: Environment, template_name: str
    ) -> TemplateSource:
        func = super().get_source_async
        try:
            return await func(env, self._normalize_name(template_name))
        except TemplateNotFound:
            return await func(env, template_name)
