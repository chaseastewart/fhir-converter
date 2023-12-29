import re
from typing import IO, Callable, Optional, Union

from pyjson5 import loads as json5_loads
from xmltodict import parse as xmltodict_parse

REGEX = re.compile(r"\r\n?|\n")


def parse_json(json_input: str) -> dict:
    json_data = _apply(
        json5_loads(json_input.strip()),
        _remove_null_empty,
    )
    unique_entrys = {}
    for entry in json_data.get("entry", []):
        key = _get_key(entry)
        if key in unique_entrys:
            _merge_dict(unique_entrys[key], entry)
        else:
            unique_entrys[key] = entry
    json_data["entry"] = list(unique_entrys.values())
    return json_data


def _remove_null_empty(data: dict, key_val: tuple) -> None:
    key, val = key_val
    if val is None or not val:
        del data[key]


def _apply(data: dict, func: Callable[[dict, tuple], None]) -> dict:
    for key in set(data.keys()):
        val = data[key]
        if isinstance(val, dict):
            _apply(val, func)
        elif isinstance(val, list):
            l = []
            for el in val:
                if isinstance(el, dict):
                    _apply(el, func)
                if el:
                    l.append(el)
            if l:
                val, data[key] = l, l
            else:
                val = None

        if val:
            func(data, (key, val))
        else:
            del data[key]
    return data


def _get_key(entry: dict) -> str:
    resource = entry.get("resource", {})
    return "_".join(
        filter(
            None,
            [
                resource.get("resourceType", ""),
                resource.get("meta", {}).get("versionId", ""),
                resource.get("id", ""),
            ],
        )
    )


def _merge_dict(a: dict, b: dict) -> dict:
    for bk, bv in b.items():
        if not bk in a:
            a[bk] = bv
        else:
            av = a[bk]
            if type(av) != type(bv):
                a[bk] = bv
            elif isinstance(bv, dict):
                _merge_dict(av, bv)
            elif isinstance(bv, list):
                for v in bv:
                    if not v in av:
                        av.append(v)
    return a


def parse_xml(xml_input: Union[str, IO], encoding: Optional[str] = None) -> dict:
    if not encoding:
        encoding = "utf-8"

    if isinstance(xml_input, str):
        xml = xml_input
    else:
        xml = xml_input.read()
        if not isinstance(xml, str):
            xml = xml.decode(encoding)
    xml = REGEX.sub("", xml.strip())

    data = xmltodict_parse(
        xml,
        encoding=encoding,
        force_cdata=True,
        attr_prefix="",
        cdata_key="_",
        postprocessor=lambda _, key, value: (
            (key.replace(":", "_") if ":" in key else key, value) if value else None
        ),
    )
    data["_originalData"] = xml
    return data
