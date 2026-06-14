"""Tests for empty resource filtering in FHIR conversion"""

import json
import pytest
from fhir_converter.hl7 import (
    get_fhir_entry_key,
    is_empty_resource,
    merge_extension,
    post_process_fhir,
)
from fhir_converter.parsers import parse_json
from fhir_converter.utils import merge_dict, to_list_or_empty


def _slow_parse_fhir(json_input: str):
    json_data = parse_json(json_input, use_fast_parser=False)
    if isinstance(json_data, dict):
        entries = to_list_or_empty(json_data.get("entry", []))
        if len(entries) > 1:
            unique_entries = {}
            for entry in entries:
                resource = entry.get("resource", {})
                if is_empty_resource(resource):
                    continue

                key = get_fhir_entry_key(entry)
                if key in unique_entries:
                    merge_dict(unique_entries[key], entry)
                else:
                    unique_entries[key] = entry
            json_data["entry"] = list(unique_entries.values())
        elif len(entries) == 1 and is_empty_resource(entries[0].get("resource", {})):
            json_data["entry"] = []
    return json_data


def _slow_post_process_fhir(json_data: str):
    init = _slow_parse_fhir(json_data)
    if isinstance(init, dict):
        entries = to_list_or_empty(init.get("entry", []))
        i = len(entries) - 1
        while i > 0:
            previous_type = entries[i - 1].get("resource", {}).get("resourceType")
            current_resource = entries[i].get("resource", {})
            if previous_type == current_resource.get("resourceType"):
                if "extension" in current_resource:
                    merge_extension(entries[i - 1], entries[i])
                    del entries[i]
            i -= 1

    return init


