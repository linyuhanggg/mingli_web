import json
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

import pytest
from app.adapters.runtime import (
    FakeMingliRuntimeAdapter,
    OneShotMingliRuntimeAdapter,
    build_runtime_startup_gate,
)
from app.charts.contracts import (
    CanwenViewV1,
    ChartSimilarityViewV1,
    FengshuiViewV1,
    LumingNayinChartV1,
    MeihuaChartV1,
    PhysiognomyViewV1,
    QimenChartV1,
    SelectionChartV1,
    TaiyiChartV1,
    WenshiViewV1,
)
from app.charts.projectors import (
    project_canwen_view_model,
    project_chart_similarity_view_model,
    project_fengshui_view_model,
    project_luming_nayin_view_model,
    project_meihua_view_model,
    project_physiognomy_view_model,
    project_qimen_view_model,
    project_selection_view_model,
    project_taiyi_view_model,
    project_wenshi_view_model,
)
from app.config import Settings
from app.readings.errors import RuntimeTransportError
from app.readings.request_compiler import (
    ConfirmedProfileVersion,
    compile_canwen_prepare,
    compile_chart_similarity_prepare,
    compile_fengshui_prepare,
    compile_luming_nayin_prepare,
    compile_meihua_prepare,
    compile_physiognomy_prepare,
    compile_qimen_prepare,
    compile_selection_prepare,
    compile_taiyi_prepare,
    compile_wenshi_prepare,
)
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


@pytest.mark.skipif(
    os.environ.get("MINGLI_RUN_REAL_RUNTIME_TESTS") != "1",
    reason="real frozen Runtime test is opt-in",
)
async def test_frozen_runtime_prepares_the_canwen_three_art_brief() -> None:
    """Run the real release gate without making it a default unit-test dependency."""

    settings = Settings()
    gate = build_runtime_startup_gate(settings)
    await gate.startup()
    command = compile_canwen_prepare(
        action="canwen_preview",
        query="比较三张命盘在事业与关系上的共同信号",
        profile=ConfirmedProfileVersion(
            subject_ref="profile-version:canwen-synthetic",
            birth_datetime="1994-04-30T05:55:00+08:00",
            birth_datetime_or_four_pillars="1994-04-30T05:55:00+08:00",
            timezone="Asia/Shanghai",
            location="福建省福州市",
            gender="female",
            time_basis_policy="civil",
            zi_hour_policy="midnight",
            longitude=119.2965,
            latitude=26.0745,
            coordinate_source="synthetic-fixture",
        ),
        selected_art_ids=("bazi", "ziwei", "qizheng"),
        dimension_ids=("career", "relationship", "state"),
    )

    result = await gate.runtime.execute(command)

    assert isinstance(result, Prepared)
    brief = result.brief.to_dict()
    request_view = brief["request_view"]
    assert request_view["capability_ids"] == ["bazi", "ziwei", "xingming"]
    calculated_refs = [
        str(item["ref"])
        for item in brief["facts"]
        if "/input/" not in str(item["ref"])
    ]
    assert {"/bazi/", "/ziwei/", "/xingming/"} <= {
        "/" + ref.split("/calculated/", 1)[1].split("/", 1)[0] + "/"
        for ref in calculated_refs
    }
    view_model = project_canwen_view_model(brief)
    assert isinstance(view_model, CanwenViewV1)
    assert view_model.selected_art_ids == ("bazi", "ziwei", "qizheng")
    expected_missing_art_ids = (
        () if settings.runtime_release_profile == "v52-relationship" else ("qizheng",)
    )
    assert all(
        dimension.missing_art_ids == expected_missing_art_ids
        for dimension in view_model.dimensions
    )
    expected_convergence = (
        ("所选术数的计算事实范围均已提供；尚未形成实质性互证结论。",)
        if settings.runtime_release_profile == "v52-relationship"
        else ()
    )
    assert all(
        dimension.convergence == expected_convergence
        for dimension in view_model.dimensions
    )


