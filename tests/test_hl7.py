from unittest import TestCase

from pytest import raises

from fhir_converter.hl7 import (
    FhirDtmPrecision,
    Hl7DtmPrecision,
    get_ccda_component3,
    get_component3_section_templateId,
    get_fhir_entry_key,
    get_template_id_key,
    hl7_to_fhir_dtm,
    is_template_id,
    parse_fhir,
    parse_hl7_dtm,
)


class Hl7DtmPrecisionTest(TestCase):
    def test_fhir_precision_year(self) -> None:
        self.assertEqual(Hl7DtmPrecision.YEAR.fhir_precision, FhirDtmPrecision.YEAR)

    def test_fhir_precision_month(self) -> None:
        self.assertEqual(Hl7DtmPrecision.MONTH.fhir_precision, FhirDtmPrecision.MONTH)

    def test_fhir_precision_day(self) -> None:
        self.assertEqual(Hl7DtmPrecision.DAY.fhir_precision, FhirDtmPrecision.DAY)

    def test_fhir_precision_hour(self) -> None:
        self.assertEqual(Hl7DtmPrecision.HOUR.fhir_precision, FhirDtmPrecision.HOUR)

    def test_fhir_precision_min(self) -> None:
        self.assertEqual(Hl7DtmPrecision.MIN.fhir_precision, FhirDtmPrecision.MIN)

    def test_fhir_precision_sec(self) -> None:
        self.assertEqual(Hl7DtmPrecision.SEC.fhir_precision, FhirDtmPrecision.SEC)

    def test_fhir_precision_millis(self) -> None:
        self.assertEqual(Hl7DtmPrecision.MILLIS.fhir_precision, FhirDtmPrecision.MILLIS)

    def test_from_dtm_year(self) -> None:
        self.assertEqual(Hl7DtmPrecision.YEAR, Hl7DtmPrecision.from_dtm("2024"))

    def test_from_dtm_month(self) -> None:
        self.assertEqual(Hl7DtmPrecision.MONTH, Hl7DtmPrecision.from_dtm("202401"))

    def test_from_dtm_day(self) -> None:
        self.assertEqual(Hl7DtmPrecision.DAY, Hl7DtmPrecision.from_dtm("20240110"))

    def test_from_dtm_hour(self) -> None:
        self.assertEqual(Hl7DtmPrecision.HOUR, Hl7DtmPrecision.from_dtm("2024011006"))

    def test_from_dtm_min(self) -> None:
        self.assertEqual(Hl7DtmPrecision.MIN, Hl7DtmPrecision.from_dtm("202401100635"))

    def test_from_dtm_sec(self) -> None:
        self.assertEqual(Hl7DtmPrecision.SEC, Hl7DtmPrecision.from_dtm("20240110063557"))

    def test_from_dtm_millis(self) -> None:
        self.assertEqual(
            Hl7DtmPrecision.MILLIS, Hl7DtmPrecision.from_dtm("20240110063557.920")
        )


class FhirDtmPrecisionTest(TestCase):
    def test_timespec_year(self) -> None:
        self.assertEqual("seconds", FhirDtmPrecision.YEAR.timespec)

    def test_timespec_month(self) -> None:
        self.assertEqual("seconds", FhirDtmPrecision.MONTH.timespec)

    def test_timespec_day(self) -> None:
        self.assertEqual("seconds", FhirDtmPrecision.DAY.timespec)

    def test_timespec_hour(self) -> None:
        self.assertEqual("seconds", FhirDtmPrecision.HOUR.timespec)

    def test_timespec_min(self) -> None:
        self.assertEqual("seconds", FhirDtmPrecision.MIN.timespec)

    def test_timespec_sec(self) -> None:
        self.assertEqual("seconds", FhirDtmPrecision.SEC.timespec)

    def test_timespec_millis(self) -> None:
        self.assertEqual("milliseconds", FhirDtmPrecision.MILLIS.timespec)


