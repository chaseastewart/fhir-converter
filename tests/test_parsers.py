from pathlib import Path
from unittest import TestCase

from lxml import etree
from pyjson5 import Json5EOF
from pytest import raises

from fhir_converter.parsers import ParseXmlOpts, parse_json, parse_xml, Hl7v2DataParser


class ParseJsonTest(TestCase):
    empty_file = Path("tests/data/empty.json")
    simple_file = Path("tests/data/simple.json")

    def test_empty_text(self) -> None:
        with raises(Json5EOF):
            parse_json("")

    def test_blank_text(self) -> None:
        with raises(Json5EOF):
            parse_json(" ")

    def test_empty_bytes(self) -> None:
        with raises(Json5EOF):
            parse_json(bytes())

    def test_empty_text_io(self) -> None:
        with raises(Json5EOF):
            with self.empty_file.open() as json_in:
                parse_json(json_in)

    def test_empty_binary_io(self) -> None:
        with raises(Json5EOF):
            with self.empty_file.open("rb") as json_in:
                parse_json(json_in)

    def test_simple(self) -> None:
        self.assertEqual({"test": "ok"}, parse_json('{"test": "ok"}'))

    def test_simple_bytes(self) -> None:
        self.assertEqual({"test": "ok"}, parse_json(b'{"test": "ok"}'))

    def test_simple_text_io(self) -> None:
        with self.simple_file.open() as json_in:
            self.assertEqual(parse_json(json_in), {"test": "ok"})

    def test_simple_binary_io(self) -> None:
        with self.simple_file.open("rb") as json_in:
            self.assertEqual(parse_json(json_in), {"test": "ok"})

    def test_bytearray(self) -> None:
        self.assertEqual({"test": "ok"}, parse_json(bytearray(b'{"test": "ok"}')))

    def test_memoryview(self) -> None:
        self.assertEqual({"test": "ok"}, parse_json(memoryview(b'{"test": "ok"}')))

    def test_list_empty(self) -> None:
        self.assertEqual([], parse_json("[]"))

    def test_list_bool(self) -> None:
        self.assertEqual([True, False], parse_json("[true, false]"))

    def test_list_str(self) -> None:
        self.assertEqual(["ok"], parse_json("['', ' ', 'ok']"))

    def test_list_dict(self) -> None:
        self.assertEqual([{"test": "ok"}], parse_json('[{}, {"test": "ok"}]'))

    def test_list_nested_empty(self) -> None:
        self.assertEqual([], parse_json("[[[],[]]]"))

    def test_dict_empty(self) -> None:
        self.assertEqual({}, parse_json("{}"))

    def test_dict_bool(self) -> None:
        self.assertEqual({"test": False}, parse_json('{"test": false}'))

    def test_dict_str_empty(self) -> None:
        self.assertEqual({}, parse_json('{"test": ""}'))

    def test_dict_list_empty(self) -> None:
        self.assertEqual({}, parse_json('{"test": []}'))

    def test_dict_list_bool(self) -> None:
        self.assertEqual({"test": [True, False]}, parse_json('{"test": [true, false]}'))

    def test_dict_list_str(self) -> None:
        self.assertEqual({"test": ["ok"]}, parse_json('{"test": ["", " ", "ok"]}'))

    def test_dict_list_dict(self) -> None:
        self.assertEqual(
            {"test": [{"test": "ok"}]}, parse_json('{"test": [{}, {"test": "ok"}]}')
        )

    def test_dict_nested_empty(self) -> None:
        self.assertEqual({}, parse_json('{"test": {"test": {"test": {}}}}'))

    def test_dict_nested_str_empty(self) -> None:
        self.assertEqual({}, parse_json('{"name": [{"family": "","given": [""]}]}'))

    def test_dict_ignore_trailing_comma(self) -> None:
        expected = {"name": [{"family": "Relative", "given": ["Ralph"]}]}
        self.assertEqual(
            expected,
            parse_json('{"name": [{"family": "Relative","given": ["Ralph"]}],}'),
        )

    def test_dict_ignore_lead_trail_spaces(self) -> None:
        expected = {"name": [{"family": "Relative", "given": ["Ralph"]}]}
        self.assertEqual(
            expected,
            parse_json('   {"name": [{"family": "Relative","given": ["Ralph"]}]}   '),
        )

    def test_include_empty_fields(self) -> None:
        self.assertEqual(
            {"name": [{"family": "", "given": [""]}]},
            parse_json(
                '{"name": [{"family": "","given": [""]}]}', ignore_empty_fields=False
            ),
        )


