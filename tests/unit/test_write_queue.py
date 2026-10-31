"""Write-queue batching vs barrier (drain / put_and_wait) latency."""

from __future__ import annotations

import threading
import time

from colosseum.database.write_queue import DatabaseWriteQueue, WriteJob


def test_drain_does_not_wait_for_batch_interval() -> None:
    """A drain barrier must flush immediately, not after batch_interval_s."""
    lock = threading.RLock()
    applied: list[str] = []
    queue = DatabaseWriteQueue(
        lock=lock,
        batch_size=32,
        batch_interval_s=0.5,
        commit=lambda: None,
    )
    queue.start()
    try:
        queue.put(WriteJob(apply=lambda: applied.append("a")))
        started = time.perf_counter()
        queue.drain(timeout=2.0)
        elapsed = time.perf_counter() - started
        assert applied == ["a"]
        assert elapsed < 0.1, f"drain waited {elapsed:.3f}s (batch interval is 0.5s)"
    finally:
        queue.stop(timeout=2.0)


def test_put_and_wait_flushes_without_batch_interval() -> None:
    lock = threading.RLock()
    applied: list[str] = []
    queue = DatabaseWriteQueue(
        lock=lock,
        batch_size=32,
        batch_interval_s=0.5,
        commit=lambda: None,
    )
    queue.start()
    try:
        started = time.perf_counter()
        queue.put_and_wait(WriteJob(apply=lambda: applied.append("sync")), timeout=2.0)
        elapsed = time.perf_counter() - started
        assert applied == ["sync"]
        assert elapsed < 0.1, f"put_and_wait waited {elapsed:.3f}s"
    finally:
        queue.stop(timeout=2.0)


def test_fire_and_forget_still_batches_until_size() -> None:
    lock = threading.RLock()
    commits = 0
    applied: list[int] = []

    def commit() -> None:
        nonlocal commits
        commits += 1

    queue = DatabaseWriteQueue(
        lock=lock,
        batch_size=4,
        batch_interval_s=0.5,
        commit=commit,
    )
    queue.start()
    try:
        for index in range(4):
            queue.put(WriteJob(apply=lambda i=index: applied.append(i)))
        # Size-triggered flush should land without waiting on the idle interval.
        deadline = time.perf_counter() + 0.2
        while commits < 1 and time.perf_counter() < deadline:
            time.sleep(0.005)
        assert commits == 1
        assert applied == [0, 1, 2, 3]
    finally:
        queue.stop(timeout=2.0)
