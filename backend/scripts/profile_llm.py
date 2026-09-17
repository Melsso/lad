"""Profiling for LAD's LLM-touching paths (chat mode and agent mode).

This is deliberately NOT a load test. Local Ollama inference is the
bottleneck for these endpoints, not LAD's own code, so throwing concurrency
at them mostly measures how a single machine's model inference queues under
load -- not anything actionable about the app. See load_test_crud.py for the
endpoints where real concurrency testing is actually meaningful.

Part 1 (sequential): times four representative, deliberately simple
messages -- a trivial no-tool reply, a single-web_search reply, a single
run_command call, and a clean two-tool-call flow -- and reports
time-to-first-event and total duration for each. This is the "how does it
feel to use, on this machine" baseline.

Part 2 (small bounded concurrency): runs the same simple two-file task in
two separate agent-mode chats, first solo then concurrently, to see how much
a second simultaneous agent-mode chat degrades the first (expected, given
the sandbox container's fixed 0.5 CPU / 512MB budget shared across all
chats) and to confirm the two chats' sandboxed files never cross-contaminate
(a real correctness check, not a performance one).

Usage:
    poetry run python scripts/profile_llm.py
    poetry run python scripts/profile_llm.py --base-url http://localhost:8000/api --repeat 3
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
import uuid
from dataclasses import dataclass, field

import httpx


@dataclass
class StreamOutcome:
    event_order: list[str] = field(default_factory=list)
    time_to_first_event_ms: float = 0.0
    total_duration_ms: float = 0.0
    final_content: str = ""
    tool_results: list[str] = field(default_factory=list)
    ok: bool = True
    error: str = ""


async def create_chat(client: httpx.AsyncClient, mode: str, title: str) -> int:
    response = await client.post("/chat/create", json={"title": title, "mode": mode})
    response.raise_for_status()
    return response.json()["id"]


async def delete_chat(client: httpx.AsyncClient, chat_id: int) -> None:
    await client.delete(f"/chat/{chat_id}")


async def stream_message(
    client: httpx.AsyncClient, chat_id: int, msg: str
) -> StreamOutcome:
    outcome = StreamOutcome()
    start = time.perf_counter()
    first_event_recorded = False

    event_name = ""

    async with client.stream(
        "POST",
        "/chat/msg/stream",
        data={"chat_id": str(chat_id), "msg": msg},
        timeout=180.0,
    ) as response:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            outcome.ok = False
            outcome.error = str(exc)
            return outcome

        async for line in response.aiter_lines():
            if line.startswith("event:"):
                event_name = line.removeprefix("event:").strip()
                continue

            if line.startswith("data:"):
                if not first_event_recorded:
                    outcome.time_to_first_event_ms = (
                        time.perf_counter() - start
                    ) * 1000
                    first_event_recorded = True

                outcome.event_order.append(event_name)
                payload = json.loads(line.removeprefix("data:").strip())

                if event_name == "tool_result":
                    outcome.tool_results.append(payload.get("content", ""))

                if event_name == "done":
                    outcome.final_content = payload.get("content", "")

                if event_name == "error":
                    outcome.ok = False
                    outcome.error = payload.get("detail", "unknown error")

    outcome.total_duration_ms = (time.perf_counter() - start) * 1000
    return outcome


def _report(label: str, outcomes: list[StreamOutcome]) -> None:
    ok_outcomes = [o for o in outcomes if o.ok]

    print(f"\n{label}")
    print(
        f"  events: {' -> '.join(ok_outcomes[0].event_order) if ok_outcomes else 'n/a'}"
    )

    if not ok_outcomes:
        for o in outcomes:
            print(f"  FAILED: {o.error}")
        return

    ttfe = [o.time_to_first_event_ms for o in ok_outcomes]
    total = [o.total_duration_ms for o in ok_outcomes]

    if len(ok_outcomes) == 1:
        print(f"  time to first event: {ttfe[0]:.0f}ms")
        print(f"  total duration:      {total[0]:.0f}ms")
    else:
        print(
            f"  time to first event: min={min(ttfe):.0f}ms "
            f"median={statistics.median(ttfe):.0f}ms max={max(ttfe):.0f}ms"
        )
        print(
            f"  total duration:      min={min(total):.0f}ms "
            f"median={statistics.median(total):.0f}ms max={max(total):.0f}ms"
        )

    failed = len(outcomes) - len(ok_outcomes)
    if failed:
        print(f"  {failed}/{len(outcomes)} runs failed")

    print(f"  final reply: {ok_outcomes[-1].final_content[:200]!r}")


async def run_part_1(client: httpx.AsyncClient, repeat: int) -> None:
    print("=" * 70)
    print("PART 1: sequential profiling (single request at a time)")
    print("=" * 70)

    cases = [
        ("plain_trivial", "chat", "What's 2+2?"),
        ("plain_web_search", "chat", "What's the weather in Paris right now?"),
        (
            "agent_single_tool",
            "agent",
            "Run the command `pwd` and tell me its output.",
        ),
        (
            "agent_two_tool",
            "agent",
            (
                "In one command, write the text 'hello world' to a file "
                "named greeting.txt. Then, in a second command, read that "
                "file back and tell me exactly what it contains."
            ),
        ),
    ]

    for name, mode, msg in cases:
        outcomes = []
        for i in range(repeat):
            chat_id = await create_chat(client, mode, f"profile-{name}-{i}")
            outcomes.append(await stream_message(client, chat_id, msg))
            await delete_chat(client, chat_id)
        _report(name, outcomes)


async def run_part_2(client: httpx.AsyncClient) -> None:
    print("\n" + "=" * 70)
    print("PART 2: two agent-mode chats, solo vs concurrent")
    print("=" * 70)
    print(
        "Note: any slowdown under concurrency is expected -- the sandbox "
        "container has a fixed 0.5 CPU / 512MB budget shared by every chat. "
        "The only real pass/fail here is the contamination check."
    )

    token_a = uuid.uuid4().hex[:8]
    token_b = uuid.uuid4().hex[:8]

    def task_for(token: str) -> str:
        return (
            f"In one command, write the exact text '{token}' to a file "
            f"named marker.txt. Then, in a second command, read that file "
            f"back and tell me exactly what it contains."
        )

    chat_a = await create_chat(client, "agent", "profile-contention-a")
    chat_b = await create_chat(client, "agent", "profile-contention-b")

    print("\nRunning solo (A then B, one at a time)...")
    solo_a = await stream_message(client, chat_a, task_for(token_a))
    solo_b_chat = await create_chat(client, "agent", "profile-contention-b-solo")
    solo_b = await stream_message(client, solo_b_chat, task_for(token_b))
    await delete_chat(client, solo_b_chat)

    print("Running concurrently (A and B at the same time)...")
    concurrent_chat_a = await create_chat(client, "agent", "profile-contention-a-2")
    concurrent_chat_b = await create_chat(client, "agent", "profile-contention-b-2")

    concurrent_a, concurrent_b = await asyncio.gather(
        stream_message(client, concurrent_chat_a, task_for(token_a)),
        stream_message(client, concurrent_chat_b, task_for(token_b)),
    )

    print(f"\n  solo A:       {solo_a.total_duration_ms:.0f}ms")
    print(f"  solo B:       {solo_b.total_duration_ms:.0f}ms")
    print(f"  concurrent A: {concurrent_a.total_duration_ms:.0f}ms")
    print(f"  concurrent B: {concurrent_b.total_duration_ms:.0f}ms")

    def contains_token(outcome: StreamOutcome, token: str) -> bool:
        haystack = " ".join(outcome.tool_results) + outcome.final_content
        return token in haystack

    a_clean = contains_token(concurrent_a, token_a) and not contains_token(
        concurrent_a, token_b
    )
    b_clean = contains_token(concurrent_b, token_b) and not contains_token(
        concurrent_b, token_a
    )

    print(
        f"\n  contamination check: "
        f"{'PASS' if a_clean and b_clean else 'FAIL - cross-chat contamination detected'}"
    )

    for chat_id in (chat_a, chat_b, concurrent_chat_a, concurrent_chat_b):
        await delete_chat(client, chat_id)


async def main(base_url: str, repeat: int, skip_part_2: bool) -> None:
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        await run_part_1(client, repeat)

        if not skip_part_2:
            await run_part_2(client)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8000/api")
    parser.add_argument(
        "--repeat", type=int, default=1, help="repeats per case in part 1"
    )
    parser.add_argument("--skip-part-2", action="store_true")
    args = parser.parse_args()

    asyncio.run(main(args.base_url, args.repeat, args.skip_part_2))