class ParseXmlTest(TestCase):
    empty_file = Path("tests/data/empty.xml")
    simple_file = Path("tests/data/simple.xml")

    def test_empty_text(self) -> None:
        with raises(etree.XMLSyntaxError):
            parse_xml("")

    def test_blank_text(self) -> None:
        with raises(etree.XMLSyntaxError):
            parse_xml(" ")

    def test_empty_bytes(self) -> None:
        with raises(etree.XMLSyntaxError):
            parse_xml(bytes())

    def test_empty_text_io(self) -> None:
        with raises(etree.XMLSyntaxError):
            with self.empty_file.open() as xml_in:
                parse_xml(xml_in)

    def test_empty_binary_io(self) -> None:
        with raises(etree.XMLSyntaxError):
            with self.empty_file.open("rb") as xml_in:
                parse_xml(xml_in)

    def test_bytearray(self) -> None:
        with raises(TypeError):
            parse_xml(bytearray(b"<a>data</a>"))

    def test_memoryview(self) -> None:
        with raises(TypeError):
            parse_xml(memoryview(b"<a>data</a>"))

    def test_minimal(self) -> None:
        self.assertEqual(parse_xml("<a/>"), {"a": {}})

    def test_simple(self) -> None:
        self.assertEqual(parse_xml("<a>data</a>"), {"a": {"_": "data"}})

    def test_simple_bytes(self) -> None:
        self.assertEqual(parse_xml(b"<a>data</a>"), {"a": {"_": "data"}})

    def test_simple_path(self) -> None:
        self.assertEqual(parse_xml(self.simple_file), {"a": {"_": "data"}})

    def test_simple_text_io(self) -> None:
        with self.simple_file.open() as xml_in:
            self.assertEqual(parse_xml(xml_in), {"a": {"_": "data"}})

    def test_simple_binary_io(self) -> None:
        with self.simple_file.open("rb") as xml_in:
            self.assertEqual(parse_xml(xml_in), {"a": {"_": "data"}})

    def test_cdata_key(self) -> None:
        self.assertEqual(
            parse_xml("<a>data</a>", parse_opts=ParseXmlOpts(cdata_key="#text")),
            {"a": {"#text": "data"}},
        )

    def test_parse_filter(self) -> None:
        def filter_parse(element, parent, opts):
            return {} if element.tag == "b" else None

        self.assertEqual(
            parse_xml("<a><b>ignore</b><c>include</c></a>", parse_filter=filter_parse),
            {"a": {"c": {"_": "include"}}},
        )

    def test_after_parse(self) -> None:
        def after_parse(parsed_dict, tree, opts):
            a_dict = parsed_dict["a"]
            a_dict["after"] = "parse"
            return parsed_dict

        self.assertEqual(
            parse_xml("<a>data</a>", after_parse_xml=after_parse),
            {"a": {"_": "data", "after": "parse"}},
        )

    def test_list(self) -> None:
        self.assertEqual(
            parse_xml("<a><b>1</b><b>2</b><b>3</b></a>"),
            {"a": {"b": [{"_": "1"}, {"_": "2"}, {"_": "3"}]}},
        )

    def test_attrib(self) -> None:
        self.assertEqual(parse_xml('<a href="xyz"/>'), {"a": {"href": "xyz"}})

    def test_attrib_and_cdata(self) -> None:
        self.assertEqual(
            parse_xml('<a href="xyz">123</a>'), {"a": {"href": "xyz", "_": "123"}}
        )

    def test_semi_structured(self) -> None:
        self.assertEqual(parse_xml("<a>abc<b/>def</a>"), {"a": {"_": "abcdef"}})

    def test_nested_semi_structured(self) -> None:
        self.assertEqual(
            parse_xml("<a>abc<b>123<c/>456</b>def</a>"),
            {"a": {"_": "abcdef", "b": {"_": "123456"}}},
        )

    def test_sanitize_text(self) -> None:
        xml = """
        <root>  This text spans
            multiple lines, that should be sanitized.
            Line with trailing space </root>
        """
        self.assertEqual(
            parse_xml(xml),
            {
                "root": {
                    "_": "This text spans multiple lines, that should be sanitized. Line with trailing space"
                }
            },
        )

    def test_ignore_whitespace(self) -> None:
        xml = """
        <root>


          <emptya>           </emptya>
          <emptyb attr="attrvalue">


          </emptyb>
          <value>hello</value>
        </root>
        """
        self.assertEqual(
            parse_xml(xml),
            {"root": {"emptyb": {"attr": "attrvalue"}, "value": {"_": "hello"}}},
        )

    def test_keep_empty_root(self) -> None:
        self.assertEqual(parse_xml("<root></root>"), {"root": {}})

    def test_keep_blank_root(self) -> None:
        self.assertEqual(parse_xml("<root>      </root>"), {"root": {}})

    def test_namespace(self) -> None:
        xml = """
        <root xmlns="http://defaultns.com/"
              xmlns:a="http://a.com/"
              xmlns:b="http://b.com/"
              version="1.00">
          <x>1</x>
          <a:y>2</a:y>
          <b:z>3</b:z>
        </root>
        """
        d = {
            "root": {
                "xmlns": "http://defaultns.com/",
                "xmlns_a": "http://a.com/",
                "xmlns_b": "http://b.com/",
                "version": "1.00",
                "x": {"_": "1"},
                "a_y": {"_": "2"},
                "b_z": {"_": "3"},
            },
        }
        self.assertEqual(parse_xml(xml), d)

    def test_ignores_xmlbomb(self) -> None:
        xml = """
        <!DOCTYPE xmlbombz [
            <!ENTITY a "1234567890" >
            <!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">
        ]>
        <bomb>&b;</bomb>
        """
        self.assertEqual(parse_xml(xml), {"bomb": {}})

    def test_ignores_external_dtd(self) -> None:
        xml = """
        <!DOCTYPE external [
            <!ENTITY ee SYSTEM "http://www.python.org/">
        ]>
        <root>&ee;</root>
        """
        self.assertEqual(parse_xml(xml), {"root": {}})

    def test_ignores_xml_declaration(self) -> None:
        xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><root/>"""
        self.assertEqual(parse_xml(xml), {"root": {}})

    def test_ignores_xml_stylesheet(self) -> None:
        xml = """<?xml-stylesheet type="text/xsl" href="CDA.xsl"?><root/>"""
        self.assertEqual(parse_xml(xml), {"root": {}})

    def test_ignores_comments(self) -> None:
        xml = """
        <!-- pre comment -->
        <a>
          <b>
            <!-- b comment -->
            <c>
                1
                <!-- c comment -->
            </c>
            <d><!-- d comment -->2</d>
            <e>3<!-- e comment -->4<!-- e comment -->5</e>
            <f><!-- f comment --></f>
          </b>
        </a>
        <!-- post comment -->
        """
        self.assertEqual(
            parse_xml(xml),
            {
                "a": {
                    "b": {
                        "c": {"_": "1"},
                        "d": {"_": "2"},
                        "e": {"_": "345"},
                    }
                }
            },
        )

class Hl7v2DataParserTest(TestCase):
    def test_parse_hl7v2(self) -> None:
        hl7v2_str = ("""MSH|^~\&|ADTApp|GHHSFacility^2.16.840.1.122848.1.30^ISO|EHRApp^1.Edu^ISO|GHHRFacility^2.16.840.1.1122848.1.32^ISO|198908181126+0215|SECURITY|ADT^A01^ADT_A01|MSG00001|P|2.8|||||USA||en-US|||22 GHH Inc.|23 GHH Inc.|24GHH^2.16.840.1.114884.10.20^ISO|25GHH^2.16.840.1.114884.10.23^ISO
