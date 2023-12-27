from functools import partial
from sys import intern
from typing import Dict, List, Optional, TextIO, Tuple, Type

from liquid.ast import ChildNode, Node
from liquid.context import Context
from liquid.exceptions import LiquidSyntaxError
from liquid.expression import Expression
from liquid.expressions import TokenStream as ExprTokenStream
from liquid.expressions.common import (
    parse_string_or_identifier,
    parse_unchained_identifier,
)
from liquid.expressions.filtered.parse import parse_obj
from liquid.lex import _compile_rules, _tokenize, include_expression_rules
from liquid.parse import expect
from liquid.stream import TokenStream
from liquid.tag import Tag
from liquid.token import (
    TOKEN_BLANK,
    TOKEN_COLON,
    TOKEN_COMMA,
    TOKEN_EMPTY,
    TOKEN_EOF,
    TOKEN_EXPRESSION,
    TOKEN_FALSE,
    TOKEN_IDENTIFIER,
    TOKEN_NIL,
    TOKEN_NULL,
    TOKEN_TRUE,
    Token,
)

TAG_EVALUATE = intern("evaluate")
TOKEN_USING = intern("using")

evaluate_expression_keywords = frozenset(
    [
        TOKEN_TRUE,
        TOKEN_FALSE,
        TOKEN_NIL,
        TOKEN_NULL,
        TOKEN_EMPTY,
        TOKEN_BLANK,
        TOKEN_USING,
    ]
)

tokenize_evaluate_expression = partial(
    _tokenize,
    rules=_compile_rules(include_expression_rules),
    keywords=evaluate_expression_keywords,
)


class EvaluateNode(Node):
    """Parse tree node for the built-in "evaluate" tag."""

    __slots__ = ("tok", "name", "template_name", "args")
    tag = TAG_EVALUATE

    def __init__(
        self,
        tok: Token,
        name: str,
        template_name: Expression,
        args: Optional[Dict[str, Expression]] = None,
    ) -> None:
        self.tok = tok
        self.name = name
        self.template_name = template_name
        self.args = args or {}

    def __str__(self) -> str:
        buf = [f"{self.name}", f" using {self.template_name}"]

        if self.args:
            buf.append(", ")
        args = (f"{key}={val}" for key, val in self.args.items())
        buf.append(", ".join(args))

        return f"{self.tag}({''.join(buf)})"

    def __repr__(self) -> str:
        return f"EvaluateNode(tok={self.tok!r}, name={self.name})"

    def render_to_output(self, context: Context, _: TextIO) -> Optional[bool]:
        template_name = str(self.template_name.evaluate(context))
        template = context.get_template_with_context(template_name, tag=self.tag)

        namespace: Dict[str, object] = {}
        for _key, _val in self.args.items():
            namespace[_key] = _val.evaluate(context)

        with context.get_buffer() as buffer:
            with context.extend(namespace, template=template):
                template.render_with_context(context, buffer, partial=True)
                context.assign(key=self.name, val=buffer.getvalue().strip())

        return False

    def children(self) -> List[ChildNode]:
        block_scope: List[str] = list(self.args.keys())
        _children = [
            ChildNode(
                linenum=self.tok.linenum,
                node=None,
                expression=self.template_name,
                block_scope=block_scope,
                load_mode="include",
                load_context={"tag": "evaluate"},
            )
        ]
        for expr in self.args.values():
            _children.append(ChildNode(linenum=self.tok.linenum, expression=expr))
        return _children


class EvaluateTag(Tag):
    """The "evaluate" tag."""

    name = TAG_EVALUATE
    block = False
    node_class = EvaluateNode

    def parse(self, stream: TokenStream) -> Node:
        """Read an EvaluateNode from the given stream of tokens."""
        tok = next(stream)
        expect(stream, TOKEN_EXPRESSION)

        expr_stream = ExprTokenStream(
            tokenize_evaluate_expression(stream.current.value)
        )
        name = str(parse_string_or_identifier(expr_stream))
        next(expr_stream)

        if expr_stream.current[1] != TOKEN_USING:
            raise LiquidSyntaxError(
                f'invalid evaluate expression "{stream.current.value}"',
                linenum=stream.current.linenum,
            )
        next(expr_stream)

        template_name = parse_string_or_identifier(expr_stream)
        next(expr_stream)

        args: Dict[str, Expression] = {}
        if expr_stream.current[1] == TOKEN_IDENTIFIER:
            key, val = _parse_argument(expr_stream)
            args[key] = val

        while expr_stream.current[1] != TOKEN_EOF:
            if expr_stream.current[1] == TOKEN_COMMA:
                next(expr_stream)  # Eat comma
                key, val = _parse_argument(expr_stream)
                args[key] = val
            else:
                typ = expr_stream.current[1]
                raise LiquidSyntaxError(
                    f"expected a comma separated list of arguments, found {typ}",
                    linenum=tok.linenum,
                )

        return self.node_class(tok, name=name, template_name=template_name, args=args)


def _parse_argument(stream: ExprTokenStream) -> Tuple[str, Expression]:
    key = str(parse_unchained_identifier(stream))
    stream.next_token()
    stream.expect(TOKEN_COLON)
    stream.next_token()  # Eat colon
    val = parse_obj(stream)
    stream.next_token()
    return key, val


__default__: list[Type[Tag]] = [EvaluateTag]