class ParseHl7DtmTest(TestCase):
    def test_empty_str(self) -> None:
        with raises(ValueError):
            parse_hl7_dtm("")

    def test_blank_str(self) -> None:
        with raises(ValueError):
            parse_hl7_dtm(" ")

    def test_less_than_year(self) -> None:
        with raises(ValueError):
            parse_hl7_dtm("200")

    def test_less_than_month(self) -> None:
        with raises(ValueError):
            parse_hl7_dtm("20041")

    def test_less_than_day(self) -> None:
        with raises(ValueError):
            parse_hl7_dtm("2004101")

    def test_less_than_hour(self) -> None:
        with raises(ValueError):
            parse_hl7_dtm("200410121")

    def test_less_than_min(self) -> None:
        with raises(ValueError):
            parse_hl7_dtm("20041012101")

    def test_less_than_sec(self) -> None:
        with raises(ValueError):
            parse_hl7_dtm("2004101210154")

    def test_less_than_millis(self) -> None:
        with raises(ValueError):
            parse_hl7_dtm("20041012101545.")

    def test_strip_whitespace(self) -> None:
        result = parse_hl7_dtm("   2024    ")
        self.assertEqual(result.precision, Hl7DtmPrecision.YEAR)
        self.assertEqual("2024-01-01T00:00:00", result.dt.isoformat())

    def test_year(self) -> None:
        result = parse_hl7_dtm("2024")
        self.assertEqual(result.precision, Hl7DtmPrecision.YEAR)
        self.assertEqual("2024-01-01T00:00:00", result.dt.isoformat())

    def test_month(self) -> None:
        result = parse_hl7_dtm("202402")
        self.assertEqual(result.precision, Hl7DtmPrecision.MONTH)
        self.assertEqual("2024-02-01T00:00:00", result.dt.isoformat())

    def test_day(self) -> None:
        result = parse_hl7_dtm("20240210")
        self.assertEqual(result.precision, Hl7DtmPrecision.DAY)
        self.assertEqual("2024-02-10T00:00:00", result.dt.isoformat())

    def test_hour(self) -> None:
        result = parse_hl7_dtm("2024021006")
        self.assertEqual(result.precision, Hl7DtmPrecision.HOUR)
        self.assertEqual("2024-02-10T06:00:00", result.dt.isoformat())

    def test_min(self) -> None:
        result = parse_hl7_dtm("202402100635")
        self.assertEqual(result.precision, Hl7DtmPrecision.MIN)
        self.assertEqual("2024-02-10T06:35:00", result.dt.isoformat())

    def test_sec(self) -> None:
        result = parse_hl7_dtm("20240210063557")
        self.assertEqual(result.precision, Hl7DtmPrecision.SEC)
        self.assertEqual("2024-02-10T06:35:57", result.dt.isoformat())

    def test_tenth_second(self) -> None:
        result = parse_hl7_dtm("20240210063557.1")
        self.assertEqual(result.precision, Hl7DtmPrecision.MILLIS)
        self.assertEqual(
            "2024-02-10T06:35:57.100", result.dt.isoformat(timespec="milliseconds")
        )

    def test_hundredth_second(self) -> None:
        result = parse_hl7_dtm("20240210063557.01")
        self.assertEqual(result.precision, Hl7DtmPrecision.MILLIS)
        self.assertEqual(
            "2024-02-10T06:35:57.010", result.dt.isoformat(timespec="milliseconds")
        )

    def test_millisecond(self) -> None:
        result = parse_hl7_dtm("20240210063557.001")
        self.assertEqual(result.precision, Hl7DtmPrecision.MILLIS)
        self.assertEqual(
            "2024-02-10T06:35:57.001", result.dt.isoformat(timespec="milliseconds")
        )

    def test_tenth_millisecond(self) -> None:
        result = parse_hl7_dtm("20240210063557.0001")
        self.assertEqual(result.precision, Hl7DtmPrecision.MILLIS)
        self.assertEqual(
            "2024-02-10T06:35:57.000100", result.dt.isoformat(timespec="microseconds")
        )

    def test_microsecond(self) -> None:
        result = parse_hl7_dtm("20240210063557.123456")
        self.assertEqual(result.precision, Hl7DtmPrecision.MILLIS)
        self.assertEqual(
            "2024-02-10T06:35:57.123456", result.dt.isoformat(timespec="microseconds")
        )

    def test_tz_utc(self) -> None:
        result = parse_hl7_dtm("20240210063557.920+0000")
        self.assertEqual(result.precision, Hl7DtmPrecision.MILLIS)
        self.assertEqual(
            "2024-02-10T06:35:57.920+00:00", result.dt.isoformat(timespec="milliseconds")
        )

    def test_tz_plus(self) -> None:
        result = parse_hl7_dtm("20240210063557.920+0100")
        self.assertEqual(result.precision, Hl7DtmPrecision.MILLIS)
        self.assertEqual(
            "2024-02-10T06:35:57.920+01:00", result.dt.isoformat(timespec="milliseconds")
        )

    def test_tz_minus(self) -> None:
        result = parse_hl7_dtm("20240210063557.920-0100")
        self.assertEqual(result.precision, Hl7DtmPrecision.MILLIS)
        self.assertEqual(
            "2024-02-10T06:35:57.920-01:00", result.dt.isoformat(timespec="milliseconds")
        )

    def test_hour_tz(self) -> None:
        result = parse_hl7_dtm("2024021006+0400")
        self.assertEqual(result.precision, Hl7DtmPrecision.HOUR)
        self.assertEqual("2024-02-10T06:00:00+04:00", result.dt.isoformat())

    def test_min_tz(self) -> None:
        result = parse_hl7_dtm("202402100635+0400")
        self.assertEqual(result.precision, Hl7DtmPrecision.MIN)
        self.assertEqual("2024-02-10T06:35:00+04:00", result.dt.isoformat())

    # Edge case tests for invalid dates
    def test_invalid_day_too_high(self) -> None:
        """Test that day 55 is invalid"""
        with raises(ValueError):
            parse_hl7_dtm("20240555")

    def test_invalid_day_32(self) -> None:
        """Test that day 32 is invalid for any month"""
        with raises(ValueError):
            parse_hl7_dtm("20240132")

    def test_invalid_month_00(self) -> None:
        """Test that month 00 is invalid"""
        with raises(ValueError):
            parse_hl7_dtm("20240010")

    def test_invalid_month_13(self) -> None:
        """Test that month 13 is invalid"""
        with raises(ValueError):
            parse_hl7_dtm("20241310")

    def test_february_30_non_leap_year(self) -> None:
        """Test that Feb 30 is invalid in non-leap year"""
        with raises(ValueError):
            parse_hl7_dtm("20230230")

    def test_february_29_non_leap_year(self) -> None:
        """Test that Feb 29 is invalid in non-leap year"""
        with raises(ValueError):
            parse_hl7_dtm("20230229")

    def test_february_29_leap_year(self) -> None:
        """Test that Feb 29 is valid in leap year"""
        result = parse_hl7_dtm("20240229")
        self.assertEqual(result.precision, Hl7DtmPrecision.DAY)
        self.assertEqual("2024-02-29T00:00:00", result.dt.isoformat())

    def test_february_28_non_leap_year(self) -> None:
        """Test that Feb 28 is valid in non-leap year"""
        result = parse_hl7_dtm("20230228")
        self.assertEqual(result.precision, Hl7DtmPrecision.DAY)
        self.assertEqual("2023-02-28T00:00:00", result.dt.isoformat())

    def test_april_31(self) -> None:
        """Test that April 31 is invalid (April has 30 days)"""
        with raises(ValueError):
            parse_hl7_dtm("20240431")

    def test_june_31(self) -> None:
        """Test that June 31 is invalid (June has 30 days)"""
        with raises(ValueError):
            parse_hl7_dtm("20240631")

    def test_september_31(self) -> None:
        """Test that September 31 is invalid (September has 30 days)"""
        with raises(ValueError):
            parse_hl7_dtm("20240931")

    def test_november_31(self) -> None:
        """Test that November 31 is invalid (November has 30 days)"""
        with raises(ValueError):
            parse_hl7_dtm("20241131")

    def test_january_31(self) -> None:
        """Test that January 31 is valid (January has 31 days)"""
        result = parse_hl7_dtm("20240131")
        self.assertEqual(result.precision, Hl7DtmPrecision.DAY)
        self.assertEqual("2024-01-31T00:00:00", result.dt.isoformat())

    def test_march_31(self) -> None:
        """Test that March 31 is valid (March has 31 days)"""
        result = parse_hl7_dtm("20240331")
        self.assertEqual(result.precision, Hl7DtmPrecision.DAY)
        self.assertEqual("2024-03-31T00:00:00", result.dt.isoformat())

    def test_may_31(self) -> None:
        """Test that May 31 is valid (May has 31 days)"""
        result = parse_hl7_dtm("20240531")
        self.assertEqual(result.precision, Hl7DtmPrecision.DAY)
        self.assertEqual("2024-05-31T00:00:00", result.dt.isoformat())

    def test_july_31(self) -> None:
        """Test that July 31 is valid (July has 31 days)"""
        result = parse_hl7_dtm("20240731")
        self.assertEqual(result.precision, Hl7DtmPrecision.DAY)
        self.assertEqual("2024-07-31T00:00:00", result.dt.isoformat())

    def test_august_31(self) -> None:
        """Test that August 31 is valid (August has 31 days)"""
        result = parse_hl7_dtm("20240831")
        self.assertEqual(result.precision, Hl7DtmPrecision.DAY)
        self.assertEqual("2024-08-31T00:00:00", result.dt.isoformat())

    def test_october_31(self) -> None:
        """Test that October 31 is valid (October has 31 days)"""
        result = parse_hl7_dtm("20241031")
        self.assertEqual(result.precision, Hl7DtmPrecision.DAY)
        self.assertEqual("2024-10-31T00:00:00", result.dt.isoformat())

    def test_december_31(self) -> None:
        """Test that December 31 is valid (December has 31 days)"""
        result = parse_hl7_dtm("20241231")
        self.assertEqual(result.precision, Hl7DtmPrecision.DAY)
        self.assertEqual("2024-12-31T00:00:00", result.dt.isoformat())

    def test_invalid_hour_24(self) -> None:
        """Test that hour 24 is invalid"""
        with raises(ValueError):
            parse_hl7_dtm("2024010124")

    def test_invalid_hour_25(self) -> None:
        """Test that hour 25 is invalid"""
        with raises(ValueError):
            parse_hl7_dtm("2024010125")

    def test_invalid_minute_60(self) -> None:
        """Test that minute 60 is invalid"""
        with raises(ValueError):
            parse_hl7_dtm("202401010060")

    def test_invalid_second_60(self) -> None:
        """Test that second 60 is invalid"""
        with raises(ValueError):
            parse_hl7_dtm("20240101000060")

    def test_valid_hour_23(self) -> None:
        """Test that hour 23 is valid"""
        result = parse_hl7_dtm("2024010123")
        self.assertEqual(result.precision, Hl7DtmPrecision.HOUR)
        self.assertEqual("2024-01-01T23:00:00", result.dt.isoformat())

    def test_valid_minute_59(self) -> None:
        """Test that minute 59 is valid"""
        result = parse_hl7_dtm("202401010059")
        self.assertEqual(result.precision, Hl7DtmPrecision.MIN)
        self.assertEqual("2024-01-01T00:59:00", result.dt.isoformat())

    def test_valid_second_59(self) -> None:
        """Test that second 59 is valid"""
        result = parse_hl7_dtm("20240101000059")
        self.assertEqual(result.precision, Hl7DtmPrecision.SEC)
        self.assertEqual("2024-01-01T00:00:59", result.dt.isoformat())

    def test_century_year_2000_leap(self) -> None:
        """Test that year 2000 is a leap year (divisible by 400)"""
        result = parse_hl7_dtm("20000229")
        self.assertEqual(result.precision, Hl7DtmPrecision.DAY)
        self.assertEqual("2000-02-29T00:00:00", result.dt.isoformat())

    def test_century_year_1900_not_leap(self) -> None:
        """Test that year 1900 is not a leap year (divisible by 100 but not 400)"""
        with raises(ValueError):
            parse_hl7_dtm("19000229")

    def test_invalid_date_with_full_timestamp(self) -> None:
        """Test invalid date with complete timestamp (like the Nadine.hl7 example)"""
        with raises(ValueError):
            parse_hl7_dtm("202405551151000")


