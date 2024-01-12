from base64 import b64decode
from datetime import timezone
from unittest import TestCase
from zlib import decompress

from liquid import BoundTemplate, DictLoader, Environment
from liquid.exceptions import (
    FilterArgumentError,
    NoSuchFilterFunc,
    OutputStreamLimitError,
    TemplateNotFound,
)
from pytest import fixture, raises

from fhir_converter.filters import all_filters, register_filters
from fhir_converter.hl7 import Hl7DtmPrecision


class FilterTest:
    template: str
    bound_template: BoundTemplate

    def setup_template(self, **kwargs) -> None:
        Environment.output_stream_limit = None
        env = Environment(strict_filters=True, **kwargs)
        register_filters(env, all_filters)

        self.template = self.template.strip()
        self.bound_template = env.from_string(self.template)

    def test_unregistered(self) -> None:
        with raises(NoSuchFilterFunc):
            Environment().from_string(self.template).render()


class ToJsonStringTest(TestCase, FilterTest):
    template = """{{ content | to_json_string }}"""

    def setUp(self) -> None:
        self.setup_template()

    def test_undefined(self) -> None:
        result = self.bound_template.render()
        self.assertEqual(result, "")

    def test_empty_content(self) -> None:
        result = self.bound_template.render(content="")
        self.assertEqual(result, "")

        result = self.bound_template.render(content={})
        self.assertEqual(result, "")

    def test_content(self) -> None:
        result = self.bound_template.render(content={"key": "val"})
        self.assertEqual(result, """{"key":"val"}""")


class ToArrayTest(TestCase, FilterTest):
    template = """
        {% assign keys = el.key | to_array -%}
        {% for key in keys -%}{{key}},{% endfor -%}
        """

    def setUp(self) -> None:
        self.setup_template()

    def test_list(self) -> None:
        result = self.bound_template.render(el={"key": ["one", "two", "three"]})
        self.assertEqual(result, "one,two,three,")

    def test_wrap(self) -> None:
        result = self.bound_template.render(el={"key": "one"})
        self.assertEqual(result, "one,")

    def test_undefined(self) -> None:
        result = self.bound_template.render()
        self.assertEqual(result, "")


class MatchTest(TestCase, FilterTest):
    template = """{{data | match: "[0123456789.]+" | join}}"""

    def setUp(self) -> None:
        self.setup_template()

    def test_match(self) -> None:
        result = self.bound_template.render(data="2.16.840.1.113883.6.1")
        self.assertEqual(result, "2.16.840.1.113883.6.1")

        result = self.bound_template.render(data="2.16,840.1.113883,6.1")
        self.assertEqual(result, "2.16 840.1.113883 6.1")

    def test_does_not_match(self) -> None:
        result = self.bound_template.render(data="nonumbers")
        self.assertEqual(result, "")

    def test_empty_string(self) -> None:
        result = self.bound_template.render(data="")
        self.assertEqual(result, "")

    def test_undefined(self) -> None:
        result = self.bound_template.render()
        self.assertEqual(result, "")


class GzipTest(TestCase, FilterTest):
    template = """{{ content | gzip }}"""

    def setUp(self) -> None:
        self.setup_template()

    @staticmethod
    def decode(result: str = "") -> str:
        return decompress(b64decode(result)).decode()

    def test_undefined(self) -> None:
        result = self.bound_template.render()
        self.assertEqual("", self.decode(result))

    def test_empty_content(self) -> None:
        result = self.bound_template.render(content="")
        self.assertEqual("", self.decode(result))

    def test_content(self) -> None:
        result = self.bound_template.render(content="test")
        self.assertEqual("test", self.decode(result))


class Sha1HashTest(TestCase, FilterTest):
    template = """{{ content | sha1_hash }}"""

    def setUp(self) -> None:
        self.setup_template()

    def test_undefined(self) -> None:
        result = self.bound_template.render()
        self.assertEqual(result, "da39a3ee5e6b4b0d3255bfef95601890afd80709")

    def test_empty_content(self) -> None:
        result = self.bound_template.render(content="")
        self.assertEqual(result, "da39a3ee5e6b4b0d3255bfef95601890afd80709")

    def test_content(self) -> None:
        result = self.bound_template.render(content="test")
        self.assertEqual(result, "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3")


