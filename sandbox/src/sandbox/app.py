import os
import signal
import subprocess
from pathlib import Path

from fastapi import FastAPI

from sandbox import schemas

app = FastAPI(title="lad-sandbox", version="0.1.0")


def _chat_workdir(chat_id: str) -> Path:
    workdir = schemas.CHAT_SANDBOXES_ROOT / chat_id
    workdir.mkdir(parents=True, exist_ok=True)
    return workdir


@app.post("/execute", response_model=schemas.ExecuteResponse)
def execute(request: schemas.ExecuteRequest) -> schemas.ExecuteResponse:
    workdir = _chat_workdir(request.chat_id)

    process = subprocess.Popen(
        ["sh", "-c", request.command],
        cwd=workdir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
        start_new_session=True,
    )

    try:
        stdout, stderr = process.communicate(timeout=request.timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

        stdout, stderr = process.communicate()

        return schemas.ExecuteResponse(
            exit_code=-1,
            stdout=stdout,
            stderr=stderr + f"\n[command timed out after {request.timeout}s]",
            timed_out=True,
        )

    return schemas.ExecuteResponse(
        exit_code=process.returncode,
        stdout=stdout,
        stderr=stderr,
        timed_out=False,
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
