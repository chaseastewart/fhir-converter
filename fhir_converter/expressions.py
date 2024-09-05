from liquid.expressions.arguments import parse_call_arguments  # noqa: D104
from liquid.expressions.arguments import parse_keyword_arguments
from liquid.expressions.arguments import parse_macro_arguments
from liquid.expressions.boolean.parse import parse as parse_boolean_expression
from liquid.expressions.boolean.parse import (
    parse_with_parens as parse_boolean_expression_with_parens,
)
from liquid.expressions.common import Token
from liquid.expressions.conditional.parse import parse as parse_conditional_expression
from liquid.expressions.conditional.parse import (
    parse_with_parens as parse_conditional_expression_with_parens,
)
from liquid.expressions.filtered.parse import parse as parse_filtered_expression
from liquid.expressions.stream import TokenStream

from fhir_converter.common import parse_identifier, parse_string_literal, TOKEN_MAP, LiquidSyntaxError

from liquid.expressions.loop.lex import tokenize as loop_tokenize
from liquid.expressions.loop.parse import (
    LoopArgument,
    LoopExpression,
    LoopIterable,
    parse_range,
    TOKEN_IDENTIFIER,
    TOKEN_IN,
    TOKEN_STRING,
    TOKEN_LPAREN,
    parse_loop_arguments
)

def parse_loop_argument(stream: TokenStream) -> LoopArgument:
    """Parse a object from the stream of tokens as a loop argument."""
    try:
        return TOKEN_MAP[stream.current[1]](stream)
    except KeyError as err:
        raise LiquidSyntaxError(f"unexpected {stream.current[2]!r}") from err

def parse_loop_expression(expr: str, linenum: int = 1) -> LoopExpression:
    """Parse a loop expression string."""
    stream = TokenStream(loop_tokenize(expr, linenum))
    stream.expect(TOKEN_IDENTIFIER)
    name = next(stream)[2]

    # Eat TOKEN_IN
    stream.expect(TOKEN_IN)
    next(stream)

    if stream.current[1] == TOKEN_IDENTIFIER:
        expression: LoopIterable = parse_identifier(stream)
        next(stream)
    elif stream.current[1] == TOKEN_STRING:
        expression = parse_string_literal(stream)
        next(stream)
    elif stream.current[1] == TOKEN_LPAREN:
        expression = parse_range(stream)
        next(stream)
    else:
        raise LiquidSyntaxError("invalid loop expression", linenum=stream.current[0])

    args, reversed_ = parse_loop_arguments(stream)
    return LoopExpression(name=name, iterable=expression, reversed_=reversed_, **args)

__all__ = (
    "parse_call_arguments",
    "parse_keyword_arguments",
    "parse_macro_arguments",
    "parse_boolean_expression",
    "parse_boolean_expression_with_parens",
    "parse_conditional_expression",
    "parse_conditional_expression_with_parens",
    "parse_filtered_expression",
    "parse_loop_expression",
    "TokenStream",
    "Token",
)
