from io import BytesIO, StringIO
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from liquid import Undefined
from lxml import etree
from pytest import raises

from fhir_converter.utils import (
    blank_str_to_empty,
    del_empty_dirs_quietly,
    del_path_quietly,
    etree_element_to_str,
    etree_to_str,
    is_undefined_none_or_blank,
    join_strs,
    join_subpath,
    load_xslt,
    merge_dict,
    mkdir,
    parse_etree,
    sanitize_str,
    tail,
    to_list_or_empty,
    transform_xml_str,
    walk_path,
)


class SanitizeStrTest(TestCase):
    def test_none(self) -> None:
        self.assertEqual(sanitize_str(None), "")

    def test_empty_str(self) -> None:
        self.assertEqual(sanitize_str(""), "")

    def test_leading_trailing(self) -> None:
        self.assertEqual(sanitize_str("  test  "), "test")

    def test_consecutive_spaces(self) -> None:
        self.assertEqual(sanitize_str("test    test"), "test test")

    def test_tabs(self) -> None:
        self.assertEqual(sanitize_str("test\t\ttest"), "test test")

    def test_line_endings(self) -> None:
        self.assertEqual(sanitize_str("\ntest\r\ntest\n"), "test test")

    def test_mixed(self) -> None:
        self.assertEqual(sanitize_str(" \t\ntest\r\n\t         test\n\t "), "test test")


class JoinStrsTest(TestCase):
    def test_none(self) -> None:
        self.assertEqual(join_strs(None, None), "")

    def test_empty_strs(self) -> None:
        self.assertEqual(join_strs("", ""), "")

    def test_blank_strs(self) -> None:
        self.assertEqual(join_strs("", " "), " ")
        self.assertEqual(join_strs(" ", ""), " ")
        self.assertEqual(join_strs(" ", " "), " _ ")

    def test_a(self) -> None:
        self.assertEqual(join_strs("a", None), "a")
        self.assertEqual(join_strs("a", ""), "a")

    def test_b(self) -> None:
        self.assertEqual(join_strs(None, "b"), "b")
        self.assertEqual(join_strs("", "b"), "b")

    def test_a_b(self) -> None:
        self.assertEqual(join_strs("a", "b"), "a_b")

    def test_sep(self) -> None:
        self.assertEqual(join_strs("a", "b", sep="|"), "a|b")


class IsUndefinedNoneOrBlankTest(TestCase):
    def test_undefined(self) -> None:
        self.assertTrue(is_undefined_none_or_blank(Undefined("")))

    def test_none(self) -> None:
        self.assertTrue(is_undefined_none_or_blank(None))

    def test_false(self) -> None:
        self.assertFalse(is_undefined_none_or_blank(False))

    def test_true(self) -> None:
        self.assertFalse(is_undefined_none_or_blank(True))

    def test_zero(self) -> None:
        self.assertFalse(is_undefined_none_or_blank(0))

    def test_one(self) -> None:
        self.assertFalse(is_undefined_none_or_blank(1))

    def test_str_empty(self) -> None:
        self.assertTrue(is_undefined_none_or_blank(""))

    def test_str_blank(self) -> None:
        self.assertTrue(is_undefined_none_or_blank(" "))

    def test_str(self) -> None:
        self.assertFalse(is_undefined_none_or_blank("test"))

    def test_list_empty(self) -> None:
        self.assertTrue(is_undefined_none_or_blank([]))

    def test_list(self) -> None:
        self.assertFalse(is_undefined_none_or_blank(["test"]))

    def test_tuple_empty(self) -> None:
        self.assertTrue(is_undefined_none_or_blank(()))

    def test_tuple(self) -> None:
        self.assertFalse(is_undefined_none_or_blank(("test", "ok")))

    def test_dict_empty(self) -> None:
        self.assertTrue(is_undefined_none_or_blank({}))

    def test_dict(self) -> None:
        self.assertFalse(is_undefined_none_or_blank({"test": "ok"}))

    def test_set_empty(self) -> None:
        self.assertTrue(is_undefined_none_or_blank(set()))

    def test_set(self) -> None:
        self.assertFalse(is_undefined_none_or_blank(set("ok")))


