from base64 import b64encode
from collections.abc import Callable, Iterable, Mapping, Sequence
from datetime import datetime, timezone
from functools import wraps
from hashlib import sha1, sha256
from re import findall as re_findall
from typing import Any, Optional
from uuid import UUID
from zlib import compress as z_compress

from liquid import Environment
from liquid.context import Context
from liquid.exceptions import FilterArgumentError
from liquid.filter import (
    flatten,
    liquid_filter,
    sequence_filter,
    string_filter,
    with_context,
)
from liquid.undefined import Undefined
from pyjson5 import dumps as json5_dumps

from fhir_converter.hl7 import (
    Hl7DtmPrecision,
    get_ccda_components,
    get_ccda_section_template_ids,
    get_template_id_key,
    hl7_to_fhir_dtm,
    is_template_id,
    to_fhir_dtm,
)
from fhir_converter.utils import to_list


def str_arg(val: Optional[Any], default: str = "") -> str:
    if not val:
        return default
    elif not isinstance(val, str):
        return str(val)
    return val


def mapping_filter(_filter: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(_filter)
    def wrapper(val: object, *args: Any, **kwargs: Any) -> Any:
        if not isinstance(val, Mapping):
            raise FilterArgumentError(f"expected a mapping, found {type(val).__name__}")

        try:
            return _filter(val, *args, **kwargs)
        except TypeError as err:
            raise FilterArgumentError(err) from err

    return wrapper


@liquid_filter
def to_json_string(data: Any) -> str:
    if isinstance(data, Undefined) or not data:
        return ""
    return json5_dumps(data)


@liquid_filter
def to_array(obj: Any) -> list:
    if isinstance(obj, Undefined):
        return []
    return to_list(obj)


@string_filter
def match(data: str, regex: Any) -> list:
    if not data:
        return []
    return re_findall(str_arg(regex), data)


@string_filter
def gzip(data: str) -> str:
    return b64encode(z_compress(data.encode())).decode()


@string_filter
def sha1_hash(data: str) -> str:
    return sha1(data.encode()).hexdigest()


@string_filter
def add_hyphens_date(dtm: str) -> str:
    if not dtm:
        return dtm
    return hl7_to_fhir_dtm(dtm, precision=Hl7DtmPrecision.DAY)


@string_filter
def format_as_date_time(dtm: str) -> str:
    if not dtm:
        return dtm
    return hl7_to_fhir_dtm(dtm)


@string_filter
def now(_: str) -> str:
    return to_fhir_dtm(datetime.now(timezone.utc))


@string_filter
def generate_uuid(data: str) -> str:
    if not data:
        return ""
    return str(UUID(bytes=sha256(data.encode()).digest()[:16]))


@with_context
@string_filter
def get_property(
    code: str, mapping_key: Any, property: Optional[Any] = None, *, context: Context
) -> str:
    property = str_arg(property, default="code")
    mapping = context.resolve("code_mapping", default={}).get(str_arg(mapping_key), None)
    if mapping:
        code_mapping = mapping.get(code, None)
        if not code_mapping:
            code_mapping = mapping.get("__default__", {})

        mapped_code = code_mapping.get(property, None)
        if mapped_code:
            return mapped_code

    return code if property in ("code", "display") else ""


@mapping_filter
def get_first_ccda_sections_by_template_id(data: Mapping, template_ids: Any) -> Mapping:
    sections, search_template_ids = {}, list(
        filter(None, str_arg(template_ids).split("|"))
    )
    if search_template_ids and data:
        components = get_ccda_components(data)
        if components:
            for template_id in search_template_ids:
                template_id_key = get_template_id_key(template_id)
                for component in components:
                    for id in get_ccda_section_template_ids(component):
                        if is_template_id(id, template_id):
                            sections[template_id_key] = component["section"]
                            break
                    if template_id_key in sections:
                        break
    return sections


@mapping_filter
def get_ccda_section_by_template_id(
    data: Mapping, template_id: Any, *template_ids: Any
) -> Mapping:
    search_template_ids = [template_id]
    if template_ids:
        search_template_ids += template_ids

    search_template_ids = list(filter(None, map(str_arg, flatten(search_template_ids))))
    if search_template_ids and data:
        for component in get_ccda_components(data):
            for id in get_ccda_section_template_ids(component):
                for template_id in search_template_ids:
                    if is_template_id(id, template_id):
                        return component["section"]
    return {}


@with_context
@sequence_filter
def batch_render(
    batch: Sequence, template_name: Any, arg_name: Any, *, context: Context
) -> str:
    if not batch:
        return ""
    template = context.get_template_with_context(str_arg(template_name))
    with context.get_buffer() as buffer:
        for data in batch:
            with context.extend(namespace={str_arg(arg_name): data}, template=template):
                template.render_with_context(context, buffer, partial=True)
        return buffer.getvalue()


all_filters: Sequence[tuple[str, Callable]] = [
    ("to_json_string", to_json_string),
    ("to_array", to_array),
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


def register_filters(env: Environment, filters: Iterable[tuple[str, Callable]]) -> None:
    for name, func in filter(lambda f: f[0] not in env.filters, filters):
        env.add_filter(name, func)
