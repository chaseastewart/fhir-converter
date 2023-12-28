import re
from datetime import datetime, timezone
from hashlib import sha1, sha256
from typing import Any, Callable, Optional
from uuid import UUID
from zlib import compress as z_compress

from liquid.builtin.filters.string import base64_encode
from liquid.context import Context
from liquid.filter import liquid_filter, string_filter, with_context
from liquid.undefined import Undefined
from pyjson5 import dumps as json5_dumps

from fhir_converter import datatypes


@liquid_filter
def to_json_string(data: Any) -> str:
    if isinstance(data, Undefined):
        return ""
    return json5_dumps(data)


@liquid_filter
def to_array(obj: Any) -> list:
    if isinstance(obj, Undefined):
        return []
    elif isinstance(obj, list):
        return obj
    return [obj]


@string_filter
def contains(data: str, sub_str: str) -> bool:
    return sub_str in data if data else False


@string_filter
def match(data: str, regex: str) -> list:
    return re.findall(regex, data)


@string_filter
def gzip(data: str) -> str:
    return base64_encode(z_compress(data.encode()))


@string_filter
def sha1_hash(data: str) -> str:
    return sha1(data.encode()).hexdigest()


@string_filter
def add_hyphens_date(input: str) -> str:
    if not input:
        return input
    return datatypes.hl7_to_fhir_dtm(input, precision=datatypes.Hl7DtmPrecision.DAY)


@string_filter
def format_as_date_time(input: str) -> str:
    if not input:
        return input
    return datatypes.hl7_to_fhir_dtm(input)


@string_filter
def now(_: str) -> str:
    return datatypes.to_fhir_dtm(datetime.now(timezone.utc))


@string_filter
def generate_uuid(data: str) -> str:
    return str(UUID(bytes=sha256(data.encode()).digest()[:16]))


@with_context
@string_filter
def get_property(
    code: str, mapping_key: str, property: Optional[str] = "code", *, context: Context
) -> str:
    mapping = context.resolve("code_mapping", default={}).get(mapping_key, None)
    if mapping:
        code_mapping = mapping.get(code, None)
        if not code_mapping:
            code_mapping = mapping.get("__default__", {})

        mapped_code = code_mapping.get(property, None)
        if mapped_code:
            return mapped_code

    return code if property in ("code", "display") else ""


@liquid_filter
def get_first_ccda_sections_by_template_id(data: dict, template_ids: str) -> dict:
    sections, search_template_ids = {}, list(filter(None, template_ids.split("|")))
    if search_template_ids:
        components = _get_ccda_components(data)
        if components:
            for template_id in search_template_ids:
                template_id_key = _get_template_id_key(template_id)
                for component in components:
                    for id in _get_ccda_section_template_ids(component):
                        if _is_template_id(id, template_id):
                            sections[template_id_key] = component["section"]
                            break
                    if template_id_key in sections:
                        break
    return sections


@liquid_filter
def get_ccda_section_by_template_id(
    data: dict, template_id: str, *template_ids: str
) -> dict:
    search_template_ids = [template_id]
    if template_ids:
        search_template_ids += template_ids

    search_template_ids = list(filter(None, search_template_ids))
    if search_template_ids:
        for component in _get_ccda_components(data):
            for id in _get_ccda_section_template_ids(component):
                for template_id in search_template_ids:
                    if _is_template_id(id, template_id):
                        return component["section"]
    return {}


def _get_ccda_components(data: dict) -> list:
    component = (
        data.get("ClinicalDocument", {})
        .get("component", {})
        .get("structuredBody", {})
        .get("component", [])
    )
    if not isinstance(component, list):
        return [component]
    return component


def _get_ccda_section_template_ids(component: dict) -> list:
    return to_array(component.get("section", {}).get("templateId", []))


def _get_template_id_key(template_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "_", template_id)


def _is_template_id(id: dict, template_id: str) -> bool:
    return template_id == id.get("root", "").strip()


@with_context
@liquid_filter
def batch_render(
    batch: list, template_name: str, arg_name: str, *, context: Context
) -> str:
    if not batch:
        return ""
    template = context.get_template_with_context(template_name)
    with context.get_buffer() as buffer:
        for data in batch:
            with context.extend(namespace={arg_name: data}, template=template):
                template.render_with_context(context, buffer, partial=True)
        return buffer.getvalue()


__default__: list[tuple[str, Callable]] = [
    ("to_json_string", to_json_string),
    ("to_array", to_array),
    ("contains", contains),
    ("match", match),
    ("gzip", gzip),
    ("sha1_hash", sha1_hash),
    ("add_hyphens_date", add_hyphens_date),
    ("format_as_date_time", format_as_date_time),
    ("now", now),
    ("generate_uuid", generate_uuid),
    ("get_property", get_property),
    ("get_first_ccda_sections_by_template_id", get_first_ccda_sections_by_template_id),
    ("get_ccda_section_by_template_id", get_ccda_section_by_template_id),
    ("batch_render", batch_render),
]