class Hl7ToFhirDtmTest(TestCase):
    def test_year(self) -> None:
        self.assertEqual("2024", hl7_to_fhir_dtm("2024"))

    def test_month(self) -> None:
        self.assertEqual("2024-02", hl7_to_fhir_dtm("202402"))

    def test_day(self) -> None:
        self.assertEqual("2024-02-10", hl7_to_fhir_dtm("20240210"))

    def test_hour(self) -> None:
        self.assertEqual("2024-02-10T06:00:00+04:00", hl7_to_fhir_dtm("2024021006+0400"))

    def test_min(self) -> None:
        self.assertEqual(
            "2024-02-10T06:35:00+04:00", hl7_to_fhir_dtm("202402100635+0400")
        )

    def test_sec(self) -> None:
        self.assertEqual(
            "2024-02-10T06:35:57+04:00", hl7_to_fhir_dtm("20240210063557+0400")
        )

    def test_local_hour(self) -> None:
        self.assertEqual("2024-02-10T06:00:00Z", hl7_to_fhir_dtm("2024021006"))

    def test_local_min(self) -> None:
        self.assertEqual("2024-02-10T06:35:00Z", hl7_to_fhir_dtm("202402100635"))

    def test_local_sec(self) -> None:
        self.assertEqual("2024-02-10T06:35:57Z", hl7_to_fhir_dtm("20240210063557"))

    def test_tz_utc(self) -> None:
        self.assertEqual(
            "2024-02-10T06:35:57.920Z", hl7_to_fhir_dtm("20240210063557.920+0000")
        )
        self.assertEqual(
            "2024-02-10T06:35:57.920Z", hl7_to_fhir_dtm("20240210063557.920-0000")
        )

    def test_tz_offset(self) -> None:
        self.assertEqual(
            "2024-02-10T06:35:57.920+01:00", hl7_to_fhir_dtm("20240210063557.920+0100")
        )
        self.assertEqual(
            "2024-02-10T06:35:57.920-01:00", hl7_to_fhir_dtm("20240210063557.920-0100")
        )

    def test_precision_greater(self) -> None:
        res = hl7_to_fhir_dtm("20240210063557.920-0100", precision=Hl7DtmPrecision.DAY)
        self.assertEqual("2024-02-10", res)

    def test_precision_less(self) -> None:
        res = hl7_to_fhir_dtm("202402", precision=Hl7DtmPrecision.DAY)
        self.assertEqual("2024-02", res)

    def test_precision_equal(self) -> None:
        res = hl7_to_fhir_dtm("20240210", precision=Hl7DtmPrecision.DAY)
        self.assertEqual("2024-02-10", res)


