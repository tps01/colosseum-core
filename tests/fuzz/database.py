"""Model-based evidence round trips and queue lifecycle fuzzing, without plugins."""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
from contextlib import closing, suppress
from dataclasses import asdict
from pathlib import Path


def check_input(data: bytes) -> None:
    """Compare short operation sequences with an independently retained row model."""
    from colosseum.database.manager import DatabaseManager, MeasurementRow

    text = data[16:144].decode("utf-8", errors="replace")
    number = int.from_bytes(data[16:24], "big", signed=True)
    values = (
        None,
        False,
        number,
        number / 1024,
        text,
        [text, number, None],
        {"text": text, "n": number},
    )
    deferred = bool(data and data[0] & 1)
    expected = []

    def projection(row: MeasurementRow) -> dict:
        result = asdict(row)
        result.pop("id")
        return result

    def assert_rows(db: DatabaseManager, path: Path) -> None:
        assert json.dumps(
            [projection(row) for row in db.fetch_all_measurements()],
            sort_keys=True,
        ) == json.dumps(expected, sort_keys=True)
        # A separate connection observes committed rows, independently of the manager reader.
        with closing(sqlite3.connect(path)) as reader:
            stored = reader.execute(
                "SELECT domain, command, key, row_index, value_json, units, artifact_path, "
                "status, timestamp FROM measurements ORDER BY id",
            ).fetchall()
        assert len(stored) == len(expected)
        for actual, model in zip(stored, expected):
            assert actual[:4] == (
                model["domain"],
                model["command"],
                model["key"],
                model["row_index"],
            )
            value = json.loads(actual[4]) if actual[4] is not None else None
            assert json.dumps(value, sort_keys=True) == json.dumps(model["value"], sort_keys=True)
            assert actual[5:] == (
                model["units"],
                model["artifact_path"],
                model["status"],
                model["timestamp"],
            )
        for model in expected:
            matches = [
                row for row in expected if all(row[field] == model[field] for field in ("domain", "command", "key"))
            ]
            rows = db.list_measurements(model["domain"], model["command"], model["key"])
            assert [projection(row) for row in rows] == matches
            latest = next(row for row in reversed(matches) if row["row_index"] == model["row_index"])
            found = db.get_measurement(
                model["domain"],
                model["command"],
                model["key"],
                model["row_index"],
            )
            assert found is not None and projection(found) == latest
        assert db.get_measurement("missing", "missing", "missing") is None

    with tempfile.TemporaryDirectory(prefix="colosseum-db-fuzz-") as temporary:
        path = Path(temporary) / "evidence.sqlite"
        db = DatabaseManager()
        db.initialize(path)
        db.defer_commits = deferred
        try:
            # At most 17 writes/actions; input bytes also choose values and repeated keys.
            for index, opcode in enumerate(b"\x00" + data[:16]):
                row = MeasurementRow(
                    domain=f"domain{opcode % 2}",
                    command=f"command{opcode % 3}",
                    key=("key", "key'\x00\n", text)[opcode % 3],
                    row_index=opcode % 2,
                    value=values[(opcode + index) % len(values)],
                    units=None if opcode & 1 else text,
                    status=("PASS", "FAIL", "ERROR")[opcode % 3],
                    timestamp="2026-01-01T00:00:00+00:00",
                )
                action = opcode % 8
                if action < 3:
                    db.enqueue_measurement(row)
                    expected.append(projection(row))
                elif action == 3:
                    db.drain(timeout=2)
                    assert_rows(db, path)
                elif action == 4:
                    db.drain(timeout=2)
                    db.insert_measurement(row)
                    expected.append(projection(row))
                elif action == 5:
                    db.flush()
                    assert_rows(db, path)
                else:
                    db.close()
                    db.close()
                    if action == 7:
                        try:
                            db.enqueue_measurement(row)
                        except RuntimeError:
                            pass
                        else:
                            raise AssertionError("Write accepted after close")
                    db.open_readonly(path)
                    assert_rows(db, path)
                    db.close()
                    db.initialize(path)
                    db.defer_commits = deferred
            # Close itself must persist pending writes, without a preceding drain.
            db.close()
            db.open_readonly(path)
            assert_rows(db, path)
        finally:
            db.close()

    check_failures(data)
    check_close_boundary(data)


