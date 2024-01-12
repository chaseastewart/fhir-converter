from __future__ import annotations

from collections.abc import Mapping, MutableMapping, Sequence
from datetime import datetime, timedelta, timezone
from enum import IntEnum
from math import copysign
from re import compile as re_compile
from re import sub as re_sub
from typing import NamedTuple, Optional

from fhir_converter.utils import merge_mappings, parse_json, to_list

DTM_REGEX = re_compile(r"(\d+(?:\.\d*)?)(?:([+-]\d{2})(\d{2}))?")


class FhirDtmPrecision(IntEnum):
    YEAR = 4
    MONTH = 7
    DAY = 10
    HOUR = 13
    MIN = 16
    SEC = 19
    MILLIS = 21

    @property
    def timespec(self) -> str:
        return "milliseconds" if self > FhirDtmPrecision.SEC else "seconds"


class Hl7DtmPrecision(IntEnum):
    YEAR = 4
    MONTH = 6
    DAY = 8
    HOUR = 10
    MIN = 12
    SEC = 14
    MILLIS = 16

    @property
    def fhir_precision(self) -> FhirDtmPrecision:
        return FhirDtmPrecision[self.name]

    @staticmethod
    def from_dtm(dtm: str) -> Hl7DtmPrecision:
        _len = len(dtm)
        if _len >= Hl7DtmPrecision.MILLIS:
            return Hl7DtmPrecision.MILLIS
        elif _len == Hl7DtmPrecision.SEC:
            return Hl7DtmPrecision.SEC
        elif _len == Hl7DtmPrecision.MIN:
            return Hl7DtmPrecision.MIN
        elif _len == Hl7DtmPrecision.HOUR:
            return Hl7DtmPrecision.HOUR
        elif _len == Hl7DtmPrecision.DAY:
            return Hl7DtmPrecision.DAY
        elif _len == Hl7DtmPrecision.MONTH:
            return Hl7DtmPrecision.MONTH
        elif _len == Hl7DtmPrecision.YEAR:
            return Hl7DtmPrecision.YEAR
        raise ValueError("Malformed HL7 datetime {0}".format(dtm))


class Hl7ParsedDtm(NamedTuple):
    precision: Hl7DtmPrecision
    dt: datetime


def parse_hl7_dtm(hl7_input: str) -> Hl7ParsedDtm:
    dt_match = DTM_REGEX.match(hl7_input.strip())
    if not dt_match:
        raise ValueError("Malformed HL7 datetime {0}".format(hl7_input))

    dtm = dt_match.group(1)
    tzh = dt_match.group(2)
    tzm = dt_match.group(3)
    if tzh and tzm:
        minutes = int(tzh) * 60.0
        minutes += copysign(int(tzm), minutes)
        tzinfo = timezone(timedelta(minutes=minutes))
    else:
        tzinfo = None

    precision = Hl7DtmPrecision.from_dtm(dtm)
    year = int(dtm[: Hl7DtmPrecision.YEAR])

    if precision >= Hl7DtmPrecision.MONTH:
        month = int(dtm[Hl7DtmPrecision.YEAR : Hl7DtmPrecision.MONTH])
    else:
        month = 1

    if precision >= Hl7DtmPrecision.DAY:
        day = int(dtm[Hl7DtmPrecision.MONTH : Hl7DtmPrecision.DAY])
    else:
        day = 1

    if precision >= Hl7DtmPrecision.HOUR:
        hour = int(dtm[Hl7DtmPrecision.DAY : Hl7DtmPrecision.HOUR])
    else:
        hour = 0

    if precision >= Hl7DtmPrecision.MIN:
        minute = int(dtm[Hl7DtmPrecision.HOUR : Hl7DtmPrecision.MIN])
    else:
        minute = 0

    if precision >= Hl7DtmPrecision.SEC:
        delta = timedelta(seconds=float(dtm[Hl7DtmPrecision.MIN :]))
        second, microsecond = delta.seconds, delta.microseconds
    else:
        second = 0
        microsecond = 0

    return Hl7ParsedDtm(
        precision,
        dt=datetime(year, month, day, hour, minute, second, microsecond, tzinfo=tzinfo),
    )


