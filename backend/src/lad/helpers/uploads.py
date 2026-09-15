import shutil
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Protocol

SANDBOX_ROOT = Path("/data/chat_sandboxes")

MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024
MAX_FILES_PER_MESSAGE = 10

ALLOWED_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".json",
    ".txt",
    ".md",
    ".csv",
    ".tsv",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".html",
    ".css",
    ".scss",
    ".sh",
    ".sql",
    ".xml",
    ".go",
    ".rs",
    ".java",
    ".c",
    ".h",
    ".cpp",
    ".hpp",
    ".rb",
    ".php",
    ".pdf",
    ".zip",
}


class UploadedFile(Protocol):
    filename: str | None
    size: int | None
    file: Any


def validate_uploads(files: Sequence[UploadedFile]) -> None:
    if len(files) > MAX_FILES_PER_MESSAGE:
        raise ValueError(
            f"Too many files attached ({len(files)}); the limit is "
            f"{MAX_FILES_PER_MESSAGE} per message"
        )

    for file in files:
        filename = file.filename or ""
        extension = Path(filename).suffix.lower()

        if extension not in ALLOWED_EXTENSIONS:
            raise ValueError(f"File type '{extension}' is not allowed: {filename}")

        if file.size is not None and file.size > MAX_FILE_SIZE_BYTES:
            raise ValueError(f"File '{filename}' exceeds the 20MB size limit")


def chat_sandbox_dir(chat_id: int) -> Path:
    return SANDBOX_ROOT / str(chat_id)


def save_uploads(chat_id: int, files: Sequence[UploadedFile]) -> list[str]:
    target_dir = chat_sandbox_dir(chat_id)
    target_dir.mkdir(parents=True, exist_ok=True)

    filenames = []

    for file in files:
        filename = Path(file.filename or "unnamed").name
        dest_path = target_dir / filename

        with dest_path.open("wb") as dest:
            shutil.copyfileobj(file.file, dest)

        filenames.append(filename)

    return filenames
