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


def test_chunk_python_source_splits_by_function_and_class():
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

    assert len(chunks) == 3
    assert chunks[0] == "import os"
    assert "def foo():" in chunks[1]
    assert "class Bar:" in chunks[2]


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