@pytest.mark.skipif(
    os.environ.get("MINGLI_RUN_REAL_RUNTIME_TESTS") != "1",
    reason="real frozen Runtime test is opt-in",
)
async def test_frozen_runtime_prepares_and_projects_chart_similarity_facts() -> None:
    gate = build_runtime_startup_gate(Settings())
    await gate.startup()
    command = compile_chart_similarity_prepare(
        action="chart_similarity_preview",
        query="比较两份已确认命盘的八字四柱事实。",
        profiles=(
            ConfirmedProfileVersion(
                subject_ref="profile-version:similarity-left",
                birth_datetime="1994-04-30T05:55:00+08:00",
                birth_datetime_or_four_pillars="1994-04-30T05:55:00+08:00",
                timezone="Asia/Shanghai",
                location="福建省福州市",
                gender="male",
                time_basis_policy="civil",
                zi_hour_policy="midnight",
                longitude=119.2965,
                latitude=26.0745,
                coordinate_source="synthetic-fixture",
            ),
            ConfirmedProfileVersion(
                subject_ref="profile-version:similarity-right",
                birth_datetime="1999-04-30T05:55:00+08:00",
                birth_datetime_or_four_pillars="1999-04-30T05:55:00+08:00",
                timezone="Asia/Shanghai",
                location="福建省福州市",
                gender="female",
                time_basis_policy="civil",
                zi_hour_policy="midnight",
                longitude=119.2965,
                latitude=26.0745,
                coordinate_source="synthetic-fixture",
            ),
        ),
        dimension_ids=("state",),
    )

    result = await gate.runtime.execute(command)

    assert isinstance(result, Prepared)
    brief = result.brief.to_dict()
    calculated_refs = {
        str(item["ref"])
        for item in brief["facts"]
        if "/input/" not in str(item["ref"])
    }
    assert any(
        ref.endswith("/calculated/bazi/four_pillars")
        and "similarity-left" in ref
        for ref in calculated_refs
    )
    assert any(
        ref.endswith("/calculated/bazi/four_pillars")
        and "similarity-right" in ref
        for ref in calculated_refs
    )
    view_model = project_chart_similarity_view_model(brief)
    assert isinstance(view_model, ChartSimilarityViewV1)
    assert view_model.basis == "bazi.four_pillars.exact"
    assert len(view_model.comparisons) == 4


@pytest.mark.skipif(
    os.environ.get("MINGLI_RUN_REAL_RUNTIME_TESTS") != "1",
    reason="real frozen Runtime test is opt-in",
)
async def test_frozen_runtime_prepares_and_projects_the_wenshi_three_art_brief() -> None:
    gate = build_runtime_startup_gate(Settings())
    await gate.startup()
    command = compile_wenshi_prepare(
        action="wenshi_one_question",
        query="这次合作能否按期完成？",
        subject_ref="wenshi:synthetic-runtime",
        cast=(6, 7, 8, 9, 6, 7),
        event_datetime=datetime.fromisoformat("2026-08-14T10:00:00+08:00"),
        confirmed_timezone="Asia/Shanghai",
        location="福建省莆田市",
        dimension_ids=("outcome", "timing"),
        longitude=119.1,
        latitude=25.4,
        coordinate_source="synthetic-fixture",
    )

    result = await gate.runtime.execute(command)

    assert isinstance(result, Prepared)
    brief = result.brief.to_dict()
    assert brief["request_view"]["capability_ids"] == ["liuyao", "qimen", "liuren"]
    calculated_refs = [
        str(item["ref"])
        for item in brief["facts"]
        if "/input/" not in str(item["ref"])
    ]
    assert any("/calculated/liuyao/" in ref for ref in calculated_refs)
    assert any("/calculated/qimen/" in ref for ref in calculated_refs)
    assert any("/calculated/liuren/" in ref for ref in calculated_refs)
    assert isinstance(project_wenshi_view_model(brief), WenshiViewV1)


