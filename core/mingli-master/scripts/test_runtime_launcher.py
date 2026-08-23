from __future__ import annotations

import os
import subprocess
import sys
import shutil
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "scripts" / "run_reading_transaction.sh"


class RuntimeLauncherTests(unittest.TestCase):
    def test_launcher_uses_the_declared_runtime_without_system_python_fallback(self) -> None:
        text = LAUNCHER.read_text(encoding="utf-8")
        self.assertIn("MINGLI_PYTHON", text)
        self.assertIn(".local/share/mingli-master/venv/bin/python", text)
        self.assertNotIn("/usr/bin/" + "python", text)
        self.assertIn('"$runtime" -I -S -B "$skill_dir/scripts/runtime_launcher.py"', text)
        self.assertNotIn('exec "$runtime" "$skill_dir/scripts/reading_transaction.py"', text)
        self.assertIn("runtime_launcher.py", text)

    def test_launcher_module_validates_before_importing_or_running_transaction(self) -> None:
        launcher_module = (ROOT / "scripts/runtime_launcher.py").read_text(encoding="utf-8")
        validation = launcher_module.index("validate_installed_runtime")
        preimport = launcher_module.index("current_runtime_identity")
        run = launcher_module.index("runpy.run_path")
        self.assertLess(validation, preimport)
        self.assertLess(preimport, run)
        self.assertIn("runtime_lock", launcher_module)
        self.assertIn("runtime_python.py", launcher_module)
        self.assertIn("validate_runtime_identity", launcher_module)
        self.assertIn('sys.pycache_prefix = "/dev/null"', launcher_module)

    def test_production_exec_ignores_checkout_and_environment_module_shadows(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            artifact = Path(temporary) / "artifact"
            scripts = artifact / "scripts"
            vendor = artifact / "vendor" / "cnlunar-0.2.4"
            scripts.mkdir(parents=True)
            vendor.mkdir(parents=True)
            shutil.copy2(LAUNCHER, scripts / LAUNCHER.name)
            shutil.copy2(ROOT / "scripts/runtime_python.py", scripts / "runtime_python.py")
            shutil.copy2(ROOT / "scripts/runtime_launcher.py", scripts / "runtime_launcher.py")
            shutil.copy2(
                ROOT / "vendor/cnlunar-0.2.4/PROVENANCE.json",
                vendor / "PROVENANCE.json",
            )
            shutil.copy2(ROOT / "requirements-runtime.lock", artifact / "requirements-runtime.lock")
            (scripts / "cnlunar.py").write_text(
                "raise RuntimeError('checkout cnlunar shadow imported')\n", encoding="utf-8"
            )
            (scripts / "yaml.py").write_text(
                "raise RuntimeError('checkout yaml shadow imported')\n", encoding="utf-8"
            )
            environment_shadow = Path(temporary) / "environment-shadow"
            environment_shadow.mkdir()
            (environment_shadow / "cnlunar.py").write_text(
                "raise RuntimeError('environment cnlunar shadow imported')\n", encoding="utf-8"
            )
            (scripts / "adapters").mkdir()
            (scripts / "adapters" / "json_cli.py").write_text(
                "import cnlunar, yaml\n"
                "from pathlib import Path\n"
                "assert 'site-packages' in str(Path(cnlunar.__file__).resolve())\n"
                "assert 'site-packages' in str(Path(yaml.__file__).resolve())\n"
                "print('isolated-production-exec')\n",
                encoding="utf-8",
            )
            completed = subprocess.run(
                [str(scripts / LAUNCHER.name)],
                cwd=environment_shadow,
                env={
                    **os.environ,
                    "MINGLI_PYTHON": sys.executable,
                    "PYTHONPATH": str(environment_shadow),
                },
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(completed.stdout.strip(), "isolated-production-exec")

    def test_production_exec_prevents_child_python_bytecode(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            artifact = Path(temporary) / "artifact"
            scripts = artifact / "scripts"
            vendor = artifact / "vendor" / "cnlunar-0.2.4"
            scripts.mkdir(parents=True)
            vendor.mkdir(parents=True)
            shutil.copy2(LAUNCHER, scripts / LAUNCHER.name)
            shutil.copy2(ROOT / "scripts/runtime_python.py", scripts / "runtime_python.py")
            shutil.copy2(ROOT / "scripts/runtime_launcher.py", scripts / "runtime_launcher.py")
            shutil.copy2(
                ROOT / "vendor/cnlunar-0.2.4/PROVENANCE.json",
                vendor / "PROVENANCE.json",
            )
            shutil.copy2(ROOT / "requirements-runtime.lock", artifact / "requirements-runtime.lock")
            child_module = scripts / "child_runtime_probe.py"
            child_module.write_text("VALUE = 1\n", encoding="utf-8")
            (scripts / "adapters").mkdir()
            (scripts / "adapters" / "json_cli.py").write_text(
                "import subprocess, sys\n"
                "from pathlib import Path\n"
                "scripts = Path(__file__).resolve().parents[1]\n"
                "completed = subprocess.run(\n"
                "    [sys.executable, '-c', "
                "f\"import sys; sys.path.insert(0, {str(scripts)!r}); import child_runtime_probe\"],\n"
                "    check=False, capture_output=True, text=True,\n"
                ")\n"
                "assert completed.returncode == 0, completed.stderr\n"
                "assert not (scripts / '__pycache__').exists(), "
                "'child Python wrote unchecked bytecode'\n"
                "print('child-bytecode-disabled')\n",
                encoding="utf-8",
            )
            environment = {**os.environ, "MINGLI_PYTHON": sys.executable}
            environment.pop("PYTHONDONTWRITEBYTECODE", None)
            completed = subprocess.run(
                [str(scripts / LAUNCHER.name)],
                cwd=artifact,
                env=environment,
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(completed.stdout.strip(), "child-bytecode-disabled")

    def test_launcher_can_open_the_transaction_cli(self) -> None:
        import json

        # The launcher forwards no argv: the only surface is one Command
        # JSON on stdin answered by one Result JSON on stdout.
        with tempfile.TemporaryDirectory() as home_dir:
            completed = subprocess.run(
                [str(LAUNCHER)],
                cwd=ROOT,
                env={
                    **os.environ,
                    "MINGLI_PYTHON": sys.executable,
                    "HOME": home_dir,
                },
                capture_output=True,
                text=True,
                input=json.dumps({"kind": "describe"}),
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        lines = [line for line in completed.stdout.splitlines() if line.strip()]
        self.assertEqual(len(lines), 1, completed.stdout)
        payload = json.loads(lines[0])
        self.assertEqual(payload.get("kind"), "described")
        self.assertTrue(payload.get("capabilities"))

    def test_launcher_rejects_executable_files_that_are_not_the_pinned_python_runtime(self) -> None:
        import json

        for executable in ("/bin/echo", "/usr/bin/true"):
            with self.subTest(executable=executable):
                completed = subprocess.run(
                    [str(LAUNCHER)],
                    cwd=ROOT,
                    env={**os.environ, "MINGLI_PYTHON": executable},
                    capture_output=True,
                    text=True,
                    input="{}",
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                payload = json.loads(completed.stdout.strip())
                self.assertEqual(payload.get("kind"), "stopped")
                self.assertTrue(str(payload.get("public_copy") or "").strip())
                self.assertEqual(
                    payload.get("failure", {}).get("category"),
                    "bootstrap",
                )
                self.assertIn("runtime", completed.stderr.lower())

    def test_launcher_without_home_still_returns_one_stopped_result(self) -> None:
        import json

        environment = {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}
        completed = subprocess.run(
            [str(LAUNCHER)],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            input="{}",
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout.strip())
        self.assertEqual(payload.get("kind"), "stopped")
        self.assertTrue(str(payload.get("public_copy") or "").strip())
        self.assertEqual(
            payload.get("failure", {}).get("category"),
            "bootstrap",
        )

    def test_launcher_missing_bootstrap_still_returns_one_stopped_result(self) -> None:
        import json

        with tempfile.TemporaryDirectory() as temporary:
            artifact = Path(temporary) / "artifact"
            scripts = artifact / "scripts"
            scripts.mkdir(parents=True)
            copied = scripts / LAUNCHER.name
            shutil.copy2(LAUNCHER, copied)
            completed = subprocess.run(
                [str(copied)],
                cwd=artifact,
                env={
                    **os.environ,
                    "MINGLI_PYTHON": sys.executable,
                    "HOME": str(artifact / "home"),
                },
                capture_output=True,
                text=True,
                input="{}",
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout.strip())
        self.assertEqual(payload.get("kind"), "stopped")
        self.assertTrue(str(payload.get("public_copy") or "").strip())
        self.assertEqual(
            payload.get("failure", {}).get("category"),
            "bootstrap",
        )

    def test_launcher_rejects_legacy_shell_arguments_as_a_stopped_result(self) -> None:
        import json

        with tempfile.TemporaryDirectory() as home_dir:
            completed = subprocess.run(
                [str(LAUNCHER), "probe"],
                cwd=ROOT,
                env={
                    **os.environ,
                    "MINGLI_PYTHON": sys.executable,
                    "HOME": home_dir,
                },
                capture_output=True,
                text=True,
                input=json.dumps({"kind": "describe"}),
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout.strip())
        self.assertEqual(payload.get("kind"), "stopped")
        self.assertEqual(payload.get("reason"), "error")
        self.assertTrue(str(payload.get("public_copy") or "").strip())
        self.assertEqual(
            payload.get("failure", {}).get("code"),
            "bootstrap.unexpected_arguments",
        )


if __name__ == "__main__":
    unittest.main()
