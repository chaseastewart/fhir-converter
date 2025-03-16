from typing import Optional
from unittest import TestCase

from liquid import BaseLoader, BoundTemplate, DictLoader, Environment
from liquid.exceptions import LiquidSyntaxError, TemplateNotFoundError
from pyjson5 import Json5Exception
from pytest import raises

from fhir_converter.tags import EvaluateNode, MergeDiffNode, all_tags, register_tags


def get_template(
    source: str,
    register: bool = True,
    loader: Optional[BaseLoader] = None,
) -> BoundTemplate:
    env = Environment(loader=loader)
    if register:
        register_tags(env, all_tags)
    return env.from_string(source)


class MergeDiffTest(TestCase):
    missing_endmerge = "{% mergeDiff var -%}"
    missing_identifier = "{% mergeDiff -%}{% endmergeDiff -%}"
    block = "{% mergeDiff var -%}{{block}}{% endmergeDiff -%}"

    def test_unregistered(self) -> None:
        with raises(LiquidSyntaxError, match="unexpected tag 'mergeDiff'"):
            get_template(source=self.block, register=False).render()

    def test_missing_endmerge(self) -> None:
        with raises(
            LiquidSyntaxError,
            match="expected tag endmergeDiff, found end of expression",
        ):
            get_template(source=self.missing_endmerge).render()

    def test_missing_identifier(self) -> None:
        with raises(LiquidSyntaxError, match="missing expression"):
            get_template(source=self.missing_identifier).render()

    def test_invalid(self) -> None:
        with raises(Json5Exception):
            template = get_template(source=self.block)
            template.render(var={"test": "ok"}, block="{test:ok}")

    def test_empty(self) -> None:
        template = get_template(source=self.block)
        self.assertEqual(template.render(var={"test": "ok"}, block=""), '{"test":"ok"}')

    def test_space(self) -> None:
        template = get_template(source=self.block)
        self.assertEqual(
            template.render(var={"test": "ok"}, block=" "), '{"test":"ok"}'
        )

    def test_empty_quote(self) -> None:
        template = get_template(source=self.block)
        self.assertEqual(
            template.render(var={"test": "ok"}, block='""'), '{"test":"ok"}'
        )

    def test_str(self) -> None:
        template = get_template(source=self.block)
        self.assertEqual(
            template.render(var={"test": "ok"}, block='"failed"'),
            '{"test":"ok"}',
        )

    def test_variable_undefined(self) -> None:
        template = get_template(source=self.block)
        self.assertEqual(template.render(block={"test": "ok"}), "{}")

    def test_variable_str(self) -> None:
        template = get_template(source=self.block)
        self.assertEqual(template.render(var="ok", block={"test": "ok"}), '"ok"')

    def test_add(self) -> None:
        template = get_template(source=self.block)
        self.assertEqual(len(template.nodes), 1)

        node = template.nodes[0]
        self.assertIsInstance(node, MergeDiffNode)
        self.assertEqual(str(node), "{% mergeDiff var %}{{ block }}{% endmergeDiff %}")

        self.assertEqual(
            template.render(var={}, block={"test": "add"}), '{"test":"add"}'
        )

    def test_update(self) -> None:
        template = get_template(source=self.block)
        self.assertEqual(
            template.render(var={"test": "ok"}, block={"test": "update"}),
            '{"test":"update"}',
        )

    def test_remove(self) -> None:
        template = get_template(source=self.block)
        self.assertEqual(
            template.render(var={"test": "ok"}, block={"test": ""}), '{"test":""}'
        )

    def test_empty_dict(self) -> None:
        template = get_template(source=self.block)
        self.assertEqual(template.render(var={"test": "ok"}, block={}), '{"test":"ok"}')

    def test_empty_dicts(self) -> None:
        template = get_template(source=self.block)
        self.assertEqual(template.render(var={}, block={}), "{}")

    def test_choice_update(self) -> None:
        template = get_template(source=self.block)
        self.assertEqual(
            template.render(var={"test_first": "ok"}, block={"test[x]": "update"}),
            '{"test_first":"update"}',
        )

    def test_choice_update_first(self) -> None:
        template = get_template(source=self.block)
        self.assertEqual(
            template.render(
                var={"test_first": "ok", "test_second": "failed"},
                block={"test[x]": "update"},
            ),
            '{"test_first":"update","test_second":"failed"}',
        )

    def test_choice_remove(self) -> None:
        template = get_template(source=self.block)
        self.assertEqual(
            template.render(var={"test_first": "ok"}, block={"test[x]": ""}),
            '{"test_first":""}',
        )

    def test_choice_remove_first(self) -> None:
        template = get_template(source=self.block)
        self.assertEqual(
            template.render(
                var={"test_first": "ok", "test_second": "failed"}, block={"test[x]": ""}
            ),
            '{"test_first":"","test_second":"failed"}',
        )

    def test_choice_remove_multiple(self) -> None:
        template = get_template(source=self.block)
        self.assertEqual(
            template.render(
                var={"test_first": "ok", "test_second": "failed"},
                block={"test_f[x]": "", "test_s[x]": ""},
            ),
            '{"test_first":"","test_second":""}',
        )

    def test_choice_ignore(self) -> None:
        template = get_template(source=self.block)
        self.assertEqual(
            template.render(var={"other": "unknown"}, block={"test[x]": "ok"}),
            '{"other":"unknown"}',
        )