class ToListOrEmptyTest(TestCase):
    def test_none(self) -> None:
        self.assertEqual([], to_list_or_empty(None))

    def test_false(self) -> None:
        self.assertEqual([False], to_list_or_empty(False))

    def test_true(self) -> None:
        self.assertEqual([True], to_list_or_empty(True))

    def test_str_empty(self) -> None:
        self.assertEqual([], to_list_or_empty(""))

    def test_str_blank(self) -> None:
        self.assertEqual([], to_list_or_empty(" "))

    def test_str(self) -> None:
        self.assertEqual(["test"], to_list_or_empty("test"))

    def test_list_empty(self) -> None:
        self.assertEqual([], to_list_or_empty([]))

    def test_list(self) -> None:
        self.assertEqual([False], to_list_or_empty([False]))

    def test_dict_empty(self) -> None:
        self.assertEqual([], to_list_or_empty({}))

    def test_dict(self) -> None:
        self.assertEqual([{"test": "ok"}], to_list_or_empty({"test": "ok"}))


class BlankStrToEmptyTest(TestCase):
    def test_empty(self) -> None:
        self.assertEqual("", blank_str_to_empty(""))

    def test_blank(self) -> None:
        self.assertEqual("", blank_str_to_empty(" "))

    def test_not_blank(self) -> None:
        self.assertEqual("test", blank_str_to_empty("test"))


class MergeDictTest(TestCase):
    def test_empty(self) -> None:
        self.assertEqual({}, merge_dict({}, {}))

    def test_mapping_update_none(self) -> None:
        a = {"FirstName": None}
        b = {"FirstName": "Alex"}
        expected = {"FirstName": "Alex"}
        self.assertEqual(expected, merge_dict(a, b))

    def test_mapping_update_value(self) -> None:
        a = {"FirstName": "John"}
        b = {"FirstName": "Alex"}
        expected = {"FirstName": "Alex"}
        self.assertEqual(expected, merge_dict(a, b))

    def test_mapping_update_with_empty_value(self) -> None:
        a = {"FirstName": "John"}
        b = {"FirstName": ""}
        expected = {"FirstName": ""}
        self.assertEqual(expected, merge_dict(a, b))

    def test_mapping_update_type(self) -> None:
        a = {"NickNames": "Johnny"}
        b = {"NickNames": ["Slick", "Johnny"]}
        expected = {"NickNames": ["Slick", "Johnny"]}
        self.assertEqual(expected, merge_dict(a, b))

    def test_mapping_update_ignore_none(self) -> None:
        a = {"FirstName": "John"}
        b = {"FirstName": None}
        expected = {"FirstName": "John"}
        self.assertEqual(expected, merge_dict(a, b))

    def test_mapping_equal(self) -> None:
        a = {"FirstName": "John"}
        b = {"FirstName": "John"}
        expected = {"FirstName": "John"}
        self.assertEqual(expected, merge_dict(a, b))

    def test_add_mapping(self) -> None:
        a = {"FirstName": "John"}
        b = {"LastName": "Smith"}
        expected = {"FirstName": "John", "LastName": "Smith"}
        self.assertEqual(expected, merge_dict(a, b))

    def test_add_mapping_empty_str(self) -> None:
        a = {"FirstName": "John"}
        b = {"LastName": ""}
        expected = {"FirstName": "John", "LastName": ""}
        self.assertEqual(expected, merge_dict(a, b))

    def test_add_mapping_ignore_none(self) -> None:
        a = {"FirstName": "John"}
        b = {"LastName": None}
        expected = {"FirstName": "John"}
        self.assertEqual(expected, merge_dict(a, b))

    def test_concat_list(self) -> None:
        a = {"NickNames": ["Johnny"]}
        b = {"NickNames": ["Slick", "Johnny", "Jon"]}
        expected = {"NickNames": ["Johnny", "Slick", "Jon"]}
        self.assertEqual(expected, merge_dict(a, b))

    def test_update_list(self) -> None:
        a: dict = {"NickNames": []}
        b: dict = {"NickNames": ["Slick", "Johnny", "Jon"]}
        expected = {"NickNames": ["Slick", "Johnny", "Jon"]}
        self.assertEqual(expected, merge_dict(a, b))

    def test_ignore_empty_list(self) -> None:
        a: dict = {"NickNames": ["Slick", "Johnny", "Jon"]}
        b: dict = {"NickNames": []}
        expected = {"NickNames": ["Slick", "Johnny", "Jon"]}
        self.assertEqual(expected, merge_dict(a, b))


