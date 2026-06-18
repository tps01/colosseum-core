"""Unit tests for colosseum.resource_cache helpers."""

from __future__ import annotations

import logging

from colosseum.resource_cache import cached_resource, close_cached_resources


def test_cached_resource_opens_once() -> None:
    cache: dict[str, object] = {}
    calls = {"count": 0}

    def loader() -> str:
        calls["count"] += 1
        return "resource"

    first = cached_resource(cache, "key", loader)
    second = cached_resource(cache, "key", loader)

    assert first is second
    assert calls["count"] == 1


def test_close_cached_resources_honors_prefix_group_order() -> None:
    cache: dict[str, object] = {}
    order: list[str] = []

    class _Resource:
        def __init__(self, label: str) -> None:
            self._label = label

        def close(self) -> None:
            order.append(self._label)

    cache["instrument:psu:1"] = _Resource("instrument")
    cache["io:backend:dio:1"] = _Resource("io")
    cache["equipment:psu:1"] = _Resource("equipment")

    close_cached_resources(
        cache,
        (("instrument:",), ("io:backend:",), ("equipment:",)),
    )

    assert order == ["instrument", "io", "equipment"]
    assert cache == {}


def test_close_cached_resources_logs_failures_and_continues(caplog) -> None:
    cache: dict[str, object] = {}
    order: list[str] = []

    class _Fail:
        def close(self) -> None:
            raise RuntimeError("boom")

    class _Ok:
        def close(self) -> None:
            order.append("ok")

    cache["equipment:a:1"] = _Fail()
    cache["equipment:b:1"] = _Ok()

    with caplog.at_level(logging.ERROR, logger="colosseum.test"):
        close_cached_resources(cache, (("equipment:",),), logger=logging.getLogger("colosseum.test"))

    assert order == ["ok"]
    assert cache == {}
