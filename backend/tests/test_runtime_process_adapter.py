import json
import sys
import traceback
from pathlib import Path

import pytest
from app.adapters.runtime import FakeMingliRuntimeAdapter, OneShotMingliRuntimeAdapter
from app.readings.errors import RuntimeTransportError
from app.readings.runtime_contracts import (
    Accepted,
    Complete,
    Describe,
    Described,
    Prepare,
    Prepared,
    Stopped,
)


def _write_executable(path: Path, source: str) -> Path:
    path.write_text(
        source.replace("#!/usr/bin/env python3", f"#!{sys.executable}", 1),
        encoding="utf-8",
    )
    path.chmod(0o700)
    return path


def _described_payload() -> dict[str, object]:
    return {
        "kind": "described",
        "protocol_version": "mingli-portable-interface-v2",
        "manifest_digest": "0" * 64,
        "capabilities": [],
    }


def _adapter(launcher: Path, state_root: Path, **overrides: object) -> OneShotMingliRuntimeAdapter:
    options: dict[str, object] = {
        "launcher_path": launcher,
        "runtime_python_path": Path("/usr/bin/python3"),
        "state_root": state_root,
        "timeout_seconds": 1,
    }
    options.update(overrides)
    return OneShotMingliRuntimeAdapter(**options)  # type: ignore[arg-type]


async def test_process_adapter_sends_one_json_command_on_stdin_and_reads_one_result(
    tmp_path: Path,
) -> None:
    launcher = _write_executable(
        tmp_path / "runtime-fixture",
        """#!/usr/bin/env python3
import json
from pathlib import Path
import sys

raw = sys.stdin.buffer.read()
Path(__file__).with_suffix('.stdin').write_bytes(raw)
command = json.loads(raw)
assert command == {"kind": "describe"}
print(json.dumps({
    "kind": "described",
    "protocol_version": "mingli-portable-interface-v2",
    "manifest_digest": "0" * 64,
    "capabilities": [],
}, separators=(",", ":")))
""",
    )
    state_root = tmp_path / "state"
    state_root.mkdir()
    adapter = _adapter(launcher, state_root)

    result = await adapter.execute(Describe())

    assert isinstance(result, Described)
    assert json.loads(launcher.with_suffix(".stdin").read_bytes()) == {"kind": "describe"}
    assert launcher.with_suffix(".stdin").read_bytes().endswith(b"\n")


async def test_process_adapter_decodes_the_entire_result_union(tmp_path: Path) -> None:
    fake_runtime = FakeMingliRuntimeAdapter()
    intent = {
        "subject_refs": ["fixture:subject"],
        "object_id": "natal",
        "dimension_ids": ["overview"],
        "horizon": {"kind_id": "life", "start": None, "end": None},
        "capability_id": "bazi",
        "comparisons": [],
    }
    prepare_missing = Prepare(query="需要资料", intent=intent, facts={})
    prepare_ready = Prepare(
        query="已有资料",
        intent=intent,
        facts={"fixture:subject": {"fixture_input": "present"}},
    )
    prepared = await fake_runtime.execute(prepare_ready)
    assert isinstance(prepared, Prepared)
    commands_and_results = (
        (Describe(), await fake_runtime.execute(Describe()), Described),
        (prepare_missing, await fake_runtime.execute(prepare_missing), Stopped),
        (prepare_ready, prepared, Prepared),
        (
            Complete(state_token=prepared.state_token, public_copy="fixture copy"),
            await fake_runtime.execute(
                Complete(state_token=prepared.state_token, public_copy="fixture copy")
            ),
            Accepted,
        ),
    )
    for index, (command, expected, result_type) in enumerate(commands_and_results):
        launcher = _write_executable(
            tmp_path / f"runtime-fixture-{index}",
            f"""#!/usr/bin/env python3
import json
import sys
sys.stdin.buffer.read()
sys.stdout.write({json.dumps(expected.to_dict(), ensure_ascii=False)!r} + "\\n")
""",
        )
        state_root = tmp_path / f"state-{index}"
        state_root.mkdir()

        result = await _adapter(launcher, state_root).execute(command)

        assert isinstance(result, result_type)
        assert result.to_dict() == expected.to_dict()


@pytest.mark.parametrize(
    "stdout",
    [
        "",
        "not-json\n",
        json.dumps(_described_payload()) + "\n" + json.dumps(_described_payload()) + "\n",
    ],
    ids=("empty", "malformed", "multiple-results"),
)
async def test_process_adapter_rejects_any_stdout_other_than_exactly_one_json_result(
    tmp_path: Path,
    stdout: str,
) -> None:
    launcher = _write_executable(
        tmp_path / "runtime-fixture",
        f"""#!/usr/bin/env python3
import sys
sys.stdout.write({stdout!r})
""",
    )
    state_root = tmp_path / "state"
    state_root.mkdir()

    with pytest.raises(RuntimeTransportError, match="runtime_invalid_output"):
        await _adapter(launcher, state_root).execute(Describe())