class ParseFhirTest(TestCase):
    def test_empty(self) -> None:
        self.assertEqual({}, parse_fhir("{}"))

    def test_empty_entry(self) -> None:
        self.assertEqual(
            {"resourceType": "Bundle", "type": "batch"},
            parse_fhir('{"resourceType": "Bundle", "type": "batch", "entry": []}'),
        )

    def test_trailing_commas_and_duplicate_keys(self) -> None:
        self.assertEqual(
            {
                "resourceType": "Bundle",
                "type": "batch",
                "entry": [
                    {
                        "resource": {
                            "resourceType": "Patient",
                            "id": "patient-1",
                            "name": {"family": "Doe", "given": ["John"]},
                        }
                    }
                ],
            },
            parse_fhir(
                """
                {
                    "resourceType": "Bundle",
                    "type": "batch",
                    "entry": [
                        {
                            "resource": {
                                "resourceType": "Patient",
                                "id": "patient-1",
                                "name": {"family": "Doe"},
                                "name": {"given": ["John"]},
                            },
                        },
                    ],
                }
                """
            ),
        )

    def test_empty_fields_are_skipped_by_fast_parser(self) -> None:
        self.assertEqual(
            {
                "resourceType": "Patient",
                "id": "patient-1",
                "active": False,
            },
            parse_fhir(
                """
                {
                    "resourceType": "Patient",
                    "id": "patient-1",
                    "name": [],
                    "gender": "",
                    "active": false,
                }
                """
            ),
        )

    def test_json5_fallback(self) -> None:
        self.assertEqual(
            {"resourceType": "Bundle", "type": "batch"},
            parse_fhir("{'resourceType':'Bundle','type':'batch','entry':[],}"),
        )

    def test(self) -> None:
        fhir_json = {
            "resourceType": "Bundle",
            "type": "batch",
            "entry": [
                {
                    "fullUrl": "urn:uuid:8c92075f-ae59-6be3-037f",
                    "resource": {
                        "resourceType": "Observation",
                        "id": "8c92075f-ae59-6be3-037f-e2d87e29185a",
                        "meta": {
                            "profile": [
                                "http://hl7.org/fhir/us/core/StructureDefinition/us-core-observationresults"
                            ]
                        },
                        "identifier": [
                            {
                                "system": "urn:ietf:rfc:3986",
                                "value": "urn:uuid:c03e5445-af1b-4911-a419-e2782f21448c",
                            }
                        ],
                        "effectiveDateTime": "2014-10-01T10:30:26-05:00",
                        "bodySite": {
                            "coding": [
                                {
                                    "code": "302509004",
                                    "display": "Entire Heart",
                                    "system": "http://snomed.info/sct",
                                }
                            ]
                        },
                    },
                },
            ],
        }
        fhir_str = "".join(
            [
                '{"resourceType":"Bundle","type":"batch","entry":[',
                '{"fullUrl":"urn:uuid:8c92075f-ae59-6be3-037f",',
                '"resource":{"resourceType":"Observation",',
                '"id":"8c92075f-ae59-6be3-037f-e2d87e29185a","meta":{"profile":',
                '["http://hl7.org/fhir/us/core/StructureDefinition/us-core-observationresults"]},',
                '"identifier":[{"system":"urn:ietf:rfc:3986","value":"urn:uuid:c03e5445-af1b-4911-a419-e2782f21448c"}]',
                '}},{"fullUrl":"urn:uuid:8c92075f-ae59-6be3-037f","resource":{"resourceType":',
                '"Observation","id":"8c92075f-ae59-6be3-037f-e2d87e29185a","effectiveDateTime":',
                '"2014-10-01T10:30:26-05:00","bodySite":{"coding":[{"code":"302509004","display":',
                '"Entire Heart","system":"http://snomed.info/sct"}]}}}]}',
            ]
        )
        self.assertEqual(fhir_json, parse_fhir(fhir_str))