class JoinSubpathTest(TestCase):
    def test_parent_is_file(self) -> None:
        with raises(ValueError):
            join_subpath(
                Path("data/out"),
                parent=Path("data/sample/ccd.ccda"),
                child=Path("data/sample/sample.ccda"),
            )

    def test_not_subdirectory(self) -> None:
        with raises(ValueError):
            join_subpath(
                Path("data/out"),
                parent=Path("data/sample"),
                child=Path("data/templates/sample.ccda"),
            )

    def test_child_is_parent(self) -> None:
        with raises(ValueError):
            join_subpath(
                Path("data/out"),
                parent=Path("data/sample"),
                child=Path("data"),
            )

    def test_root(self) -> None:
        path = join_subpath(
            Path("data/out"), parent=Path("data/sample"), child=Path("data/sample")
        )
        self.assertEqual(Path("data/out"), path)

    def test_root_file(self) -> None:
        path = join_subpath(
            Path("data/out"),
            parent=Path("data/sample"),
            child=Path("data/sample/ccd.ccda"),
        )
        self.assertEqual(Path("data/out"), path)

    def test_subdirectory(self) -> None:
        path = join_subpath(
            Path("data/out"), parent=Path("data/sample"), child=Path("data/sample/ccda")
        )
        self.assertEqual(Path("data/out/ccda"), path)

    def test_subdirectory_file(self) -> None:
        path = join_subpath(
            Path("data/out"),
            parent=Path("data/sample"),
            child=Path("data/sample/ccda/ccd.ccda"),
        )
        self.assertEqual(Path("data/out/ccda"), path)

    def test_nested_directory(self) -> None:
        path = join_subpath(
            Path("data/out"),
            parent=Path("tests/data"),
            child=Path("tests/data/nested/ccda"),
        )
        self.assertEqual(Path("data/out/nested/ccda"), path)

    def test_nested_directory_file(self) -> None:
        path = join_subpath(
            Path("data/out"),
            parent=Path("tests/data"),
            child=Path("tests/data/nested/ccda/ccd.ccda"),
        )
        self.assertEqual(Path("data/out/nested/ccda"), path)


class DelEmptyDirsQuietlyTest(TestCase):
    @patch.object(Path, "is_dir", return_value=True)
    @patch.object(Path, "rmdir", return_value=None)
    @patch("fhir_converter.utils.os_walk", return_value=[(Path(), [], [])])
    def test_dir_empty(self, os_walk_mock, rmdir_mock, is_dir_mock) -> None:
        del_empty_dirs_quietly(Path())
        os_walk_mock.assert_called_once()
        rmdir_mock.assert_not_called()
        is_dir_mock.assert_not_called()

    @patch.object(Path, "is_dir", return_value=True)
    @patch.object(Path, "rmdir", return_value=None)
    @patch(
        "fhir_converter.utils.os_walk",
        return_value=[(Path(), ["test"], []), (Path("test/"), [], [])],
    )
    def test_del_empty_dir(self, os_walk_mock, rmdir_mock, is_dir_mock) -> None:
        del_empty_dirs_quietly(Path())
        os_walk_mock.assert_called_once()
        rmdir_mock.assert_called_once()
        is_dir_mock.assert_called_once()

    @patch.object(Path, "is_dir", return_value=True)
    @patch.object(Path, "rmdir", side_effect=OSError)
    @patch(
        "fhir_converter.utils.os_walk",
        return_value=[(Path(), ["test"], []), (Path("test/"), [], [])],
    )
    def test_del_empty_dir_ignore_error(
        self, os_walk_mock, rmdir_mock, is_dir_mock
    ) -> None:
        del_empty_dirs_quietly(Path())
        os_walk_mock.assert_called_once()
        rmdir_mock.assert_called_once()
        is_dir_mock.assert_called_once()


