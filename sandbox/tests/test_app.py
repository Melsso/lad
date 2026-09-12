def test_health_returns_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_execute_returns_stdout_and_exit_code(client):
    response = client.post(
        "/execute",
        json={"chat_id": "1", "command": "echo hello", "timeout": 5},
    )

    body = response.json()
    assert response.status_code == 200
    assert body["exit_code"] == 0
    assert body["stdout"].strip() == "hello"
    assert body["timed_out"] is False


def test_execute_captures_stderr(client):
    response = client.post(
        "/execute",
        json={"chat_id": "1", "command": "echo oops 1>&2", "timeout": 5},
    )

    body = response.json()
    assert body["stderr"].strip() == "oops"


def test_execute_passes_through_nonzero_exit_code(client):
    response = client.post(
        "/execute",
        json={"chat_id": "1", "command": "exit 7", "timeout": 5},
    )

    assert response.json()["exit_code"] == 7


def test_execute_times_out_long_running_commands(client):
    response = client.post(
        "/execute",
        json={"chat_id": "1", "command": "sleep 5", "timeout": 1},
    )

    body = response.json()
    assert body["timed_out"] is True
    assert body["exit_code"] == -1
    assert "timed out" in body["stderr"]


def test_execute_scopes_working_directory_per_chat(client, tmp_path):
    client.post(
        "/execute",
        json={"chat_id": "1", "command": "echo chat_one > note.txt", "timeout": 5},
    )
    client.post(
        "/execute",
        json={"chat_id": "2", "command": "echo chat_two > note.txt", "timeout": 5},
    )

    chat_one_note = (tmp_path / "1" / "note.txt").read_text().strip()
    chat_two_note = (tmp_path / "2" / "note.txt").read_text().strip()

    assert chat_one_note == "chat_one"
    assert chat_two_note == "chat_two"


def test_execute_creates_the_chat_directory_if_missing(client, tmp_path):
    assert not (tmp_path / "42").exists()

    client.post(
        "/execute",
        json={"chat_id": "42", "command": "pwd", "timeout": 5},
    )

    assert (tmp_path / "42").is_dir()


def test_execute_rejects_timeout_above_maximum(client):
    response = client.post(
        "/execute",
        json={"chat_id": "1", "command": "echo hi", "timeout": 9999},
    )

    assert response.status_code == 422
