from lad.tools import web_search_server


def test_web_search_clamps_max_results_below_minimum(monkeypatch):
    captured = {}

    def fake_search_web(query, max_results=5):
        captured["max_results"] = max_results
        return []

    monkeypatch.setattr(web_search_server, "search_web", fake_search_web)

    web_search_server.web_search("test query", max_results=1)

    assert captured["max_results"] == web_search_server.MIN_RESULTS


def test_web_search_does_not_raise_a_max_results_already_above_minimum(monkeypatch):
    captured = {}

    def fake_search_web(query, max_results=5):
        captured["max_results"] = max_results
        return []

    monkeypatch.setattr(web_search_server, "search_web", fake_search_web)

    web_search_server.web_search("test query", max_results=10)

    assert captured["max_results"] == 10


def test_web_search_returns_message_when_no_results(monkeypatch):
    monkeypatch.setattr(web_search_server, "search_web", lambda query, max_results: [])

    result = web_search_server.web_search("anything")

    assert result == "No results found."


def test_web_search_formats_results_with_title_url_and_content(monkeypatch):
    def fake_search_web(query, max_results):
        return [
            {
                "title": "Example Page",
                "url": "https://example.com/page",
                "content": "some relevant content",
            }
        ]

    monkeypatch.setattr(web_search_server, "search_web", fake_search_web)

    result = web_search_server.web_search("test query")

    assert "Example Page" in result
    assert "https://example.com/page" in result
    assert "some relevant content" in result


def test_web_search_handles_missing_fields_gracefully(monkeypatch):
    monkeypatch.setattr(
        web_search_server, "search_web", lambda query, max_results: [{}]
    )

    result = web_search_server.web_search("test query")

    assert "Untitled" in result