@pytest.mark.skipif(
    os.environ.get("MINGLI_RUN_REAL_RUNTIME_TESTS") != "1",
    reason="real frozen Runtime test is opt-in",
)
async def test_frozen_runtime_prepares_and_projects_the_meihua_time_plate() -> None:
    """Verify the real Meihua provider and the strict public plate contract."""

    gate = build_runtime_startup_gate(Settings())
    await gate.startup()
    command = compile_meihua_prepare(
        action="meihua_preview",
        query="用时间起一卦看这件事的状态与结果",
        subject_ref="meihua:synthetic",
        casting_method="time",
        event_datetime=datetime.fromisoformat("2026-01-08T04:00:00+00:00"),
        confirmed_timezone="Asia/Shanghai",
        location="福建省福州市",
        dimension_ids=("outcome", "state"),
    )

    result = await gate.runtime.execute(command)

    assert isinstance(result, Prepared)
    brief = result.brief.to_dict()
    assert brief["request_view"]["capability_ids"] == ["meihua"]
    calculated_refs = [
        str(item["ref"])
        for item in brief["facts"]
        if "/input/" not in str(item["ref"])
    ]
    assert any("/meihua/primary_hexagram" in ref for ref in calculated_refs)
    view_model = project_meihua_view_model(brief)
    assert isinstance(view_model, MeihuaChartV1)
    assert view_model.casting_method == "time"
    assert view_model.primary_hexagram.name
    assert view_model.core_facts is not None
    assert view_model.core_facts.body_relation_facts is not None
    assert len(view_model.core_facts.body_relation_facts) >= 1
    assert view_model.core_facts.seasonal_strength is not None


@pytest.mark.skipif(
    os.environ.get("MINGLI_RUN_REAL_RUNTIME_TESTS") != "1",
    reason="real frozen Runtime test is opt-in",
)
async def test_frozen_runtime_prepares_and_projects_all_meihua_casting_methods() -> None:
    """Verify every explicit Meihua input contract reaches the real provider."""

    gate = build_runtime_startup_gate(Settings())
    await gate.startup()
    cases: tuple[tuple[str, dict[str, object]], ...] = (
        (
            "supplied_number",
            {"number": 17, "provenance": {"kind": "user_supplied", "source": "runtime-test"}},
        ),
        (
            "sound_count",
            {"count": 9, "observation_source": {"kind": "sound_count", "source": "runtime-test"}},
        ),
        (
            "observation",
            {
                "upper_trigram": "乾",
                "lower_trigram": "坤",
                "observation_source": {"kind": "direct_observation", "source": "runtime-test"},
            },
        ),
        (
            "supplied_hexagram",
            {
                "upper_trigram": "乾",
                "lower_trigram": "坤",
                "moving_line": 4,
                "provenance": {"kind": "user_supplied", "source": "runtime-test"},
            },
        ),
    )

    for method, method_kwargs in cases:
        command = compile_meihua_prepare(
            action="meihua_preview",
            query=f"按 {method} 起卦",
            subject_ref=f"meihua:{method}",
            casting_method=method,
            event_datetime=datetime.fromisoformat("2026-01-08T04:00:00+00:00"),
            confirmed_timezone="Asia/Shanghai",
            location="福建省福州市",
            dimension_ids=("outcome", "state"),
            **method_kwargs,
        )

        result = await gate.runtime.execute(command)

        assert isinstance(result, Prepared)
        brief = result.brief.to_dict()
        assert brief["request_view"]["capability_ids"] == ["meihua"]
        view_model = project_meihua_view_model(brief)
        assert isinstance(view_model, MeihuaChartV1)
        assert view_model.casting_method == method
        assert view_model.primary_hexagram.name


@pytest.mark.skipif(
    os.environ.get("MINGLI_RUN_REAL_RUNTIME_TESTS") != "1",
    reason="real frozen Runtime test is opt-in",
)
async def test_frozen_runtime_prepares_and_projects_the_qimen_structural_board() -> None:
    """Verify the real Qimen provider's board markers remain typed and public-safe."""

    gate = build_runtime_startup_gate(Settings())
    await gate.startup()
    command = compile_qimen_prepare(
        action="qimen_one_question",
        query="这次合作应该如何推进？",
        subject_ref="qimen:synthetic-shanghai",
        event_datetime=datetime.fromisoformat("2026-08-14T10:00:00+08:00"),
        confirmed_timezone="Asia/Shanghai",
        location="上海市",
        dimension_ids=("outcome", "timing"),
        time_basis_policy="civil",
        zi_hour_policy="midnight",
        longitude=121.4737,
        latitude=31.2304,
        coordinate_source="synthetic-fixture",
    )

    result = await gate.runtime.execute(command)

    assert isinstance(result, Prepared)
    brief = result.brief.to_dict()
    calculated_refs = [
        str(item["ref"])
        for item in brief["facts"]
        if "/input/" not in str(item["ref"])
    ]
    required_qimen_fields = {
        f"/qimen/{field}"
        for field in (
            "ju",
            "chief",
            "director",
            "palaces",
            "instruments_wonders",
            "stars_doors_deities",
            "xunkong",
            "horse",
            "named_patterns",
        )
    }
    actual_qimen_fields = {
        "/" + ref.split("/calculated/", 1)[1].split("/", 1)[0] + "/" + ref.rsplit("/", 1)[-1]
        for ref in calculated_refs
        if "/qimen/" in ref
    }
    assert required_qimen_fields <= actual_qimen_fields
    view_model = project_qimen_view_model(brief)
    assert isinstance(view_model, QimenChartV1)
    assert len(view_model.palaces) == 9
    assert view_model.chief.star
    assert view_model.director.door
    assert view_model.xunkong.branches
    assert view_model.named_patterns


