import io

import pytest

from lad.helpers import uploads as uploads_module


class FakeUploadFile:
    def __init__(self, filename, content=b"", size=None):
        self.filename = filename
        self.file = io.BytesIO(content)
        self.size = size if size is not None else len(content)


def test_validate_uploads_accepts_valid_files():
    files = [
        FakeUploadFile("main.py", b"print(1)"),
        FakeUploadFile("notes.txt", b"hi"),
    ]

    uploads_module.validate_uploads(files)


def test_validate_uploads_accepts_empty_list():
    uploads_module.validate_uploads([])


def test_validate_uploads_rejects_too_many_files():
    files = [FakeUploadFile(f"f{i}.txt", b"x") for i in range(11)]

    with pytest.raises(ValueError, match="Too many files"):
        uploads_module.validate_uploads(files)


def test_validate_uploads_allows_exactly_the_max_file_count():
    files = [FakeUploadFile(f"f{i}.txt", b"x") for i in range(10)]

    uploads_module.validate_uploads(files)


def test_validate_uploads_rejects_disallowed_extension():
    files = [FakeUploadFile("virus.exe", b"x")]

    with pytest.raises(ValueError, match="not allowed"):
        uploads_module.validate_uploads(files)


def test_validate_uploads_rejects_missing_extension():
    files = [FakeUploadFile("Makefile", b"x")]

    with pytest.raises(ValueError, match="not allowed"):
        uploads_module.validate_uploads(files)


def test_validate_uploads_rejects_oversized_file():
    files = [
        FakeUploadFile("big.txt", b"x", size=uploads_module.MAX_FILE_SIZE_BYTES + 1)
    ]

    with pytest.raises(ValueError, match="exceeds the 20MB"):
        uploads_module.validate_uploads(files)


def test_validate_uploads_allows_exactly_the_max_file_size():
    files = [FakeUploadFile("big.txt", b"x", size=uploads_module.MAX_FILE_SIZE_BYTES)]

    uploads_module.validate_uploads(files)


def test_chat_sandbox_dir_uses_chat_id():
    result = uploads_module.chat_sandbox_dir(42)

    assert result == uploads_module.SANDBOX_ROOT / "42"


def test_save_uploads_writes_files_to_sandbox_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(uploads_module, "SANDBOX_ROOT", tmp_path)
    files = [FakeUploadFile("main.py", b"print(1)")]

    filenames = uploads_module.save_uploads(chat_id=7, files=files)

    saved_path = tmp_path / "7" / "main.py"
    assert filenames == ["main.py"]
    assert saved_path.read_bytes() == b"print(1)"


def test_save_uploads_writes_multiple_files(monkeypatch, tmp_path):
    monkeypatch.setattr(uploads_module, "SANDBOX_ROOT", tmp_path)
    files = [
        FakeUploadFile("a.py", b"a"),
        FakeUploadFile("b.py", b"b"),
    ]

    filenames = uploads_module.save_uploads(chat_id=7, files=files)

    assert filenames == ["a.py", "b.py"]
    assert (tmp_path / "7" / "a.py").read_bytes() == b"a"
    assert (tmp_path / "7" / "b.py").read_bytes() == b"b"


def test_save_uploads_overwrites_existing_file_with_same_name(monkeypatch, tmp_path):
    monkeypatch.setattr(uploads_module, "SANDBOX_ROOT", tmp_path)
    uploads_module.save_uploads(chat_id=7, files=[FakeUploadFile("main.py", b"old")])

    filenames = uploads_module.save_uploads(
        chat_id=7, files=[FakeUploadFile("main.py", b"new")]
    )

    saved_path = tmp_path / "7" / "main.py"
    assert filenames == ["main.py"]
    assert saved_path.read_bytes() == b"new"


def test_save_uploads_strips_path_components(monkeypatch, tmp_path):
    monkeypatch.setattr(uploads_module, "SANDBOX_ROOT", tmp_path)
    files = [FakeUploadFile("../../etc/passwd", b"x")]

    filenames = uploads_module.save_uploads(chat_id=1, files=files)

    assert filenames == ["passwd"]
    assert (tmp_path / "1" / "passwd").read_bytes() == b"x"
    assert not (tmp_path.parent / "etc").exists()
