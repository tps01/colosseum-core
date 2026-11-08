"""Write-queue batching vs barrier (drain / put_and_wait) latency."""

from __future__ import annotations

import threading
import time

import pytest

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
        # Distinguishes an immediate barrier from the 0.5s idle batch interval.
        assert elapsed < 0.35, f"drain waited {elapsed:.3f}s (batch interval is 0.5s)"
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
        # Distinguishes an immediate barrier from the 0.5s idle batch interval.
        assert elapsed < 0.35, f"put_and_wait waited {elapsed:.3f}s"
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
        deadline = time.perf_counter() + 0.4
        while commits < 1 and time.perf_counter() < deadline:
            time.sleep(0.005)
        assert commits == 1
        assert applied == [0, 1, 2, 3]
    finally:
        queue.stop(timeout=2.0)


def test_commit_failure_reaches_waiter_and_shutdown() -> None:
    def fail():
        raise OSError("disk unavailable")

    queue = DatabaseWriteQueue(lock=threading.RLock(), commit=fail)
    queue.start()
    try:
        with pytest.raises(OSError, match="disk unavailable"):
            queue.put_and_wait(WriteJob(apply=lambda: None), timeout=0.3)
    finally:
        try:
            queue.stop(timeout=0.3)
        except (OSError, TimeoutError):
            pass
    assert not queue.started


def test_stop_timeout_retains_worker_and_repeated_stop_finishes():
    entered, release = threading.Event(), threading.Event()

    def held_write():
        entered.set()
        release.wait(2)

    queue = DatabaseWriteQueue(lock=threading.RLock(), commit=lambda: None, batch_size=1)
    queue.start()
    queue.put(WriteJob(apply=held_write))
    try:
        assert entered.wait(1)
        with pytest.raises(TimeoutError, match="did not stop"):
            queue.stop(timeout=0.001)
        assert queue.started and queue._thread.is_alive()
        with pytest.raises(RuntimeError, match="not accepting"):
            queue.put(WriteJob(apply=lambda: None))
    finally:
        release.set()
        queue.stop(timeout=2)
        queue.stop(timeout=2)
    assert not queue.started and queue._thread is None


def test_finalization_snapshots_after_pending_writes(tmp_path, monkeypatch) -> None:
    from colosseum.context import init_context
    from colosseum.database import MeasurementRow
    from colosseum.runner.runtime import ensure_runtime_ready
    from colosseum.results.finalize import finalize_run
    from colosseum.results.finalize_policy import policy_for_single

    gate = threading.Event()
    original_run = DatabaseWriteQueue._run

    def held_run(self):
        gate.wait(2)
        original_run(self)

    monkeypatch.setattr(DatabaseWriteQueue, "_run", held_run)
    ctx = init_context(test_case_name="pending", no_artifacts=True)
    ensure_runtime_ready(ctx)
    # The unit tier replaces initialize; restore a real writer for this boundary test.
    ctx.db._start_write_queue()
    ctx.db.enqueue_measurement(MeasurementRow(domain="core", command="listener", key="a", value=1))
    original_drain = ctx.db.drain

    def release(**kwargs):
        gate.set()
        original_drain(**kwargs)

    monkeypatch.setattr(ctx.db, "drain", release)
    try:
        result = finalize_run(ctx, policy=policy_for_single(run_shutdown=False))
        assert result.measurement_count == 1
        assert [row.value for row in result.measurements] == [1]
    finally:
        gate.set()
        ctx.db.close()
