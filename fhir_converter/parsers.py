import re
from typing import Callable, TextIO, Union

from pyjson5 import loads as json5_loads
from xmltodict import parse as xmltodict_parse

REGEX = re.compile(r"\r\n?|\n")


def _normalize_dict(data: dict, func: Callable[[dict, tuple], None]) -> dict:
    for key in set(data.keys()):
        val = data[key]
        if isinstance(val, dict):
            _normalize_dict(val, func)
        elif isinstance(val, list):
            normalized = []
            for el in val:
                if isinstance(el, dict):
                    _normalize_dict(el, func)
                if el:
                    normalized.append(el)
            val = normalized
            data[key] = val

        if val:
            func(data, (key, val))
        else:
            del data[key]
    return data


def parse_json(json_input: str) -> dict:
    def strip_null_empty(data: dict, key_val: tuple) -> None:
        key, val = key_val
        if val is None or not val:
            del data[key]

    return _normalize_dict(json5_loads(json_input.strip()), strip_null_empty)


def parse_xml(xml_input: Union[str, TextIO]) -> dict:
    def normalize_text(data: dict, key_val: tuple) -> None:
        key, val = key_val
        if key == "#text":
            data["_"] = val
            del data[key]
        elif not key.startswith("@") and isinstance(val, str):
            data[key] = {"_": val}

    def normalize_keys(data: dict, key_val: tuple) -> None:
        key, val = key_val
        if key.startswith("@"):
            data[key[1:]] = val
            del data[key]
        elif ":" in key:
            data[key.replace(":", "_")] = val
            del data[key]

    
    if not isinstance(xml_input, str):
        xml_input = xml_input.read()
    xml_input = REGEX.sub("", xml_input.strip())

    data = _normalize_dict(
        _normalize_dict(xmltodict_parse(xml_input), normalize_text), normalize_keys
    )
    data["_originalData"] = xml_input
    return data
