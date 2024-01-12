from collections.abc import Callable, MutableMapping, Sequence
from os import remove as os_remove
from os import walk as os_walk
from pathlib import Path
from re import compile as re_compile
from typing import IO, Any, Union

from pyjson5 import loads as json_loads
from xmltodict import parse as xmltodict_parse

line_endings_regex = re_compile(r"\r\n?|\n")


def apply_mapping(
    func: Callable[[MutableMapping, tuple], None], data: MutableMapping
) -> MutableMapping:
    for key in set(data.keys()):
        val = data[key]
        if isinstance(val, MutableMapping):
            apply_mapping(func, val)
        elif isinstance(val, list):
            new_list = []
            for el in val:
                if isinstance(el, MutableMapping):
                    apply_mapping(func, el)
                if el:
                    new_list.append(el)
            if new_list:
                val, data[key] = new_list, new_list
            else:
                val = None

        if val:
            func(data, (key, val))
        else:
            del data[key]
    return data


def merge_mappings(a: MutableMapping, b: MutableMapping) -> MutableMapping:
    for bk, bv in b.items():
        if bk not in a:
            a[bk] = bv
        else:
            av = a[bk]
            if type(av) != type(bv):
                a[bk] = bv
            elif isinstance(bv, MutableMapping):
                merge_mappings(av, bv)
            elif isinstance(bv, list):
                for v in bv:
                    if v not in av:
                        av.append(v)
    return a


def to_list(obj: Any) -> list:
    if obj is None or not obj:
        return []
    elif isinstance(obj, list):
        return obj
    return [obj]


def parse_json(json_input: str) -> MutableMapping:
    def remove_null_empty(json: MutableMapping, key_val: tuple) -> None:
        key, val = key_val
        if not val:
            del json[key]

    return apply_mapping(remove_null_empty, json_loads(json_input.strip()))


def parse_xml(xml_input: Union[str, IO], encoding: str = "utf-8") -> MutableMapping:
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


def rm_empty_dirs(parent: Path) -> None:
    def rmdir(root: Path, dirs: list[str], filenames: list[str]) -> None:
        if root != parent and not dirs and not filenames:
            try:
                root.rmdir()
            except OSError:
                pass

    apply_dir(rmdir, parent)


def rmdir_if_empty(dir: Path) -> None:
    if next(dir.iterdir(), None) is None:
        dir.rmdir()


def rm_path(path: Path) -> None:
    try:
        os_remove(path)
    except OSError:
        pass


def apply_dir(func: Callable[[Path, list[str], list[str]], None], dir: Path) -> None:
    for root, dirs, filenames in os_walk(dir):
        func(Path(root), dirs, filenames)


def mkdir(dir: Path, **kwargs) -> bool:
    if not dir.is_dir():
        dir.mkdir(**kwargs)
        return True
    return False


def mkdirs(root: Path, dirnames: Sequence[str], **kwargs) -> None:
    mkdir(root, **kwargs)
    for dirname in dirnames:
        mkdir(root.joinpath(dirname), **kwargs)
