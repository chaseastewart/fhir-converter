"""
Extension pour supporter la syntaxe MSH."7" dans liquid 2.0
Compatible avec la syntaxe legacy des templates FHIR.
"""

from typing import TYPE_CHECKING, Union
from liquid.builtin.expressions.path import Path, Segments
from liquid.exceptions import LiquidSyntaxError
from liquid.limits import to_int
from liquid.token import (
    TOKEN_DOT, TOKEN_FLOAT, TOKEN_IDENTINDEX, TOKEN_IDENTSTRING, 
    TOKEN_INTEGER, TOKEN_LBRACKET, TOKEN_RBRACKET, TOKEN_WORD, TOKEN_STRING
)
from liquid import Mode

if TYPE_CHECKING:
    from liquid import Environment, TokenStream

# Stockage de la méthode originale
_original_path_parse = None


def fhir_compatible_path_parse(env: 'Environment', tokens: 'TokenStream') -> Path:
    """
    Version modifiée de Path.parse qui supporte la syntaxe MSH."7"
    """
    token = tokens.current
    segments: Segments = []

    while True:
        kind, value, _index, _source = tokens.current

        if kind == TOKEN_WORD:
            segments.append(value)
            if tokens.peek.kind == TOKEN_WORD:
                # Two consecutive words indicate end of path.
                next(tokens)
                break
        elif kind == TOKEN_IDENTSTRING:
            segments.append(value)
            if env.mode == Mode.STRICT and tokens.peek.kind == TOKEN_WORD:
                raise LiquidSyntaxError(
                    f"expected a dot or bracket notation, found {tokens.peek.kind}",
                    token=tokens.peek,
                )
        elif kind == TOKEN_IDENTINDEX:
            segments.append(to_int(value))
            if env.mode == Mode.STRICT and tokens.peek.kind == TOKEN_WORD:
                raise LiquidSyntaxError(
                    f"expected a dot or bracket notation, found {tokens.peek.kind}",
                    token=tokens.peek,
                )
        elif kind == TOKEN_LBRACKET:
            next(tokens)
            segments.append(Path.parse(env, tokens))
            tokens.expect(TOKEN_RBRACKET)
            if env.mode == Mode.STRICT and tokens.peek.kind == TOKEN_WORD:
                raise LiquidSyntaxError(
                    f"expected a dot or bracket notation, found {tokens.peek.kind}",
                    token=tokens.peek,
                )
        elif kind == TOKEN_DOT:
            # MODIFICATION: Accepter TOKEN_STRING en plus de TOKEN_WORD après un point
            peek_kind = tokens.peek.kind
            if (
                not env.shorthand_indexes
                and env.mode == Mode.STRICT
                and peek_kind not in (TOKEN_WORD, TOKEN_STRING)
            ):
                raise LiquidSyntaxError(
                    f"expected an identifier, found {peek_kind}",
                    token=tokens.peek,
                )
            # Si c'est un string après un point, on continue le parsing
        elif kind == TOKEN_STRING:
            # NOUVELLE FONCTIONNALITÉ: Traiter les strings comme des clés
            # Cela permet MSH."7" où "7" sera traité comme une clé string
            segments.append(value)
            if env.mode == Mode.STRICT and tokens.peek.kind == TOKEN_WORD:
                raise LiquidSyntaxError(
                    f"expected a dot or bracket notation, found {tokens.peek.kind}",
                    token=tokens.peek,
                )
        elif kind == TOKEN_FLOAT and env.shorthand_indexes:
            segments.extend(to_int(i) for i in value.rstrip(".").split("."))
        elif kind == TOKEN_INTEGER and env.shorthand_indexes:
            segments.append(to_int(value))
        else:
            break

        next(tokens)

    if not segments:
        raise LiquidSyntaxError(
            "missing or unexpected path segment",
            token=tokens.current,
        )

    return Path(token, segments)


def enable_fhir_syntax():
    """
    Active le support de la syntaxe FHIR MSH."7" globalement.
    """
    global _original_path_parse
    from liquid.builtin.expressions import path as path_module
    
    if _original_path_parse is None:
        # Sauvegarder l'original
        _original_path_parse = path_module.Path.parse
        # Remplacer par notre version
        path_module.Path.parse = staticmethod(fhir_compatible_path_parse)
        
        # Extension activée avec succès
    
    return True


def disable_fhir_syntax():
    """
    Désactive le support de la syntaxe FHIR et restaure le comportement original.
    """
    global _original_path_parse
    from liquid.builtin.expressions import path as path_module
    
    if _original_path_parse is not None:
        # Restaurer l'original
        path_module.Path.parse = _original_path_parse
        _original_path_parse = None
    
    return True


def register_fhir_compatible_path(env):
    """
    Active le support FHIR pour un environnement spécifique.
    Deprecated: utiliser enable_fhir_syntax() à la place.
    """
    return enable_fhir_syntax()


def restore_original_path(env):
    """
    Restaure le comportement original pour un environnement spécifique.
    Deprecated: utiliser disable_fhir_syntax() à la place.
    """
    return disable_fhir_syntax()