class GetFhirEntryKeyTest(TestCase):
    def test_empty(self) -> None:
        self.assertEqual("", get_fhir_entry_key({}))

    def test_empty_resource(self) -> None:
        self.assertEqual("", get_fhir_entry_key({"resource": {}}))

    def test_basic_fields(self) -> None:
        res = get_fhir_entry_key({"resource": {"resourceType": "observation", "id": "1"}})
        self.assertEqual("observation_1", res)

    def test_empty_type(self) -> None:
        res = get_fhir_entry_key({"resource": {"resourceType": "", "id": "1"}})
        self.assertEqual("1", res)

        res = get_fhir_entry_key({"resource": {"id": "1"}})
        self.assertEqual("1", res)

    def test_empty_id(self) -> None:
        res = get_fhir_entry_key({"resource": {"resourceType": "observation", "id": ""}})
        self.assertEqual("observation", res)

        res = get_fhir_entry_key({"resource": {"resourceType": "observation"}})
        self.assertEqual("observation", res)

    def test_empty_meta(self) -> None:
        res = get_fhir_entry_key(
            {
                "resource": {
                    "resourceType": "observation",
                    "id": "1",
                    "meta": {},
                }
            }
        )
        self.assertEqual("observation_1", res)

    def test_all_fields(self) -> None:
        res = get_fhir_entry_key(
            {
                "resource": {
                    "resourceType": "observation",
                    "id": "1",
                    "meta": {"versionId": "0"},
                }
            }
        )
        self.assertEqual("observation_0_1", res)


