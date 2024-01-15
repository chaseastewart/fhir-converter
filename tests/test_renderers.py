from collections.abc import Mapping
from io import StringIO
from json import loads
from unittest import TestCase

from liquid import FileExtensionLoader
from liquid.utils import LRUCache
from pyexpat import ExpatError
from pytest import raises

from fhir_converter.loaders import TemplateSystemLoader
from fhir_converter.renderers import (
    CcdaRenderer,
    RenderingError,
    ccda_default_loader,
    get_environment,
)


class GetEnvironmentTest(TestCase):
    def test_defaults(self) -> None:
        env = get_environment(loader=ccda_default_loader)
        self.assertFalse(env.auto_reload)
        self.assertIsNone(env.cache)

        self.assertIsInstance(env.loader, TemplateSystemLoader)
        loader: TemplateSystemLoader = env.loader  # type: ignore
        self.assertFalse(loader.auto_reload)
        self.assertTrue(loader.is_caching)
        self.assertEqual([ccda_default_loader], loader.loaders)

        self.assertIsInstance(loader.cache, LRUCache)
        self.assertEqual(loader.cache.capacity, 300)  # type: ignore

    def test_auto_reload(self) -> None:
        env = get_environment(loader=ccda_default_loader, auto_reload=True)
        self.assertFalse(env.auto_reload)
        self.assertIsNone(env.cache)

        self.assertTrue(env.loader.auto_reload)  # type: ignore

    def test_cache_size(self) -> None:
        env = get_environment(loader=ccda_default_loader, cache_size=1)
        self.assertFalse(env.auto_reload)
        self.assertIsNone(env.cache)

        self.assertTrue(env.loader.is_caching)  # type: ignore
        self.assertEqual(env.loader.cache.capacity, 1)  # type: ignore

    def test_cache_disabled(self) -> None:
        env = get_environment(loader=ccda_default_loader, cache_size=0)
        self.assertFalse(env.auto_reload)
        self.assertIsNone(env.cache)

        self.assertFalse(env.loader.is_caching)  # type: ignore
        self.assertIsInstance(env.loader.cache, dict)  # type: ignore

    def test_additional_loaders(self) -> None:
        loader = FileExtensionLoader(search_path="data/templates/ccda")
        env = get_environment(
            loader,
            additional_loaders=[ccda_default_loader],
        )
        self.assertEqual([loader, ccda_default_loader], env.loader.loaders)  # type: ignore


class CcdaRendererTest(TestCase):
    def validate(self, fhir: Mapping) -> None:
        self.assertEqual(fhir["resourceType"], "Bundle")
        self.assertEqual(fhir["type"], "batch")
        self.assertIsInstance(fhir["entry"], list)
        # TODO validation!

    def test_render_fhir_string_xml_error(self) -> None:
        with raises(RenderingError, match="Failed to render FHIR") as exc_info:
            CcdaRenderer().render_fhir_string("CCD", "")
        self.assertIsInstance(exc_info.value.__cause__, ExpatError)

    def test_render_fhir_string_text_str(self) -> None:
        with open("tests/data/ccda/CCD.ccda") as xml_in:
            self.validate(loads(CcdaRenderer().render_fhir_string("CCD", xml_in.read())))

    def test_render_fhir_string_text(self) -> None:
        with open("tests/data/ccda/CCD.ccda") as xml_in:
            self.validate(loads(CcdaRenderer().render_fhir_string("CCD", xml_in)))

    def test_render_fhir_string_binary(self) -> None:
        with open("tests/data/ccda/CCD.ccda", "rb") as xml_in:
            self.validate(loads(CcdaRenderer().render_fhir_string("CCD", xml_in)))

    def test_render_to_fhir_xml_error(self) -> None:
        with raises(RenderingError, match="Failed to render FHIR") as exc_info:
            CcdaRenderer().render_to_fhir("CCD", "")
        self.assertIsInstance(exc_info.value.__cause__, ExpatError)
        self.assertEqual(
            str(exc_info.value.__cause__), "no element found: line 1, column 0"
        )

    def test_render_to_fhir_text_str(self) -> None:
        with open("tests/data/ccda/CCD.ccda") as xml_in:
            self.validate(CcdaRenderer().render_to_fhir("CCD", xml_in.read()))

    def test_render_to_fhir_text(self) -> None:
        with open("tests/data/ccda/CCD.ccda") as xml_in:
            self.validate(CcdaRenderer().render_to_fhir("CCD", xml_in))

    def test_render_to_fhir_binary(self) -> None:
        with open("tests/data/ccda/CCD.ccda", "rb") as xml_in:
            self.validate(CcdaRenderer().render_to_fhir("CCD", xml_in))

    def test_render_fhir_serialize_error(self) -> None:
        buffer = StringIO()
        buffer.close()

        with raises(RenderingError, match="Failed to serialize FHIR") as exc_info:
            with open("tests/data/ccda/CCD.ccda") as xml_in:
                CcdaRenderer().render_fhir("CCD", xml_in, buffer)
        self.assertIsInstance(exc_info.value.__cause__, ValueError)
        self.assertEqual(str(exc_info.value.__cause__), "I/O operation on closed file")
