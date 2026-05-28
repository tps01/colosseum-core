from .aggregation import ResultAggregator


def endex():
    from .exit_policy import endex as _endex

    return _endex()

__all__ = ["ResultAggregator", "endex"]
