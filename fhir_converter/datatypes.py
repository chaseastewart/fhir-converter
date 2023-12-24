from __future__ import annotations

import datetime
import math
import re
from enum import IntEnum
from typing import NamedTuple, Optional

DTM_REGEX = re.compile(r"(\d+(?:\.\d+)?)(?:([+-]\d{2})(\d{2}))?")


class _UTCOffset(datetime.tzinfo):
    def __init__(self, minutes) -> None:
        self.minutes = minutes

    def utcoffset(self, _) -> datetime.timedelta:
        return datetime.timedelta(minutes=self.minutes)

    def tzname(self, _) -> str:
        minutes = abs(self.minutes)
        return "{0}{1:02}{2:02}".format(
            "-" if self.minutes < 0 else "+", minutes // 60, minutes % 60
        )

    def dst(self, _) -> datetime.timedelta:
        return datetime.timedelta(0)


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

    @classmethod
    def from_dtm(cls, dtm: str) -> Hl7DtmPrecision:
        _len = len(dtm)
        if _len > Hl7DtmPrecision.SEC:
            return Hl7DtmPrecision.MILLIS
        elif _len > Hl7DtmPrecision.MIN:
            return Hl7DtmPrecision.SEC
        elif _len > Hl7DtmPrecision.HOUR:
            return Hl7DtmPrecision.MIN
        elif _len > Hl7DtmPrecision.DAY:
            return Hl7DtmPrecision.HOUR
        elif _len > Hl7DtmPrecision.MONTH:
            return Hl7DtmPrecision.DAY
        elif _len > Hl7DtmPrecision.YEAR:
            return Hl7DtmPrecision.MONTH
        elif _len == Hl7DtmPrecision.YEAR:
            return Hl7DtmPrecision.YEAR
        raise ValueError("Malformed HL7 datetime {0}".format(dtm))


class Hl7ParsedDtm(NamedTuple):
    precision: Hl7DtmPrecision
    dt: datetime.datetime


def parse_hl7_dtm(hl7_input: str) -> Hl7ParsedDtm:
    dt_match = DTM_REGEX.match(hl7_input.strip())
    if not dt_match:
        raise ValueError("Malformed HL7 datetime {0}".format(hl7_input))

    dtm = dt_match.group(1)
    tzh = dt_match.group(2)
    tzm = dt_match.group(3)
    if tzh and tzm:
        minutes = int(tzh) * 60
        minutes += math.copysign(int(tzm), minutes)
        tzinfo = _UTCOffset(minutes)
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
        delta = datetime.timedelta(seconds=float(dtm[Hl7DtmPrecision.MIN :]))
        second, microsecond = delta.seconds, delta.microseconds
    else:
        second = 0
        microsecond = 0

    return Hl7ParsedDtm(
        precision,
        dt=datetime.datetime(
            year, month, day, hour, minute, second, microsecond, tzinfo=tzinfo
        ),
    )


def hl7_to_fhir_dtm(input: str, precision: Optional[Hl7DtmPrecision] = None) -> str:
    parsed_dtm = parse_hl7_dtm(input)
    if precision is None or precision > parsed_dtm.precision:
        precision = parsed_dtm.precision

    return to_fhir_dtm(
        dt=parsed_dtm.dt,
        precision=precision.fhir_precision,
    )


def to_fhir_dtm(
    dt: datetime.datetime, precision: Optional[FhirDtmPrecision] = None
) -> str:
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