class GetCcdaComponent3Test(TestCase):
    def test_empty(self) -> None:
        self.assertEqual([], get_ccda_component3({}))

    def test_empty_document(self) -> None:
        self.assertEqual([], get_ccda_component3({"ClinicalDocument": {}}))

    def test_empty_component2(self) -> None:
        self.assertEqual([], get_ccda_component3({"ClinicalDocument": {"component": {}}}))

    def test_empty_structuredbody(self) -> None:
        res = get_ccda_component3(
            {"ClinicalDocument": {"component": {"structuredBody": {}}}}
        )
        self.assertEqual([], res)

    def test_empty_component3(self) -> None:
        res = get_ccda_component3(
            {"ClinicalDocument": {"component": {"structuredBody": {"component": {}}}}}
        )
        self.assertEqual([], res)

        res = get_ccda_component3(
            {"ClinicalDocument": {"component": {"structuredBody": {"component": []}}}}
        )
        self.assertEqual([], res)

    def test_component3(self) -> None:
        res = get_ccda_component3(
            {
                "ClinicalDocument": {
                    "component": {
                        "structuredBody": {"component": {"templateId": "1.2.3"}}
                    }
                }
            }
        )
        self.assertEqual([{"templateId": "1.2.3"}], res)

    def test_many_component3(self) -> None:
        res = get_ccda_component3(
            {
                "ClinicalDocument": {
                    "component": {
                        "structuredBody": {
                            "component": [
                                {"templateId": "1.2.3"},
                                {"templateId": "3.2.1"},
                            ]
                        }
                    }
                }
            }
        )
        self.assertEqual([{"templateId": "1.2.3"}, {"templateId": "3.2.1"}], res)