def hl7_to_fhir_dtm(input: str, precision: Optional[Hl7DtmPrecision] = None) -> str:
    parsed_dtm = parse_hl7_dtm(input)
    if precision is None or precision > parsed_dtm.precision:
        precision = parsed_dtm.precision

    return to_fhir_dtm(
        dt=parsed_dtm.dt,
        precision=precision.fhir_precision,
    )


def to_fhir_dtm(dt: datetime, precision: Optional[FhirDtmPrecision] = None) -> str:
    if precision is None:
        precision = FhirDtmPrecision.MILLIS

    iso_dtm = dt.isoformat(timespec=precision.timespec)
    off = dt.utcoffset()
    if off is not None and int(off.total_seconds()) == 0:
        iso_dtm = iso_dtm[:-6] + "Z"

    if precision > FhirDtmPrecision.DAY:
        return iso_dtm
    elif precision > FhirDtmPrecision.MONTH:
        return iso_dtm[: FhirDtmPrecision.DAY]
    elif precision > FhirDtmPrecision.YEAR:
        return iso_dtm[: FhirDtmPrecision.MONTH]
    return iso_dtm[: FhirDtmPrecision.YEAR]


def parse_fhir(json_input: str) -> MutableMapping:
    json_data = parse_json(json_input)
    if json_data:
        entries = to_list(json_data.get("entry", []))
        if len(entries) > 1:
            unique_entrys: dict[str, dict] = {}
            for entry in entries:
                key = get_fhir_entry_key(entry)
                if key in unique_entrys:
                    merge_mappings(unique_entrys[key], entry)
                else:
                    unique_entrys[key] = entry
            json_data["entry"] = list(unique_entrys.values())
    return json_data


def get_fhir_entry_key(entry: Mapping) -> str:
    resource = entry.get("resource", {})
    return "_".join(
        filter(
            None,
            (
                resource.get("resourceType", ""),
                resource.get("meta", {}).get("versionId", ""),
                resource.get("id", ""),
            ),
        )
    )


def get_ccda_section(
    ccda: Mapping, search_template_ids: Sequence[str]
) -> Optional[Mapping]:
    """get_ccda_section Gets the POCD_MT000040.Section
    from the ClinicalDocument that matches one of the templateIds

    See https://github.com/HL7/CDA-core-2.0/tree/master/schema

    Arguments:
        ccda (Mapping): The ccda document as a map
        search_template_ids (Sequence): The templateIds

    Returns:
        The section from the document if present
    """
    if search_template_ids:
        for component in get_ccda_component3(ccda):
            for id in get_component3_section_templateId(component):
                for template_id in search_template_ids:
                    if is_template_id(id, template_id):
                        return component["section"]
    return None


def get_ccda_component3(ccda: Mapping) -> Sequence:
    """get_ccda_component3 Gets the POCD_MT000040.Component3
    from the ClinicalDocument.

    See https://github.com/HL7/CDA-core-2.0/tree/master/schema

    Arguments:
        ccda (Mapping): The ccda document as a map

    Returns:
        The Component3 elements from the document, otherwise []
    """
    return to_list(
        ccda.get("ClinicalDocument", {})
        .get("component", {})
        .get("structuredBody", {})
        .get("component", [])
    )


def get_component3_section_templateId(component: Mapping) -> Sequence:
    """get_component3_section_template_id Gets the templateId
    from the POCD_MT000040.Component3.

    See https://github.com/HL7/CDA-core-2.0/tree/master/schema

    Arguments:
        component (Mapping): The component3 as a map

    Returns:
        The templateId from the component3, otherwise []
    """
    return to_list(component.get("section", {}).get("templateId", []))


def get_template_id_key(template_id: str) -> str:
    return re_sub(r"[^A-Za-z0-9]", "_", template_id)


def is_template_id(id: Mapping, template_id: str) -> bool:
    return template_id == id.get("root", "").strip()
