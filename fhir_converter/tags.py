from sys import intern
from typing import Any, Iterable, Sequence, TextIO, Type

from liquid import Environment, RenderContext
from liquid.ast import BlockNode, Node, Partial, PartialScope
from liquid.builtin.expressions import (
    parse_name,
    Identifier,
    parse_string_or_path,
    KeywordArgument,
)
from liquid.exceptions import LiquidSyntaxError, TemplateNotFoundError
from liquid.expression import Expression
from liquid.parser import get_parser
from liquid.stream import TokenStream
from liquid.tag import Tag
from liquid.token import (
    TOKEN_EOF,
    TOKEN_WORD,
    TOKEN_TAG,
    Token,
)
from liquid.undefined import is_undefined
from pyjson5 import encode_io
from pyjson5 import loads as json_loads

TAG_MERGE_DIFF = intern("mergeDiff")
TAG_ENDMERGE_DIFF = intern("endmergeDiff")
ENDMERGE_DIFFBLOCK = frozenset((TAG_ENDMERGE_DIFF, TOKEN_EOF))

TAG_EVALUATE = intern("evaluate")
TOKEN_USING = intern("using")


class MergeDiffNode(Node):
    """Parse tree node for the "mergeDiff" tag."""

    __slots__ = ("identifier", "block")

    def __init__(self, token: Token, identifier: Identifier, block: BlockNode) -> None:
        super().__init__(token)
        self.identifier = identifier
        self.block = block

    def __str__(self) -> str:
        return f"{{% {TAG_MERGE_DIFF} {self.identifier} %}}{self.block}{{% {TAG_ENDMERGE_DIFF} %}}"

    @staticmethod
    def __merge(a: Any, b: Any) -> Any:
        if isinstance(a, dict) and isinstance(b, dict):
            for k, v in b.items():
                if isinstance(k, str) and k.endswith("[x]"):
                    choice_name = k[:-3]
                    choices = [ak for ak in a.keys() if ak.startswith(choice_name)]
                    if choices:
                        a[choices[0]] = v
                else:
                    a[k] = v
        return a

    def render_to_output(self, context: RenderContext, buffer: TextIO) -> int:
        original = context.resolve(self.identifier)
        if not is_undefined(original):
            buf = context.get_buffer(buffer)
            if self.block.render(context, buf):
                val = buf.getvalue()
                if val and not val.isspace():
                    self.__merge(original, json_loads(val))

        encode_io(
            original,
            fp=buffer,  # type: ignore
            supply_bytes=False,
        )

        # TODO: Ideally we should be returning number of bytes written to buffer.
        return 0

    def children(
        self,
        static_context: RenderContext,
        *,
        include_partials: bool = True,
    ) -> Iterable[Node]:
        yield self.block


class MergeDiffTag(Tag):
    """The "mergeDiff" tag."""

    name = TAG_MERGE_DIFF
    end = TAG_ENDMERGE_DIFF
    node_class = MergeDiffNode

    def parse(self, stream: TokenStream) -> Node:
        token = stream.eat(TOKEN_TAG)
        identifier = parse_name(self.env, stream.into_inner())

        block = get_parser(self.env).parse_block(stream, ENDMERGE_DIFFBLOCK)
        stream.expect(TOKEN_TAG, value=TAG_ENDMERGE_DIFF)

        return self.node_class(
            token=token,
            identifier=identifier,
            block=block,
        )


class EvaluateNode(Node):
    """Parse tree node for the built-in "evaluate" tag."""

    __slots__ = ("name", "template_name", "args")
    tag = TAG_EVALUATE

    def __init__(
        self,
        token: Token,
        name: Identifier,
        template_name: Expression,
        args: list[KeywordArgument],
    ) -> None:
        super().__init__(token)
        self.name = name
        self.template_name = template_name
        self.args = args

    def __str__(self) -> str:
        args = " " + ", ".join(str(arg) for arg in self.args) if self.args else ""
        return f"{{% {self.tag} {self.name} using {self.template_name}{args} %}}"

    def render_to_output(self, context: RenderContext, _: TextIO) -> int:
        template_name = str(self.template_name.evaluate(context))
        template = context.env.get_template(template_name, tag=self.tag)

        namespace: dict[str, object] = {
            arg.name: arg.value.evaluate(context) for arg in self.args
        }

        with context.get_buffer() as buffer:
            with context.extend(namespace, template=template):
                template.render_with_context(context, buffer, partial=True)
                context.assign(key=self.name, val=buffer.getvalue().strip())

        return False

    def children(
        self, static_context: RenderContext, *, include_partials: bool = True
    ) -> Iterable[Node]:
        """Return this node's children."""
        if include_partials:
            name = self.template_name.evaluate(static_context)
            try:
                template = static_context.env.get_template(
                    str(name), context=static_context, tag=self.tag
                )
                yield from template.nodes
            except TemplateNotFoundError as err:
                err.token = self.template_name.token
                err.template_name = static_context.template.full_name()
                raise

    def expressions(self) -> Iterable[Expression]:
        """Return this node's expressions."""
        yield self.template_name
        yield from (arg.value for arg in self.args)

    def partial_scope(self) -> Partial | None:
        """Return information about a partial template loaded by this node."""
        scope: list[Identifier] = [
            Identifier(arg.name, token=arg.token) for arg in self.args
        ]

        return Partial(
            name=self.template_name, scope=PartialScope.SHARED, in_scope=scope
        )


class EvaluateTag(Tag):
    """The "evaluate" tag."""

    name = TAG_EVALUATE
    block = False
    node_class = EvaluateNode

    def parse(self, stream: TokenStream) -> Node:
        """Read an EvaluateNode from the given stream of tokens."""
        tok = stream.eat(TOKEN_TAG)
        tokens = stream.into_inner(eat=False)
        name = parse_name(self.env, tokens)

        if not (
            tokens.current.kind == TOKEN_WORD and tokens.current.value == TOKEN_USING
        ):
            raise LiquidSyntaxError(
                f'invalid evaluate expression "{stream.current.value}"',
                token=tok,
            )

        tokens.eat(TOKEN_WORD)
        template_name = parse_string_or_path(self.env, tokens)
        args = KeywordArgument.parse(self.env, tokens)
        return self.node_class(tok, name=name, template_name=template_name, args=args)


all_tags: Sequence[Type[Tag]] = [EvaluateTag, MergeDiffTag]
"""Sequence[type[Tag]]: All of the tags provided by the module"""


def register_tags(env: Environment, tags: Iterable[Type[Tag]]) -> None:
    """register_tags Adds the given tags to the Environment as long as a tag
    with the same name has not already been added

    Args:
        env (Environment): The rendering environment
        tags (Iterable[type[Tag]]): The tags to register / add
    """
    for tag in filter(lambda tag: tag.name not in env.tags, tags):
        env.add_tag(tag)
