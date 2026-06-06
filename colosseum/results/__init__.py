from typing import NoReturn

from .aggregation import ResultAggregator


def endex() -> NoReturn:
    from .exit_policy import endex as _endex

    _endex()


__all__ = ["ResultAggregator", "endex"]