@pytest.mark.parametrize(
    ("stream", "error_code"),
    (("stdout", "runtime_stdout_too_large"), ("stderr", "runtime_stderr_too_large")),
)
async def test_process_adapter_enforces_output_caps_while_the_process_is_running(
    tmp_path: Path,
    stream: str,
    error_code: str,
) -> None:
    launcher = _write_executable(
        tmp_path / "runtime-fixture",
        f"""#!/usr/bin/env python3
import sys
import time
target = getattr(sys, {stream!r}).buffer
target.write(b"x" * 4096)
target.flush()
time.sleep(5)
""",
    )
    state_root = tmp_path / "state"
    state_root.mkdir()

    with pytest.raises(RuntimeTransportError, match=error_code):
        await _adapter(
            launcher,
            state_root,
            max_stdout_bytes=128,
            max_stderr_bytes=128,
        ).execute(Describe())


async def test_process_adapter_rejects_oversized_stdin_before_spawning(
    tmp_path: Path,
) -> None:
    marker = tmp_path / "spawned"
    launcher = _write_executable(
        tmp_path / "runtime-fixture",
        f"""#!/usr/bin/env python3
from pathlib import Path
Path({str(marker)!r}).write_text('spawned')
""",
    )
    state_root = tmp_path / "state"
    state_root.mkdir()
    command = Complete(state_token="opaque-token", public_copy="x" * 1024)

    with pytest.raises(RuntimeTransportError, match="runtime_stdin_too_large"):
        await _adapter(launcher, state_root, max_stdin_bytes=64).execute(command)

    assert not marker.exists()


async def test_process_adapter_timeout_kills_the_entire_process_group(
    tmp_path: Path,
) -> None:
    marker = tmp_path / "orphan-ran"
    launcher = _write_executable(
        tmp_path / "runtime-fixture",
        f"""#!/usr/bin/env python3
import subprocess
import sys
import time
subprocess.Popen([
    sys.executable,
    "-c",
    "import pathlib,time; time.sleep(0.5); pathlib.Path({str(marker)!r}).write_text('orphan')",
])
time.sleep(5)
""",
    )
    state_root = tmp_path / "state"
    state_root.mkdir()

    with pytest.raises(RuntimeTransportError, match="runtime_timed_out"):
        await _adapter(launcher, state_root, timeout_seconds=0.05).execute(Describe())

    await __import__("asyncio").sleep(0.7)
    assert not marker.exists()


async def test_process_adapter_never_exposes_stderr_secrets_or_command_content(
    tmp_path: Path,
) -> None:
    launcher = _write_executable(
        tmp_path / "runtime-fixture",
        """#!/usr/bin/env python3
import sys
raw = sys.stdin.buffer.read()
sys.stderr.buffer.write(raw)
sys.stderr.write("SERVICE_SECRET=test-only-secret-canary\\n")
raise SystemExit(23)
""",
    )
    state_root = tmp_path / "state"
    state_root.mkdir()
    command = Complete(
        state_token="secret-state-token",
        public_copy="用户原文不能进异常",
    )

    with pytest.raises(RuntimeTransportError) as caught:
        await _adapter(launcher, state_root).execute(command)

    rendered = f"{caught.value!s} {caught.value!r}"
    assert rendered == "runtime_nonzero_exit RuntimeTransportError('runtime_nonzero_exit')"
    assert "secret-state-token" not in rendered
    assert "用户原文" not in rendered
    assert "test-only-secret-canary" not in rendered


async def test_process_adapter_scrubs_untrusted_result_values_from_exception_chains(
    tmp_path: Path,
) -> None:
    launcher = _write_executable(
        tmp_path / "runtime-fixture",
        """#!/usr/bin/env python3
import json
import sys
sys.stdin.buffer.read()
print(json.dumps({
    "kind": "accepted",
    "state_token": "secret-token-from-runtime",
    "public_copy": "private-user-copy",
    "unexpected": "schema-error-canary",
}))
""",
    )
    state_root = tmp_path / "state"
    state_root.mkdir()

    with pytest.raises(RuntimeTransportError) as caught:
        await _adapter(launcher, state_root).execute(Describe())

    rendered = "".join(
        traceback.format_exception(
            type(caught.value),
            caught.value,
            caught.value.__traceback__,
        )
    )
    assert "secret-token-from-runtime" not in rendered
    assert "private-user-copy" not in rendered
    assert "schema-error-canary" not in rendered
    assert caught.value.__context__ is None


