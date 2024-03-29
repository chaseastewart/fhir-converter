from collections.abc import Mapping
from io import StringIO
from json import loads
from pathlib import Path
from typing import cast
from unittest import TestCase

from liquid import FileExtensionLoader
from liquid.utils import LRUCache
from pyexpat import ExpatError
from pyjson5 import Json5EOF
from pytest import raises

from fhir_converter.loaders import CachingTemplateSystemLoader, TemplateSystemLoader
from fhir_converter.renderers import (
    CcdaRenderer,
    RenderingError,
    Stu3FhirRenderer,
    ccda_default_loader,
    make_environment,
    stu3_default_loader,
)


class MakeEnvironmentTest(TestCase):
    def test_defaults(self) -> None:
        env = make_environment(loader=ccda_default_loader)
        self.assertFalse(env.auto_reload)
        self.assertIsNone(env.cache)

        self.assertIsInstance(env.loader, CachingTemplateSystemLoader)
        loader = cast(CachingTemplateSystemLoader, env.loader)
        self.assertFalse(loader.auto_reload)
        self.assertEqual([ccda_default_loader], loader.loaders)

        self.assertIsInstance(loader.cache, LRUCache)
        self.assertEqual(loader.cache.capacity, 300)  # type: ignore

    def test_auto_reload(self) -> None:
        env = make_environment(loader=ccda_default_loader, auto_reload=True)
        self.assertFalse(env.auto_reload)
        self.assertIsNone(env.cache)

        loader = cast(CachingTemplateSystemLoader, env.loader)
        self.assertTrue(loader.auto_reload)

    def test_cache_size(self) -> None:
        env = make_environment(loader=ccda_default_loader, cache_size=1)
        self.assertFalse(env.auto_reload)
        self.assertIsNone(env.cache)

        loader = cast(CachingTemplateSystemLoader, env.loader)
        self.assertEqual(loader.cache.capacity, 1)  # type: ignore

    def test_cache_disabled(self) -> None:
        env = make_environment(loader=ccda_default_loader, cache_size=0)
        self.assertFalse(env.auto_reload)
        self.assertIsNone(env.cache)
        self.assertIsInstance(env.loader, TemplateSystemLoader)

    def test_additional_loaders(self) -> None:
        loader = FileExtensionLoader(search_path="data/templates/ccda")
        env = make_environment(
            loader,
            additional_loaders=[ccda_default_loader],
        )
        self.assertEqual([loader, ccda_default_loader], env.loader.loaders)  # type: ignore


class Stu3FhirRendererTest(TestCase):
    stu3_file = Path("tests/data/stu3/Immunization.json")

    def validate_str(self, fhir_str: str) -> None:
        self.validate(loads(fhir_str))

    def validate(self, fhir: Mapping) -> None:
        self.assertEqual(fhir["resourceType"], "Immunization")
        self.assertEqual(fhir["status"], "completed")
        self.assertNotIn("notGiven", fhir)
        # TODO validation!

    def test_render_fhir_string_json_error(self) -> None:
        with raises(RenderingError, match="Failed to render FHIR") as exc_info:
            Stu3FhirRenderer().render_fhir_string("Immunization", "")
        self.assertIsInstance(exc_info.value.__cause__, Json5EOF)

    def test_render_fhir_string_text(self) -> None:
        self.validate_str(
            Stu3FhirRenderer().render_fhir_string(
                "Immunization", self.stu3_file.read_text(encoding="utf-8")
            )
        )

    def test_render_fhir_string_bytes(self) -> None:
        self.validate_str(
            Stu3FhirRenderer().render_fhir_string(
                "Immunization", self.stu3_file.read_bytes()
            )
        )

    def test_render_fhir_string_text_io(self) -> None:
        with self.stu3_file.open(encoding="utf-8") as fhir_in:
            self.validate_str(
                Stu3FhirRenderer().render_fhir_string("Immunization", fhir_in)
            )

    def test_render_fhir_string_binary_io(self) -> None:
        with self.stu3_file.open("rb") as fhir_in:
            self.validate_str(
                Stu3FhirRenderer().render_fhir_string("Immunization", fhir_in)
            )

    def test_render_to_fhir_json_error(self) -> None:
        with raises(RenderingError, match="Failed to render FHIR") as exc_info:
            Stu3FhirRenderer().render_to_fhir("Immunization", "")
        self.assertIsInstance(exc_info.value.__cause__, Json5EOF)

    def test_render_to_fhir_text(self) -> None:
        self.validate(
            Stu3FhirRenderer().render_to_fhir(
                "Immunization", self.stu3_file.read_text(encoding="utf-8")
            )
        )

    def test_render_to_fhir_bytes(self) -> None:
        self.validate(
            Stu3FhirRenderer().render_to_fhir("Immunization", self.stu3_file.read_bytes())
        )

    def test_render_to_fhir_text_io(self) -> None:
        with self.stu3_file.open(encoding="utf-8") as fhir_in:
            self.validate(Stu3FhirRenderer().render_to_fhir("Immunization", fhir_in))

    def test_render_to_fhir_binary_io(self) -> None:
        with self.stu3_file.open("rb") as fhir_in:
            self.validate(Stu3FhirRenderer().render_to_fhir("Immunization", fhir_in))

    def test_render_fhir_serialize_error(self) -> None:
        buffer = StringIO()
        buffer.close()

        with raises(RenderingError, match="Failed to serialize FHIR") as exc_info:
            with self.stu3_file.open(encoding="utf-8") as fhir_in:
                Stu3FhirRenderer().render_fhir("Immunization", fhir_in, buffer)
        self.assertIsInstance(exc_info.value.__cause__, ValueError)
        self.assertEqual(str(exc_info.value.__cause__), "I/O operation on closed file")

    def test_render_fhir_text(self) -> None:
        buffer = StringIO()
        Stu3FhirRenderer().render_fhir(
            "Immunization", self.stu3_file.read_text(encoding="utf-8"), buffer
        )
        self.validate_str(buffer.getvalue())

    def test_render_fhir_bytes(self) -> None:
        buffer = StringIO()
        Stu3FhirRenderer().render_fhir(
            "Immunization", self.stu3_file.read_bytes(), buffer
        )
        self.validate_str(buffer.getvalue())

    def test_render_env_provided(self) -> None:
        renderer = Stu3FhirRenderer(make_environment(loader=stu3_default_loader))
        self.validate(
            renderer.render_to_fhir(
                "Immunization", self.stu3_file.read_text(encoding="utf-8")
            )
        )