@pytest.mark.skipif(
    os.environ.get("MINGLI_RUN_REAL_RUNTIME_TESTS") != "1",
    reason="real frozen Runtime test is opt-in",
)
@pytest.mark.parametrize("action", ["luming_nayin_preview", "rhythm_preview"])
async def test_frozen_runtime_prepares_and_projects_luming_nayin(action: str) -> None:
    gate = build_runtime_startup_gate(Settings())
    await gate.startup()
    command = compile_luming_nayin_prepare(
        action=action,
        query="只查看四柱纳音基础事实",
        profile=ConfirmedProfileVersion(
            subject_ref="profile-version:luming-synthetic",
            birth_datetime="1994-04-30T05:55:00+08:00",
            birth_datetime_or_four_pillars="1994-04-30T05:55:00+08:00",
            timezone="Asia/Shanghai",
            location="福建省福州市",
            gender="female",
            time_basis_policy="civil",
            zi_hour_policy="midnight",
            longitude=119.2965,
            latitude=26.0745,
            coordinate_source="synthetic-fixture",
        ),
        dimension_ids=("career", "state"),
    )

    result = await gate.runtime.execute(command)

    assert isinstance(result, Prepared)
    brief = result.brief.to_dict()
    view_model = project_luming_nayin_view_model(brief)
    assert isinstance(view_model, LumingNayinChartV1)
    assert len(view_model.pillars) == 4
    assert view_model.pillars[0].nayin
    assert view_model.relations


@pytest.mark.skipif(
    os.environ.get("MINGLI_RUN_REAL_RUNTIME_TESTS") != "1",
    reason="real frozen Runtime test is opt-in",
)
async def test_frozen_runtime_prepares_and_projects_taiyi() -> None:
    gate = build_runtime_startup_gate(Settings())
    await gate.startup()
    command = compile_taiyi_prepare(
        action="taiyi_preview",
        query="查看年度太乙年计盘结构",
        subject_ref="taiyi:synthetic",
        reference_datetime=datetime.fromisoformat("2026-08-14T02:00:00+00:00"),
        confirmed_timezone="Asia/Shanghai",
        location="上海市",
        dimension_ids=("outcome", "timing"),
        time_basis_policy="solar",
        longitude=121.4737,
        latitude=31.2304,
        coordinate_source="synthetic-fixture",
    )

    result = await gate.runtime.execute(command)

    assert isinstance(result, Prepared)
    view_model = project_taiyi_view_model(result.brief.to_dict())
    assert isinstance(view_model, TaiyiChartV1)
    assert view_model.calendar.year_ganzhi
    assert view_model.scope_contract.supported_horizons == ("year",)


@pytest.mark.skipif(
    os.environ.get("MINGLI_RUN_REAL_RUNTIME_TESTS") != "1",
    reason="real frozen Runtime test is opt-in",
)
async def test_frozen_runtime_prepares_and_projects_selection() -> None:
    gate = build_runtime_startup_gate(Settings())
    await gate.startup()
    command = compile_selection_prepare(
        action="selection_preview",
        query="比较一段日期里的开市日课事实",
        subject_ref="selection:synthetic",
        event_profile="business_opening_transaction",
        requested_actions=("开市",),
        date_range_start="2026-09-01",
        date_range_end="2026-09-03",
        confirmed_timezone="Asia/Shanghai",
        location="上海市",
        dimension_ids=("timing", "state"),
    )

    result = await gate.runtime.execute(command)

    assert isinstance(result, Prepared)
    view_model = project_selection_view_model(result.brief.to_dict())
    assert isinstance(view_model, SelectionChartV1)
    assert view_model.event_profile == "business_opening_transaction"
    assert view_model.ranking.method == "explainable_lexicographic_v1"
    assert view_model.basis_projection["candidate_limit_per_list"] == 12


