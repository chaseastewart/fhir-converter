from dataclasses import dataclass
from os import PathLike
from typing import IO, Any, Callable, Dict, List, Optional, Union

from lxml import etree
from pyjson5 import loads as json_loads
from typing_extensions import TypeAlias

from fhir_converter.utils import (
    blank_str_to_empty,
    is_undefined_none_or_blank,
    join_strs,
    parse_etree,
    read_text,
    sanitize_str,
)


@dataclass(frozen=True)
class ParseXmlOpts:
    cdata_key: str = "_"
    encoding: str = "utf-8"


XmlDataIn: TypeAlias = Union[IO[str], IO[bytes], PathLike, str, bytes]
JsonDataIn: TypeAlias = Union[IO[str], IO[bytes], str, bytes]

ParsedXml: TypeAlias = Dict[str, Any]
XmlElement: TypeAlias = etree._Element

ParseXmlFilter: TypeAlias = Callable[
    [XmlElement, Optional[XmlElement], ParseXmlOpts],
    Optional[ParsedXml],
]
AfterParseXml: TypeAlias = Callable[
    [ParsedXml, etree._ElementTree, ParseXmlOpts],
    ParsedXml,
]


def _remove_empty_json_list(obj: List[Any]) -> List[Any]:
    """remove_empty_json_list Removes any empty values from the JSON list

    See is_none_or_empty and remove_empty_json for more info

    Args:
        obj (List[Any]): the JSON list to check

    Returns:
        List[Any]: the JSON list with non empty values. May be empty if all values
        were empty
    """
    new_list = []
    for val in obj:
        val = _remove_empty_json(val)
        if not is_undefined_none_or_blank(val):
            new_list.append(val)
    return new_list


def _remove_empty_json_dict(obj: Dict[Any, Any]) -> Dict[Any, Any]:
    """remove_empty_json_dict Removes any empty JSON key/value mappings from
    the supplied key/value pairs

    See is_none_or_empty and remove_empty_json for more info

    Args:
        obj (Dict[Any, Any]): the JSON key/value pairs to check

    Returns:
        Dict[Any, Any]: the non empty key/value pairs, May be empty if
        all key/value pairs were empty
    """
    for key in list(obj.keys()):
        val = _remove_empty_json(obj[key])
        if not is_undefined_none_or_blank(val):
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


def parse_json(
    json_in: JsonDataIn, encoding: str = "utf-8", ignore_empty_fields: bool = True
) -> Any:
    """parse_json Parses the JSON string using a JSON 5 compliant decoder

    Any empty JSON will be removed from decoded output. See remove_empty_json

    Args:
        json_in (JsonDataIn): the json to decode
        encoding (str, optional): the character encoding to use. Defaults to "utf-8"
        ignore_empty_fields (bool): Whether to ignore empty fields. Defaults to True

    Returns:
        Any: the decoded output
    """
    json = json_loads(read_text(json_in, encoding))
    return _remove_empty_json(json) if ignore_empty_fields else json


def _get_xml_element_name(element: XmlElement) -> str:
    """get_xml_element_name Gets the elements name including its prefix if available

    Args:
        element (XmlElement): the current element
    Returns:
        str: the elements name
    """
    return join_strs(element.prefix, etree.QName(element).localname)


def _xml_ns_to_dict(
    element: XmlElement, parent: Optional[XmlElement] = None
) -> Dict[str, str]:
    """xml_ns_to_dict Converts the elements namespaces to a dict if a
        namespace is different than the parent's

    Args:
        element (XmlElement): the current element
        parent (Optional[XmlElement], optional): the parent element. Defaults to None
    Returns:
        Dict[str, str]: the elements namespaces or an empty dict
    """
    parent_nsmap, nsmap = parent.nsmap if parent is not None else {}, element.nsmap
    if nsmap == parent_nsmap:
        return {}

    ns_out = {}
    for prefix, uri in nsmap.items():
        if parent_nsmap.get(prefix, None) != uri:
            name, ns_out[name] = join_strs("xmlns", prefix), uri
    return ns_out


def _xml_attrib_to_dict(element: XmlElement) -> Dict[str, str]:
    """xml_attrib_to_dict Converts the elements's attributtes to a dict.
        Namespaces will be mapped to their corresponding prefix if available

    Args:
        element (XmlElement): the current element
    Returns:
        Dict[str, str]: the elements attributes or an empty dict
    """
    attrib_out = {}
    for ns_name, value in element.attrib.items():
        qname = etree.QName(ns_name)
        candidates = [
            pfx
            for (pfx, uri) in element.nsmap.items()
            if pfx is not None and uri == qname.namespace
        ]
        prefix = (
            candidates[0]
            if len(candidates) == 1
            else min(candidates) if candidates else None
        )
        name, attrib_out[name] = join_strs(prefix, qname.localname), value
    return attrib_out


