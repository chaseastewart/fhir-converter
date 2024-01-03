from collections.abc import Callable
from re import compile as re_compile
from typing import IO, Any, Union

from pyjson5 import loads as json5_loads
from xmltodict import parse as xmltodict_parse

line_endings_regex = re_compile(r"\r\n?|\n")


def apply(data: dict, func: Callable[[dict, tuple], None]) -> dict:
    for key in set(data.keys()):
        val = data[key]
        if isinstance(val, dict):
            apply(val, func)
        elif isinstance(val, list):
            l = []
            for el in val:
                if isinstance(el, dict):
                    apply(el, func)
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


def remove_null_empty(data: dict) -> dict:
    def _remove_null_empty(d: dict, key_val: tuple) -> None:
        key, val = key_val
        if not val:
            del d[key]

    return apply(data, _remove_null_empty)


def merge_dict(a: dict, b: dict) -> dict:
    for bk, bv in b.items():
        if not bk in a:
            a[bk] = bv
        else:
            av = a[bk]
            if type(av) != type(bv):
                a[bk] = bv
            elif isinstance(bv, dict):
                merge_dict(av, bv)
            elif isinstance(bv, list):
                for v in bv:
                    if not v in av:
                        av.append(v)
    return a


def to_list(obj: Any) -> list:
    if obj is None:
        return []
    elif isinstance(obj, list):
        return obj
    return [obj]


def parse_json(json_input: str, encoding: str = "utf-8") -> dict:
    return remove_null_empty(
        json5_loads(json_input.strip(), encoding=encoding),
    )


def parse_xml(xml_input: Union[str, IO], encoding: str = "utf-8") -> dict:
    if isinstance(xml_input, str):
        xml = xml_input
    else:
        xml = xml_input.read()
        if not isinstance(xml, str):
            xml = xml.decode(encoding)
    xml = line_endings_regex.sub("", xml.strip())

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
