from pathlib import Path

from lad.tools import rag_ingest


def _make_repo(tmp_path: Path) -> Path:
    (tmp_path / "backend" / "src" / "lad").mkdir(parents=True)
    (tmp_path / "backend" / "src" / "lad" / "core.py").write_text(
        "def f():\n    pass\n"
    )
    (tmp_path / "frontend" / "src").mkdir(parents=True)
    (tmp_path / "frontend" / "src" / "App.tsx").write_text(
        "export const App = () => null;"
    )
    (tmp_path / "node_modules" / "pkg").mkdir(parents=True)
    (tmp_path / "node_modules" / "pkg" / "index.ts").write_text("ignored")
    (tmp_path / "README.md").write_text("# Readme")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "adr-001.md").write_text("# ADR")

    return tmp_path


def test_find_source_files_includes_expected_and_excludes_node_modules(tmp_path):
    repo_root = _make_repo(tmp_path)

    files = rag_ingest.find_source_files(repo_root)
    relative = {str(f.relative_to(repo_root)) for f in files}

    assert "backend/src/lad/core.py" in relative
    assert "frontend/src/App.tsx" in relative
    assert "README.md" in relative
    assert "docs/adr-001.md" in relative
    assert not any("node_modules" in path for path in relative)


def test_run_ingestion_embeds_and_persists_chunks(monkeypatch, tmp_path, mock_session):
    repo_root = _make_repo(tmp_path)

    captured_texts: list[str] = []

    def fake_embed_texts(texts):
        captured_texts.extend(texts)
        return [[0.1, 0.2, 0.3] for _ in texts]

    monkeypatch.setattr(rag_ingest, "embed_texts", fake_embed_texts)

    class _SessionContext:
        def __enter__(self):
            return mock_session

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(rag_ingest, "get_db_session", lambda: _SessionContext())

    rag_ingest.run_ingestion(repo_root)

    mock_session.execute.assert_called_once()
    assert mock_session.add.call_count > 0
    mock_session.commit.assert_called_once()

    assert any(text.startswith("# backend/src/lad/core.py") for text in captured_texts)

    added_chunks = [call.args[0] for call in mock_session.add.call_args_list]
    assert all(
        "# backend/src/lad/core.py" not in chunk.content for chunk in added_chunks
    )


def test_run_ingestion_with_no_matching_files_does_nothing(
    monkeypatch, tmp_path, mock_session
):
    def fake_embed_texts(texts):
        return [[0.1] for _ in texts]

    monkeypatch.setattr(rag_ingest, "embed_texts", fake_embed_texts)
    monkeypatch.setattr(rag_ingest, "get_db_session", lambda: None)

    rag_ingest.run_ingestion(tmp_path)

    mock_session.execute.assert_not_called()