class TestEmptyResourceDetection:
    """Test suite for detecting and filtering empty FHIR resources"""

    def test_is_empty_resource_with_only_id_and_type(self):
        """Test that a resource with only id and resourceType is considered empty"""
        resource = {
            "resourceType": "Practitioner",
            "id": "ab70f8b2-cbda-5bf7-8910-0e934e6a387b"
        }
        assert is_empty_resource(resource) is True

    def test_is_empty_resource_with_data(self):
        """Test that a resource with actual data is not considered empty"""
        resource = {
            "resourceType": "Practitioner",
            "id": "ab70f8b2-cbda-5bf7-8910-0e934e6a387b",
            "name": [
                {
                    "family": "Smith",
                    "given": ["John"]
                }
            ]
        }
        assert is_empty_resource(resource) is False

    def test_is_empty_resource_with_empty_arrays(self):
        """Test that a resource with only empty arrays is considered empty"""
        resource = {
            "resourceType": "Practitioner",
            "id": "test-id",
            "identifier": [],
            "name": []
        }
        assert is_empty_resource(resource) is True

    def test_is_empty_resource_with_empty_objects(self):
        """Test that a resource with only empty objects is considered empty"""
        resource = {
            "resourceType": "Organization",
            "id": "test-id",
            "address": {},
            "contact": {}
        }
        assert is_empty_resource(resource) is True

    def test_is_empty_resource_with_null_values(self):
        """Test that a resource with only null values is considered empty"""
        resource = {
            "resourceType": "Device",
            "id": "test-id",
            "manufacturer": None,
            "deviceName": None
        }
        assert is_empty_resource(resource) is True

    def test_is_empty_resource_with_mixed_empty_and_data(self):
        """Test that a resource with some empty fields and some data is not empty"""
        resource = {
            "resourceType": "Practitioner",
            "id": "test-id",
            "identifier": [],
            "name": [{"family": "Doe"}],  # This has data
            "address": None
        }
        assert is_empty_resource(resource) is False

    def test_is_empty_resource_not_a_dict(self):
        """Test that non-dict objects return False"""
        assert is_empty_resource("not a dict") is False
        assert is_empty_resource(None) is False
        assert is_empty_resource([]) is False

    def test_post_process_fhir_filters_empty_resources(self):
        """Test that post_process_fhir removes empty resources from bundle"""
        bundle_json = json.dumps({
            "resourceType": "Bundle",
            "type": "batch",
            "entry": [
                {
                    "fullUrl": "urn:uuid:good-resource",
                    "resource": {
                        "resourceType": "Patient",
                        "id": "good-resource",
                        "name": [{"family": "Test"}]
                    }
                },
                {
                    "fullUrl": "urn:uuid:empty-resource",
                    "resource": {
                        "resourceType": "Practitioner",
                        "id": "empty-resource"
                    }
                },
                {
                    "fullUrl": "urn:uuid:another-good-resource",
                    "resource": {
                        "resourceType": "Organization",
                        "id": "another-good-resource",
                        "name": "Test Org"
                    }
                }
            ]
        })
        
        result = post_process_fhir(bundle_json)
        
        # Should only have 2 entries (the two with data)
        assert len(result["entry"]) == 2
        
        # Check that the empty Practitioner is removed
        resource_types = [e["resource"]["resourceType"] for e in result["entry"]]
        assert "Practitioner" not in resource_types
        assert "Patient" in resource_types
        assert "Organization" in resource_types

    def test_post_process_fhir_keeps_all_with_data(self):
        """Test that post_process_fhir keeps all resources that have data"""
        bundle_json = json.dumps({
            "resourceType": "Bundle",
            "type": "batch",
            "entry": [
                {
                    "fullUrl": "urn:uuid:resource-1",
                    "resource": {
                        "resourceType": "Patient",
                        "id": "resource-1",
                        "name": [{"family": "Test"}]
                    }
                },
                {
                    "fullUrl": "urn:uuid:resource-2",
                    "resource": {
                        "resourceType": "Practitioner",
                        "id": "resource-2",
                        "identifier": [{"value": "12345"}]
                    }
                }
            ]
        })
        
        result = post_process_fhir(bundle_json)
        
        # Should keep both entries
        assert len(result["entry"]) == 2

    def test_post_process_fhir_handles_non_bundle(self):
        """Test that post_process_fhir handles non-bundle resources correctly"""
        resource_json = json.dumps({
            "resourceType": "Patient",
            "id": "test-patient",
            "name": [{"family": "Test"}]
        })
        
        result = post_process_fhir(resource_json)
        
        # Should return the resource unchanged
        assert result["resourceType"] == "Patient"
        assert result["id"] == "test-patient"

    def test_integration_with_hl7v2_conversion(self):
        """Integration test to verify empty resources are filtered in actual HL7v2 conversion"""
        from fhir_converter.renderers import Hl7v2Renderer, make_environment, hl7v2_default_loader
        from liquid import FileSystemLoader
        
        renderer = Hl7v2Renderer(
            env=make_environment(
                loader=hl7v2_default_loader,
            )
        )
        
        # Simple HL7v2 message with minimal OBR data that might create empty resources
        input_data = """MSH|^~\\&|System||EMR||20241007143000||ORU^R01^ORU_R01|MSG001|P|2.5.1
PID|1||12345||Doe^John
OBR|1|ORDER001|ORDER001|TEST^Test^L|||20241007143000|||||||||||||||20241007143000"""
        
        result_json = renderer.render_fhir_string("ORU_R01", input_data)
        result = json.loads(result_json)
        
        # Check that no empty resources exist in the result
        entries = result.get("entry", [])
        for entry in entries:
            resource = entry.get("resource", {})
            assert not is_empty_resource(resource), \
                f"Found empty resource: {resource.get('resourceType')} with id {resource.get('id')}"

    def test_oru_r01_matches_json5_processing_path(self):
        """Optimized HL7v2 post-processing must match the previous JSON5-only path"""
        from fhir_converter.renderers import Hl7v2Renderer, make_environment, hl7v2_default_loader

        renderer = Hl7v2Renderer(
            env=make_environment(
                loader=hl7v2_default_loader,
            )
        )
        input_data = """MSH|^~\\&|System||EMR||20241007143000||ORU^R01^ORU_R01|MSG001|P|2.5.1
PID|1||12345||Doe^John||19850312|M
OBR|1|ORDER001|ORDER001|TEST^Test^L|||20241007143000|||||||||||||||20241007143000
OBX|1|NM|8480-6^Systolic blood pressure^LN|1|135|mm[Hg]||||||F|||20241007143000"""

        template = renderer.env.get_template("ORU_R01", globals=renderer.template_globals)
        rendered = template.render({"hl7v2Data": renderer._parse_hl7v2(input_data)})

        assert post_process_fhir(rendered) == _slow_post_process_fhir(rendered)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
