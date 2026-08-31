from __future__ import annotations

import hashlib
import importlib
import io
import json
import os
import select
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from dataclasses import replace
from pathlib import Path, PurePosixPath
from typing import BinaryIO
from unittest.mock import Mock, patch

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

runtime_worker = importlib.import_module("reading_engine.runtime_worker")
interface_contracts = importlib.import_module("reading_engine.interface_contracts")
HorizonSelection = interface_contracts.HorizonSelection
IntentSelection = interface_contracts.IntentSelection
Prepare = interface_contracts.Prepare

WORKER_RELATIVE = "scripts/reading_engine/runtime_worker.py"

_BIRTH_FACTS = {
    "birth_datetime": "1994-04-30T05:55:00",
    "timezone": "Asia/Shanghai",
    "location": "福建省福州市",
    "gender": "female",
    "time_basis_policy": "civil",
    "zi_hour_policy": "midnight",
    "longitude": 119.3,
    "latitude": 26.08,
    "coordinate_source": "declared",
}
_EVENT_FACTS = {
    "event_datetime": "2026-08-03T09:00:00+08:00",
    "timezone": "Asia/Shanghai",
    "location": "上海",
    "time_basis_policy": "civil",
    "longitude": 121.4737,
    "latitude": 31.2304,
    "coordinate_source": "declared",
}
_PRODUCT_CASES = {
    "bazi": (
        "natal",
        "life",
        {
            "birth_datetime_or_four_pillars": _BIRTH_FACTS["birth_datetime"],
            "timezone": _BIRTH_FACTS["timezone"],
            "location": _BIRTH_FACTS["location"],
            "gender": _BIRTH_FACTS["gender"],
            "time_basis_policy": _BIRTH_FACTS["time_basis_policy"],
        },
    ),
    "ziwei": ("natal", "life", _BIRTH_FACTS),
    "liuyao": (
        "concrete_event",
        "instant",
        {"cast": [6, 7, 8, 9, 7, 8], **_EVENT_FACTS},
    ),
    "meihua": (
        "concrete_event",
        "instant",
        {"casting_method": "time", **_EVENT_FACTS},
    ),
    "liuren": (
        "concrete_event",
        "instant",
        {
            "event_datetime_or_reference_datetime": _EVENT_FACTS["event_datetime"],
            **_EVENT_FACTS,
        },
    ),
}


def _prepare_command(product_id: str, *, query_suffix: str = "") -> dict[str, object]:
    object_id, horizon_id, facts = _PRODUCT_CASES[product_id]
    return Prepare(
        query=f"测试 {product_id}{query_suffix}",
        intent=IntentSelection(
            subject_refs=("subject:client",),
            object_id=object_id,
            dimension_ids=(),
            horizon=HorizonSelection(kind_id=horizon_id),
            capability_id=product_id,
        ),
        facts={"subject:client": facts},
    ).to_dict()


def _normalize_result(payload: dict[str, object]) -> dict[str, object]:
    normalized = json.loads(json.dumps(payload, ensure_ascii=False))
    if normalized.get("state_token") is not None:
        normalized["state_token"] = "<state-token>"
    return normalized


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _write_regular(root: Path, relative: str, payload: bytes) -> None:
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    target.chmod(0o644)


def _command(
    sequence: int = 1,
    *,
    request_id: str = "request-1",
    identity_sha256: str = "a" * 64,
    protocol: str = runtime_worker.WORKER_PROTOCOL,
    command: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "type": "command",
        "protocol": protocol,
        "identity_sha256": identity_sha256,
        "request_id": request_id,
        "sequence": sequence,
        "command": command or {"kind": "describe"},
    }


def _expected_terminal(
    *,
    identity_sha256: str = "a" * 64,
    request_id: str = "request-1",
    sequence: int = 1,
) -> dict[str, object]:
    return {
        "type": runtime_worker.TURN_TERMINAL_TYPE,
        "protocol": runtime_worker.WORKER_PROTOCOL,
        "identity_sha256": identity_sha256,
        "request_id": request_id,
        "sequence": sequence,
    }


def _read_success_turn(
    stream: BinaryIO,
    *,
    stderr: BinaryIO | None = None,
    identity_sha256: str = "a" * 64,
    request_id: str = "request-1",
    sequence: int = 1,
) -> dict[str, object]:
    """Independent host probe for the frozen Result -> idle turn contract."""

    result = runtime_worker.read_frame(stream)
    if (
        not isinstance(result, dict)
        or set(result)
        != {
            "type",
            "protocol",
            "identity_sha256",
            "request_id",
            "sequence",
            "result",
            "worker_action",
        }
        or result.get("type") != "result"
        or result.get("protocol") != runtime_worker.WORKER_PROTOCOL
        or result.get("identity_sha256") != identity_sha256
        or result.get("request_id") != request_id
        or result.get("sequence") != sequence
        or result.get("worker_action") != "continue"
    ):
        raise runtime_worker.FrameError("turn did not begin with Result")
    if stderr is not None:
        readable, _, _ = select.select([stream, stderr], [], [], 2.0)
        if not readable:
            raise runtime_worker.FrameError("turn terminal did not arrive")
        if stderr in readable and stderr.read(1):
            raise runtime_worker.FrameError("stderr arrived before turn terminal")
        if stream not in readable:
            readable, _, _ = select.select([stream], [], [], 2.0)
            if not readable:
                raise runtime_worker.FrameError("turn terminal did not arrive")
    terminal = runtime_worker.read_frame(stream)
    if terminal != _expected_terminal(
        identity_sha256=identity_sha256,
        request_id=request_id,
        sequence=sequence,
    ):
        raise runtime_worker.FrameError("turn terminal is invalid")
    return result


