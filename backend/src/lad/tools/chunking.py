import ast
from pathlib import Path

GENERIC_CHUNK_SIZE = 1500
GENERIC_CHUNK_OVERLAP = 200

_CHUNKABLE_NODE_TYPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


def _is_import_only(text: str) -> bool:
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    if not lines:
        return True

    return all(line.startswith(("import ", "from ")) for line in lines)


def chunk_generic_text(
    content: str,
    chunk_size: int = GENERIC_CHUNK_SIZE,
    overlap: int = GENERIC_CHUNK_OVERLAP,
) -> list[str]:
    content = content.strip()
    if not content:
        return []

    chunks: list[str] = []
    start = 0

    while start < len(content):
        end = min(start + chunk_size, len(content))

        if end < len(content):
            newline_pos = content.rfind("\n", start, end)
            if newline_pos > start:
                end = newline_pos

        piece = content[start:end].strip()
        if piece:
            chunks.append(piece)

        if end >= len(content):
            break

        start = max(end - overlap, start + 1)

    return chunks


def chunk_python_source(content: str) -> list[str]:
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return chunk_generic_text(content)

    top_level_nodes = [
        node for node in tree.body if isinstance(node, _CHUNKABLE_NODE_TYPES)
    ]

    if not top_level_nodes:
        return chunk_generic_text(content)

    lines = content.splitlines()
    preamble = "\n".join(lines[: top_level_nodes[0].lineno - 1]).strip()

    chunks = [preamble] if preamble and not _is_import_only(preamble) else []

    for node in top_level_nodes:
        segment = ast.get_source_segment(content, node)
        if segment:
            chunks.append(segment)

    return chunks


def chunk_file(path: Path, content: str) -> list[str]:
    if path.suffix == ".py":
        return chunk_python_source(content)

    return chunk_generic_text(content)
