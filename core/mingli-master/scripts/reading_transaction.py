#!/usr/bin/env python3
"""Production entrypoint: the one-shot JSON codec for reading commands.

This module is only a doorway to :mod:`adapters.json_cli`. It keeps no
state, stores no tokens, builds no caller policy and never reads the
reading store directly; hosts speak exactly one Command JSON on stdin and
receive exactly one Result JSON on stdout.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from adapters.json_cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
