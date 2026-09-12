import subprocess
from pathlib import Path

from fastapi import FastAPI

from sandbox import schemas

app = FastAPI()


def _chat_workdir(chat_id: str) -> Path:
    workdir = schemas.CHAT_SANDBOXES_ROOT / chat_id
    workdir.mkdir(parents=True, exist_ok=True)
    return workdir


def _to_str(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return value


@app.post("/execute", response_model=schemas.ExecuteResponse)
def execute(request: schemas.ExecuteRequest) -> schemas.ExecuteResponse:
    workdir = _chat_workdir(request.chat_id)

    try:
        result = subprocess.run(
            ["sh", "-c", request.command],
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=request.timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        stderr = _to_str(exc.stderr)
        return schemas.ExecuteResponse(
            exit_code=-1,
            stdout=_to_str(exc.stdout),
            stderr=stderr + f"\n[command timed out after {request.timeout}s]",
            timed_out=True,
        )

    return schemas.ExecuteResponse(
        exit_code=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
        timed_out=False,
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
