from __future__ import annotations

import sys
import shlex
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import provision_runtime
import runtime_python as runtime_guard


class ProvisionRuntimeTests(unittest.TestCase):
    def test_provision_rejects_a_symlinked_target_parent_before_install(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            real_parent = root / "real-parent"
            real_parent.mkdir()
            linked_parent = root / "linked-parent"
            linked_parent.symlink_to(real_parent, target_is_directory=True)
            requirements = root / "requirements.lock"
            requirements.write_text(
                "PyYAML==6.0.3 --hash=sha256:" + "0" * 64 + "\n",
                encoding="utf-8",
            )

            with (
                patch("provision_runtime.venv.EnvBuilder.create") as create,
                self.assertRaisesRegex(RuntimeError, "symlink"),
            ):
                provision_runtime.provision(
                    linked_parent / "venv",
                    requirements,
                    install=True,
                )
            create.assert_not_called()

    def test_existing_runtime_cannot_be_replaced_by_a_different_python_minor(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "venv"
            executable = provision_runtime.runtime_python(root)
            executable.parent.mkdir(parents=True)
            executable.write_text(
                "#!/bin/sh\necho '[99, 99]'\n", encoding="utf-8"
            )
            executable.chmod(0o700)
            with self.assertRaisesRegex(RuntimeError, "Python minor"):
                provision_runtime.assert_provision_interpreter_compatible(root)

    def test_install_is_hash_locked_and_staged_before_atomic_replace(self) -> None:
        source = Path(provision_runtime.__file__).read_text(encoding="utf-8")
        self.assertIn("--require-hashes", source)
        self.assertIn("--no-compile", source)
        self.assertIn("TemporaryDirectory", source)
        self.assertIn("os.replace", source)
        lock = Path(provision_runtime.__file__).resolve().parents[1] / "requirements-runtime.lock"
        text = lock.read_text(encoding="utf-8")
        for requirement in (
            "PyYAML==6.0.3",
            "sxtwl==2.0.7",
            "astronomy-engine==2.1.19",
            "cnlunar==0.2.4",
            "zhconv==1.4.3",
        ):
            self.assertIn(requirement, text)
        self.assertIn(
            "c458b6d084f9b935061bc36216e8a69a7e293a2f1e68bf956dcd9e6cbcd143f5",
            text,
        )
        self.assertEqual(text.count("--hash=sha256:"), 7)
        requirements_txt = lock.with_name("requirements.txt").read_text(encoding="utf-8")
        self.assertIn("zhconv==1.4.3", requirements_txt.splitlines())
        build_lock = lock.with_name("requirements-runtime-build.lock")
        build_text = build_lock.read_text(encoding="utf-8")
        self.assertIn("setuptools==82.0.1", build_text)
        self.assertIn("wheel==0.46.3", build_text)
        self.assertIn("packaging==26.2", build_text)
        self.assertEqual(build_text.count("--hash=sha256:"), 3)
        self.assertIn("--no-build-isolation", source)
        build_install = source.index("DEFAULT_BUILD_REQUIREMENTS")
        runtime_install = source.index('"--no-build-isolation"')
        self.assertLess(build_install, runtime_install)

    def test_provision_holds_exclusive_runtime_lock(self) -> None:
        source = Path(provision_runtime.__file__).read_text(encoding="utf-8")
        self.assertIn("runtime_lock", source)
        self.assertIn("exclusive=True", source)

    def test_provision_removes_bootstrap_site_hooks_before_manifesting(self) -> None:
        source = Path(provision_runtime.__file__).read_text(encoding="utf-8")
        uninstall = source.index('"uninstall"')
        manifest = source.index("write_installed_runtime_manifest", uninstall)
        self.assertLess(uninstall, manifest)
        self.assertIn('"pip"', source[uninstall:manifest])
        self.assertIn('"setuptools"', source[uninstall:manifest])
        self.assertIn('"wheel"', source[uninstall:manifest])
        self.assertIn('"packaging"', source[uninstall:manifest])

    def test_atomic_install_reprobes_the_final_relocated_runtime(self) -> None:
        source = Path(provision_runtime.__file__).read_text(encoding="utf-8")
        replace = source.index("os.replace(staged, venv_root)")
        final_probe = source.index(
            "probe_runtime_identity(str(runtime_python(venv_root)))", replace
        )
        self.assertGreater(final_probe, replace)

    def test_probe_is_isolated_and_checks_cnlunar_origin_and_known_answer(self) -> None:
        source = Path(provision_runtime.__file__).read_text(encoding="utf-8")
        self.assertIn("probe_runtime_identity", source)
        helper_source = Path(provision_runtime.__file__).with_name("runtime_python.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('"-I"', helper_source)
        self.assertIn("module.__file__", helper_source)
        self.assertIn("cnlunar_known_answer", helper_source)
        self.assertIn("cnlunar_reviewed_files", helper_source)

    def test_runtime_python_uses_platform_venv_layout(self) -> None:
        root = Path("/tmp/example-mingli-runtime")
        expected = root / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        self.assertEqual(provision_runtime.runtime_python(root), expected)

    def test_check_mode_rejects_a_missing_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            requirements = Path(temporary) / "requirements.txt"
            requirements.write_text("PyYAML==6.0.3\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "runtime does not exist"):
                provision_runtime.provision(
                    Path(temporary) / "venv",
                    requirements,
                    install=False,
                )

    def test_check_mode_rejects_wrong_pinned_dependency_versions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            requirements = root / "requirements.txt"
            requirements.write_text("PyYAML==6.0.3\nsxtwl==2.0.7\n", encoding="utf-8")
            executable = provision_runtime.runtime_python(root / "venv")
            executable.parent.mkdir(parents=True)
            executable.write_text(
                f'#!/bin/sh\nexec {shlex.quote(sys.executable)} "$@"\n', encoding="utf-8"
            )
            executable.chmod(0o700)

            wrong_pins = {**runtime_guard.PINNED_VERSIONS, "yaml": "0.0"}
            with patch.object(runtime_guard, "PINNED_VERSIONS", wrong_pins):
                with self.assertRaisesRegex(RuntimeError, "pinned"):
                    provision_runtime.provision(
                        root / "venv",
                        requirements,
                        install=False,
                    )


if __name__ == "__main__":
    unittest.main()