class EvaluateTest(TestCase):
    missing_keyword = "{% evaluate var 'nosuchthing' -%}"
    not_found = "{% evaluate var using 'nosuchthing' -%}"
    no_arg = "{% evaluate var using 'no_arg' -%}{{ var }}"
    single_arg = "{% evaluate var using 'single_arg' arg1: val -%}{{ var }}"
    missing_comma = "{% evaluate var using 'multi_arg' arg1: val1 arg2: val2 -%}"
    multi_arg = "{% evaluate var using 'multi_arg' arg1: val1, arg2: val2 -%}{{ var }}"

    loader = DictLoader(
        {
            "no_arg": "ok",
            "single_arg": "{{ arg1 }}",
            "multi_arg": "{{ arg1 }}, {{ arg2 }}",
        }
    )

    def test_unregistered(self) -> None:
        with raises(LiquidSyntaxError):
            get_template(source=self.no_arg, register=False).render()

    def test_template_not_found(self) -> None:
        with raises(TemplateNotFoundError):
            get_template(source=self.not_found).render()

    def test_missing_keyword(self) -> None:
        with raises(LiquidSyntaxError):
            get_template(source=self.missing_keyword).render()

    def test_missing_comma(self) -> None:
        with raises(LiquidSyntaxError):
            get_template(source=self.missing_comma).render(val1="test", val2="ok")

    def test_no_arg(self) -> None:
        template = get_template(source=self.no_arg, loader=self.loader)
        self.assertEqual(len(template.nodes), 2)

        node = template.nodes[0]
        self.assertIsInstance(node, EvaluateNode)
        self.assertEqual(str(node), "{% evaluate var using 'no_arg' %}")
        self.assertEqual(template.variables(), ["var"])
        self.assertEqual(template.render(), "ok")

    def test_single_arg(self) -> None:
        template = get_template(source=self.single_arg, loader=self.loader)
        self.assertEqual(len(template.nodes), 2)

        node = template.nodes[0]
        self.assertIsInstance(node, EvaluateNode)
        self.assertEqual(str(node), "{% evaluate var using 'single_arg' arg1:val %}")
        self.assertEqual(template.variables(), ["val", "arg1", "var"])
        self.assertEqual(template.render(val="test"), "test")

    def test_multiple_args(self) -> None:
        template = get_template(source=self.multi_arg, loader=self.loader)
        self.assertEqual(len(template.nodes), 2)

        node = template.nodes[0]
        self.assertIsInstance(node, EvaluateNode)

        self.assertEqual(
            str(node),
            "{% evaluate var using 'multi_arg' arg1:val1, arg2:val2 %}",
        )

        self.assertEqual(template.variables(), ["val1", "val2", "arg1", "arg2", "var"])
        self.assertEqual(template.render(val1="test", val2="ok"), "test, ok")
