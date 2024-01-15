from collections.abc import Generator
from os import remove as os_remove
from os import walk as os_walk
from pathlib import Path
from re import compile as re_compile
from typing import IO, Any, Union

from pyjson5 import loads as json_loads
from xmltodict import parse as xmltodict_parse

line_endings_regex = re_compile(r"\r\n?|\n")


def is_none_or_empty(obj: Any) -> bool:
    """is_none_or_empty returns whether the object is none or empty

    Will return True for the following::
        - None
        - '' (empty string)
        - ' ' (blank string)
        - [] (empty list)
        - () (empty tuple)
        - {} (empty dictionary)

    Args:
        obj (Any): the object to check

    Returns:
        bool: returns True if the object is none or empty, otherwise, False
    """
    if type(obj) in (int, float, bool):
        return False
    elif isinstance(obj, str):
        obj = blank_str_to_empty(obj)
    return not obj


def to_list_or_empty(obj: Any) -> list[Any]:
    """to_list_or_empty returns the object as a list if its a list or not empty
    or none, otherwise, []

    Args:
        obj (Any): the object to check

    Returns:
        list[Any]: returns the object as a list if its a list or not empty or none,
        otherwise, []
    """
    if isinstance(obj, list):
        return obj
    elif is_none_or_empty(obj):
        return []
    return [obj]


def blank_str_to_empty(obj: str) -> str:
    """blank_str_to_empty returns the given string if it's not blank, otherwise, empty

    Args:
        obj (str): the string to check

    Returns:
        str: returns the given string if it's not blank, otherwise, empty
    """
    return obj if obj and not obj.isspace() else ""


def merge_dict(a: dict[Any, Any], b: dict[Any, Any]) -> dict[Any, Any]:
    """merge_dict Merges the key/value pair mappings similarly to
    newtonsoft Merge.

    See https://www.newtonsoft.com/json/help/html/MergeJson.htm

    Args:
        a (dict[Any, Any]): the mappings to merge into
        b (dict[Any, Any]): the mappings to merge

    Returns:
        dict[Any, Any]: the merged mappings
    """
    for bk, bv in b.items():
        if bv is None:
            continue

        if bk not in a:
            a[bk] = bv
        else:
            av = a[bk]
            if type(av) != type(bv):
                a[bk] = bv
            elif isinstance(bv, dict):
                merge_dict(av, bv)
            elif isinstance(bv, list):
                for v in bv:
                    if v not in av:
                        av.append(v)
            else:
                a[bk] = bv
    return a


def _remove_empty_json_list(obj: list[Any]) -> list[Any]:
    """remove_empty_json_list Removes any empty values from the JSON list

    See is_none_or_empty and remove_empty_json for more info

    Args:
        obj (list[Any]): the JSON list to check

    Returns:
        list[Any]: the JSON list with non empty values. May be empty if all values
        were empty
    """
    new_list = []
    for val in obj:
        val = _remove_empty_json(val)
        if not is_none_or_empty(val):
            new_list.append(val)
    return new_list


def _remove_empty_json_dict(obj: dict[Any, Any]) -> dict[Any, Any]:
    """remove_empty_json_dict Removes any empty JSON key/value mappings from
    the supplied key/value pairs

    See is_none_or_empty and remove_empty_json for more info

    Args:
        obj (dict[Any, Any]): the JSON key/value pairs to check

    Returns:
        dict[Any, Any]: the non empty key/value pairs, May be empty if
        all key/value pairs were empty
    """
    for key in list(obj.keys()):
        val = _remove_empty_json(obj[key])
        if not is_none_or_empty(val):
            obj[key] = val
        else:
            del obj[key]
    return obj


def _remove_empty_json(obj: Any) -> Any:
    """remove_empty_json Removes empty JSON

    Removes from the JSON object as follows::

        - '', ' ' strings will be converted to ''. See blank_str_to_empty
        - Lists with empty elements will be removed. See remove_empty_json_list
        - Dicts with empty key/value mappings will be removed. See remove_empty_json_dict

    Args:
        obj (Any): the JSON to check

    Returns:
        Any: the non empty JSON, or empty
    """
    if isinstance(obj, dict):
        return _remove_empty_json_dict(obj)
    elif isinstance(obj, list):
        return _remove_empty_json_list(obj)
    elif isinstance(obj, str):
        return blank_str_to_empty(obj)
    return obj


def parse_json(json_input: str) -> Any:
    """parse_json parses the JSON string using a JSON 5 compliant decoder

    Any empty JSON will be removed from decoded output. See remove_empty_json

    Args:
        json_input (str): the json to decode

    Returns:
        Any: the decoded output
    """
    return _remove_empty_json(json_loads(json_input))


def parse_xml(xml_input: Union[str, IO], encoding: str = "utf-8") -> dict[str, Any]:
    """parse_xml Parses the xml imput string or text/binary IO

    Wraps xmltodict customizing the output as follows::
        - Sets _originalData key with the original xml string with line endings removed
        - Forces cdata along with settng the key to _
        - Disables the prepanding of @ to attribute keys
        - Replaces any : characters in keys with _

    Args:
        xml_input (Union[str, IO]): the xml input
        encoding (str, optional): The character encoding to use. Defaults to "utf-8"

    Returns:
        dict[str, Any]: the parsed xml
    """
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


def join_subpath(path: Path, parent: Path, child: Path) -> Path:
    """join_subpath joins the parts from the child relative to the parent
    path to the supplied path. The final file part from child will be
    excluded if child is a file

    Args:
        path (Path): the path to join the parts to
        parent (Path): the parent path
        child (Path): the child within the parent path

    Returns:
        Path: the new path
    """
    if not parent.is_dir():
        raise ValueError("parent must be a directory")
    child_parts = list(child.parts if child.is_dir() else child.parts[:-1])
    for parent_part in parent.parts:
        child_part = child_parts.pop(0) if child_parts else None
        if parent_part != child_part:
            raise ValueError("child must be a subdirectory of parent")
    return path.joinpath(*child_parts)


def del_empty_dirs_quietly(path: Path) -> None:
    """del_empty_dirs_quietly Quietly deletes any empty sub directories within
    the path ignoring any errors that may have occurred

    Args:
        path (Path): the path to scan
    """
    for dir, dirs, filenames in walk_path(path):
        if not dirs and not filenames and dir != path:
            del_path_quietly(dir)


def del_path_quietly(path: Path) -> None:
    """del_path_quietly Quietly deletes a path ignoring any errors that
    may have occurred

    Allows callers to attempt to delete a path while not having to worry
    about file system errors

    Args:
        path (Path): the path to delete
    """
    try:
        if path.is_dir():
            path.rmdir()
        else:
            os_remove(path)
    except OSError:
        pass


def mkdir(path: Path, **kwargs) -> bool:
    """mkdir wrapper around Path.mkdir forwarding additional keyword args

    Allows callers to discern between a directory existing, an actual error
    while creating the directory and a successful creation aka the directory
    didn't exist previously

    Args:
        path (Path): the path

    Returns:
        bool: True if the directory was created, otherwise, False to indicate the
        directory already exists
    """
    if not path.is_dir():
        path.mkdir(**kwargs)
        return True
    return False


def walk_path(
    path: Path,
) -> Generator[tuple[Path, list[str], list[str]], Any, None]:
    """walk_path wrapper around os.walk to semi bridge the gap of path.walk
    added in 3.12.

    Args:
        path (Path): the path to walk

    Yields:
        Generator[tuple[Path, list[str], list[str]], Any, None]: The directory
        tree generator
    """
    for dir, dirs, filenames in os_walk(path):
        yield (Path(dir), dirs, filenames)
