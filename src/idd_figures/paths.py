"""Loader for absolute, machine-specific paths.

idd-figures is primarily a plotting library and usually receives its data via
caller-supplied callbacks (see ``plot_map``), so most code never needs absolute
paths. When a script or notebook genuinely does, call :func:`load_paths` rather
than hardcoding ``/ihme``, ``/mnt/share``, ``/snfs1`` etc. — those strings must
never be committed to this public repo (STANDARDS §Path safety).

This loader is function-based (not import-time) on purpose: ``import
idd_figures`` must succeed on a machine that has no ``paths.yaml``. The scaffold
template raises at import; that is wrong for an importable library, so this is a
documented deviation (see .claude/DECISIONS.md).
"""

from pathlib import Path
from typing import Any

import yaml

_PATHS_FILE = Path(__file__).resolve().parents[2] / "paths.yaml"


def load_paths() -> dict[str, Any]:
    """Return the contents of ``paths.yaml`` as a dict.

    Raises:
        FileNotFoundError: if ``paths.yaml`` does not exist. Copy
            ``paths.yaml.example`` to ``paths.yaml`` and edit it for your machine.
    """
    if not _PATHS_FILE.exists():
        msg = (
            f"paths.yaml missing at {_PATHS_FILE}. "
            "Run: cp paths.yaml.example paths.yaml; then edit the values."
        )
        raise FileNotFoundError(msg)
    with _PATHS_FILE.open() as f:
        return yaml.safe_load(f)
