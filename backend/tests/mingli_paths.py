from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MINGLI_CORE_ROOT = Path(
    os.environ.get(
        "MINGLI_CORE_SOURCE_ROOT",
        str(PROJECT_ROOT / "core" / "mingli-master"),
    )
).expanduser()
MINGLI_CORE_SCRIPTS = MINGLI_CORE_ROOT / "scripts"
MINGLI_RUNTIME_RELEASE_ROOT = Path(
    os.environ.get(
        "MINGLI_RUNTIME_TEST_RELEASE_ROOT",
        str(PROJECT_ROOT / ".runtime" / "v53-time-check-release"),
    )
).expanduser()
