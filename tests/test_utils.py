from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from pyexpat import ExpatError
from pyjson5 import Json5EOF
from pytest import raises

from fhir_converter.hl7 import get_ccda_section
from fhir_converter.utils import (
    blank_str_to_empty,
    del_empty_dirs_quietly,
    del_path_quietly,
    is_none_or_empty,
    join_subpath,
    merge_dict,
    mkdir,
    parse_json,
    parse_xml,
    to_list_or_empty,
    walk_path,
)


class IsNoneOrEmptyTest(TestCase):
    def test_none(self) -> None:
        self.assertTrue(is_none_or_empty(None))

    def test_false(self) -> None:
        self.assertFalse(is_none_or_empty(False))

    def test_true(self) -> None:
        self.assertFalse(is_none_or_empty(True))

    def test_zero(self) -> None:
        self.assertFalse(is_none_or_empty(0))

    def test_one(self) -> None:
        self.assertFalse(is_none_or_empty(1))

    def test_str_empty(self) -> None:
        self.assertTrue(is_none_or_empty(""))

    def test_str_blank(self) -> None:
        self.assertTrue(is_none_or_empty(" "))

    def test_str(self) -> None:
        self.assertFalse(is_none_or_empty("test"))

    def test_list_empty(self) -> None:
        self.assertTrue(is_none_or_empty([]))

    def test_list(self) -> None:
        self.assertFalse(is_none_or_empty(["test"]))

    def test_tuple_empty(self) -> None:
        self.assertTrue(is_none_or_empty(()))

    def test_tuple(self) -> None:
        self.assertFalse(is_none_or_empty(("test", "ok")))

    def test_dict_empty(self) -> None:
        self.assertTrue(is_none_or_empty({}))

    def test_dict(self) -> None:
        self.assertFalse(is_none_or_empty({"test": "ok"}))


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


class ParseJsonTest(TestCase):
    def test_empty(self) -> None:
        with raises(Json5EOF):
            parse_json("")

    def test_blank(self) -> None:
        with raises(Json5EOF):
            parse_json(" ")

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

    def test_dict_str(self) -> None:
        self.assertEqual({"test": "ok"}, parse_json('{"test": "ok"}'))

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


class ParseXmlTest(TestCase):
    def test_empty_str(self) -> None:
        with raises(ExpatError):
            parse_xml("")

    def test_blank_str(self) -> None:
        with raises(ExpatError):
            parse_xml(" ")

    def test_empty_file(self) -> None:
        with raises(ExpatError):
            with Path("tests/data/bad_data/empty.ccda").open() as xml_in:
                parse_xml(xml_in)

    def test_empty_file_binary(self) -> None:
        with raises(ExpatError):
            with Path("tests/data/bad_data/empty.ccda").open("rb") as xml_in:
                parse_xml(xml_in)

    def test_file(self) -> None:
        with Path("tests/data/ccda/CCD.ccda").open() as xml_in:
            xml = parse_xml(xml_in)
        self.assertIn("ClinicalDocument", xml)
        self.assertIsNotNone(
            get_ccda_section(xml, search_template_ids="2.16.840.1.113883.10.20.22.2.6.1")
        )

    def test_file_binary(self) -> None:
        with Path("tests/data/ccda/CCD.ccda").open("rb") as xml_in:
            xml = parse_xml(xml_in)
        self.assertIn("ClinicalDocument", xml)
        self.assertIsNotNone(
            get_ccda_section(xml, search_template_ids="2.16.840.1.113883.10.20.22.2.6.1")
        )


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
        self.assertSequenceEqual(["CCD.ccda", "sample.ccda"], sorted(filenames))

        with raises(StopIteration):
            next(walk)