class DelPathQuietlyTest(TestCase):
    @patch.object(Path, "is_dir", return_value=True)
    @patch.object(Path, "rmdir", return_value=None)
    def test_del_dir(self, rmdir_mock, is_dir_mock) -> None:
        del_path_quietly(Path())
        rmdir_mock.assert_called_once()
        is_dir_mock.assert_called_once()

    @patch.object(Path, "is_dir", return_value=True)
    @patch.object(Path, "rmdir", side_effect=OSError)
    def test_del_dir_ignore_error(self, rmdir_mock, is_dir_mock) -> None:
        del_path_quietly(Path())
        rmdir_mock.assert_called_once()
        is_dir_mock.assert_called_once()

    @patch.object(Path, "is_dir", return_value=False)
    @patch.object(Path, "rmdir", return_value=None)
    @patch("fhir_converter.utils.os_remove", return_value=None)
    def test_del_file(self, os_remove_mock, rmdir_mock, is_dir_mock) -> None:
        del_path_quietly(Path())
        rmdir_mock.assert_not_called()
        is_dir_mock.assert_called_once()
        os_remove_mock.assert_called_once()

    @patch.object(Path, "is_dir", return_value=False)
    @patch.object(Path, "rmdir", return_value=None)
    @patch("fhir_converter.utils.os_remove", side_effect=OSError)
    def test_del_file_ignore_error(self, os_remove_mock, rmdir_mock, is_dir_mock) -> None:
        del_path_quietly(Path())
        rmdir_mock.assert_not_called()
        is_dir_mock.assert_called_once()
        os_remove_mock.assert_called_once()


class MkdirTest(TestCase):
    @patch.object(Path, "is_dir", return_value=True)
    @patch.object(Path, "mkdir", return_value=None)
    def test_dir_exists(self, mkdir_mock, is_dir_mock) -> None:
        self.assertFalse(mkdir(Path()))
        mkdir_mock.assert_not_called()
        is_dir_mock.assert_called_once()

    @patch.object(Path, "is_dir", return_value=False)
    @patch.object(Path, "mkdir", return_value=None)
    def test_create_dir(self, mkdir_mock, is_dir_mock) -> None:
        self.assertTrue(mkdir(Path()))
        mkdir_mock.assert_called_once()
        is_dir_mock.assert_called_once()

    @patch.object(Path, "is_dir", return_value=False)
    @patch.object(Path, "mkdir", return_value=None)
    def test_create_dir_with_args(self, mkdir_mock, is_dir_mock) -> None:
        self.assertTrue(mkdir(Path(), parents=False))
        mkdir_mock.assert_called_once_with(parents=False)
        is_dir_mock.assert_called_once()

    @patch.object(Path, "is_dir", return_value=False)
    @patch.object(Path, "mkdir", side_effect=OSError)
    def test_create_dir_raise(self, mkdir_mock, is_dir_mock) -> None:
        with raises(OSError):
            mkdir(Path())
        mkdir_mock.assert_called_once()
        is_dir_mock.assert_called_once()


class WalkPathTest(TestCase):
    def test_invalid_path(self) -> None:
        with raises(StopIteration):
            next(walk_path(Path("data/invalid")))

    def test_empty_path(self) -> None:
        with raises(StopIteration):
            next(walk_path(Path("data/empty")))

    def test_walk_path(self) -> None:
        walk = walk_path(Path("tests/data/ccda"))
        root, dirs, filenames = next(walk)
        self.assertEqual(Path("tests/data/ccda"), root)
        self.assertEqual([], dirs)
        self.assertSequenceEqual(
            ["CCD.ccda", "History_and_Physical.ccda", "sample.ccda"], sorted(filenames)
        )

        with raises(StopIteration):
            next(walk)


class TailTest(TestCase):
    def test_empty_text(self) -> None:
        buffer = StringIO()
        self.assertEqual("", tail(buffer))

    def test_empty_bytes(self) -> None:
        buffer = BytesIO()
        self.assertEqual("", tail(buffer))

    def test_read_all_text(self) -> None:
        buffer = StringIO()
        buffer.write("This is a test.")
        self.assertEqual("This is a test.", tail(buffer))

    def test_read_last_n_text(self) -> None:
        buffer = StringIO()
        buffer.write("This is a test.")
        self.assertEqual("st.", tail(buffer, last_n=3))

    def test_read_last_n_is_negative(self) -> None:
        buffer = StringIO()
        buffer.write("This is a test.")
        self.assertEqual("", tail(buffer, last_n=-3))

    def test_read_last_n_is_zero(self) -> None:
        buffer = StringIO()
        buffer.write("This is a test.")
        self.assertEqual("", tail(buffer, last_n=0))

    def test_read_all_bytes(self) -> None:
        buffer = BytesIO()
        buffer.write(b"This is a test.")
        self.assertEqual("This is a test.", tail(buffer))

    def test_read_last_n_bytes(self) -> None:
        buffer = BytesIO()
        buffer.write(b"This is a test.")
        self.assertEqual("st.", tail(buffer, last_n=3))


