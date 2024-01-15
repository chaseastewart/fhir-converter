from unittest import TestCase

from liquid import BoundTemplate, DictLoader, Environment
from liquid.ast import ChildNode
from liquid.exceptions import LiquidSyntaxError, TemplateNotFound
from liquid.expression import Identifier, IdentifierPathElement, StringLiteral
from pytest import raises

from fhir_converter.tags import EvaluateNode, all_tags, register_tags


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

    def get_template(self, source: str, register: bool = True) -> BoundTemplate:
        env = Environment(loader=self.loader)
        if register:
            register_tags(env, all_tags)
        return env.from_string(source)

    def test_unregistered(self) -> None:
        with raises(LiquidSyntaxError):
            self.get_template(source=self.no_arg, register=False).render()

    def test_template_not_found(self) -> None:
        with raises(TemplateNotFound):
            self.get_template(source=self.not_found).render()

    def test_missing_keyword(self) -> None:
        with raises(LiquidSyntaxError):
            self.get_template(source=self.missing_keyword).render()

    def test_missing_comma(self) -> None:
        with raises(LiquidSyntaxError):
            self.get_template(source=self.missing_comma).render(val1="test", val2="ok")

    def test_no_arg(self) -> None:
        template = self.get_template(source=self.no_arg)
        self.assertEqual(len(template.tree.statements), 2)

        node = template.tree.statements[0]
        self.assertIsInstance(node, EvaluateNode)
        self.assertEqual(
            repr(node),
            "EvaluateNode(tok=Token(linenum=1, type='tag', value='evaluate'), name=var)",
        )
        self.assertEqual(str(node), "evaluate(var using 'no_arg')")
        self.assertEqual(
            node.children(),
            [
                ChildNode(
                    linenum=1,
                    expression=StringLiteral(value="no_arg"),
                    template_scope=["var"],
                    block_scope=[],
                    load_mode="include",
                    load_context={"tag": "evaluate"},
                )
            ],
        )

        self.assertEqual(template.render(), "ok")

    def test_single_arg(self) -> None:
        template = self.get_template(source=self.single_arg)
        self.assertEqual(len(template.tree.statements), 2)

        node = template.tree.statements[0]
        self.assertIsInstance(node, EvaluateNode)
        self.assertEqual(str(node), "evaluate(var using 'single_arg', arg1=val)")
        self.assertEqual(
            node.children(),
            [
                ChildNode(
                    linenum=1,
                    expression=StringLiteral(value="single_arg"),
                    template_scope=["var"],
                    block_scope=["arg1"],
                    load_mode="include",
                    load_context={"tag": "evaluate"},
                ),
                ChildNode(
                    linenum=1,
                    expression=Identifier(path=[IdentifierPathElement(value="val")]),
                ),
            ],
        )

        self.assertEqual(template.render(val="test"), "test")

    def test_multiple_args(self) -> None:
        template = self.get_template(source=self.multi_arg)
        self.assertEqual(len(template.tree.statements), 2)

        node = template.tree.statements[0]
        self.assertIsInstance(node, EvaluateNode)
        self.assertEqual(
            str(node),
            "evaluate(var using 'multi_arg', arg1=val1, arg2=val2)",
        )
        self.assertEqual(
            node.children(),
            [
                ChildNode(
                    linenum=1,
                    expression=StringLiteral(value="multi_arg"),
                    template_scope=["var"],
                    block_scope=["arg1", "arg2"],
                    load_mode="include",
                    load_context={"tag": "evaluate"},
                ),
                ChildNode(
                    linenum=1,
                    expression=Identifier(path=[IdentifierPathElement(value="val1")]),
                ),
                ChildNode(
                    linenum=1,
                    expression=Identifier(path=[IdentifierPathElement(value="val2")]),
                ),
            ],
        )

        self.assertEqual(template.render(val1="test", val2="ok"), "test, ok")