class AddHyphensDateTest(TestCase, FilterTest):
    template = """{{ date | add_hyphens_date }}"""

    @fixture(autouse=True, scope="function")
    def hl7_to_fhir_dtm_mock(self, mocker):
        mocked = mocker.patch(
            "fhir_converter.filters.hl7_to_fhir_dtm",
            return_value="2024-01-10",
        )
        self._hl7_to_fhir_dtm_mock = mocked
        return mocked

    def setUp(self) -> None:
        self.setup_template()

    def test_undefined(self) -> None:
        result = self.bound_template.render()
        self.assertEqual(result, "")
        self._hl7_to_fhir_dtm_mock.assert_not_called()

    def test_empty_date(self) -> None:
        result = self.bound_template.render(date="")
        self.assertEqual(result, "")
        self._hl7_to_fhir_dtm_mock.assert_not_called()

    def test_date(self) -> None:
        result = self.bound_template.render(date="20240110063457.920+0000")
        self.assertEqual(result, "2024-01-10")
        self._hl7_to_fhir_dtm_mock.assert_called_once_with(
            "20240110063457.920+0000", precision=Hl7DtmPrecision.DAY
        )


class FormatAsDateTimeTest(TestCase, FilterTest):
    template = """{{ date | format_as_date_time }}"""

    def setUp(self) -> None:
        self.setup_template()

    def test_undefined(self) -> None:
        result = self.bound_template.render()
        self.assertEqual(result, "")

    def test_empty_date(self) -> None:
        result = self.bound_template.render(date="")
        self.assertEqual(result, "")

    def test(self) -> None:
        result = self.bound_template.render(date="20240110063557.920+0000")
        self.assertEqual(result, "2024-01-10T06:35:57.920Z")


class NowTest(TestCase, FilterTest):
    template = """{{ "" | now }}"""

    @fixture(autouse=True, scope="function")
    def to_fhir_dtm_mock(self, mocker):
        mocked = mocker.patch(
            "fhir_converter.filters.to_fhir_dtm", return_value="2024-01-10T06:34:57.920Z"
        )
        self._to_fhir_dtm_mock = mocked
        return mocked

    def setUp(self) -> None:
        self.setup_template()

    def test(self) -> None:
        result = self.bound_template.render()
        self.assertEqual(result, "2024-01-10T06:34:57.920Z")
        self._to_fhir_dtm_mock.assert_called_once()

        args, kwargs = self._to_fhir_dtm_mock.call_args
        self.assertDictEqual({}, kwargs)
        self.assertEqual(1, len(args))
        self.assertEqual(timezone.utc, args[0].tzinfo)


class GenerateUuidTest(TestCase, FilterTest):
    template = """{{ data | generate_uuid }}"""

    def setUp(self) -> None:
        self.setup_template()

    def test_undefined(self) -> None:
        result = self.bound_template.render()
        self.assertEqual(result, "")

    def test_uuid(self) -> None:
        result = self.bound_template.render(data="This is a test.")
        self.assertEqual(result, "a8a2f6eb-e286-697c-527e-b35a58b55395")


