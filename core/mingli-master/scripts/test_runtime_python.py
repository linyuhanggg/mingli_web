from __future__ import annotations

import os
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import runtime_python


ROOT = Path(__file__).resolve().parents[1]
CHILD_LAUNCHERS = (
    "scripts/bazi_calc.py",
    "scripts/fortune_calc.py",
    "scripts/liuren_calc.py",
)
CALENDAR_ADAPTERS = (
    "scripts/bazi_fact_adapter.py",
    "scripts/near_time_fortune_adapter.py",
    "scripts/liuren_fact_adapter.py",
)


class RuntimePythonTests(unittest.TestCase):
    def test_provider_audit_startup_does_not_compile_runtime_packages(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            cache_root = Path(temporary) / "pycache"
            env = os.environ.copy()
            env.pop("PYTHONDONTWRITEBYTECODE", None)
            env["PYTHONPYCACHEPREFIX"] = str(cache_root)
            env["PYTHONPATH"] = str(ROOT / "scripts")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/audit_provider_completeness.py"),
                    "--help",
                ],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                timeout=30,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            compiled_runtime_packages = [
                path
                for path in cache_root.rglob("*.pyc")
                if "site-packages" in path.parts
            ]
            self.assertEqual(compiled_runtime_packages, [])

    def test_readme_audit_commands_disable_bytecode_writes(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for script in (
            "scripts/audit_provider_completeness.py --check",
            "scripts/audit_v51_vocabulary_locality.py --check",
        ):
            with self.subTest(script=script):
                self.assertIn(
                    f'PYTHONPATH=scripts "$MINGLI_PYTHON" -B \\\n  {script}',
                    readme,
                )

    def test_runtime_root_rejects_a_symlinked_virtual_environment(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            real = parent / "real-venv"
            executable = real / "bin/python"
            executable.parent.mkdir(parents=True)
            (real / "pyvenv.cfg").write_text("home = /usr/bin\n", encoding="utf-8")
            executable.write_text("#!/bin/sh\n", encoding="utf-8")
            link = parent / "linked-venv"
            link.symlink_to(real, target_is_directory=True)

            with self.assertRaisesRegex(RuntimeError, "symlink"):
                runtime_python.runtime_root_for_executable(link / "bin/python")

    def test_probe_disables_site_initialization(self) -> None:
        with patch("runtime_python.subprocess.run") as run:
            run.return_value.returncode = 23
            run.return_value.stdout = ""
            run.return_value.stderr = "expected failure"
            with self.assertRaises(RuntimeError):
                runtime_python.probe_runtime_identity(str(Path(sys.executable)))
        self.assertEqual(run.call_args.args[0][1:3], ["-I", "-S"])

    def test_runtime_tree_rejects_symlink_and_unrecorded_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = root / "example"
            package.mkdir()
            (package / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
            manifest = runtime_python.build_runtime_tree_manifest(
                [root], owned_paths={"example/module.py"}
            )
            runtime_python.validate_runtime_tree([root], manifest)
            (package / "extra.py").write_text("DRIFT = 1\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "unrecorded runtime drift"):
                runtime_python.validate_runtime_tree([root], manifest)
            (package / "extra.py").unlink()
            (root / "yaml.py").write_text("DRIFT = 1\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "unrecorded runtime drift"):
                runtime_python.validate_runtime_tree([root], manifest)
            (root / "yaml.py").unlink()
            (package / "link.py").symlink_to(package / "module.py")
            with self.assertRaisesRegex(RuntimeError, "symlink"):
                runtime_python.validate_runtime_tree([root], manifest)

    def test_runtime_tree_rejects_unchecked_bytecode(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = root / "example"
            package.mkdir()
            (package / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
            manifest = runtime_python.build_runtime_tree_manifest(
                [root], owned_paths={"example/module.py"}
            )
            cache = package / "__pycache__"
            cache.mkdir()
            (cache / "module.cpython-311.pyc").write_bytes(b"unchecked")

            with self.assertRaisesRegex(RuntimeError, "bytecode"):
                runtime_python.validate_runtime_tree([root], manifest)

    def test_exclusive_provision_lock_conflicts_with_shared_runtime_lock(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            runtime_root = Path(temporary) / "venv"
            with runtime_python.runtime_lock(runtime_root, exclusive=False):
                with self.assertRaisesRegex(RuntimeError, "runtime lock"):
                    with runtime_python.runtime_lock(
                        runtime_root, exclusive=True, blocking=False
                    ):
                        self.fail("exclusive lock unexpectedly acquired")

    def test_cnlunar_provenance_requires_all_reviewed_runtime_files(self) -> None:
        provenance = json.loads(
            (ROOT / "vendor/cnlunar-0.2.4/PROVENANCE.json").read_text(encoding="utf-8")
        )
        provenance["reviewed_files"].pop("cnlunar/tools.py")
        with tempfile.TemporaryDirectory() as temporary:
            mutated = Path(temporary) / "PROVENANCE.json"
            mutated.write_text(json.dumps(provenance), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "reviewed_files"):
                runtime_python.load_cnlunar_reviewed_hashes(mutated)

    def test_cnlunar_provenance_rejects_a_non_object_document(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            mutated = Path(temporary) / "PROVENANCE.json"
            mutated.write_text("[]", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "provenance"):
                runtime_python.load_cnlunar_reviewed_hashes(mutated)

    def test_runtime_identity_rejects_non_numeric_python_version(self) -> None:
        identity = runtime_python.current_runtime_identity()
        identity["python"] = ["3", "14", "0"]
        with self.assertRaisesRegex(RuntimeError, "Python identity"):
            runtime_python.validate_runtime_identity(identity)

    def test_runtime_identity_rejects_a_mutated_installed_cnlunar_file(self) -> None:
        identity = runtime_python.current_runtime_identity()
        identity["cnlunar_reviewed_files"]["cnlunar/lunar.py"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "cnlunar reviewed-file hashes"):
            runtime_python.validate_runtime_identity(identity)

    def test_runtime_identity_binds_cnlunar_entrypoint_and_holidays(self) -> None:
        identity = runtime_python.current_runtime_identity()
        self.assertIn("cnlunar/__init__.py", identity["cnlunar_reviewed_files"])
        self.assertIn("cnlunar/holidays.py", identity["cnlunar_reviewed_files"])
        identity["cnlunar_reviewed_files"]["cnlunar/__init__.py"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "cnlunar reviewed-file hashes"):
            runtime_python.validate_runtime_identity(identity)

    def test_runtime_origins_must_be_under_exact_site_roots(self) -> None:
        identity = runtime_python.current_runtime_identity()
        identity["site_roots"] = [identity["prefix"]]
        with self.assertRaisesRegex(RuntimeError, "isolated runtime identity"):
            runtime_python.validate_runtime_identity(identity)

    def test_defaults_to_the_current_interpreter(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("MINGLI_PYTHON", None)
            self.assertEqual(runtime_python.resolve_runtime_python(), Path(sys.executable).absolute())

    def test_explicit_runtime_must_be_an_executable_file(self) -> None:
        configured = Path(sys.executable)
        with patch.dict(os.environ, {"MINGLI_PYTHON": str(configured)}):
            self.assertEqual(runtime_python.resolve_runtime_python(), configured.absolute())

    def test_child_runtime_command_disables_bytecode_writes(self) -> None:
        configured = Path(sys.executable).absolute()
        with patch("runtime_python.resolve_runtime_python", return_value=configured):
            self.assertEqual(
                runtime_python.runtime_command(),
                [str(configured), "-B"],
            )

    def test_runtime_without_required_dependencies_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            configured = Path(temporary) / "python"
            configured.write_text("#!/bin/sh\necho 'missing yaml sxtwl'\nexit 23\n", encoding="utf-8")
            configured.chmod(0o700)
            runtime_python._probe_runtime.cache_clear()
            with patch.dict(os.environ, {"MINGLI_PYTHON": str(configured)}):
                with self.assertRaisesRegex(RuntimeError, "requires Python"):
                    runtime_python.resolve_runtime_python()

    def test_non_python_executable_cannot_pass_the_runtime_probe(self) -> None:
        runtime_python._probe_runtime.cache_clear()
        with patch.dict(os.environ, {"MINGLI_PYTHON": "/bin/echo"}):
            with self.assertRaisesRegex(RuntimeError, "probe"):
                runtime_python.resolve_runtime_python()

    def test_runtime_with_wrong_pinned_versions_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            configured = Path(temporary) / "python"
            configured.write_text(
                "#!/bin/sh\n"
                "echo '{\"marker\":\"mingli-runtime-v1\",\"python\":[3,14,0],\"yaml\":\"0.0\",\"sxtwl\":\"0.0\"}'\n",
                encoding="utf-8",
            )
            configured.chmod(0o700)
            runtime_python._probe_runtime.cache_clear()
            with patch.dict(os.environ, {"MINGLI_PYTHON": str(configured)}):
                with self.assertRaisesRegex(RuntimeError, "pinned"):
                    runtime_python.resolve_runtime_python()

    def test_runtime_pins_the_astronomy_engine(self) -> None:
        self.assertEqual(runtime_python.PINNED_VERSIONS["astronomy"], "2.1.19")
        requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
        self.assertIn("astronomy-engine==2.1.19", requirements.splitlines())

    def test_runtime_pins_the_selection_engine(self) -> None:
        self.assertIn("cnlunar", runtime_python.REQUIRED_MODULES)
        self.assertEqual(runtime_python.PINNED_VERSIONS["cnlunar"], "0.2.4")
        requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
        self.assertIn("cnlunar==0.2.4", requirements.splitlines())

    def test_runtime_pins_and_manifests_the_text_normalizer(self) -> None:
        self.assertIn("zhconv", runtime_python.REQUIRED_MODULES)
        self.assertEqual(runtime_python.PINNED_VERSIONS["zhconv"], "1.4.3")
        self.assertEqual(runtime_python.REQUIRED_DISTRIBUTIONS["zhconv"], "1.4.3")
        requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
        self.assertIn("zhconv==1.4.3", requirements.splitlines())

    def test_runtime_probe_ignores_pythonpath_module_shadowing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            shadow = Path(temporary) / "cnlunar.py"
            shadow.write_text(
                "raise RuntimeError('shadow module imported')\n",
                encoding="utf-8",
            )
            runtime_python._probe_runtime.cache_clear()
            with patch.dict(os.environ, {"PYTHONPATH": temporary}):
                runtime_python._probe_runtime(str(Path(sys.executable).absolute()))

    def test_virtualenv_symlink_is_not_resolved_away(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            link = Path(temporary) / "venv-python"
            link.symlink_to(Path(sys.executable))
            with (
                patch.dict(os.environ, {"MINGLI_PYTHON": str(link)}),
                patch("runtime_python._probe_runtime") as probe,
            ):
                self.assertEqual(runtime_python.resolve_runtime_python(), link.absolute())
                probe.assert_called_once_with(str(link.absolute()))

    def test_production_launchers_do_not_select_system_python_implicitly(self) -> None:
        for relative in (*CHILD_LAUNCHERS, *CALENDAR_ADAPTERS):
            with self.subTest(relative=relative):
                text = (ROOT / relative).read_text(encoding="utf-8")
                self.assertNotIn("/usr/bin/" + "python3", text)


if __name__ == "__main__":
    unittest.main()
