from json import loads
from unittest import TestCase

from liquid import BoundTemplate, Context, Environment, FileExtensionLoader
from liquid.exceptions import TemplateNotFound
from liquid.loaders import BaseLoader
from pytest import raises

from fhir_converter.loaders import ResourceLoader, TemplateSystemLoader, read_text
from fhir_converter.tags import all_tags, register_tags


def build_env(loader: BaseLoader, **kwargs) -> Environment:
    env = Environment(loader=loader, **kwargs)
    register_tags(env, all_tags)
    return env


class ResourceLoaderTest(TestCase):
    @staticmethod
    def get_rendering_env(
        search_package: str = "fhir_converter.templates.ccda", **kwargs
    ) -> Environment:
        return build_env(ResourceLoader(search_package), **kwargs)

    def test_load_template(self) -> None:
        template = self.get_rendering_env().get_template(name="CCD.liquid")
        self.assertIsInstance(template, BoundTemplate)

    def test_load_template_without_suffix(self) -> None:
        template = self.get_rendering_env().get_template(name="CCD")
        self.assertIsInstance(template, BoundTemplate)

    def test_cached_template(self) -> None:
        env = self.get_rendering_env()
        template = env.get_template(name="CCD.liquid")
        self.assertIsInstance(template, BoundTemplate)

        another = env.get_template(name="CCD.liquid")
        self.assertIsInstance(template, BoundTemplate)
        self.assertEqual(template.tree, another.tree)

    def test_disable_template_cache(self) -> None:
        env = self.get_rendering_env(cache_size=0)
        template = env.get_template(name="CCD.liquid")
        self.assertTrue(template.is_up_to_date)

        another = env.get_template(name="CCD.liquid")
        self.assertTrue(another.is_up_to_date)
        self.assertIsNot(template.tree, another.tree)

    def test_template_not_found(self) -> None:
        with raises(TemplateNotFound):
            self.get_rendering_env().get_template(name="nosuchthing.liquid")

    def test_no_such_search_path(self) -> None:
        with raises(TemplateNotFound):
            self.get_rendering_env(search_package="nosuchthing").get_template(
                name="nosuchthing.liquid"
            )


class TemplateSystemLoaderTest(TestCase):
    loaders = [
        FileExtensionLoader(search_path="data/templates/ccda"),
        ResourceLoader(search_package="fhir_converter.templates.ccda"),
    ]

    def get_rendering_env(
        self,
        loader_cache_size: int = 1,
        **kwargs,
    ) -> Environment:
        return build_env(
            TemplateSystemLoader(
                loaders=self.loaders,
                cache_size=loader_cache_size,
            ),
            **kwargs,
        )

    def test_load_template(self) -> None:
        template = self.get_rendering_env().get_template(name="Pampi.liquid")
        self.assertIsInstance(template, BoundTemplate)

    def test_load_template_with_args(self) -> None:
        template = self.get_rendering_env().get_template_with_args(name="Pampi.liquid")
        self.assertIsInstance(template, BoundTemplate)

    def test_load_template_with_context(self) -> None:
        env = self.get_rendering_env()
        template = env.get_template_with_context(
            context=Context(env), name="Pampi.liquid"
        )
        self.assertIsInstance(template, BoundTemplate)

    def test_load_template_without_suffix(self) -> None:
        template = self.get_rendering_env().get_template(name="Pampi")
        self.assertIsInstance(template, BoundTemplate)

    def test_load_resource_template(self) -> None:
        template = self.get_rendering_env().get_template(name="CCD.liquid")
        self.assertIsInstance(template, BoundTemplate)

    def test_load_resource_without_suffix(self) -> None:
        template = self.get_rendering_env().get_template(name="CCD")
        self.assertIsInstance(template, BoundTemplate)

    def test_load_internal_resource_template(self) -> None:
        template = self.get_rendering_env().get_template(name="Utils/GenerateId")
        self.assertIsInstance(template, BoundTemplate)

    def test_cached_template(self) -> None:
        env = self.get_rendering_env()
        template = env.get_template(name="Pampi.liquid")
        self.assertIsInstance(template, BoundTemplate)

        another = env.get_template(name="Pampi.liquid")
        self.assertIsInstance(template, BoundTemplate)
        self.assertEqual(template.tree, another.tree)

    def test_cached_template_with_globals(self) -> None:
        env = self.get_rendering_env()
        template = env.get_template(name="Pampi.liquid", globals={"test": "one"})
        self.assertEqual({"test": "one"}, template.globals)

        another = env.get_template(name="Pampi.liquid", globals={"test": "two"})
        self.assertEqual({"test": "two"}, template.globals)
        self.assertEqual(template.tree, another.tree)

    def test_cached_resource_template(self) -> None:
        env = self.get_rendering_env()
        template = env.get_template(name="CCD.liquid")
        self.assertIsInstance(template, BoundTemplate)

        another = env.get_template(name="CCD.liquid")
        self.assertIsInstance(template, BoundTemplate)
        self.assertEqual(template.tree, another.tree)

    def test_disable_env_cache_template_cached(self) -> None:
        env = self.get_rendering_env(cache_size=0)
        template = env.get_template(name="Pampi.liquid")
        self.assertTrue(template.is_up_to_date)

        self.assertIsNone(env.cache)

        another = env.get_template(name="Pampi.liquid")
        self.assertTrue(another.is_up_to_date)
        self.assertEqual(template.tree, another.tree)

    def test_disable_loader_cache_template_not_cached(self) -> None:
        env = self.get_rendering_env(loader_cache_size=0)
        template = env.get_template(name="Pampi.liquid")
        self.assertTrue(template.is_up_to_date)

        # The environment only caches when the loader is not a caching loader,
        # if this changes, this will not be None
        self.assertIsNone(env.cache)

        another = env.get_template(name="Pampi.liquid")
        self.assertTrue(another.is_up_to_date)
        self.assertIsNot(template.tree, another.tree)

    def test_disable_caches_template_not_cached(self) -> None:
        env = self.get_rendering_env(loader_cache_size=0, cache_size=0)
        template = env.get_template(name="Pampi.liquid")
        self.assertTrue(template.is_up_to_date)

        another = env.get_template(name="Pampi.liquid")
        self.assertTrue(another.is_up_to_date)
        self.assertIsNot(template.tree, another.tree)

    def test_template_not_found(self) -> None:
        with raises(TemplateNotFound):
            self.get_rendering_env().get_template(name="nosuchthing.liquid")


class ReadTextTest(TestCase):
    env = build_env(ResourceLoader(search_package="fhir_converter.templates.ccda"))

    def test_file_not_found(self) -> None:
        with raises(FileNotFoundError, match="File not found nosuchthing.json"):
            read_text(self.env, "nosuchthing.json")

    def test_read_file_text(self) -> None:
        self.assertEqual({"type": "ccda"}, loads(read_text(self.env, "metadata.json")))
