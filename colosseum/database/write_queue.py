"""Background SQLite write queue for thread-safe evidence inserts."""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class _StopSentinel:
    pass


_STOP = _StopSentinel()


@dataclass
class WriteJob:
    """One queued write. ``apply`` runs under the DB manager lock."""

    apply: Callable[[], None]
    done: threading.Event | None = None
    error: list[BaseException] | None = None


class DatabaseWriteQueue:
    """Serialize DB writes from a dedicated consumer thread.

    Producers call :meth:`put` (non-blocking) or :meth:`put_and_wait`.
    The consumer owns applying jobs under ``lock`` so listeners never touch
    the SQLite connection directly.
    """

    def __init__(
        self,
        *,
        lock: threading.Lock,
        batch_size: int = 32,
        batch_interval_s: float = 0.05,
        commit: Callable[[], None],
    ) -> None:
        self._lock = lock
        self._batch_size = max(1, batch_size)
        self._batch_interval_s = max(0.001, batch_interval_s)
        self._commit = commit
        self._queue: queue.Queue[WriteJob | _StopSentinel] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._started = False

    @property
    def started(self) -> bool:
        return self._started

    def start(self) -> None:
        if self._started:
            return
        self._started = True
        self._thread = threading.Thread(
            target=self._run,
            name="colosseum-db-writer",
            daemon=True,
        )
        self._thread.start()

    def put(self, job: WriteJob) -> None:
        if not self._started:
            raise RuntimeError("Database write queue is not started")
        self._queue.put(job)

    def put_and_wait(self, job: WriteJob, *, timeout: float | None = None) -> None:
        done = threading.Event()
        job.done = done
        job.error = []
        self.put(job)
        if not done.wait(timeout=timeout):
            raise TimeoutError("Timed out waiting for database write queue")
        if job.error:
            raise job.error[0]

    def drain(self, *, timeout: float | None = 30.0) -> None:
        """Block until all queued jobs are applied and committed."""
        if not self._started:
            return
        done = threading.Event()
        self._queue.put(
            WriteJob(apply=lambda: None, done=done, error=[]),
        )
        if not done.wait(timeout=timeout):
            raise TimeoutError("Timed out draining database write queue")

    def stop(self, *, timeout: float | None = 30.0) -> None:
        if not self._started:
            return
        self.drain(timeout=timeout)
        self._queue.put(_STOP)
        if self._thread is not None:
            self._thread.join(timeout=timeout)
        self._thread = None
        self._started = False

    def _run(self) -> None:
        batch: list[WriteJob] = []
        while True:
            try:
                item = self._queue.get(timeout=self._batch_interval_s)
            except queue.Empty:
                if batch:
                    self._flush(batch)
                    batch = []
                continue
            if isinstance(item, _StopSentinel):
                if batch:
                    self._flush(batch)
                return
            batch.append(item)
            if len(batch) >= self._batch_size:
                self._flush(batch)
                batch = []

    def _flush(self, batch: list[WriteJob]) -> None:
        with self._lock:
            for job in batch:
                try:
                    job.apply()
                except BaseException as exc:  # noqa: BLE001 — surface to waiter
                    if job.error is not None:
                        job.error.append(exc)
                    elif job.done is None:
                        raise
            try:
                self._commit()
            except BaseException as exc:  # noqa: BLE001
                for job in batch:
                    if job.error is not None and not job.error:
                        job.error.append(exc)
                raise
        for job in batch:
            if job.done is not None:
                job.done.set()
