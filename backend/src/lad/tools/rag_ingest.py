import sys
from pathlib import Path

from sqlalchemy import delete

from lad.core.db import connect_db, get_db_session
from lad.core.embeddings import embed_texts
from lad.models.db import DocumentChunk
from lad.tools.chunking import chunk_file

DEFAULT_INCLUDE_GLOBS = [
    "backend/src/**/*.py",
    "frontend/src/**/*.ts",
    "frontend/src/**/*.tsx",
    "*.md",
    "docs/**/*.md",
]

EXCLUDE_DIR_NAMES = {"node_modules", "__pycache__", ".git"}

EMBED_BATCH_SIZE = 32


def find_source_files(repo_root: Path) -> list[Path]:
    seen: set[Path] = set()
    files: list[Path] = []

    for pattern in DEFAULT_INCLUDE_GLOBS:
        for path in sorted(repo_root.glob(pattern)):
            if not path.is_file():
                continue
            if any(part in EXCLUDE_DIR_NAMES for part in path.parts):
                continue
            if path in seen:
                continue
            seen.add(path)
            files.append(path)

    return files


def _batched(items: list, size: int):
    for start in range(0, len(items), size):
        yield items[start : start + size]


def run_ingestion(repo_root: Path) -> None:
    files = find_source_files(repo_root)
    print(f"Found {len(files)} source files under {repo_root}")

    records: list[tuple[str, int, str]] = []

    for path in files:
        content = path.read_text(encoding="utf-8", errors="ignore")
        relative_path = str(path.relative_to(repo_root))

        for index, chunk_text in enumerate(chunk_file(path, content)):
            records.append((relative_path, index, chunk_text))

    print(f"Chunked into {len(records)} chunks")

    if not records:
        print("Nothing to index.")
        return

    texts = [
        f"# {relative_path}\n\n{chunk_text}" for relative_path, _, chunk_text in records
    ]
    embeddings: list[list[float]] = []

    for batch in _batched(texts, EMBED_BATCH_SIZE):
        embeddings.extend(embed_texts(batch))

    with get_db_session() as db:
        db.execute(delete(DocumentChunk))

        for (relative_path, index, chunk_text), embedding in zip(
            records, embeddings, strict=True
        ):
            db.add(
                DocumentChunk(
                    source_path=relative_path,
                    chunk_index=index,
                    content=chunk_text,
                    embedding=embedding,
                )
            )

        db.commit()

    print(f"Indexed {len(records)} chunks from {len(files)} files")


if __name__ == "__main__":
    default_repo_root = Path(__file__).resolve().parents[4]
    repo_root = Path(sys.argv[1]) if len(sys.argv) > 1 else default_repo_root

    connect_db()
    run_ingestion(repo_root)
