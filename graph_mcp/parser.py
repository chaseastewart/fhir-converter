
import ast
import re
from pathlib import Path, PurePath

from tree_sitter import Language, Parser

import tree_sitter_python


LANGUAGES = {
    ".py": Language(tree_sitter_python.language()),
}

CLASS_TYPES = {
    "class_definition",
    "class_declaration",
}

FUNCTION_TYPES = {
    "function_definition",
    "function_declaration",
    "method_definition",
    "arrow_function",
    "function_expression",
}

IMPORT_TYPES = {
    "import_statement",
    "import_from_statement",
    "import_declaration",
}

CALL_TYPES = {
    "call",
    "call_expression",
}


def node_text(node, source):
    return source[node.start_byte:node.end_byte].decode(
        "utf-8", errors="replace"
    )


def get_name(node, source):
    name_node = node.child_by_field_name("name")

    if name_node:
        return node_text(name_node, source)

    return f"anonymous_{node.start_point.row + 1}"


def extract_import_targets(node, source):
    """Return [{module, level, names}] for a Python import node.

    level is the number of leading dots in a relative import (0 = absolute).
    names are the imported names for `from X import a, b` (empty for
    `import X` and for `from X import *`).
    """
    targets = []

    def dotted(n):
        if n is not None and n.type == "aliased_import":
            n = n.child_by_field_name("name")
        return node_text(n, source) if n is not None else ""

    if node.type == "import_statement":
        for name_node in node.children_by_field_name("name"):
            targets.append({
                "module": dotted(name_node),
                "level": 0,
                "names": []
            })

    elif node.type == "import_from_statement":
        module_node = node.child_by_field_name("module_name")
        level = 0
        module = ""

        if module_node is not None and module_node.type == "relative_import":
            for child in module_node.children:
                if child.type == "import_prefix":
                    level = len(node_text(child, source).strip())
                elif child.type == "dotted_name":
                    module = node_text(child, source)
        elif module_node is not None:
            module = node_text(module_node, source)

        names = [
            dotted(n)
            for n in node.children_by_field_name("name")
        ]

        targets.append({
            "module": module,
            "level": level,
            "names": names
        })

    return targets


def parse_file(file_path, repo_path):
    extension = file_path.suffix.lower()

    if extension not in LANGUAGES:
        return None

    source = file_path.read_bytes()

    parser = Parser(LANGUAGES[extension])
    tree = parser.parse(source)

    relative_path = str(file_path.relative_to(repo_path))
    module_name = module_name_for(relative_path)

    symbols = []
    imports = []
    calls = []

    def walk(node, parent=None):

        parent_symbol = parent["id"] if parent else None
        current_parent = parent_symbol
        current = parent

        if node.type in CLASS_TYPES | FUNCTION_TYPES:

            # The id keeps the Class/Function split so ids stay stable
            # across re-ingestion; `kind` also distinguishes methods.
            id_kind = (
                "Class"
                if node.type in CLASS_TYPES
                else "Function"
            )
            kind = (
                "Method"
                if id_kind == "Function" and parent and parent["kind"] == "Class"
                else id_kind
            )

            name = get_name(node, source)
            line = node.start_point.row + 1

            symbol_id = (
                f"{relative_path}:{line}:{id_kind}:{name}"
            )

            prefix = parent["qualified_name"] if parent else module_name
            qualified_name = f"{prefix}.{name}" if prefix else name

            bases = []
            if id_kind == "Class":
                superclasses = node.child_by_field_name("superclasses")
                if superclasses is not None:
                    bases = [
                        node_text(child, source)
                        for child in superclasses.named_children
                        if child.type in ("identifier", "attribute")
                    ]

            current = {
                "id": symbol_id,
                "name": name,
                "kind": kind,
                "qualified_name": qualified_name,
                "file": relative_path,
                "line": line,
                "end_line": node.end_point.row + 1,
                "bases": bases,
                "parent_id": parent_symbol
            }
            symbols.append(current)

            current_parent = symbol_id

        if node.type in IMPORT_TYPES:
            imports.append({
                "text": node_text(node, source),
                "line": node.start_point.row + 1,
                "targets": extract_import_targets(node, source),
                "resolved": []
            })

        if node.type in CALL_TYPES:
            function_node = node.child_by_field_name("function")

            if function_node:
                calls.append({
                    "name": node_text(function_node, source),
                    "line": node.start_point.row + 1,
                    "parent_id": current_parent
                })

        for child in node.children:
            walk(child, current)

    walk(tree.root_node)

    return {
        "path": relative_path,
        "symbols": symbols,
        "imports": imports,
        "calls": calls
    }


def parse_repository(repo_path):
    repo_path = Path(repo_path)

    ignored = {
        ".git", "node_modules", "venv",
        ".venv", "__pycache__", "dist",
        "build", ".next"
    }

    results = []

    for file_path in repo_path.rglob("*"):

        if not file_path.is_file():
            continue

        if any(part in ignored for part in file_path.parts):
            continue

        if file_path.suffix.lower() not in LANGUAGES:
            continue

        try:
            result = parse_file(file_path, repo_path)

            if result:
                results.append(result)

        except Exception as error:
            print(f"Skipping {file_path}: {error}")

    return results


def module_name_for(path):
    """fhir_converter\\filters.py -> fhir_converter.filters
    pkg\\__init__.py -> pkg"""
    parts = list(PurePath(path).with_suffix("").parts)

    if parts and parts[-1] == "__init__":
        parts = parts[:-1]

    return ".".join(parts)

