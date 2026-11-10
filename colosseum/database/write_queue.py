"""Background SQLite write queue for thread-safe evidence inserts."""

from __future__ import annotations

import queue
import threading
from contextlib import suppress
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class _StopSentinel:
    pass


@dataclass(frozen=True)
class _IdleTimeout:
    pass


_STOP = _StopSentinel()
_IDLE_TIMEOUT = _IdleTimeout()


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

    Fire-and-forget jobs still batch up to ``batch_size`` or idle
    ``batch_interval_s``. Jobs with a ``done`` event (``drain`` /
    ``put_and_wait``) flush the current batch immediately so barriers do not
    wait out the idle interval.
    """

    def __init__(
        self,
        *,
        lock: threading.RLock,
        batch_size: int = 32,
        batch_interval_s: float = 0.05,
        commit: Callable[[], None],
        rollback: Callable[[], None] | None = None,
    ) -> None:
        self._lock = lock
        self._batch_size = max(1, batch_size)
        self._batch_interval_s = max(0.001, batch_interval_s)
        self._commit = commit
        self._rollback = rollback
        self._queue: queue.Queue[WriteJob | _StopSentinel] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._started = False
        self._closing = False
        self._failure: BaseException | None = None
        self._state_lock = threading.Lock()

    @property
    def started(self) -> bool:
        return self._started

    def start(self) -> None:
        if self._started:
            return
        if self._failure is not None:
            raise self._failure
        self._closing = False
        self._started = True
        self._thread = threading.Thread(
            target=self._run,
            name="colosseum-db-writer",
            daemon=True,
        )
        self._thread.start()

    def put(self, job: WriteJob) -> None:
        with self._state_lock:
            if self._failure is not None:
                raise self._failure
            if not self._started or self._closing:
                raise RuntimeError("Database write queue is not accepting writes")
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
        self.put_and_wait(WriteJob(apply=lambda: None), timeout=timeout)

    def stop(self, *, timeout: float | None = 30.0) -> None:
        if not self._started:
            return
        with self._state_lock:
            if not self._closing:
                self._closing = True
                self._queue.put(_STOP)
        thread = self._thread
        if thread is not None:
            thread.join(timeout=timeout)
            if thread.is_alive():
                raise TimeoutError("Database write queue did not stop")
        self._thread = None
        self._started = False
        if self._failure is not None:
            raise self._failure

    def _next_event(self) -> _IdleTimeout | _StopSentinel | WriteJob:
        try:
            return self._queue.get(timeout=self._batch_interval_s)
        except queue.Empty:
            return _IDLE_TIMEOUT

    def _run(self) -> None:
        batch: list[WriteJob] = []
        try:
            while True:
                event = self._next_event()
                if isinstance(event, _IdleTimeout):
                    if batch:
                        self._flush(batch)
                        batch = []
                    continue
                if isinstance(event, _StopSentinel):
                    if batch:
                        self._flush(batch)
                    return
                batch.append(event)
                if len(batch) >= self._batch_size or event.done is not None:
                    self._flush(batch)
                    batch = []
        except BaseException as exc:  # noqa: BLE001 — forward worker failures to callers
            self._fail_batch(batch, exc)

    def _fail_batch(self, batch: list[WriteJob], exc: BaseException) -> None:
        with self._state_lock:
            self._failure = exc
            while not self._queue.empty():
                pending = self._queue.get_nowait()
                if isinstance(pending, WriteJob):
                    batch.append(pending)
        if self._rollback is not None:
            # Preserve the original storage failure if rollback also fails.
            with self._lock, suppress(Exception):
                self._rollback()
        for job in batch:
            if job.error is not None:
                job.error.append(exc)
            if job.done is not None:
                job.done.set()

    def _flush(self, batch: list[WriteJob]) -> None:
        with self._lock:
            for job in batch:
                job.apply()
            self._commit()
        for job in batch:
            if job.done is not None:
                job.done.set()
