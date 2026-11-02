"""Subprocess probe: loading plugins must fail when contract_broken is installed."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import colosseum as col
from colosseum.plugins.registry import PluginRegistrationError


def main() -> None:
    config = Path(os.environ["CONTRACT_BROKEN_CONFIG"])
    try:
        # load_config initializes runtime and calls ensure_plugins_loaded.
        col.config.load_config(str(config))
    except PluginRegistrationError as exc:
        text = str(exc)
        if "contract_broken" not in text:
            raise SystemExit(f"error missing entry-point name: {text}") from exc
        print(f"PluginRegistrationError:{text}")
        sys.exit(2)
    raise SystemExit("expected PluginRegistrationError was not raised")


if __name__ == "__main__":
    main()
