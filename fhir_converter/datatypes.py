from __future__ import annotations

import datetime
import math
import re
from enum import Enum
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


class FhirDtmPrecision(Enum):
    YEAR = 4
    MONTH = 7
    DAY = 10


class Hl7DtmPrecision(Enum):
    YEAR = 4
    MONTH = 6
    DAY = 8
    HOUR = 10
    MIN = 12
    SEC = 14
    MILLIS = 16

    def greater(self, other: Hl7DtmPrecision) -> bool:
        return self.value > other.value

    def atleast(self, other: Hl7DtmPrecision) -> bool:
        return self.value >= other.value

    @property
    def timespec(self) -> str:
        return "milliseconds" if self.greater(Hl7DtmPrecision.SEC) else "seconds"

    @classmethod
    def from_dtm(cls, dtm: str) -> Hl7DtmPrecision:
        _len = len(dtm)
        if _len > Hl7DtmPrecision.SEC.value:
            return Hl7DtmPrecision.MILLIS
        elif _len > Hl7DtmPrecision.MIN.value:
            return Hl7DtmPrecision.SEC
        elif _len > Hl7DtmPrecision.HOUR.value:
            return Hl7DtmPrecision.MIN
        elif _len > Hl7DtmPrecision.DAY.value:
            return Hl7DtmPrecision.HOUR
        elif _len > Hl7DtmPrecision.MONTH.value:
            return Hl7DtmPrecision.DAY
        elif _len > Hl7DtmPrecision.YEAR.value:
            return Hl7DtmPrecision.MONTH
        elif _len == Hl7DtmPrecision.YEAR.value:
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
    year = int(dtm[0:4])

    atleast = precision.atleast
    if atleast(Hl7DtmPrecision.MONTH):
        month, precision = int(dtm[4:6]), Hl7DtmPrecision.MONTH
    else:
        month = 1

    if atleast(Hl7DtmPrecision.DAY):
        day, precision = int(dtm[6:8]), Hl7DtmPrecision.DAY
    else:
        day = 1

    if atleast(Hl7DtmPrecision.HOUR):
        hour, precision = int(dtm[8:10]), Hl7DtmPrecision.HOUR
    else:
        hour = 0

    if atleast(Hl7DtmPrecision.MIN):
        minute, precision = int(dtm[10:12]), Hl7DtmPrecision.MIN
    else:
        minute = 0

    if atleast(Hl7DtmPrecision.SEC):
        delta = datetime.timedelta(seconds=float(dtm[Hl7DtmPrecision.MIN.value:]))
        second, microsecond = delta.seconds, delta.microseconds
    else:
        second = 0
        microsecond = 0

    return Hl7ParsedDtm(
        precision=precision,
        dt=datetime.datetime(
            year, month, day, hour, minute, second, microsecond, tzinfo=tzinfo
        ),
    )


def hl7_to_fhir_dtm(input: str, precision: Optional[Hl7DtmPrecision] = None) -> str:
    parsed_dtm = parse_hl7_dtm(input)
    if precision is None or precision.greater(parsed_dtm.precision):
        precision = parsed_dtm.precision

    iso_dtm = to_fhir_dtm(
        dt=parsed_dtm.dt,
        timespec=precision.timespec,
    )

    if precision.greater(Hl7DtmPrecision.DAY):
        return iso_dtm
    elif precision.greater(Hl7DtmPrecision.MONTH):
        return iso_dtm[: FhirDtmPrecision.DAY.value]
    elif precision.greater(Hl7DtmPrecision.YEAR):
        return iso_dtm[: FhirDtmPrecision.MONTH.value]
    return iso_dtm[: FhirDtmPrecision.YEAR.value]


def to_fhir_dtm(dt: datetime.datetime, timespec: Optional[str] = None) -> str:
    iso_dtm = dt.isoformat(timespec=timespec if timespec else "milliseconds")
    off = dt.utcoffset()
    if off is not None and int(off.total_seconds()) == 0:
        iso_dtm = iso_dtm[:-6] + "Z"
    return iso_dtm