class SyntheticRelease:
    def __init__(self, root: Path) -> None:
        self.root = root
        root.mkdir(mode=0o700)
        closure = {
            "schema_version": runtime_worker.RUNTIME_CLOSURE_SCHEMA,
            "files": [
                runtime_worker.RUNTIME_CLOSURE,
                *sorted(runtime_worker.ONE_SHOT_RELATIVES),
            ],
            "patterns": ["scripts/reading_engine/*.py"],
        }
        self.payloads = {
            runtime_worker.RUNTIME_CLOSURE: (
                json.dumps(closure, sort_keys=True, separators=(",", ":")) + "\n"
            ).encode(),
            runtime_worker.WORKER_RELATIVE: b"worker-v2\n",
            "scripts/runtime_launcher.py": b"one-shot-python\n",
            "scripts/run_reading_transaction.sh": b"one-shot-shell\n",
        }
        for relative, payload in self.payloads.items():
            _write_regular(root, relative, payload)
        self.rewrite_manifest()

    def rewrite_manifest(self) -> str:
        manifest = {
            "schema_version": 3,
            "release": "mingli-master-portable-core",
            "source_commit": "b" * 40,
            "files": {
                relative: _sha256((self.root / relative).read_bytes())
                for relative in sorted(self.payloads)
            },
            "modes": {
                relative: stat.S_IMODE((self.root / relative).stat().st_mode)
                for relative in sorted(self.payloads)
            },
        }
        payload = (
            json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode()
        _write_regular(self.root, runtime_worker.RELEASE_MANIFEST, payload)
        self.listing_sha256 = _sha256(payload)
        return self.listing_sha256


class FrameContractTests(unittest.TestCase):
    def test_frame_round_trip_is_strict_utf8_json(self) -> None:
        payload = {"type": "test", "message": "命理", "value": [1, True, None]}
        encoded = runtime_worker.encode_frame(payload)

        self.assertEqual(
            runtime_worker.read_frame(io.BytesIO(encoded)),
            payload,
        )

    def test_frame_bound_is_enforced_for_encode_and_decode(self) -> None:
        payload = {"message": "bounded"}
        encoded = runtime_worker.encode_frame(payload)
        body_size = len(encoded) - runtime_worker.FRAME_HEADER_BYTES
        self.assertEqual(
            runtime_worker.read_frame(io.BytesIO(encoded), max_bytes=body_size),
            payload,
        )
        with self.assertRaisesRegex(runtime_worker.FrameError, "explicit bound"):
            runtime_worker.encode_frame(payload, max_bytes=body_size - 1)
        with self.assertRaisesRegex(runtime_worker.FrameError, "explicit bound"):
            runtime_worker.read_frame(
                io.BytesIO(encoded),
                max_bytes=body_size - 1,
            )

    def test_frame_rejects_duplicate_keys_non_object_and_truncation(self) -> None:
        for body, error in (
            (b'{"kind":"describe","kind":"prepare"}', "strict UTF-8 JSON"),
            (b"[]", "must be an object"),
            (b"{", "strict UTF-8 JSON"),
            (b"\xff", "strict UTF-8 JSON"),
        ):
            with self.subTest(body=body):
                framed = len(body).to_bytes(4, "big") + body
                with self.assertRaisesRegex(runtime_worker.FrameError, error):
                    runtime_worker.read_frame(io.BytesIO(framed))
        with self.assertRaisesRegex(runtime_worker.FrameError, "truncated"):
            runtime_worker.read_frame(io.BytesIO(b"\x00\x00"))
        with self.assertRaisesRegex(runtime_worker.FrameError, "truncated"):
            runtime_worker.read_frame(io.BytesIO(b"\x00\x00\x00\x04{}"))

    def test_clean_boundary_eof_is_not_a_protocol_fault(self) -> None:
        self.assertIsNone(runtime_worker.read_frame(io.BytesIO()))


class ReleaseIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.release = SyntheticRelease(Path(self.temporary.name) / "release")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def verify(self) -> runtime_worker.ReleaseIdentity:
        return runtime_worker.verify_release(
            self.release.root,
            self.release.listing_sha256,
            verify_semantics=False,
        )

    def test_complete_signed_release_and_worker_extension_are_bound(self) -> None:
        identity = self.verify()
        self.assertEqual(identity.root, str(self.release.root.resolve()))
        self.assertEqual(identity.listing_sha256, self.release.listing_sha256)
        self.assertEqual(identity.source_commit, "b" * 40)
        self.assertEqual(identity.file_count, 4)
        self.assertEqual(
            identity.signed_paths_sha256,
            _sha256("\n".join(sorted(self.release.payloads)).encode()),
        )

    def test_signed_byte_drift_is_rejected(self) -> None:
        target = self.release.root / "scripts/runtime_launcher.py"
        target.write_bytes(b"tampered\n")
        with self.assertRaisesRegex(runtime_worker.IdentityError, "digest mismatch"):
            self.verify()

    def test_unsigned_file_and_symlink_are_rejected(self) -> None:
        unsigned = self.release.root / "scripts/unsigned.py"
        unsigned.write_text("drift\n", encoding="utf-8")
        with self.assertRaisesRegex(runtime_worker.IdentityError, "unsigned"):
            self.verify()
        unsigned.unlink()
        link = self.release.root / "scripts/linked.py"
        link.symlink_to(self.release.root / "scripts/runtime_launcher.py")
        with self.assertRaisesRegex(runtime_worker.IdentityError, "symlink"):
            self.verify()

    def test_manifest_listing_and_mode_drift_are_rejected(self) -> None:
        with self.assertRaisesRegex(runtime_worker.IdentityError, "manifest digest"):
            runtime_worker.verify_release(
                self.release.root,
                "0" * 64,
                verify_semantics=False,
            )
        target = self.release.root / "scripts/runtime_launcher.py"
        target.chmod(0o600)
        with self.assertRaisesRegex(runtime_worker.IdentityError, "mode mismatch"):
            self.verify()

    def test_unsigned_closure_extension_is_rejected(self) -> None:
        extra = "scripts/extra.py"
        self.release.payloads[extra] = b"extra\n"
        _write_regular(self.release.root, extra, self.release.payloads[extra])
        self.release.rewrite_manifest()
        with self.assertRaisesRegex(runtime_worker.IdentityError, "does not match"):
            self.verify()

    def test_declared_pattern_exclusion_is_source_only(self) -> None:
        closure_path = self.release.root / runtime_worker.RUNTIME_CLOSURE
        closure = json.loads(closure_path.read_text(encoding="utf-8"))
        excluded = "scripts/reading_engine/contract_only.py"
        closure["excluded_files"] = [excluded]
        closure_bytes = (
            json.dumps(closure, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode()
        self.release.payloads[runtime_worker.RUNTIME_CLOSURE] = closure_bytes
        _write_regular(
            self.release.root,
            runtime_worker.RUNTIME_CLOSURE,
            closure_bytes,
        )
        self.release.rewrite_manifest()

        self.verify()

        self.release.payloads[excluded] = b"must-not-ship\n"
        _write_regular(self.release.root, excluded, self.release.payloads[excluded])
        self.release.rewrite_manifest()
        with self.assertRaisesRegex(runtime_worker.IdentityError, "does not match"):
            self.verify()

    def test_runtime_closure_byte_tamper_is_rejected(self) -> None:
        closure_path = self.release.root / runtime_worker.RUNTIME_CLOSURE
        closure_path.write_bytes(closure_path.read_bytes() + b" ")
        with self.assertRaisesRegex(runtime_worker.IdentityError, "digest mismatch"):
            self.verify()

    def test_store_namespace_is_bound_to_path_inode_and_mode(self) -> None:
        base = Path(self.temporary.name) / "state"
        identity = runtime_worker._prepare_store_namespace(base / "instance")
        runtime_worker._verify_store_namespace(Path(identity.path), identity)
        store = Path(identity.path)
        store.rmdir()
        store.mkdir(mode=0o700)
        with self.assertRaisesRegex(runtime_worker.IdentityError, "identity drifted"):
            runtime_worker._verify_store_namespace(store, identity)


class WorkerIdentityTests(unittest.TestCase):
    def identity(self) -> runtime_worker.WorkerIdentity:
        return runtime_worker.WorkerIdentity(
            protocol=runtime_worker.WORKER_PROTOCOL,
            turn_terminal=runtime_worker.TURN_TERMINAL_CAPABILITY,
            runtime_protocol=runtime_worker.RUNTIME_PROTOCOL,
            release_path="/verified/release",
            listing_sha256="1" * 64,
            release_name="mingli-master-portable-core",
            source_commit="2" * 40,
            release_file_count=223,
            signed_paths_sha256="3" * 64,
            runtime_integrity_sha256="4" * 64,
            python_identity={"implementation": "CPython", "version": [3, 14, 6]},
            store_namespace="/private/state",
            store_namespace_identity={"device": 1, "inode": 2, "mode": 0o700},
            pid=1234,
            boot_nonce="5" * 64,
            describe_manifest_digest="6" * 64,
            capability_ids=("bazi", "ziwei"),
        )

    def test_ready_binds_every_frozen_identity_and_policy(self) -> None:
        identity = self.identity()
        ready = identity.ready_payload(
            ready_timeout_seconds=15.0,
            boot_ms=321.25,
        )
        self.assertEqual(ready["type"], "ready")
        self.assertEqual(ready["protocol"], runtime_worker.WORKER_PROTOCOL)
        self.assertEqual(
            ready["turn_terminal"],
            runtime_worker.TURN_TERMINAL_CAPABILITY,
        )
        self.assertEqual(ready["identity_sha256"], identity.identity_sha256)
        for field in (
            "release_path",
            "listing_sha256",
            "runtime_integrity_sha256",
            "python_identity",
            "store_namespace",
            "store_namespace_identity",
            "pid",
            "boot_nonce",
        ):
            self.assertIn(field, ready)
        self.assertTrue(ready["single_in_flight"])
        self.assertEqual(ready["sequence_start"], 1)
        self.assertEqual(ready["boot_ms"], 321.25)
        self.assertEqual(ready["replay_policy"], "forbidden")
        self.assertEqual(ready["fallback_policy"], "forbidden")

    def test_any_bound_identity_change_changes_the_digest(self) -> None:
        identity = self.identity()
        for changed in (
            replace(identity, listing_sha256="7" * 64),
            replace(identity, turn_terminal="legacy-no-terminal"),
        ):
            self.assertNotEqual(identity.identity_sha256, changed.identity_sha256)

    def test_ready_timeout_has_an_independent_explicit_bound(self) -> None:
        for value in (0, -1, runtime_worker.MAX_READY_TIMEOUT_SECONDS + 0.1):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(ValueError, "explicit bound"),
                runtime_worker._ready_deadline(value),
            ):
                pass

    def test_runtime_site_roots_are_admitted_before_identity_imports(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            site_root = Path(temporary) / "site-packages"
            site_root.mkdir()
            guard = Mock()
            guard.validate_installed_runtime.return_value = [site_root]
            guard.current_runtime_identity.side_effect = lambda: {
                "site_root_admitted": str(site_root) in sys.path
            }
            expected = "8" * 64
            with patch.object(
                runtime_worker,
                "_runtime_manifest_digest",
                return_value=expected,
            ):
                roots, identity = runtime_worker._validate_runtime(
                    guard,
                    sys.executable,
                    expected,
                )
            self.assertEqual(roots, (site_root,))
            self.assertTrue(identity["site_root_admitted"])
            guard.validate_runtime_identity.assert_called_once_with(identity)
            sys.path.remove(str(site_root))


class WorkerSessionTests(unittest.TestCase):
    def session(
        self,
        *,
        execute: Mock | None = None,
        verify: Mock | None = None,
    ) -> runtime_worker.WorkerSession:
        return runtime_worker.WorkerSession(
            identity_sha256="a" * 64,
            execute_command=execute or Mock(return_value={"kind": "described"}),
            verify_identity=verify or Mock(return_value=None),
        )

    def test_monotonic_single_result_echoes_request_identity(self) -> None:
        execute = Mock(return_value={"kind": "described", "capabilities": []})
        verify = Mock(return_value=None)
        session = self.session(execute=execute, verify=verify)

        first, first_isolate = session.process(_command())
        second, second_isolate = session.process(_command(2, request_id="request-2"))

        self.assertFalse(first_isolate)
        self.assertFalse(second_isolate)
        self.assertEqual(first["request_id"], "request-1")  # type: ignore[index]
        self.assertEqual(first["sequence"], 1)  # type: ignore[index]
        self.assertEqual(second["request_id"], "request-2")  # type: ignore[index]
        self.assertEqual(second["sequence"], 2)  # type: ignore[index]
        self.assertEqual(execute.call_count, 2)
        self.assertEqual(verify.call_count, 4)

    def test_duplicate_out_of_order_and_identity_mismatch_isolate(self) -> None:
        cases = (
            (_command(2), "out-of-order"),
            (_command(identity_sha256="0" * 64), "identity-mismatch"),
            (
                _command(protocol="mingli-runtime-worker-v1"),
                "legacy-protocol-mismatch",
            ),
        )
        for payload, label in cases:
            with self.subTest(label=label):
                session = self.session()
                response, isolate = session.process(payload)
                self.assertTrue(isolate)
                self.assertEqual(response["result"]["kind"], "stopped")  # type: ignore[index]
                self.assertEqual(response["worker_action"], "isolate")  # type: ignore[index]

        session = self.session()
        session.process(_command())
        response, isolate = session.process(_command(2, request_id="request-1"))
        self.assertTrue(isolate)
        self.assertEqual(response["result"]["kind"], "stopped")  # type: ignore[index]

    def test_batch_or_extra_envelope_fields_are_rejected(self) -> None:
        payload = _command()
        payload["commands"] = [{"kind": "describe"}]
        session = self.session()
        response, isolate = session.process(payload)
        self.assertTrue(isolate)
        self.assertIsNone(response)

    def test_runtime_error_invalid_result_and_identity_drift_stop_and_isolate(
        self,
    ) -> None:
        execute_error = self.session(execute=Mock(side_effect=RuntimeError("boom")))
        response, isolate = execute_error.process(_command())
        self.assertTrue(isolate)
        self.assertEqual(response["result"]["kind"], "stopped")  # type: ignore[index]

        invalid_result = self.session(execute=Mock(return_value={"kind": "unknown"}))
        response, isolate = invalid_result.process(_command())
        self.assertTrue(isolate)
        self.assertEqual(response["result"]["kind"], "stopped")  # type: ignore[index]

        drift = self.session(
            verify=Mock(side_effect=[None, runtime_worker.IdentityError("drift")])
        )
        response, isolate = drift.process(_command())
        self.assertTrue(isolate)
        self.assertEqual(response["result"]["kind"], "stopped")  # type: ignore[index]

    def test_runtime_cannot_emit_delayed_result_or_stdio_before_terminal(self) -> None:
        for delay_seconds in (0.0, 0.08):
            with self.subTest(delay_seconds=delay_seconds):

                class NoisyInterface:
                    def __init__(self, delay: float) -> None:
                        self.delay = delay

                    def execute(self, _command: object) -> Mock:
                        time.sleep(self.delay)
                        os.write(
                            sys.stdout.fileno(),
                            runtime_worker.encode_frame(
                                {"type": "result", "result": {"kind": "described"}}
                            ),
                        )
                        os.write(sys.stderr.fileno(), b"unexpected side channel\n")
                        return Mock(
                            to_dict=Mock(
                                return_value={"kind": "described", "capabilities": []}
                            )
                        )

                session = self.session(
                    execute=runtime_worker._execute_with_interface(
                        NoisyInterface(delay_seconds)
                    )
                )
                response, isolate = session.process(_command())

                self.assertTrue(isolate)
                self.assertEqual(
                    response["result"]["kind"],  # type: ignore[index]
                    "stopped",
                )
                self.assertEqual(
                    response["worker_action"],  # type: ignore[index]
                    "isolate",
                )

    def test_release_drift_before_execution_is_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            release = SyntheticRelease(Path(temporary) / "release")
            identity = runtime_worker.verify_release(
                release.root,
                release.listing_sha256,
                verify_semantics=False,
            )

            def verify() -> None:
                current = runtime_worker.verify_release(
                    release.root,
                    release.listing_sha256,
                    verify_semantics=False,
                )
                if current != identity:
                    raise runtime_worker.IdentityError("release drift")

            session = runtime_worker.WorkerSession(
                identity_sha256="a" * 64,
                execute_command=Mock(return_value={"kind": "described"}),
                verify_identity=verify,
            )
            (release.root / "scripts/runtime_launcher.py").write_text(
                "tampered\n",
                encoding="utf-8",
            )
            response, isolate = session.process(_command())
            self.assertTrue(isolate)
            self.assertEqual(response["result"]["kind"], "stopped")  # type: ignore[index]


class WorkerServeTests(unittest.TestCase):
    def session(self, execute: Mock | None = None) -> runtime_worker.WorkerSession:
        return runtime_worker.WorkerSession(
            identity_sha256="a" * 64,
            execute_command=execute or Mock(return_value={"kind": "described"}),
            verify_identity=Mock(return_value=None),
        )

    def test_one_command_writes_exactly_one_result_then_bound_terminal(self) -> None:
        stdin = io.BytesIO(runtime_worker.encode_frame(_command()))
        stdout = io.BytesIO()
        stderr = io.StringIO()
        exit_code = runtime_worker.serve(self.session(), stdin, stdout, stderr)

        self.assertEqual(exit_code, runtime_worker.EXIT_OK)
        reader = io.BytesIO(stdout.getvalue())
        response = runtime_worker.read_frame(reader)
        self.assertEqual(response["type"], "result")  # type: ignore[index]
        self.assertEqual(response["result"]["kind"], "described")  # type: ignore[index]
        self.assertEqual(
            runtime_worker.read_frame(reader),
            _expected_terminal(),
        )
        self.assertIsNone(runtime_worker.read_frame(reader))
        self.assertEqual(stderr.getvalue(), "")

    def test_pipelined_second_command_is_never_executed(self) -> None:
        execute = Mock(return_value={"kind": "described"})
        payload = runtime_worker.encode_frame(_command()) + runtime_worker.encode_frame(
            _command(2, request_id="request-2")
        )
        stdout = io.BytesIO()
        exit_code = runtime_worker.serve(
            self.session(execute),
            io.BytesIO(payload),
            stdout,
            io.StringIO(),
        )
        self.assertEqual(exit_code, runtime_worker.EXIT_PROTOCOL)
        self.assertEqual(execute.call_count, 0)
        response = runtime_worker.read_frame(io.BytesIO(stdout.getvalue()))
        self.assertEqual(response["result"]["kind"], "stopped")  # type: ignore[index]
        self.assertEqual(response["worker_action"], "isolate")  # type: ignore[index]

    def test_malformed_frame_isolates_without_emitting_unframed_output(self) -> None:
        stdout = io.BytesIO()
        exit_code = runtime_worker.serve(
            self.session(),
            io.BytesIO(b"\x00\x00\x00\x00"),
            stdout,
            io.StringIO(),
        )
        self.assertEqual(exit_code, runtime_worker.EXIT_PROTOCOL)
        self.assertEqual(stdout.getvalue(), b"")

    def test_hard_process_crash_exits_once_without_replay_or_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            marker = Path(temporary) / "executions"
            source = (
                "import os,sys\n"
                f"sys.path.insert(0, {str(SCRIPTS)!r})\n"
                "from reading_engine import runtime_worker as worker\n"
                f"marker = {str(marker)!r}\n"
                "def execute(_command):\n"
                "    with open(marker, 'ab') as handle: handle.write(b'x')\n"
                "    os._exit(91)\n"
                "session = worker.WorkerSession(\n"
                "    identity_sha256='a' * 64, execute_command=execute,\n"
                "    verify_identity=lambda: None,\n"
                ")\n"
                "raise SystemExit(worker.serve(\n"
                "    session, sys.stdin.buffer, sys.stdout.buffer, sys.stderr\n"
                "))\n"
            )
            completed = subprocess.run(
                [sys.executable, "-I", "-S", "-c", source],
                input=runtime_worker.encode_frame(_command()),
                capture_output=True,
                timeout=10,
                check=False,
            )
            self.assertEqual(completed.returncode, 91, completed.stderr)
            self.assertEqual(completed.stdout, b"")
            self.assertEqual(marker.read_bytes(), b"x")


class TurnTerminalContractTests(unittest.TestCase):
    def _result(self) -> dict[str, object]:
        session = runtime_worker.WorkerSession(
            identity_sha256="a" * 64,
            execute_command=Mock(return_value={"kind": "described"}),
            verify_identity=Mock(return_value=None),
        )
        response, isolate = session.process(_command())
        self.assertFalse(isolate)
        assert response is not None
        return response

    @staticmethod
    def _write_faulty_turn(
        stdout_writer: BinaryIO,
        stderr_writer: BinaryIO,
        result: dict[str, object],
        delay_seconds: float,
        fault_kind: str,
        writer_errors: list[Exception],
    ) -> None:
        try:
            runtime_worker.write_frame(stdout_writer, result)
            time.sleep(delay_seconds)
            if fault_kind == "second-result":
                runtime_worker.write_frame(stdout_writer, result)
            elif fault_kind == "stdout":
                stdout_writer.write(b"unframed-stdout")
                stdout_writer.flush()
            elif fault_kind == "stderr":
                stderr_writer.write(b"unexpected-stderr")
                stderr_writer.flush()
            terminal = _expected_terminal()
            if fault_kind == "identity":
                terminal["identity_sha256"] = "0" * 64
            elif fault_kind == "sequence":
                terminal["sequence"] = 2
            runtime_worker.write_frame(stdout_writer, terminal)
        except BrokenPipeError:
            pass
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            writer_errors.append(exc)
        finally:
            stdout_writer.close()
            stderr_writer.close()

    @staticmethod
    def _write_late_unsolicited_result(
        writer: BinaryIO,
        result: dict[str, object],
        delay_seconds: float,
    ) -> None:
        runtime_worker.write_frame(writer, result)
        runtime_worker.write_frame(writer, _expected_terminal())
        time.sleep(delay_seconds)
        runtime_worker.write_frame(writer, result)
        writer.close()

    def test_zero_and_eighty_ms_pre_terminal_faults_do_not_use_a_grace_window(
        self,
    ) -> None:
        for delay_seconds in (0.0, 0.08):
            for fault_kind in (
                "second-result",
                "stdout",
                "stderr",
                "identity",
                "sequence",
            ):
                with self.subTest(
                    delay_seconds=delay_seconds,
                    fault_kind=fault_kind,
                ):
                    stdout_read_fd, stdout_write_fd = os.pipe()
                    stderr_read_fd, stderr_write_fd = os.pipe()
                    stdout_reader = os.fdopen(stdout_read_fd, "rb", buffering=0)
                    stdout_writer = os.fdopen(stdout_write_fd, "wb", buffering=0)
                    stderr_reader = os.fdopen(stderr_read_fd, "rb", buffering=0)
                    stderr_writer = os.fdopen(stderr_write_fd, "wb", buffering=0)
                    writer_errors: list[Exception] = []
                    result = self._result()
                    writer = threading.Thread(
                        target=self._write_faulty_turn,
                        args=(
                            stdout_writer,
                            stderr_writer,
                            result,
                            delay_seconds,
                            fault_kind,
                            writer_errors,
                        ),
                        daemon=True,
                    )
                    writer.start()
                    started = time.perf_counter()
                    with (
                        stdout_reader,
                        stderr_reader,
                        self.assertRaises(runtime_worker.FrameError),
                    ):
                        _read_success_turn(
                            stdout_reader,
                            stderr=stderr_reader,
                        )
                    elapsed = time.perf_counter() - started
                    writer.join(timeout=2)
                    self.assertFalse(writer.is_alive())
                    self.assertEqual(writer_errors, [])
                    if delay_seconds:
                        self.assertGreaterEqual(elapsed, 0.06)

    def test_post_terminal_bytes_do_not_rewrite_the_returned_turn(self) -> None:
        for delay_seconds in (0.0, 0.08):
            with self.subTest(delay_seconds=delay_seconds):
                read_fd, write_fd = os.pipe()
                reader = os.fdopen(read_fd, "rb", buffering=0)
                writer = os.fdopen(write_fd, "wb", buffering=0)
                result = self._result()
                thread = threading.Thread(
                    target=self._write_late_unsolicited_result,
                    args=(writer, result, delay_seconds),
                    daemon=True,
                )
                thread.start()
                with reader:
                    returned = _read_success_turn(reader)
                    self.assertEqual(returned["result"]["kind"], "described")  # type: ignore[index]
                    thread.join(timeout=2)
                    self.assertFalse(thread.is_alive())
                    self.assertTrue(
                        runtime_worker._input_has_buffered_data(reader),
                        "a host must isolate before writing the next Command",
                    )
                    self.assertEqual(runtime_worker.read_frame(reader), result)


class CompatibilityBoundaryTests(unittest.TestCase):
    def test_runtime_worker_is_explicitly_declared_in_release_closure(self) -> None:
        closure = json.loads(
            (ROOT / runtime_worker.RUNTIME_CLOSURE).read_text(encoding="utf-8")
        )
        self.assertIn(WORKER_RELATIVE, closure["files"])
        self.assertNotIn(WORKER_RELATIVE, closure.get("excluded_files", []))

    def test_one_shot_entrypoint_remains_separate_and_unchanged_in_role(self) -> None:
        launcher = (SCRIPTS / "runtime_launcher.py").read_text(encoding="utf-8")
        shell = (SCRIPTS / "run_reading_transaction.sh").read_text(encoding="utf-8")
        self.assertNotIn("runtime_worker", launcher)
        self.assertNotIn("runtime_worker", shell)
        self.assertIn("runpy.run_path", launcher)
        self.assertIn("runtime_launcher.py", shell)


_RUN_INTEGRATION = os.environ.get("MINGLI_RUNTIME_WORKER_INTEGRATION") == "1"


@unittest.skipUnless(
    _RUN_INTEGRATION,
    "set MINGLI_RUNTIME_WORKER_INTEGRATION=1 for signed worker process tests",
)
class RuntimeWorkerProcessIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.scratch = Path(self.temporary.name).resolve()
        self.release_root = self.scratch / "release"
        self.release_listing = self._materialize_release(self.release_root)
        configured = os.environ.get("MINGLI_PYTHON")
        default = Path.home() / ".local/share/mingli-master/venv/bin/python"
        source_runtime_python = Path(configured or default).resolve(strict=True)
        source_runtime_root = source_runtime_python.parents[1]
        clean_runtime_root = self.scratch / "runtime"
        shutil.copytree(
            source_runtime_root,
            clean_runtime_root,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
        )
        self.runtime_python = clean_runtime_root / "bin/python"
        self.assertTrue(self.runtime_python.is_file())
        runtime_manifest = clean_runtime_root / "runtime-integrity.json"
        self.runtime_integrity = _sha256(runtime_manifest.read_bytes())

    def _release_paths(self) -> list[str]:
        closure = json.loads(
            (ROOT / "release/runtime-closure-v1.json").read_text(encoding="utf-8")
        )
        tracked = subprocess.run(
            ["git", "-C", str(ROOT), "ls-files", "-z"],
            check=True,
            capture_output=True,
        ).stdout.split(b"\0")
        candidates = {item.decode("utf-8") for item in tracked if item} | {
            WORKER_RELATIVE
        }
        selected = set(closure["files"])
        for pattern in closure["patterns"]:
            matches = {
                relative
                for relative in candidates
                if PurePosixPath(relative).match(pattern)
            }
            self.assertTrue(matches, pattern)
            selected.update(matches)
        selected.difference_update(closure.get("excluded_files", []))
        self.assertIn(WORKER_RELATIVE, selected)
        return sorted(selected)

    def _materialize_release(self, destination: Path) -> str:
        destination.mkdir(mode=0o755)
        files: dict[str, str] = {}
        modes: dict[str, int] = {}
        for relative in self._release_paths():
            source = ROOT / relative
            self.assertTrue(source.is_file(), relative)
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
            target.parent.chmod(0o755)
            shutil.copyfile(source, target)
            mode = 0o755 if os.access(source, os.X_OK) else 0o644
            target.chmod(mode)
            files[relative] = _sha256(target.read_bytes())
            modes[relative] = mode
        source_commit = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        manifest = {
            "schema_version": 3,
            "release": "mingli-master-portable-core",
            "source_commit": source_commit,
            "files": files,
            "modes": modes,
        }
        manifest_bytes = (
            json.dumps(manifest, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8")
        manifest_path = destination / ".mingli-release-manifest.json"
        manifest_path.write_bytes(manifest_bytes)
        manifest_path.chmod(0o600)
        return _sha256(manifest_bytes)

    def _start_worker(self) -> subprocess.Popen:
        state = self.scratch / "state"
        state.mkdir(exist_ok=True, mode=0o700)
        state.chmod(0o700)
        environment = os.environ.copy()
        environment.pop("PYTHONPATH", None)
        environment["MINGLI_STORE_ROOT"] = str(state)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        process = subprocess.Popen(
            [
                str(self.runtime_python),
                "-I",
                "-S",
                "-B",
                str(self.release_root / WORKER_RELATIVE),
                "--expected-listing-sha256",
                self.release_listing,
                "--expected-runtime-integrity-sha256",
                self.runtime_integrity,
                "--ready-timeout-seconds",
                "15",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
            env=environment,
        )

        def stop() -> None:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=3)
            for stream in (process.stdin, process.stdout, process.stderr):
                if stream is not None and not stream.closed:
                    stream.close()

        self.addCleanup(stop)
        return process

    def _read_process_frame(
        self,
        process: subprocess.Popen,
        timeout: float = 15.0,
    ) -> dict[str, object]:
        assert process.stdout is not None
        readable, _, _ = select.select([process.stdout], [], [], timeout)
        self.assertTrue(readable, "worker emitted no bounded frame before timeout")
        payload = runtime_worker.read_frame(process.stdout)
        self.assertIsNotNone(payload, "worker exited without a bounded frame")
        assert payload is not None
        return payload

    def _send_command(
        self,
        process: subprocess.Popen,
        ready: dict[str, object],
        command: dict[str, object],
        *,
        request_id: str,
        sequence: int,
    ) -> tuple[dict[str, object], float]:
        assert process.stdin is not None
        envelope = {
            "type": "command",
            "protocol": runtime_worker.WORKER_PROTOCOL,
            "identity_sha256": ready["identity_sha256"],
            "request_id": request_id,
            "sequence": sequence,
            "command": command,
        }
        started = time.perf_counter()
        runtime_worker.write_frame(process.stdin, envelope)
        result = self._read_process_frame(process)
        if result.get("worker_action") == "continue":
            terminal = self._read_process_frame(process)
            self.assertEqual(
                terminal,
                _expected_terminal(
                    identity_sha256=str(ready["identity_sha256"]),
                    request_id=request_id,
                    sequence=sequence,
                ),
            )
        return result, (time.perf_counter() - started) * 1000

    def _assert_isolating_result(
        self,
        process: subprocess.Popen,
        payload: dict[str, object],
    ) -> None:
        self.assertEqual(payload["type"], "result", payload)
        self.assertEqual(payload["worker_action"], "isolate", payload)
        result = payload.get("result")
        self.assertIsInstance(result, dict)
        assert isinstance(result, dict)
        self.assertEqual(result.get("kind"), "stopped", payload)
        self.assertNotEqual(process.wait(timeout=5), 0)
        assert process.stdout is not None
        self.assertEqual(process.stdout.read(), b"", "worker emitted multiple results")

    def _assert_startup_rejected(self, process: subprocess.Popen) -> None:
        self.assertNotEqual(process.wait(timeout=20), 0)
        assert process.stdout is not None
        assert process.stderr is not None
        self.assertEqual(process.stdout.read(), b"", "invalid identity emitted READY")
        self.assertTrue(process.stderr.read(), "startup failure was not diagnosed")

    def _assert_no_worker_stdio(self, process: subprocess.Popen) -> None:
        assert process.stderr is not None
        readable, _, _ = select.select([process.stderr], [], [], 0)
        self.assertFalse(
            readable, "worker leaked Runtime diagnostics on a success path"
        )

    def _run_one_shot(self, command: dict, store_base: Path) -> tuple[dict, bytes]:
        environment = os.environ.copy()
        environment.pop("PYTHONPATH", None)
        environment["MINGLI_PYTHON"] = str(self.runtime_python)
        environment["MINGLI_STORE_ROOT"] = str(store_base)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        completed = subprocess.run(
            [
                "/bin/sh",
                str(self.release_root / "scripts/run_reading_transaction.sh"),
            ],
            input=(
                json.dumps(command, ensure_ascii=False, separators=(",", ":")) + "\n"
            ).encode("utf-8"),
            capture_output=True,
            check=True,
            env=environment,
        )
        self.assertEqual(completed.stderr, b"")
        self.assertEqual(completed.stdout.count(b"\n"), 1)
        return json.loads(completed.stdout), completed.stdout

    def _store_semantics(self, store_root: Path, state_token: str) -> dict:
        token_hash = hashlib.sha256(state_token.encode("ascii")).hexdigest()
        token_path = store_root / "state-tokens/index" / f"{token_hash}.json"
        token_record = json.loads(token_path.read_text(encoding="utf-8"))
        reading_id = token_record["reading_id"]
        reading_root = store_root / "readings" / reading_id
        pending = json.loads(
            (reading_root / "pending.json").read_text(encoding="utf-8")
        )
        history = json.loads(
            (reading_root / "prepared/000001.json").read_text(encoding="utf-8")
        )
        projection = json.loads(
            (store_root / "projections" / f"{reading_id}.json").read_text(
                encoding="utf-8"
            )
        )

        def normalize(value: object, key: str = "") -> object:
            if isinstance(value, dict):
                return {
                    item_key: normalize(item_value, item_key)
                    for item_key, item_value in sorted(value.items())
                }
            if isinstance(value, list):
                return [normalize(item, key) for item in value]
            if (
                key
                in {
                    "reading_id",
                    "root_reading_id",
                    "parent_reading_id",
                }
                and value == reading_id
            ):
                return "<reading-id>"
            if key in {"token_hash", "parent_token_hash"} and value == token_hash:
                return "<token-hash>"
            if key in {
                "artifact_digest",
                "bundle_digest",
                "evidence_digest",
                "judgment_digest",
                "prepared_digest",
            }:
                return f"<{key}>"
            return value

        self.assertEqual(normalize(pending), normalize(history))
        return {
            "token": normalize(token_record),
            "pending": normalize(pending),
            "projection": normalize(projection),
        }

    def test_full_verification_emits_identity_bound_ready_with_bounded_boot(
        self,
    ) -> None:
        started = time.perf_counter()
        process = self._start_worker()
        ready = self._read_process_frame(process)
        external_boot_ms = (time.perf_counter() - started) * 1000
        self.assertEqual(ready["type"], "ready", ready)
        self.assertEqual(ready["protocol"], runtime_worker.WORKER_PROTOCOL)
        self.assertEqual(
            ready["turn_terminal"],
            runtime_worker.TURN_TERMINAL_CAPABILITY,
        )
        self.assertLess(external_boot_ms, float(ready["ready_timeout_seconds"]) * 1000)
        self.assertLess(float(ready["boot_ms"]), 15_000)
        self.assertEqual(ready["release_path"], str(self.release_root))
        self.assertEqual(ready["listing_sha256"], self.release_listing)
        self.assertEqual(
            ready["runtime_integrity_sha256"],
            self.runtime_integrity,
        )
        self.assertEqual(ready["pid"], process.pid)
        self.assertEqual(len(ready["capability_ids"]), 14)
        self.assertTrue(ready["single_in_flight"])
        self.assertEqual(ready["replay_policy"], "forbidden")
        self.assertEqual(ready["fallback_policy"], "forbidden")
        self._assert_no_worker_stdio(process)
        print(
            "MINGLI_WORKER_READY "
            + json.dumps(
                {
                    "boot_ms": ready["boot_ms"],
                    "external_boot_ms": round(external_boot_ms, 3),
                    "listing": ready["listing_sha256"],
                    "runtime_integrity": ready["runtime_integrity_sha256"],
                    "turn_terminal": ready["turn_terminal"],
                    "worker_identity": ready["identity_sha256"],
                },
                sort_keys=True,
            )
        )

    def test_damaged_signed_release_never_emits_ready(self) -> None:
        damaged = self.release_root / "resources/runtime/catalog-v1.json"
        damaged.write_bytes(damaged.read_bytes() + b"\n")
        process = self._start_worker()
        self._assert_startup_rejected(process)

    def test_legacy_v1_command_is_stopped_and_isolated_by_v2_worker(self) -> None:
        process = self._start_worker()
        ready = self._read_process_frame(process)
        self.assertEqual(ready["protocol"], "mingli-runtime-worker-v2")
        assert process.stdin is not None
        runtime_worker.write_frame(
            process.stdin,
            _command(
                protocol="mingli-runtime-worker-v1",
                identity_sha256=str(ready["identity_sha256"]),
            ),
        )
        response = self._read_process_frame(process)
        self._assert_isolating_result(process, response)

    def test_commands_are_serial_and_echo_the_exact_bound_identity(self) -> None:
        process = self._start_worker()
        ready = self._read_process_frame(process)
        for sequence in (1, 2):
            result, _ = self._send_command(
                process,
                ready,
                {"kind": "describe"},
                request_id=f"describe-{sequence}",
                sequence=sequence,
            )
            self.assertEqual(result["type"], "result", result)
            self.assertEqual(result["request_id"], f"describe-{sequence}")
            self.assertEqual(result["sequence"], sequence)
            self.assertEqual(result["identity_sha256"], ready["identity_sha256"])
            self.assertEqual(result["worker_action"], "continue")
            self.assertEqual(result["result"]["kind"], "described")
        assert process.stdout is not None
        readable, _, _ = select.select([process.stdout], [], [], 0.05)
        self.assertFalse(readable, "worker emitted an unsolicited extra result")
        self._assert_no_worker_stdio(process)

    def test_pipelined_second_command_is_rejected_without_execution(self) -> None:
        process = self._start_worker()
        ready = self._read_process_frame(process)
        assert process.stdin is not None
        first = _command(identity_sha256=str(ready["identity_sha256"]))
        second = _command(
            2,
            request_id="request-2",
            identity_sha256=str(ready["identity_sha256"]),
        )
        process.stdin.write(
            runtime_worker.encode_frame(first) + runtime_worker.encode_frame(second)
        )
        process.stdin.flush()
        response = self._read_process_frame(process)
        self._assert_isolating_result(process, response)

    def test_duplicate_and_out_of_order_commands_fail_closed(self) -> None:
        process = self._start_worker()
        ready = self._read_process_frame(process)
        first, _ = self._send_command(
            process,
            ready,
            {"kind": "describe"},
            request_id="request-1",
            sequence=1,
        )
        self.assertEqual(first["type"], "result")
        duplicate, _ = self._send_command(
            process,
            ready,
            {"kind": "describe"},
            request_id="request-1",
            sequence=2,
        )
        self._assert_isolating_result(process, duplicate)

        process = self._start_worker()
        ready = self._read_process_frame(process)
        out_of_order, _ = self._send_command(
            process,
            ready,
            {"kind": "describe"},
            request_id="request-3",
            sequence=3,
        )
        self._assert_isolating_result(process, out_of_order)

    def test_boundary_frame_and_post_ready_identity_drift_fail_closed(self) -> None:
        process = self._start_worker()
        self._read_process_frame(process)
        assert process.stdin is not None
        process.stdin.write(struct.pack(">I", runtime_worker.MAX_FRAME_BYTES + 1))
        process.stdin.flush()
        self.assertEqual(process.wait(timeout=5), runtime_worker.EXIT_PROTOCOL)
        assert process.stdout is not None
        self.assertEqual(process.stdout.read(), b"")

        process = self._start_worker()
        ready = self._read_process_frame(process)
        signed_catalog = self.release_root / "resources/runtime/catalog-v1.json"
        signed_catalog.write_bytes(signed_catalog.read_bytes() + b"\n")
        stopped, _ = self._send_command(
            process,
            ready,
            {"kind": "describe"},
            request_id="drifted-release",
            sequence=1,
        )
        self._assert_isolating_result(process, stopped)

    def test_damaged_runtime_identity_never_emits_ready(self) -> None:
        manifest = self.runtime_python.parents[1] / "runtime-integrity.json"
        manifest.write_bytes(b"{invalid-runtime-identity\n")
        process = self._start_worker()
        self._assert_startup_rejected(process)

    def test_ziwei_first_and_next_thirty_are_all_strictly_below_one_second(
        self,
    ) -> None:
        process = self._start_worker()
        ready = self._read_process_frame(process)
        timings: list[float] = []
        for sequence in range(1, 32):
            result, elapsed_ms = self._send_command(
                process,
                ready,
                _prepare_command("ziwei", query_suffix=f"-{sequence}"),
                request_id=f"ziwei-{sequence}",
                sequence=sequence,
            )
            self.assertEqual(result["type"], "result", result)
            self.assertEqual(result["result"]["kind"], "prepared", result)
            timings.append(elapsed_ms)
        self.assertTrue(all(elapsed < 1000.0 for elapsed in timings), timings)
        self._assert_no_worker_stdio(process)
        ordered = sorted(timings)
        print(
            "MINGLI_WORKER_ZIWEI_31 "
            + json.dumps(
                {
                    "pass_count": sum(elapsed < 1000.0 for elapsed in timings),
                    "sample_count": len(timings),
                    "first_ms": round(timings[0], 3),
                    "p95_ms": round(ordered[29], 3),
                    "max_ms": round(max(timings), 3),
                },
                sort_keys=True,
            )
        )

    def test_five_product_interleave_matches_one_shot_and_store_semantics(
        self,
    ) -> None:
        backend_root = ROOT.parents[1] / "backend"
        self.assertTrue(backend_root.is_dir(), "Backend ViewModel projector is missing")
        if str(backend_root) not in sys.path:
            sys.path.insert(0, str(backend_root))
        from app.charts.projectors import project_runtime_view_model

        process = self._start_worker()
        ready = self._read_process_frame(process)
        worker_store = Path(str(ready["store_namespace"]))
        products = ("ziwei", "bazi", "liuren", "meihua", "liuyao", "ziwei")
        evidence: dict[str, dict[str, object]] = {}
        for sequence, product_id in enumerate(products, start=1):
            command = _prepare_command(product_id, query_suffix=f"-{sequence}")
            worker_envelope, worker_ms = self._send_command(
                process,
                ready,
                command,
                request_id=f"interleave-{sequence}-{product_id}",
                sequence=sequence,
            )
            self.assertEqual(worker_envelope["type"], "result", worker_envelope)
            worker_result = worker_envelope["result"]
            one_shot_base = self.scratch / f"one-shot-{sequence}-{product_id}"
            one_shot_result, one_shot_stdout = self._run_one_shot(
                command,
                one_shot_base,
            )
            self.assertEqual(worker_result["kind"], "prepared", worker_result)
            self.assertEqual(one_shot_result["kind"], "prepared", one_shot_result)
            self.assertEqual(
                _normalize_result(worker_result),
                _normalize_result(one_shot_result),
            )
            worker_view_model = project_runtime_view_model(
                worker_result["brief"], product_id=product_id
            )
            one_shot_view_model = project_runtime_view_model(
                one_shot_result["brief"], product_id=product_id
            )
            self.assertIsNotNone(worker_view_model, product_id)
            self.assertIsNotNone(one_shot_view_model, product_id)
            assert worker_view_model is not None
            assert one_shot_view_model is not None
            self.assertEqual(
                worker_view_model.model_dump(mode="json"),
                one_shot_view_model.model_dump(mode="json"),
            )
            canonical_worker = json.dumps(
                _normalize_result(worker_result),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            canonical_one_shot = json.dumps(
                _normalize_result(one_shot_result),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            self.assertEqual(canonical_worker, canonical_one_shot)
            one_shot_namespaces = list(one_shot_base.glob("*/readings-v51"))
            self.assertEqual(len(one_shot_namespaces), 1)
            self.assertEqual(
                self._store_semantics(worker_store, worker_result["state_token"]),
                self._store_semantics(
                    one_shot_namespaces[0], one_shot_result["state_token"]
                ),
            )
            evidence[f"{sequence}-{product_id}"] = {
                "worker_ms": round(worker_ms, 3),
                "canonical_result_sha256": _sha256(canonical_worker),
                "one_shot_stdout_bytes": len(one_shot_stdout),
                "fact_count": len(worker_result["brief"]["facts"]),
                "source_count": len(worker_result["brief"]["evidence"]),
                "view_model_schema": worker_view_model.schema_version,
            }
        self._assert_no_worker_stdio(process)
        print(
            "MINGLI_WORKER_FIVE_PRODUCT_EQUIVALENCE "
            + json.dumps(evidence, sort_keys=True)
        )

    def test_process_crash_never_replays_an_in_flight_command(self) -> None:
        process = self._start_worker()
        ready = self._read_process_frame(process)
        assert process.stdin is not None
        envelope = _command(
            request_id="crash-in-flight",
            identity_sha256=str(ready["identity_sha256"]),
            command=_prepare_command("ziwei"),
        )
        runtime_worker.write_frame(process.stdin, envelope)
        time.sleep(0.02)
        process.kill()
        self.assertLess(process.wait(timeout=5), 0)
        assert process.stdout is not None
        self.assertEqual(process.stdout.read(), b"")
        store = Path(str(ready["store_namespace"]))
        before_restart = sorted(
            path.relative_to(store).as_posix()
            for path in store.rglob("*")
            if path.is_file()
        )

        replacement = self._start_worker()
        replacement_ready = self._read_process_frame(replacement)
        self.assertEqual(replacement_ready["type"], "ready")
        assert replacement.stdout is not None
        readable, _, _ = select.select([replacement.stdout], [], [], 0.1)
        self.assertFalse(readable, "replacement worker replayed a crashed command")
        after_restart = sorted(
            path.relative_to(store).as_posix()
            for path in store.rglob("*")
            if path.is_file()
        )
        self.assertEqual(after_restart, before_restart)


if __name__ == "__main__":
    unittest.main()
