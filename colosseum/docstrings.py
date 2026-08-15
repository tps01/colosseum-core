"""Shared Sphinx-style docstring helpers for first-party APIs."""

from __future__ import annotations

ParamSpec = tuple[str, str, str]  # name, type_name, description


def sphinx_param(name: str, type_name: str, description: str, *, optional: bool = False) -> str:
    """Format a Sphinx ``:param:`` / ``:type:`` pair.

    :param name: Parameter name.
    :type name: str
    :param type_name: Type annotation text for ``:type:``.
    :type type_name: str
    :param description: Parameter description for ``:param:``.
    :type description: str
    :param optional: When ``True``, append ``, optional`` to the type line.
    :type optional: bool, optional

    :returns: Two-line Sphinx field block.
    :rtype: str
    """
    type_line = f"{type_name}, optional" if optional else type_name
    return f":param {name}: {description}\n:type {name}: {type_line}"