class GetComponet3SectionTemplateIdTest(TestCase):
    def test_empty_component(self) -> None:
        self.assertEqual([], get_component3_section_templateId({}))

    def test_empty_section(self) -> None:
        self.assertEqual([], get_component3_section_templateId({"section": {}}))

    def test_empty_templateId(self) -> None:
        res = get_component3_section_templateId({"section": {"templateId": ""}})
        self.assertEqual([], res)

    def test_templateId(self) -> None:
        res = get_component3_section_templateId({"section": {"templateId": "1.2.3"}})
        self.assertEqual(["1.2.3"], res)

    def test_templateId_list(self) -> None:
        res = get_component3_section_templateId(
            {"section": {"templateId": ["1.2.3", "23.1"]}}
        )
        self.assertEqual(["1.2.3", "23.1"], res)


class GetTemplateIdKeyTest(TestCase):
    def test_id_empty(self) -> None:
        self.assertEqual("", get_template_id_key(""))

    def test_numbers_letters(self) -> None:
        self.assertEqual("043be7ae", get_template_id_key("043be7ae"))

    def test_guid(self) -> None:
        self.assertEqual(
            "ca8505ac_b18e_11ee_a506_0242ac120002",
            get_template_id_key("ca8505ac-b18e-11ee-a506-0242ac120002"),
        )

    def test_id(self) -> None:
        self.assertEqual(
            "2_16_840_1_113883_10_20_5_4",
            get_template_id_key("2.16.840.1.113883.10.20.5.4"),
        )


class IsTemplateIdTest(TestCase):
    def test_id_empty(self) -> None:
        self.assertFalse(is_template_id({}, "1.2.3"))

    def test_id_empty_root(self) -> None:
        self.assertFalse(is_template_id({"root": ""}, "1.2.3"))

    def test_equal(self) -> None:
        self.assertTrue(is_template_id({"root": "1.2.3"}, "1.2.3"))

    def test_not_equal(self) -> None:
        self.assertFalse(is_template_id({"root": "3.2.1"}, "1.2.3"))

    def test_strip_whitespace(self) -> None:
        self.assertTrue(is_template_id({"root": " 1.2.3 "}, "1.2.3"))
