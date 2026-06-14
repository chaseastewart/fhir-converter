"""Tags personnalisés pour FHIR Converter - Version Liquid 2.0"""

from sys import intern
from typing import Any, Dict, List, Optional, TextIO, Type

from liquid import Environment, Node, RenderContext
from liquid.ast import BlockNode
from liquid.exceptions import LiquidSyntaxError
from liquid.expression import Expression
from liquid.builtin.expressions import (
    parse_identifier, 
    FilteredExpression, 
    StringLiteral,
    parse_string_or_path,
)
from liquid.builtin.expressions.primitive import parse_primitive
from liquid.parser import get_parser
from liquid.stream import TokenStream
from liquid.tag import Tag
from liquid.token import TOKEN_TAG, TOKEN_COLON, TOKEN_COMMA, TOKEN_EOF, TOKEN_WORD, Token
from liquid.undefined import is_undefined

from json5 import loads as json_loads
from fhir_converter.utils import encode_io

# Constantes pour les tags
TAG_EVALUATE = intern("evaluate")
TOKEN_USING = intern("using")

TAG_MERGE_DIFF = intern("mergeDiff")
TAG_ENDMERGE_DIFF = intern("endmergeDiff")


class EvaluateNode(Node):
    """Parse tree node for the built-in "evaluate" tag."""

    __slots__ = ("token", "name", "template_name", "args", "blank")

    def __init__(
        self,
        token: Token,
        name: str,
        template_name: Expression,
        args: Optional[Dict[str, Expression]] = None,
    ) -> None:
        self.token = token
        self.name = name
        self.template_name = template_name
        self.args = args or {}
        self.blank = False  # Le tag evaluate produit du contenu

    def __str__(self) -> str:
        buf = [f"{self.name}", f" using {self.template_name}"]

        if self.args:
            buf.append(", ")
        args = (f"{key}={val}" for key, val in self.args.items())
        buf.append(", ".join(args))

        return f"{TAG_EVALUATE}({''.join(buf)})"

    def __repr__(self) -> str:
        return f"EvaluateNode(token={self.token!r}, name={self.name})"

    def render_to_output(self, context: RenderContext, buffer: TextIO) -> int:
        """Render the evaluate tag to output."""
        template_name = str(self.template_name.evaluate(context))
        template = context.get_template(template_name)

        # Créer un namespace pour les arguments
        namespace = {}
        for key, val in self.args.items():
            namespace[key] = val.evaluate(context)

        # Rendre le template dans un buffer
        with context.get_buffer() as temp_buffer:
            with context.extend(namespace):
                template.render_with_context(context, temp_buffer)
                context.assign(self.name, temp_buffer.getvalue().strip())

        return 0  # Ne pas imprimer de contenu
class EvaluateTag(Tag):
    """The "evaluate" tag."""

    name = TAG_EVALUATE
    block = False

    def parse(self, stream: TokenStream) -> EvaluateNode:
        """Parse tokens from stream into an EvaluateNode."""
        token = stream.eat(TOKEN_TAG)
        
        # Parse le contenu du tag
        tokens = stream.into_inner(tag=token, eat=False)
        
        # Parse le nom de la variable
        name_expr = parse_string_or_path(self.env, tokens)
        if isinstance(name_expr, StringLiteral):
            name = name_expr.value
        else:
            # Pour un Identifier ou Path
            name = str(name_expr)
        
        # Expect "using"
        if tokens.current.value != "using":
            raise LiquidSyntaxError(
                f'expected "using" after variable name, found "{tokens.current.value}"',
                token=tokens.current,
            )
        tokens.next()
        
        # Parse le nom du template
        template_name = parse_string_or_path(self.env, tokens)
        
        # Parse les arguments optionnels (keyword arguments: name: value, name2: value2)
        args = {}
        
        # Skip leading commas
        if tokens.current.kind == TOKEN_COMMA:
            next(tokens)
        
        # Parse keyword arguments like include tag does
        while True:
            # Check for end of expression
            if tokens.current.kind == TOKEN_EOF:
                break
            
            # Skip commas between arguments
            if tokens.current.kind == TOKEN_COMMA:
                next(tokens)
                if tokens.current.kind == TOKEN_EOF:
                    break
            
            # Expect argument name (word token like 'AIG', 'HD', etc.)
            token = next(tokens)
            if token.kind != TOKEN_WORD:
                # Not a keyword argument, we're done
                break
            
            arg_name = token.value
            
            # Expect ":"
            tokens.eat(TOKEN_COLON)
            
            # Parse argument value using parse_primitive (doesn't consume EOF like FilteredExpression.parse)
            arg_value = parse_primitive(self.env, tokens)
            
            args[arg_name] = arg_value

        return EvaluateNode(
            token=token,
            name=name,
            template_name=template_name,
            args=args,
        )