EVN|A01|20290801070624+0115|20290801070724|01^Patient request^HL70062|C08^Woolfson^Kathleen^2ndname^Jr^Dr^MD^^DRNBR&1.3.6.1.4.1.44750.1.2.2&ISO^L^^^ANON|20210817151943.4+0200|Cona_Health^1.3.6.1.4.1.44750.1.4^ISO
PID|1|1234567^4^M11^test^MR^University Hospital^19241011^19241012|PATID1234^5^M11^test1&2.16.1&HCD^MR^GOOD HEALTH HOSPITAL~123456789^^^USSSA^SS|PATID567^^^test2|EVERYMAN&&&&Aniston^ADAM^A^III^Dr.^MD^D^^^19241012^^^^PF^Addsm~Josh&&&&Bing^^stanley^^^^L^^^^^19241010^19241015|SMITH^Angela^L|198808181126+0215|M|elbert^Son|2106-3^White^HL70005~2028-9^Asian^HL70005|1000&Hospital Lane^Ste. 123^Ann Arbor ^MI^99999^USA^M^^&W^^^20000110&20000120^^^^^^^Near Highway|GL|78788788^^CP^5555^^^1111^^^^^2222^20010110^20020110^^^^18~12121212^^CP|7777^^CP~1111^^TDD|ara^^HL70296^eng^English-us^HL70296^v2^v2.1^TextInEnglish|M^Married|AME|4000776^^^AccMgr&1.3.6.1.4.1.44750.1.2.2&ISO^VN^1^19241011^19241012|PSSN123121234|DLN-123^US^20010123|1212121^^^NTH&rt23&HCD^AND^^19241011^19241012|N^NOT HISPANIC OR LATINO^HL70189|St. Francis Community Hospital of Lower South Side|N|2|US^United States of America^ISO3166_1|Vet123^retired^ART|BT^Bhutan^ISO3166_1|20080825111630+0115|Y|||20050110015014+0315||125097000^Goat^SCT|4880003^Beagle^SCT|||CA^Canada^ISO3166_1|89898989^WPN^Internet
PV1|1|P|HUH AE OMU&9.8&ISO^OMU B^Bed 03^HOMERTON UNIVER^^C^Homerton UH^Floor5|E|1234567^4^M11^t&2.16.840.1.113883.19&HCD^ANON^University Hospital^19241011^19241012|4 East, room 136, bed B 4E^136^B^CommunityHospital^^N^^^|1122334^Alaz^Mohammed^Mahi^JR^Dr.^MD^^PERSONNELt&1.23&HCD^B^^^BR^^^^^^19241010^19241015^Al|C006^Woolfson^Kathleen^^^Dr^^^TEST&23.2&HCD^MSK^^^BA|C008^Condoc^leen^^^Dr^^^&1.3.6.1.4.1.44750.1.2.2&ISO^NAV^^^BR|SUR|||R|NHS Provider-General (inc.A\T\E-this Hosp)||VIP^Very Important Person^L^IMP^^DCM^v1.1^v1.2^Inportant Person|37^DISNEY^WALT^^^^^^AccMgr^^^^ANC|Inpatient|40007716^^^AccMng&1.2&HCD^AM|||||||||||||||||Admitted as Inpatient^Sample^ACR|22&Homes&FDK|Vegan^Vegetarian|HOMERTON UNIVER||Active|POC^Room-2^Bed-103^^^C^Greenland|Nursing home^^^^^^Rosewood|20150208113419+0110||||||50^^^T123&1.3.6.1.4.1.44750.1.2.2&ISO^MR||Othhel^^^^^^^^testing&&HCD||EOC124^5^M11^Etest&2.16.1&HCD^MR^CommunityHospital""")
        hl7v2_parser = Hl7v2DataParser()
        hl7v2_data = hl7v2_parser.parse(hl7v2_str)

        self.assertEqual(hl7v2_str, hl7v2_data.message)
        # assert meta data = [MSH, EVN, PID, PV1]
        meta_data = ["MSH", "EVN", "PID", "PV1"]
        self.assertEqual(meta_data, hl7v2_data.meta)

        # assert encoding_chars = ["^", "~", "&", "\\", "|"]
        self.assertEqual("^", hl7v2_data.encoding_characters.component_separator)
        self.assertEqual("~", hl7v2_data.encoding_characters.repetition_separator)
        self.assertEqual("\\", hl7v2_data.encoding_characters.escape_character)
        self.assertEqual("&", hl7v2_data.encoding_characters.subcomponent_separator)

        # TODO: assert message_header = MSH