class GetPropertTest(TestCase, FilterTest):
    template = """{{ status | get_property: key, property }}"""

    template_globals: dict = {
        "code_mapping": {
            "RequestStatus": {
                "fatal": {"code": "severe", "display": "very severe"},
                "retry": {"other": "retrying"},
                "__default__": {
                    "code": "bad",
                    "display": "very bad",
                    "other": "could be worse",
                },
            }
        }
    }

    def setUp(self) -> None:
        self.setup_template(globals=self.template_globals)

    def test_undefined(self) -> None:
        result = self.bound_template.render()
        self.assertEqual(result, "")

    def test_undefined_property(self) -> None:
        result = self.bound_template.render(status="undefined", key="Undefined")
        self.assertEqual(result, "undefined")

    def test_undefined_property_code(self) -> None:
        result = self.bound_template.render(
            status="undefined", key="Undefined", property="code"
        )
        self.assertEqual(result, "undefined")

    def test_undefined_property_display(self) -> None:
        result = self.bound_template.render(
            status="undefined", key="Undefined", property="display"
        )
        self.assertEqual(result, "undefined")

    def test_undefined_property_other(self) -> None:
        result = self.bound_template.render(
            status="undefined", key="Undefined", property="other"
        )
        self.assertEqual(result, "")

    def test_default_property(self) -> None:
        result = self.bound_template.render(status="aborted", key="RequestStatus")
        self.assertEqual(result, "bad")

    def test_default_property_code(self) -> None:
        result = self.bound_template.render(
            status="aborted", key="RequestStatus", property="code"
        )
        self.assertEqual(result, "bad")

    def test_default_property_display(self) -> None:
        result = self.bound_template.render(
            status="aborted", key="RequestStatus", property="display"
        )
        self.assertEqual(result, "very bad")

    def test_default_property_other(self) -> None:
        result = self.bound_template.render(
            status="aborted", key="RequestStatus", property="other"
        )
        self.assertEqual(result, "could be worse")

    def test_default_property_undefined(self) -> None:
        result = self.bound_template.render(
            status="aborted", key="RequestStatus", property="undefined"
        )
        self.assertEqual(result, "")

    def test_property(self) -> None:
        result = self.bound_template.render(status="fatal", key="RequestStatus")
        self.assertEqual(result, "severe")

    def test_property_display(self) -> None:
        result = self.bound_template.render(
            status="fatal", key="RequestStatus", property="display"
        )
        self.assertEqual(result, "very severe")

    def test_property_other(self) -> None:
        result = self.bound_template.render(
            status="retry", key="RequestStatus", property="other"
        )
        self.assertEqual(result, "retrying")

    def test_property_undefined(self) -> None:
        result = self.bound_template.render(
            status="fatal", key="RequestStatus", property="other"
        )
        self.assertEqual(result, "")


class GetFirstCcdaSectionsByTemplateIdTest(TestCase, FilterTest):
    template = """{{ msg | get_first_ccda_sections_by_template_id: template_ids }}"""

    msg: dict = {
        "ClinicalDocument": {
            "component": {
                "structuredBody": {
                    "component": [
                        {"section": {"templateId": [{"root": "2.2"}, {"root": "2.2.1"}]}},
                        {"section": {"templateId": [{"root": "2.6"}]}},
                        {"section": {"templateId": [{"root": "2.5.1"}]}},
                    ]
                }
            }
        }
    }

    def setUp(self) -> None:
        self.setup_template()

    def test_invalid_argument(self) -> None:
        with raises(FilterArgumentError):
            self.bound_template.render(msg="Not a dict", template_ids="2.6")

    def test_undefined(self) -> None:
        result = self.bound_template.render()
        self.assertEqual(result, "{}")

    def test_undefined_object(self) -> None:
        result = self.bound_template.render(template_ids="2.6")
        self.assertEqual(result, "{}")

    def test_undefined_parameter(self) -> None:
        result = self.bound_template.render(msg=self.msg)
        self.assertEqual(result, "{}")

    def test_empty(self) -> None:
        result = self.bound_template.render(msg={}, template_ids="2.6")
        self.assertEqual(result, "{}")

    def test_not_found(self) -> None:
        result = self.bound_template.render(msg=self.msg, template_ids="2.5")
        self.assertEqual(result, "{}")

    def test_found(self) -> None:
        result = self.bound_template.render(msg=self.msg, template_ids="2.6")
        self.assertEqual(
            result,
            "{'2_6': {'templateId': [{'root': '2.6'}]}}",
        )

    def test_multiple_found(self) -> None:
        result = self.bound_template.render(msg=self.msg, template_ids="2.6|2.2.1|2.2")
        self.assertEqual(
            result,
            " ".join(
                (
                    "{'2_6': {'templateId': [{'root': '2.6'}]}, '2_2_1':",
                    "{'templateId': [{'root': '2.2'}, {'root': '2.2.1'}]},",
                    "'2_2': {'templateId': [{'root': '2.2'}, {'root': '2.2.1'}]}}",
                )
            ),
        )


