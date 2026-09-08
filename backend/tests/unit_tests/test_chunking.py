from lad.tools import chunking


def test_chunk_generic_text_empty_returns_no_chunks():
    assert chunking.chunk_generic_text("") == []
    assert chunking.chunk_generic_text("   ") == []


def test_chunk_generic_text_short_content_is_a_single_chunk():
    result = chunking.chunk_generic_text("hello world", chunk_size=100)

    assert result == ["hello world"]


def test_chunk_generic_text_splits_long_content():
    content = "line one\n" * 5 + "x" * 2000

    result = chunking.chunk_generic_text(content, chunk_size=50, overlap=10)

    assert len(result) > 1
    assert all(chunk for chunk in result)


def test_chunk_python_source_drops_import_only_preamble():
    source = (
        "import os\n"
        "\n"
        "def foo():\n"
        "    return 1\n"
        "\n"
        "\n"
        "class Bar:\n"
        "    def method(self):\n"
        "        return 2\n"
    )

    chunks = chunking.chunk_python_source(source)

    assert len(chunks) == 2
    assert "def foo():" in chunks[0]
    assert "class Bar:" in chunks[1]


def test_chunk_python_source_keeps_preamble_with_real_content():
    source = "import os\n\nMAX_RETRIES = 3\n\n\ndef foo():\n    return 1\n"

    chunks = chunking.chunk_python_source(source)

    assert len(chunks) == 2
    assert chunks[0] == "import os\n\nMAX_RETRIES = 3"
    assert "def foo():" in chunks[1]


def test_is_import_only_true_for_pure_import_block():
    assert chunking._is_import_only("import os\nfrom typing import Any")


def test_is_import_only_false_when_real_code_present():
    assert not chunking._is_import_only("import os\n\nMAX_RETRIES = 3")


def test_is_import_only_true_for_blank_text():
    assert chunking._is_import_only("")
    assert chunking._is_import_only("   \n  \n")


def test_chunk_python_source_with_no_top_level_defs_falls_back_to_generic():
    source = "x = 1\ny = 2\n"

    assert chunking.chunk_python_source(source) == [source.strip()]


def test_chunk_python_source_with_syntax_error_falls_back_to_generic():
    source = "def broken(:\n"

    assert chunking.chunk_python_source(source) == [source.strip()]


def test_chunk_file_dispatches_by_extension(tmp_path):
    py_chunks = chunking.chunk_file(tmp_path / "sample.py", "def f():\n    pass\n")
    md_chunks = chunking.chunk_file(tmp_path / "sample.md", "# Title\n\nSome text.")

    assert any("def f" in chunk for chunk in py_chunks)
    assert md_chunks == ["# Title\n\nSome text."]
