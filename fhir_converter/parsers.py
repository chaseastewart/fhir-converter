import re
from typing import TextIO, Union

from pyjson5 import loads as json5_loads
from xmltodict import parse as xmltodict_parse

from fhir_converter import utils

REGEX = re.compile(r"\r\n?|\n")


def parse_json(json_input: str) -> dict:
    json_data = utils.apply(json5_loads(json_input.strip()), _remove_null_empty)
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


def parse_xml(xml_input: Union[str, TextIO]) -> dict:
    if not isinstance(xml_input, str):
        xml_input = xml_input.read()
    xml_input = REGEX.sub("", xml_input.strip())

    data = utils.apply(
        xmltodict_parse(xml_input), _normalize_xml_text, _normalize_xml_keys
    )
    data["_originalData"] = xml_input
    return data


def _normalize_xml_text(data: dict, key_val: tuple) -> None:
    key, val = key_val
    if key == "#text":
        data["_"] = val
        del data[key]
    elif not key.startswith("@") and isinstance(val, str):
        data[key] = {"_": val}


def _normalize_xml_keys(data: dict, key_val: tuple) -> None:
    key, val = key_val
    if key.startswith("@"):
        data[key[1:]] = val
        del data[key]
    elif ":" in key:
        data[key.replace(":", "_")] = val
        del data[key]