class MergeDiffNode(Node):
    """Parse tree node for the "mergeDiff" tag."""

    __slots__ = ("token", "identifier", "block", "blank")

    def __init__(self, token: Token, identifier: str, block: BlockNode) -> None:
        self.token = token
        self.identifier = identifier
        self.block = block
        self.blank = False  # Le tag mergeDiff produit du contenu

    def __str__(self) -> str:
        return f"mergeDiff {self.identifier} {{ {self.block} }}"

    def __repr__(self) -> str:
        return f"MergeDiff(token={self.token!r} identifier={self.identifier})"

    @staticmethod
    def __merge(a: Any, b: Any) -> Any:
        """Merge deux objets dict de manière récursive."""
        if isinstance(a, dict) and isinstance(b, dict):
            for k, v in b.items():
                if isinstance(k, str) and k.endswith("[x]"):
                    # Gestion des choix FHIR (ex: value[x])
                    choice_name = k[:-3]
                    choices = [ak for ak in a.keys() if ak.startswith(choice_name)]
                    if choices:
                        a[choices[0]] = v
                else:
                    a[k] = v
        return a

    def render_to_output(self, context: RenderContext, buffer: TextIO) -> int:
        """Render the mergeDiff tag to output."""
        original = context.resolve(self.identifier)
        if not is_undefined(original):
            # Rendre le contenu du bloc dans un buffer temporaire
            with context.get_buffer() as temp_buffer:
                self.block.render(context, temp_buffer)
                val = temp_buffer.getvalue()
                
                # Si le contenu n'est pas vide, merger avec l'original
                if val and not val.isspace():
                    try:
                        parsed_json = json_loads(val)
                        self.__merge(original, parsed_json)
                    except Exception:
                        # En cas d'erreur de parsing JSON, ignorer silencieusement
                        pass

        # Encoder et écrire l'objet original (modifié) dans le buffer de sortie
        encode_io(original, fp=buffer, supply_bytes=False)
        return 1  # Indique qu'on a écrit du contenu


class MergeDiffTag(Tag):
    """The "mergeDiff" tag."""

    name = TAG_MERGE_DIFF
    block = True  # C'est un tag block

    def parse(self, stream: TokenStream) -> MergeDiffNode:
        """Parse tokens from stream into a MergeDiffNode."""
        token = stream.eat(TOKEN_TAG)
        tokens = stream.into_inner(tag=token)
        identifier = parse_identifier(self.env, tokens)
        tokens.expect_eos()
        block = get_parser(self.env).parse_block(stream, [TAG_ENDMERGE_DIFF])
        stream.expect(TOKEN_TAG, value=TAG_ENDMERGE_DIFF)
        return MergeDiffNode(
            token=token,
            identifier=str(identifier),
            block=block,
        )


# Liste des tags pour l'enregistrement
all_tags: List[Type[Tag]] = [EvaluateTag, MergeDiffTag]


def register_tags(env: Environment, tags: List[Type[Tag]]) -> None:
    """Register tags with the environment."""
    for tag_class in tags:
        if tag_class.name not in env.tags:
            env.add_tag(tag_class)