class GetCcdaSectionByTemplateIdTest(TestCase, FilterTest):
    template = """{{ msg | get_ccda_section_by_template_id: id, id2, id3 }}"""

    msg: dict = {
        "ClinicalDocument": {
            "component": {
                "structuredBody": {
                    "component": [
                        {"section": {"templateId": [{"root": "2.2"}, {"root": "2.2.1"}]}},
                        {"section": {"templateId": [{"root": "2.6"}]}},
                        {"section": {"templateId": [{"root": "2.5.1"}]}},
                    ]
                }
            }
        }
    }

    def setUp(self) -> None:
        self.setup_template()

    def test_invalid_argument(self) -> None:
        with raises(FilterArgumentError):
            self.bound_template.render(msg="Not a dict", id="2.6")

    def test_undefined(self) -> None:
        result = self.bound_template.render()
        self.assertEqual(result, "{}")

    def test_undefined_object(self) -> None:
        result = self.bound_template.render(id="2.6")
        self.assertEqual(result, "{}")

    def test_undefined_parameter(self) -> None:
        result = self.bound_template.render(msg=self.msg)
        self.assertEqual(result, "{}")

    def test_empty(self) -> None:
        result = self.bound_template.render(msg={}, id="2.6")
        self.assertEqual(result, "{}")

    def test_not_found(self) -> None:
        result = self.bound_template.render(msg=self.msg, id="2.5")
        self.assertEqual(result, "{}")

    def test_found(self) -> None:
        result = self.bound_template.render(msg=self.msg, id="2.6")
        self.assertEqual(
            result,
            "{'templateId': [{'root': '2.6'}]}",
        )

    def test_found_multiple_ids(self) -> None:
        result = self.bound_template.render(msg=self.msg, id="2.5", id2="2.6", id3="2.7")
        self.assertEqual(
            result,
            "{'templateId': [{'root': '2.6'}]}",
        )

    def test_found_flatten_ids(self) -> None:
        result = self.bound_template.render(
            msg=self.msg, id=["2.5"], id2=["2.7"], id3=["2.6"]
        )
        self.assertEqual(
            result,
            "{'templateId': [{'root': '2.6'}]}",
        )


class BatchRenderTest(TestCase, FilterTest):
    template = """{{ batch | batch_render: template, 'data' }}"""
    inner_template = """{{ data }},"""

    def setUp(self) -> None:
        self.setup_template(loader=DictLoader({"__template__": self.inner_template}))

    def test_undefined(self) -> None:
        result = self.bound_template.render()
        self.assertEqual(result, "")

    def test_empty(self) -> None:
        result = self.bound_template.render(batch=[])
        self.assertEqual(result, "")

    def test_str_to_list(self) -> None:
        result = self.bound_template.render(batch="one", template="__template__")
        self.assertEqual(result, "one,")

    def test_batch(self) -> None:
        result = self.bound_template.render(
            batch=["one", "two", "three"], template="__template__"
        )
        self.assertEqual(result, "one,two,three,")

    def test_template_not_found(self) -> None:
        with raises(TemplateNotFound):
            self.bound_template.render(batch=["one"], template="undefined")

    def test_output_limit_reached(self) -> None:
        Environment.output_stream_limit = 3
        with raises(OutputStreamLimitError):
            self.bound_template.render(batch=["one"], template="__template__")

    def test_output_limit_not_reached(self) -> None:
        Environment.output_stream_limit = 4
        result = self.bound_template.render(batch=["one"], template="__template__")
        self.assertEqual(result, "one,")
