"""Load test for LAD's CRUD endpoints (no LLM involved).

These endpoints never touch Ollama or the sandbox, so real concurrency is a
fair test here: it exercises FastAPI + SQLAlchemy + Postgres connection
pooling. This is deliberately kept separate from anything that streams a
model reply -- see profile_llm.py for that, which is profiling, not load
testing, since local LLM inference is the bottleneck there, not LAD's code.

Usage:
    poetry run python scripts/load_test_crud.py
    poetry run python scripts/load_test_crud.py --base-url http://localhost:8000/api \
        --concurrency 20 --requests 200
"""

from __future__ import annotations

import argparse
import asyncio
import statistics
import time
from dataclasses import dataclass, field

import httpx


@dataclass
class EndpointResult:
    name: str
    latencies_ms: list[float] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    wall_time_s: float = 0.0

    @property
    def total(self) -> int:
        return len(self.latencies_ms) + len(self.errors)

    def percentile(self, p: float) -> float:
        if not self.latencies_ms:
            return 0.0
        return statistics.quantiles(self.latencies_ms, n=100)[int(p) - 1]

    def summary_line(self) -> str:
        if not self.latencies_ms:
            return f"{self.name:<12} all {len(self.errors)} requests failed"

        req_per_s = self.total / self.wall_time_s if self.wall_time_s else 0.0
        error_rate = len(self.errors) / self.total * 100 if self.total else 0.0

        return (
            f"{self.name:<12} "
            f"n={self.total:<5} "
            f"errors={len(self.errors):<4} ({error_rate:4.1f}%)  "
            f"req/s={req_per_s:7.1f}  "
            f"p50={statistics.median(self.latencies_ms):7.1f}ms  "
            f"p95={self.percentile(95):7.1f}ms  "
            f"p99={self.percentile(99):7.1f}ms  "
            f"max={max(self.latencies_ms):7.1f}ms"
        )


async def _timed(result: EndpointResult, coro_factory) -> None:
    start = time.perf_counter()
    try:
        response = await coro_factory()
        response.raise_for_status()
        result.latencies_ms.append((time.perf_counter() - start) * 1000)
    except Exception as exc:  # noqa: BLE001 - we want to count any failure
        result.errors.append(str(exc))


async def _run_phase(
    name: str,
    concurrency: int,
    total: int,
    make_call,
) -> EndpointResult:
    result = EndpointResult(name=name)
    semaphore = asyncio.Semaphore(concurrency)

    async def bound_call(i: int) -> None:
        async with semaphore:
            await _timed(result, lambda: make_call(i))

    start = time.perf_counter()
    await asyncio.gather(*(bound_call(i) for i in range(total)))
    result.wall_time_s = time.perf_counter() - start

    return result


async def main(base_url: str, concurrency: int, requests: int) -> None:
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        print(f"Seeding {max(concurrency, 10)} chats for read/update ops...")

        seed_ids: list[int] = []
        for i in range(max(concurrency, 10)):
            response = await client.post(
                "/chat/create", json={"title": f"seed-{i}", "mode": "chat"}
            )
            response.raise_for_status()
            seed_ids.append(response.json()["id"])

        print(f"Pre-creating {requests} disposable chats for the delete phase...")

        delete_target_ids: list[int] = []
        for i in range(requests):
            response = await client.post(
                "/chat/create", json={"title": f"delete-target-{i}", "mode": "chat"}
            )
            response.raise_for_status()
            delete_target_ids.append(response.json()["id"])

        print()
        print(f"Running {requests} requests at concurrency={concurrency} per phase\n")

        results: list[EndpointResult] = []

        results.append(
            await _run_phase(
                "create",
                concurrency,
                requests,
                lambda i: client.post(
                    "/chat/create",
                    json={"title": f"load-{i}", "mode": "chat"},
                ),
            )
        )

        results.append(
            await _run_phase(
                "list",
                concurrency,
                requests,
                lambda i: client.get("/app/"),
            )
        )

        results.append(
            await _run_phase(
                "messages",
                concurrency,
                requests,
                lambda i: client.get(
                    "/chat/messages",
                    params={"chat_id": seed_ids[i % len(seed_ids)]},
                ),
            )
        )

        results.append(
            await _run_phase(
                "update_title",
                concurrency,
                requests,
                lambda i: client.patch(
                    "/chat/title",
                    json={
                        "chat_id": seed_ids[i % len(seed_ids)],
                        "title": f"updated-{i}",
                    },
                ),
            )
        )

        results.append(
            await _run_phase(
                "delete",
                concurrency,
                requests,
                lambda i: client.delete(f"/chat/{delete_target_ids[i]}"),
            )
        )

        print("Results:\n")
        for result in results:
            print(result.summary_line())

        print("\nCleaning up seeded chats...")
        for chat_id in seed_ids:
            await client.delete(f"/chat/{chat_id}")

        print("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8000/api")
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--requests", type=int, default=100)
    args = parser.parse_args()

    asyncio.run(main(args.base_url, args.concurrency, args.requests))