def check_failures(data: bytes) -> None:
    """Keep a committed prefix and roll back one deterministic failing batch."""
    import threading

    from colosseum.database.write_queue import DatabaseWriteQueue, WriteJob

    mode = data[0] if data else 0
    with closing(sqlite3.connect(":memory:", check_same_thread=False)) as conn:
        conn.execute("CREATE TABLE evidence (value INTEGER)")
        conn.execute("INSERT INTO evidence VALUES (-1)")
        conn.commit()

        def commit() -> None:
            if mode & 1:
                raise OSError("controlled commit failure")
            conn.commit()

        def last_write() -> None:
            if not mode & 1:
                raise OSError("controlled apply failure")
            conn.execute("INSERT INTO evidence VALUES (99)")

        queue = DatabaseWriteQueue(
            lock=threading.RLock(),
            batch_size=32,
            batch_interval_s=60,
            commit=commit,
            rollback=conn.rollback,
        )
        queue.start()
        try:
            for value in range(1 + mode % 6):
                queue.put(
                    WriteJob(
                        apply=lambda value=value: conn.execute(
                            "INSERT INTO evidence VALUES (?)",
                            (value,),
                        ),
                    ),
                )
            for operation in (
                lambda: queue.put_and_wait(WriteJob(apply=last_write), timeout=2),
                lambda: queue.put(WriteJob(apply=lambda: None)),
                lambda: queue.drain(timeout=2),
                lambda: queue.stop(timeout=2),
            ):
                try:
                    operation()
                except OSError as exc:
                    assert str(exc) == ("controlled commit failure" if mode & 1 else "controlled apply failure")
                else:
                    raise AssertionError("Storage failure was not propagated")
            assert conn.execute("SELECT value FROM evidence").fetchall() == [(-1,)]
            assert not queue.started and queue._thread is None
            queue.stop(timeout=2)
        finally:
            if queue.started:
                with suppress(OSError):
                    queue.stop(timeout=2)


def check_close_boundary(data: bytes) -> None:
    """Coordinate producer/stop ordering with events, never timing sleeps."""
    import threading
    from unittest.mock import patch

    from colosseum.database.write_queue import DatabaseWriteQueue, WriteJob

    entered, release, closing = threading.Event(), threading.Event(), threading.Event()
    applied, errors = [], []
    before = bool(data and data[0] & 1)

    def held() -> None:
        entered.set()
        if not release.wait(2):
            raise TimeoutError("Harness did not release writer")
        applied.append(0)

    queue = DatabaseWriteQueue(lock=threading.RLock(), batch_size=1, commit=lambda: None)
    original_put = queue._queue.put

    def track(item: object) -> None:
        original_put(item)
        if not isinstance(item, WriteJob):
            closing.set()

    def stop() -> None:
        try:
            queue.stop(timeout=2)
        except Exception as exc:  # noqa: BLE001 - return worker errors to the test thread
            errors.append(exc)

    worker = threading.Thread(target=stop, daemon=True)
    queue.start()
    try:
        queue.put(WriteJob(apply=held))
        assert entered.wait(2)
        if before:
            queue.put(WriteJob(apply=lambda: applied.append(1)))
        with patch.object(queue._queue, "put", side_effect=track):
            worker.start()
            assert closing.wait(2)
            try:
                queue.put(WriteJob(apply=lambda: applied.append(2)))
            except RuntimeError:
                pass
            else:
                raise AssertionError("Write accepted beyond the stop boundary")
            release.set()
            worker.join(2)
        assert not worker.is_alive() and not errors
        assert applied == ([0, 1] if before else [0])
        assert not queue.started
        queue.stop(timeout=2)
    finally:
        release.set()
        if worker.ident is not None:
            worker.join(2)
        if queue.started:
            queue.stop(timeout=2)


def main() -> None:
    """Instrument database imports and run a bounded target via libFuzzer arguments."""
    import atheris

    with atheris.instrument_imports(include=["colosseum"]):
        import colosseum.database.manager  # noqa: F401
    atheris.Setup(sys.argv, atheris.instrument_func(check_input))
    atheris.Fuzz()


if __name__ == "__main__":
    main()