def _xml_text_to_dict(element: XmlElement, cdata_key: str) -> Dict[str, str]:
    """xml_text_to_dict Converts the elements text to a dict using the provided
        cdata key

    Args:
        element (XmlElement): the current element
        cdata_key (str): the cdata key to use
    Returns:
        Dict[str, str]: the elements text or an empty dict
    """
    text = sanitize_str(element.text)
    return {cdata_key: text} if text else {}


def _xml_tail_to_dict(
    parsed_dict: ParsedXml, element: XmlElement, cdata_key: str
) -> None:
    """xml_tail_to_dict Adds the elements tail to the provided dict
        using the specified cdata key

    Args:
        parsed_dict (ParsedXml): the dict being constructed
        element (XmlElement): the current element
        cdata_key (str): the cdata key to use
    """
    tail = sanitize_str(element.tail)
    if tail:
        try:
            parsed_dict[cdata_key] += tail
        except KeyError:
            parsed_dict[cdata_key] = tail


def _xml_element_to_dict(
    parse_filter: ParseXmlFilter,
    parse_opts: ParseXmlOpts,
    element: XmlElement,
    parent: Optional[XmlElement] = None,
) -> ParsedXml:
    """xml_element_to_dict Converts the current element to a dict using the provided parse
        options and mapping function

    Args:
        parse_filter (ParseXmlFilter, optional): the parse filter
        parse_opts (ParseXmlOpts): the parser options
        element (XmlElement): the current element
        parent (Optional[XmlElement]): the current elements parent. May be None for the root
    Returns:
        ParsedXml: the parsed xml dict
    """
    filtered_out = parse_filter(element, parent, parse_opts)
    if filtered_out is not None:
        return filtered_out

    el_out: ParsedXml = {
        **_xml_ns_to_dict(element, parent),
        **_xml_attrib_to_dict(element),
        **_xml_text_to_dict(element, parse_opts.cdata_key),
    }
    for child in element:
        child_out = _xml_element_to_dict(parse_filter, parse_opts, child, element)
        if child_out:
            child_name = _get_xml_element_name(child)
            try:
                cur_value = el_out[child_name]
                if not isinstance(cur_value, list):
                    cur_value = [cur_value]
                    el_out[child_name] = cur_value
                cur_value.append(child_out)
            except KeyError:
                el_out[child_name] = child_out
        _xml_tail_to_dict(el_out, child, parse_opts.cdata_key)
    return el_out


def parse_xml_filter(element: XmlElement, *_) -> Optional[ParsedXml]:
    """parse_xml_filter Determines if the element should be filtered or not

    Args:
        element (XmlElement): the current element
    Returns:
        Optional[ParsedXml]: An empty dict if the element should be filtered or None
    """
    tag = element.tag
    if tag is etree.Comment or tag is etree.ProcessingInstruction or tag is etree.Entity:
        return {}
    return None


def parse_xml(
    xml_in: XmlDataIn,
    parse_opts: ParseXmlOpts = ParseXmlOpts(),
    parse_filter: ParseXmlFilter = parse_xml_filter,
    after_parse_xml: AfterParseXml = lambda parsed_dict, *_: parsed_dict,
) -> ParsedXml:
    """parse_xml Parses the xml imput string or text/binary IO to a dict

    Args:
        xml_in (DataIn): the xml input. May be path like, any string, or file like
        parse_opts (ParseXmlOpts, optional): the parser options. See ParseXmlOpts for defaults
        parse_filter (ParseXmlFilter, optional): the parse filter to use while parsing the provided xml.
            Filters should return ParsedXml, an empty dict or None. None indicates the current element is
            not filtered and parsing should continue down the elements tree. See parse_xml_filter for
            additional information
        after_parse_xml (AfterParseXml, optional): the post processing logic to apply to the
            parsed dict after all processing has completed. Noop by default
    Returns:
        ParsedXml: the parsed xml dict
    """
    tree = parse_etree(
        xml_in,
        encoding=parse_opts.encoding,
        remove_blank_text=True,
        remove_comments=True,
    )
    parsed_dict = _xml_element_to_dict(parse_filter, parse_opts, tree.getroot())
    parsed_dict = {_get_xml_element_name(tree.getroot()): parsed_dict}
    return after_parse_xml(parsed_dict, tree, parse_opts)
