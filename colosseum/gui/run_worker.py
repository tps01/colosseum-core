from __future__ import annotations

import queue
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

from ..output.runs import find_run_directory
from ..runner.suite import load_suite_toml


class RunKind(Enum):
    TEST = auto()
    SUITE = auto()


@dataclass
class RunRequest:
    kind: RunKind
    path: Path
    config_path: str | None
    verbose: bool


@dataclass
class RunFinished:
    run_dir: Path | None
    exit_code: int


class RunWorker:
    """Background subprocess runner with debug.log tailing."""

    def __init__(self, cwd: Path | None = None) -> None:
        self._cwd = cwd or Path.cwd()
        self._queue: queue.Queue = queue.Queue()
        self._thread: threading.Thread | None = None
        self._process: subprocess.Popen | None = None
        self._stop_requested = False

    @property
    def events(self) -> queue.Queue:
        return self._queue

    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def stop(self) -> None:
        self._stop_requested = True
        proc = self._process
        if proc is None or proc.poll() is not None:
            return
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    def start(self, request: RunRequest) -> None:
        if self.is_running():
            raise RuntimeError("A run is already in progress")
        self._stop_requested = False
        self._thread = threading.Thread(target=self._run, args=(request,), daemon=True)
        self._thread.start()

    def _logical_name(self, request: RunRequest) -> str:
        if request.kind == RunKind.TEST:
            return request.path.stem
        suite = load_suite_toml(request.path)
        return suite.name

    def _build_argv(self, request: RunRequest) -> list[str]:
        argv = [sys.executable, "-m", "colosseum.runner.cli"]
        if request.kind == RunKind.TEST:
            argv.extend(["run", str(request.path)])
        else:
            argv.extend(["run-suite", str(request.path)])
        if request.config_path:
            argv.extend(["--config", request.config_path])
        if request.verbose:
            argv.append("--verbose")
        return argv

    def _tail_log(self, log_path: Path, offset: int) -> tuple[int, list[str]]:
        if not log_path.is_file():
            return offset, []
        data = log_path.read_bytes()
        if len(data) <= offset:
            return offset, []
        chunk = data[offset:]
        new_offset = len(data)
        text = chunk.decode("utf-8", errors="replace")
        return new_offset, text.splitlines()

    def _run(self, request: RunRequest) -> None:
        logical_name = self._logical_name(request)
        start_time = time.time()
        argv = self._build_argv(request)
        self._queue.put(("started", logical_name))

        try:
            self._process = subprocess.Popen(
                argv,
                cwd=str(self._cwd),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError as exc:
            self._queue.put(("error", str(exc)))
            self._process = None
            return

        run_dir: Path | None = None
        log_offset = 0
        proc = self._process

        while proc.poll() is None or (run_dir is None and not self._stop_requested):
            if run_dir is None:
                run_dir = find_run_directory(self._cwd, logical_name, since=start_time - 1.0)
                if run_dir is None:
                    run_dir = find_run_directory(self._cwd, logical_name, since=None)

            if run_dir is not None:
                log_path = run_dir / "debug.log"
                log_offset, lines = self._tail_log(log_path, log_offset)
                for line in lines:
                    self._queue.put(("log", line))

            if proc.poll() is not None:
                break
            time.sleep(0.3)

        exit_code = proc.wait()
        if run_dir is None:
            run_dir = find_run_directory(self._cwd, logical_name, since=start_time - 1.0)
        if run_dir is None:
            run_dir = find_run_directory(self._cwd, logical_name, since=None)

        if run_dir is not None:
            log_path = run_dir / "debug.log"
            log_offset, lines = self._tail_log(log_path, log_offset)
            for line in lines:
                self._queue.put(("log", line))

        self._queue.put(("finished", RunFinished(run_dir=run_dir, exit_code=exit_code)))
        self._process = None