class ParseEtreeTest(TestCase):
    def _validate(self, tree) -> None:
        self.assertIsNotNone(tree)
        root = tree.getroot()
        self.assertIsNotNone(root)
        self.assertEqual("root", root.tag)
        self.assertEqual("simple", root.text)

    def test_empty_text(self) -> None:
        with raises(etree.XMLSyntaxError):
            parse_etree("")

    def test_blank_text(self) -> None:
        with raises(etree.XMLSyntaxError):
            parse_etree(" ")

    def test_empty_bytes(self) -> None:
        with raises(etree.XMLSyntaxError):
            parse_etree(bytes())

    def test_empty_text_io(self) -> None:
        with raises(etree.XMLSyntaxError):
            parse_etree(StringIO())

    def test_empty_binary_io(self) -> None:
        with raises(etree.XMLSyntaxError):
            parse_etree(BytesIO())

    def test_str(self) -> None:
        self._validate(parse_etree("<root>simple</root>"))

    def test_bytes(self) -> None:
        self._validate(parse_etree(b"<root>simple</root>"))

    def test_text_io(self) -> None:
        self._validate(parse_etree(StringIO("<root>simple</root>")))

    def test_binary_io(self) -> None:
        self._validate(parse_etree(BytesIO(b"<root>simple</root>")))


class EtreeToStrTest(TestCase):
    tree = parse_etree("<root>simple</root>")

    def test_defaults(self) -> None:
        self.assertEqual(etree_to_str(self.tree), "<root>simple</root>")

    def test_encoding(self) -> None:
        self.assertEqual(
            sanitize_str(
                etree_to_str(self.tree, encoding="UTF-16"),
                repl="",
            ),
            "<?xml version='1.0' encoding='UTF-16'?><root>simple</root>",
        )

    def test_standalone(self) -> None:
        self.assertEqual(
            sanitize_str(
                etree_to_str(self.tree, encoding="UTF-8", standalone=True),
                repl="",
            ),
            "<?xml version='1.0' encoding='UTF-8' standalone='yes'?><root>simple</root>",
        )


class EtreeElementToStrTest(TestCase):
    element = parse_etree("<root>simple</root>").getroot()

    def test_defaults(self) -> None:
        self.assertEqual(
            etree_element_to_str(self.element),
            "<root>simple</root>",
        )

    def test_encoding(self) -> None:
        self.assertEqual(
            sanitize_str(
                etree_element_to_str(self.element, encoding="UTF-16"),
                repl="",
            ),
            "<?xml version='1.0' encoding='UTF-16'?><root>simple</root>",
        )

    def test_standalone(self) -> None:
        self.assertEqual(
            sanitize_str(
                etree_element_to_str(self.element, encoding="UTF-8", standalone=True),
                repl="",
            ),
            "<?xml version='1.0' encoding='UTF-8' standalone='yes'?><root>simple</root>",
        )


class TransformXmlStrTest(TestCase):
    def test_output_text(self) -> None:
        stylesheet = """<?xml version="1.0"?>
            <xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
                <xsl:output method="text" encoding="ascii"/>
                <xsl:template match="/">
                    <xsl:value-of select="/root"/>
                </xsl:template>
            </xsl:stylesheet>
        """
        self.assertEqual(
            transform_xml_str(load_xslt(stylesheet), "<root>text</root>"),
            "text",
        )

    def test_output_xml(self) -> None:
        stylesheet = """<?xml version="1.0"?>
            <xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
                <xsl:output method="xml" encoding="utf-8" omit-xml-declaration="yes" indent="no"/>
                <xsl:template match="/">
                    <out>
                        <xsl:value-of select="/in"/>
                    </out>
                </xsl:template>
            </xsl:stylesheet>
        """
        self.assertEqual(
            transform_xml_str(load_xslt(stylesheet), "<in>text</in>"),
            "<out>text</out>",
        )
