from __future__ import annotations

import logging
from typing import Any, cast

from colosseum_shared.parsing.text import strip_response

_logger = logging.getLogger("colosseum.shared")


class SSHClientWrapper:
    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config
        self._client: Any = None
        driver = str(config.get("driver", "ssh")).lower()
        if driver == "sim":
            self._sim = True
            _logger.debug("SSH client id sim mode enabled")
        else:
            self._sim = False
            self._connect_paramiko()

    def _connect_paramiko(self) -> None:
        try:
            import paramiko
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "paramiko is required for SSH. Install with: pip install colosseum[ssh]"
            ) from exc

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # nosec B507  # bench DUT SSH
        connect_kwargs = {
            "hostname": self._config["host"],
            "port": int(self._config.get("port", 22)),
            "username": self._config["username"],
            "timeout": float(self._config.get("timeout", 30.0)),
        }
        password = self._config.get("password")
        key_filename = self._config.get("key_filename") or ""
        if key_filename:
            connect_kwargs["key_filename"] = key_filename
        elif password is not None:
            connect_kwargs["password"] = password
            connect_kwargs["allow_agent"] = False
            connect_kwargs["look_for_keys"] = False
        client.connect(**connect_kwargs)
        self._client = cast(Any, client)
        _logger.debug(
            "SSH connected to %s:%s as %s",
            connect_kwargs["hostname"],
            connect_kwargs["port"],
            connect_kwargs["username"],
        )

    def exec_stdout(self, command: str, timeout: float = 30.0) -> str:
        _logger.debug("SSH exec: %s (timeout=%ss)", command, timeout)
        if self._sim:
            response = self._sim_stdout(command)
        else:
            assert self._client is not None
            _stdin, stdout, _stderr = self._client.exec_command(  # nosec B601  # test script command
                command, timeout=timeout
            )
            response = strip_response(stdout.read().decode("utf-8", errors="replace"))
        preview = response[:200] + ("..." if len(response) > 200 else "")
        _logger.debug("SSH stdout: %r", preview)
        return response

    def _sim_stdout(self, command: str) -> str:
        cmd = command.strip()
        if "version" in cmd:
            return "v1.2.3"
        if "os-release" in cmd:
            return "present"
        return "ok"

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