async def test_process_adapter_drops_malformed_json_from_the_exception_context(
    tmp_path: Path,
) -> None:
    launcher = _write_executable(
        tmp_path / "runtime-fixture",
        """#!/usr/bin/env python3
import sys
sys.stdin.buffer.read()
sys.stdout.write('{"state_token":"malformed-secret-token"')
""",
    )
    state_root = tmp_path / "state"
    state_root.mkdir()

    with pytest.raises(RuntimeTransportError) as caught:
        await _adapter(launcher, state_root).execute(Describe())

    assert caught.value.__context__ is None
    assert "malformed-secret-token" not in repr(caught.value)


async def test_process_adapter_uses_a_fixed_path_not_the_host_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launcher = _write_executable(
        tmp_path / "runtime-fixture",
        """#!/usr/bin/env python3
import json
import os
from pathlib import Path
import sys
sys.stdin.buffer.read()
Path(__file__).with_suffix('.path').write_text(os.environ['PATH'])
print(json.dumps({
    "kind": "described",
    "protocol_version": "mingli-portable-interface-v2",
    "manifest_digest": "0" * 64,
    "capabilities": [],
}))
""",
    )
    state_root = tmp_path / "state"
    state_root.mkdir()
    monkeypatch.setenv("PATH", str(tmp_path / "attacker-controlled-bin"))

    await _adapter(launcher, state_root).execute(Describe())

    assert launcher.with_suffix(".path").read_text() == "/opt/node/bin:/usr/local/bin:/usr/bin:/bin"


async def test_process_adapter_passes_user_content_only_through_json_stdin(
    tmp_path: Path,
) -> None:
    shell_side_effect = tmp_path / "shell-expanded"
    launcher = _write_executable(
        tmp_path / "runtime-fixture",
        """#!/usr/bin/env python3
import json
from pathlib import Path
import sys
Path(__file__).with_suffix('.argv').write_text(json.dumps(sys.argv))
command = json.load(sys.stdin)
assert command['kind'] == 'prepare'
print(json.dumps({
    "kind": "stopped",
    "reason": "unsupported",
    "public_copy": "fixture",
    "state_token": None,
    "input_request": None,
}))
""",
    )
    state_root = tmp_path / "state"
    state_root.mkdir()
    query = f"$(touch {shell_side_effect}) ; `id`"
    command = Prepare(
        query=query,
        intent={
            "subject_refs": ["fixture:subject"],
            "object_id": "natal",
            "dimension_ids": [],
            "horizon": {"kind_id": "life", "start": None, "end": None},
            "capability_id": "bazi",
            "comparisons": [],
        },
        facts={"fixture:subject": {"fixture_input": query}},
    )

    await _adapter(launcher, state_root).execute(command)

    assert json.loads(launcher.with_suffix(".argv").read_text()) == [str(launcher)]
    assert not shell_side_effect.exists()


async def test_unknown_no_token_prepare_is_never_automatically_retried(
    tmp_path: Path,
) -> None:
    launcher = _write_executable(
        tmp_path / "runtime-fixture",
        """#!/usr/bin/env python3
from pathlib import Path
import sys
counter = Path(__file__).with_suffix('.count')
count = int(counter.read_text()) + 1 if counter.exists() else 1
counter.write_text(str(count))
sys.stdin.buffer.read()
sys.stdout.write('transport outcome unknown')
""",
    )
    state_root = tmp_path / "state"
    state_root.mkdir()
    command = Prepare(
        query="只调用一次",
        intent={
            "subject_refs": ["fixture:subject"],
            "object_id": "natal",
            "dimension_ids": [],
            "horizon": {"kind_id": "life", "start": None, "end": None},
            "capability_id": "bazi",
            "comparisons": [],
        },
        facts={"fixture:subject": {"fixture_input": "present"}},
    )

    with pytest.raises(RuntimeTransportError, match="runtime_invalid_output"):
        await _adapter(launcher, state_root).execute(command)

    assert launcher.with_suffix(".count").read_text() == "1"


async def test_identical_complete_can_be_replayed_safely_by_the_caller(
    tmp_path: Path,
) -> None:
    launcher = _write_executable(
        tmp_path / "runtime-fixture",
        """#!/usr/bin/env python3
import json
import os
from pathlib import Path
import sys
command = json.load(sys.stdin)
state = Path(os.environ['MINGLI_STORE_ROOT']) / 'accepted.json'
if state.exists():
    accepted = json.loads(state.read_text())
else:
    accepted = {
        "kind": "accepted",
        "state_token": command["state_token"],
        "public_copy": command["public_copy"],
    }
    state.write_text(json.dumps(accepted))
print(json.dumps(accepted))
""",
    )
    state_root = tmp_path / "state"
    state_root.mkdir()
    command = Complete(
        state_token="opaque-replay-token",
        public_copy="逐字节相同的成稿。",
    )
    adapter = _adapter(launcher, state_root)

    first = await adapter.execute(command)
    replay = await adapter.execute(command)

    assert isinstance(first, Accepted)
    assert replay == first
    assert replay.state_token == command.state_token
    assert replay.public_copy.encode() == command.public_copy.encode()