@pytest.mark.skipif(
    os.environ.get("MINGLI_RUN_REAL_RUNTIME_TESTS") != "1",
    reason="real frozen Runtime test is opt-in",
)
async def test_frozen_runtime_prepares_and_projects_fengshui_observations() -> None:
    gate = build_runtime_startup_gate(Settings())
    await gate.startup()
    measurement = {
        "measurement_id": "m-door",
        "method": "synthetic-compass",
        "source_ref": "synthetic-compass-1",
        "source_type": "user_measurement",
        "north_reference": "true",
        "facing_degrees": 180,
        "correction_degrees": 0,
        "uncertainty_degrees": 0,
        "quality": "good",
    }
    command = compile_fengshui_prepare(
        action="fengshui_preview",
        query="只查看已测空间事实",
        subject_ref="fengshui:synthetic",
        fengshui_spec={
            "schema_version": "mingli-fengshui-input-v1",
            "property_scope": "residential",
            "subprofiles": ["liqi"],
            "requested_form_variables": [],
            "liqi": {
                "selected_school": "bazhai",
                "origin_basis": "door_trigram",
                "origin_node_id": "door-1",
            },
            "building": {},
            "assets": [],
            "observations": [],
            "compass_measurements": [measurement],
            "declared_orientation": {},
            "layout_graph": {
                "nodes": [
                    {
                        "node_id": "door-1",
                        "kind": "door",
                        "direction_measurement": measurement,
                    }
                ],
                "edges": [],
            },
        },
        dimension_ids=("current_state", "direction"),
    )

    result = await gate.runtime.execute(command)

    assert isinstance(result, Prepared)
    view_model = project_fengshui_view_model(result.brief.to_dict())
    assert isinstance(view_model, FengshuiViewV1)
    assert view_model.compass["status"] == "resolved"
    assert view_model.liqi["status"] == "calculated_selected_school_facts_not_verdict"


@pytest.mark.skipif(
    os.environ.get("MINGLI_RUN_REAL_RUNTIME_TESTS") != "1",
    reason="real frozen Runtime test is opt-in",
)
async def test_frozen_runtime_prepares_and_projects_physiognomy_observations() -> None:
    gate = build_runtime_startup_gate(Settings())
    await gate.startup()
    subject_ref = "sid-11111111111111111111111111111111"
    command = compile_physiognomy_prepare(
        action="physiognomy_preview",
        query="只查看已确认的可见观察事实",
        subject_ref=subject_ref,
        physiognomy_spec={
            "schema_version": "mingli-physiognomy-input-v1",
            "observation_scope": "face",
            "subject_ref": subject_ref,
            "requested_targets": [
                {
                    "target_id": "tid-22222222222222222222222222222222",
                    "taxonomy": "anatomical_face_v1",
                    "region": "forehead",
                    "feature_kind": "visible_morphology",
                    "required": True,
                }
            ],
            "assets": [],
            "observations": [
                {
                    "observation_id": "oid-33333333333333333333333333333333",
                    "target_id": "tid-22222222222222222222222222222222",
                    "source_type": "user_text",
                    "region": "forehead",
                    "feature_kind": "visible_morphology",
                    "visibility": "full",
                    "value": {"descriptor": "region_visible"},
                    "occlusion": 0,
                    "uncertainty": 0,
                    "source_ref": "rid-44444444444444444444444444444444",
                    "quality": {
                        "lighting": "not_applicable",
                        "camera_angle": "caller_description",
                        "focus": "not_applicable",
                        "resolution": "not_applicable",
                        "filtering": "not_applicable",
                        "color_fidelity": "not_applicable",
                    },
                }
            ],
            "confirmed_observation_ids": ["oid-33333333333333333333333333333333"],
            "comparison_relations": [],
            "source_layer_policy": "terminology_and_methodology_only",
        },
        dimension_ids=("state", "source_comparison"),
    )

    result = await gate.runtime.execute(command)

    assert isinstance(result, Prepared)
    view_model = project_physiognomy_view_model(result.brief.to_dict())
    assert isinstance(view_model, PhysiognomyViewV1)
    assert view_model.mode == "face"
    assert view_model.observations[0].region_id == "forehead"