class CcdaRendererTest(TestCase):
    ccda_file = Path("tests/data/ccda/CCD.ccda")

    def validate_str(self, fhir_str: str) -> None:
        self.validate(loads(fhir_str))

    def validate(self, fhir: Mapping) -> None:
        self.assertEqual(fhir["resourceType"], "Bundle")
        self.assertEqual(fhir["type"], "batch")
        self.assertIsInstance(fhir["entry"], list)
        # TODO validation!

    def test_render_fhir_string_xml_error(self) -> None:
        with raises(RenderingError, match="Failed to render FHIR") as exc_info:
            CcdaRenderer().render_fhir_string("CCD", "")
        self.assertIsInstance(exc_info.value.__cause__, ExpatError)

    def test_render_fhir_string_text(self) -> None:
        self.validate_str(
            CcdaRenderer().render_fhir_string(
                "CCD", self.ccda_file.read_text(encoding="utf-8")
            )
        )

    def test_render_fhir_string_bytes(self) -> None:
        self.validate_str(
            CcdaRenderer().render_fhir_string("CCD", self.ccda_file.read_bytes())
        )

    def test_render_fhir_string_text_io(self) -> None:
        with self.ccda_file.open(encoding="utf-8") as xml_in:
            self.validate_str(CcdaRenderer().render_fhir_string("CCD", xml_in))

    def test_render_fhir_string_binary_io(self) -> None:
        with self.ccda_file.open("rb") as xml_in:
            self.validate_str(CcdaRenderer().render_fhir_string("CCD", xml_in))

    def test_render_to_fhir_xml_error(self) -> None:
        with raises(RenderingError, match="Failed to render FHIR") as exc_info:
            CcdaRenderer().render_to_fhir("CCD", "")
        self.assertIsInstance(exc_info.value.__cause__, ExpatError)
        self.assertEqual(
            str(exc_info.value.__cause__), "no element found: line 1, column 0"
        )

    def test_render_to_fhir_text(self) -> None:
        self.validate(
            CcdaRenderer().render_to_fhir(
                "CCD", self.ccda_file.read_text(encoding="utf-8")
            )
        )

    def test_render_to_fhir_bytes(self) -> None:
        self.validate(CcdaRenderer().render_to_fhir("CCD", self.ccda_file.read_bytes()))

    def test_render_to_fhir_text_io(self) -> None:
        with self.ccda_file.open(encoding="utf-8") as xml_in:
            self.validate(CcdaRenderer().render_to_fhir("CCD", xml_in))

    def test_render_to_fhir_binary_io(self) -> None:
        with self.ccda_file.open("rb") as xml_in:
            self.validate(CcdaRenderer().render_to_fhir("CCD", xml_in))

    def test_render_fhir_serialize_error(self) -> None:
        buffer = StringIO()
        buffer.close()

        with raises(RenderingError, match="Failed to serialize FHIR") as exc_info:
            with self.ccda_file.open(encoding="utf-8") as xml_in:
                CcdaRenderer().render_fhir("CCD", xml_in, buffer)
        self.assertIsInstance(exc_info.value.__cause__, ValueError)
        self.assertEqual(str(exc_info.value.__cause__), "I/O operation on closed file")

    def test_render_fhir_text(self) -> None:
        buffer = StringIO()
        CcdaRenderer().render_fhir(
            "CCD", self.ccda_file.read_text(encoding="utf-8"), buffer
        )
        self.validate_str(buffer.getvalue())

    def test_render_fhir_bytes(self) -> None:
        buffer = StringIO()
        CcdaRenderer().render_fhir("CCD", self.ccda_file.read_bytes(), buffer)
        self.validate_str(buffer.getvalue())

    def test_render_env_provided(self) -> None:
        renderer = CcdaRenderer(make_environment(loader=ccda_default_loader))
        self.validate(
            renderer.render_to_fhir("CCD", self.ccda_file.read_text(encoding="utf-8"))
        )
