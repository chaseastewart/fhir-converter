"""
Test custom template loading with FileSystemLoader and additional_loaders
"""
import pytest
import tempfile
import os
from pathlib import Path
from liquid import FileSystemLoader
from fhir_converter.renderers import Hl7v2Renderer, make_environment, hl7v2_default_loader


class TestCustomTemplateLoading:
    """Test that custom templates can be loaded with FileSystemLoader alongside default templates"""

    def test_custom_template_with_file_system_loader(self):
        """Test loading a custom template from FileSystemLoader with fallback to default templates"""
        # Create a temporary directory with a custom template
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a simple custom template
            custom_template_path = Path(tmpdir) / "CUSTOM_TEST.liquid"
            custom_template_content = """
{
    "resourceType": "Bundle",
    "type": "custom",
    "id": "test-bundle"
}
"""
            custom_template_path.write_text(custom_template_content)

            # Create renderer with FileSystemLoader (with ext parameter) and additional_loaders
            renderer = Hl7v2Renderer(
                env=make_environment(
                    loader=FileSystemLoader(search_path=tmpdir, ext=".liquid"),
                    additional_loaders=[hl7v2_default_loader],
                )
            )

            # Test data
            test_hl7_data = """MSH|^~\\&|ADT1|MCM|LABADT|MCM|198808181126|SECURITY|ADT^A01|MSG00001|P|2.5|
EVN|A01|198808181123||
PID|||PATID1234^5^M11||DOE^JOHN||||M||WH|1200 N ELM STREET^^GREENSBORO^NC^27401-1020|GL|(919)379-1212|(919)271-3434||S||PATID12345001^2^M10|123456789|9-87654^NC"""

            # Try to render using the custom template
            result = renderer.render_fhir_string("CUSTOM_TEST", test_hl7_data)
            
            # Verify the custom template was used
            assert "test-bundle" in result
            assert "custom" in result

    def test_fallback_to_default_template(self):
        """Test that default templates are still accessible when using custom FileSystemLoader"""
        # Create a temporary directory (empty)
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create renderer with empty FileSystemLoader but with additional_loaders
            renderer = Hl7v2Renderer(
                env=make_environment(
                    loader=FileSystemLoader(search_path=tmpdir, ext=".liquid"),
                    additional_loaders=[hl7v2_default_loader],
                )
            )

            # Test data
            test_hl7_data = """MSH|^~\\&|ADT1|MCM|LABADT|MCM|198808181126|SECURITY|ADT^A01|MSG00001|P|2.5|
EVN|A01|198808181123||
PID|||PATID1234^5^M11||DOE^JOHN||||M||WH|1200 N ELM STREET^^GREENSBORO^NC^27401-1020|GL|(919)379-1212|(919)271-3434||S||PATID12345001^2^M10|123456789|9-87654^NC"""

            # Try to render using a default template (should fallback to additional_loaders)
            result = renderer.render_fhir_string("ADT_A01", test_hl7_data)
            
            # Verify it rendered successfully (default template was found)
            assert "Bundle" in result
            assert "resourceType" in result

    def test_custom_template_overrides_default(self):
        """Test that custom template takes precedence over default template with same name"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a custom ADT_A01 template that overrides the default
            custom_template_path = Path(tmpdir) / "ADT_A01.liquid"
            custom_template_content = """
{
    "resourceType": "Bundle",
    "type": "custom-override",
    "id": "override-bundle"
}
"""
            custom_template_path.write_text(custom_template_content)

            # Create renderer with FileSystemLoader (with ext parameter) and additional_loaders
            renderer = Hl7v2Renderer(
                env=make_environment(
                    loader=FileSystemLoader(search_path=tmpdir, ext=".liquid"),
                    additional_loaders=[hl7v2_default_loader],
                )
            )

            # Test data
            test_hl7_data = """MSH|^~\\&|ADT1|MCM|LABADT|MCM|198808181126|SECURITY|ADT^A01|MSG00001|P|2.5|
EVN|A01|198808181123||
PID|||PATID1234^5^M11||DOE^JOHN||||M||WH|1200 N ELM STREET^^GREENSBORO^NC^27401-1020|GL|(919)379-1212|(919)271-3434||S||PATID12345001^2^M10|123456789|9-87654^NC"""

            # Render using ADT_A01 - should use custom version
            result = renderer.render_fhir_string("ADT_A01", test_hl7_data)
            
            # Verify the custom template was used (not the default)
            assert "override-bundle" in result
            assert "custom-override" in result

    def test_filesystem_loader_requires_ext_parameter(self):
        """Test that FileSystemLoader without ext parameter requires full filename"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a custom template
            custom_template_path = Path(tmpdir) / "TEST_NO_EXT.liquid"
            custom_template_content = """{"test": "no-ext"}"""
            custom_template_path.write_text(custom_template_content)

            # Create renderer WITHOUT ext parameter - should NOT find template by name only
            renderer_no_ext = Hl7v2Renderer(
                env=make_environment(
                    loader=FileSystemLoader(search_path=tmpdir),  # No ext parameter
                    additional_loaders=[hl7v2_default_loader],
                )
            )

            # Test data
            test_hl7_data = """MSH|^~\\&|ADT1|MCM|LABADT|MCM|198808181126|SECURITY|ADT^A01|MSG00001|P|2.5|
EVN|A01|198808181123||
PID|||PATID1234^5^M11||DOE^JOHN||||M||WH|1200 N ELM STREET^^GREENSBORO^NC^27401-1020|GL|(919)379-1212|(919)271-3434||S||PATID12345001^2^M10|123456789|9-87654^NC"""

            # Try to render with just the name (should fail or fallback to default)
            from fhir_converter.exceptions import RenderingError
            with pytest.raises(RenderingError):
                renderer_no_ext.render_fhir_string("TEST_NO_EXT", test_hl7_data)

            # But should work with full filename including extension
            result = renderer_no_ext.render_fhir_string("TEST_NO_EXT.liquid", test_hl7_data)
            assert "no-ext" in result
