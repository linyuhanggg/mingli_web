import io
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import release_deploy


class ReleaseDeployTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.source = self.root / "source"
        self.destination = self.root / "destination"
        (self.source / "scripts").mkdir(parents=True)
        (self.source / "SKILL.md").write_text("release\n", encoding="utf-8")
        (self.source / "scripts" / "runner.py").write_text(
            "print('v2')\n", encoding="utf-8"
        )
        self.files = ["SKILL.md", "scripts/runner.py"]

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _write_runtime_closure(
        self,
        *,
        files: list[str],
        patterns: list[str] | None = None,
    ) -> None:
        closure = self.source / release_deploy.RUNTIME_CLOSURE_RELATIVE
        closure.parent.mkdir(parents=True, exist_ok=True)
        closure.write_text(
            json.dumps(
                {
                    "schema_version": release_deploy.RUNTIME_CLOSURE_SCHEMA,
                    "files": files,
                    "patterns": patterns or [],
                }
            )
            + "\n",
            encoding="utf-8",
        )

    def test_manifest_is_deterministic_and_hash_bound(self) -> None:
        first = release_deploy.build_manifest(self.source, self.files, "abc123")
        second = release_deploy.build_manifest(self.source, reversed(self.files), "abc123")

        self.assertEqual(first, second)
        self.assertEqual(
            first["release"],
            "mingli-master-portable-core",
        )
        self.assertEqual(first["source_commit"], "abc123")
        self.assertEqual(list(first["files"]), sorted(self.files))
        self.assertEqual(len(first["files"]["SKILL.md"]), 64)
        self.assertEqual(
            first["modes"]["SKILL.md"],
            stat.S_IMODE((self.source / "SKILL.md").stat().st_mode),
        )

    def test_tracked_release_files_use_explicit_runtime_closure(self) -> None:
        excluded = {
            "agents/openai.yaml": "host-specific prompt\n",
            "docs/release-notes.md": "release notes\n",
            "runtime/readings/store.json": "runtime state\n",
            "tmp/release-draft.md": "temporary draft\n",
            "personal/profile.json": "personal data\n",
            "secrets/token.txt": "secret\n",
            "references/regression/cases/real/case.input.json": "{}\n",
            "references/regression/cases/example/case.outcome.json": "{}\n",
            "scripts/test_runner.py": "test\n",
            ".env": "TOKEN=not-a-real-secret\n",
        }
        for relative, content in excluded.items():
            path = self.source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

        self._write_runtime_closure(
            files=[
                "SKILL.md",
                release_deploy.RUNTIME_CLOSURE_RELATIVE,
                "scripts/runner.py",
            ]
        )

        subprocess.run(["git", "init", "-q", str(self.source)], check=True)
        subprocess.run(["git", "-C", str(self.source), "add", "."], check=True)

        self.assertEqual(
            release_deploy.tracked_release_files(self.source),
            [
                "SKILL.md",
                release_deploy.RUNTIME_CLOSURE_RELATIVE,
                "scripts/runner.py",
            ],
        )

    def test_runtime_closure_expands_only_tracked_pattern_matches(self) -> None:
        runtime_manifest = self.source / "resources/runtime/providers/alpha.json"
        runtime_manifest.parent.mkdir(parents=True)
        runtime_manifest.write_text("{}\n", encoding="utf-8")
        ignored = self.source / "resources/runtime/providers/alpha.md"
        ignored.write_text("not runtime data\n", encoding="utf-8")
        self._write_runtime_closure(
            files=[
                "SKILL.md",
                release_deploy.RUNTIME_CLOSURE_RELATIVE,
                "scripts/runner.py",
            ],
            patterns=["resources/runtime/providers/*.json"],
        )
        subprocess.run(["git", "init", "-q", str(self.source)], check=True)
        subprocess.run(["git", "-C", str(self.source), "add", "."], check=True)

        self.assertEqual(
            release_deploy.tracked_release_files(self.source),
            [
                "SKILL.md",
                release_deploy.RUNTIME_CLOSURE_RELATIVE,
                "resources/runtime/providers/alpha.json",
                "scripts/runner.py",
            ],
        )

    def test_runtime_closure_rejects_untracked_or_unlisted_paths(self) -> None:
        self._write_runtime_closure(
            files=[
                "SKILL.md",
                release_deploy.RUNTIME_CLOSURE_RELATIVE,
                "scripts/untracked.py",
            ]
        )
        (self.source / "scripts/untracked.py").write_text(
            "print('untracked')\n", encoding="utf-8"
        )
        subprocess.run(["git", "init", "-q", str(self.source)], check=True)
        subprocess.run(
            ["git", "-C", str(self.source), "add", "SKILL.md", "scripts/runner.py", "release"],
            check=True,
        )

        with self.assertRaisesRegex(ValueError, "not tracked"):
            release_deploy.tracked_release_files(self.source)

    def test_sync_prunes_stale_release_files_but_preserves_local_corpus_and_git(self) -> None:
        (self.destination / "references" / "fulltext").mkdir(parents=True)
        (self.destination / ".git").mkdir(parents=True)
        (self.destination / "stale").mkdir(parents=True)
        (self.destination / "references" / "fulltext" / "book.md").write_text(
            "local corpus\n", encoding="utf-8"
        )
        (self.destination / ".git" / "HEAD").write_text(
            "ref: refs/heads/main\n", encoding="utf-8"
        )
        (self.destination / "stale" / "prompt.md").write_text(
            "old prompt\n", encoding="utf-8"
        )

        manifest = release_deploy.build_manifest(self.source, self.files, "abc123")
        result = release_deploy.sync_destination(
            self.source,
            self.destination,
            manifest,
            apply=True,
        )

        self.assertTrue(result["verified"])
        self.assertFalse((self.destination / "stale" / "prompt.md").exists())
        self.assertEqual(
            (self.destination / "references" / "fulltext" / "book.md").read_text(
                encoding="utf-8"
            ),
            "local corpus\n",
        )
        self.assertTrue((self.destination / ".git" / "HEAD").exists())
        installed_manifest = json.loads(
            (self.destination / release_deploy.MANIFEST_NAME).read_text(encoding="utf-8")
        )
        self.assertEqual(installed_manifest, manifest)

    def test_dry_run_changes_nothing(self) -> None:
        self.destination.mkdir()
        stale = self.destination / "old.txt"
        stale.write_text("old\n", encoding="utf-8")
        manifest = release_deploy.build_manifest(self.source, self.files, "abc123")

        result = release_deploy.sync_destination(
            self.source,
            self.destination,
            manifest,
            apply=False,
        )

        self.assertFalse(result["verified"])
        self.assertTrue(stale.exists())
        self.assertFalse((self.destination / "SKILL.md").exists())
        self.assertIn("old.txt", result["remove"])

    def test_verify_detects_destination_drift(self) -> None:
        manifest = release_deploy.build_manifest(self.source, self.files, "abc123")
        release_deploy.sync_destination(
            self.source,
            self.destination,
            manifest,
            apply=True,
        )
        (self.destination / "SKILL.md").write_text("tampered\n", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            release_deploy.verify_destination(self.destination, manifest)

    def test_manifest_rejects_paths_outside_release_root(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsafe release path"):
            release_deploy.build_manifest(self.source, ["../secret"], "abc123")

    def test_sync_rejects_directory_symlinks_before_writing(self) -> None:
        external = self.root / "external"
        external.mkdir()
        self.destination.mkdir()
        (self.destination / "scripts").symlink_to(external, target_is_directory=True)
        manifest = release_deploy.build_manifest(self.source, self.files, "abc123")

        with self.assertRaisesRegex(ValueError, "symbolic link"):
            release_deploy.sync_destination(
                self.source,
                self.destination,
                manifest,
                apply=True,
            )

        self.assertEqual(list(external.iterdir()), [])

    def test_main_never_resolves_a_top_level_destination_symlink(self) -> None:
        external = self.root / "external-install"
        external.mkdir()
        linked = self.root / "linked-install"
        linked.symlink_to(external, target_is_directory=True)
        manifest = release_deploy.build_manifest(self.source, self.files, "abc123")

        with (
            patch.object(release_deploy, "require_clean_source"),
            patch.object(release_deploy, "tracked_release_files", return_value=self.files),
            patch.object(release_deploy, "source_commit", return_value="abc123"),
            patch.object(release_deploy, "build_committed_manifest", return_value=manifest),
        ):
            with self.assertRaisesRegex(ValueError, "symbolic link"):
                release_deploy.main([
                    "--source", str(self.source),
                    "--destination", str(linked),
                ])

    def test_parent_symlink_swap_cannot_redirect_a_managed_copy(self) -> None:
        external = self.root / "external"
        external.mkdir()
        self.destination.mkdir()
        manifest = release_deploy.build_manifest(self.source, self.files, "abc123")
        real_copy = release_deploy._copy_release_file

        def swap_before_runner(handle, source, relative, mode):
            if relative == "scripts/runner.py":
                scripts = self.destination / "scripts"
                scripts.mkdir(exist_ok=True)
                scripts.rmdir()
                scripts.symlink_to(external, target_is_directory=True)
            return real_copy(handle, source, relative, mode)

        with patch.object(
            release_deploy,
            "_copy_release_file",
            side_effect=swap_before_runner,
        ):
            with self.assertRaises((OSError, ValueError)):
                release_deploy.sync_destination(
                    self.source,
                    self.destination,
                    manifest,
                    apply=True,
                )

        self.assertEqual(list(external.iterdir()), [])

    def test_failed_copy_restores_the_previous_managed_tree(self) -> None:
        self.destination.mkdir()
        old_skill = self.destination / "SKILL.md"
        old_skill.write_text("old release\n", encoding="utf-8")
        manifest = release_deploy.build_manifest(self.source, self.files, "abc123")
        real_copy = release_deploy._copy_release_file

        def fail_on_runner(handle, source, relative, mode):
            if Path(source) == self.source / "scripts" / "runner.py":
                raise OSError("injected copy failure")
            return real_copy(handle, source, relative, mode)

        with patch.object(release_deploy, "_copy_release_file", side_effect=fail_on_runner):
            with self.assertRaisesRegex(OSError, "injected copy failure"):
                release_deploy.sync_destination(
                    self.source,
                    self.destination,
                    manifest,
                    apply=True,
                )

        self.assertEqual(old_skill.read_text(encoding="utf-8"), "old release\n")
        self.assertFalse((self.destination / "scripts" / "runner.py").exists())
        self.assertFalse((self.destination / release_deploy.MANIFEST_NAME).exists())

    def test_keyboard_interrupt_also_restores_the_previous_managed_tree(self) -> None:
        self.destination.mkdir()
        old_skill = self.destination / "SKILL.md"
        old_skill.write_text("old release\n", encoding="utf-8")
        manifest = release_deploy.build_manifest(self.source, self.files, "abc123")
        real_copy = release_deploy._copy_release_file

        def interrupt_on_runner(handle, source, relative, mode):
            if relative == "scripts/runner.py":
                raise KeyboardInterrupt("injected interruption")
            return real_copy(handle, source, relative, mode)

        with patch.object(
            release_deploy,
            "_copy_release_file",
            side_effect=interrupt_on_runner,
        ):
            with self.assertRaisesRegex(KeyboardInterrupt, "injected interruption"):
                release_deploy.sync_destination(
                    self.source,
                    self.destination,
                    manifest,
                    apply=True,
                )

        self.assertEqual(old_skill.read_text(encoding="utf-8"), "old release\n")
        self.assertFalse((self.destination / "scripts" / "runner.py").exists())
        self.assertFalse((self.destination / release_deploy.MANIFEST_NAME).exists())

    def test_protection_attempts_every_destination_without_masking_primary_failure(self) -> None:
        second = self.root / "destination-two"
        self.destination.mkdir()
        second.mkdir()
        manifest = release_deploy.build_manifest(self.source, self.files, "abc123")

        with (
            patch.object(release_deploy, "require_clean_source"),
            patch.object(release_deploy, "_verify_release_sources", return_value={
                "research_root": str(self.source),
                "provider_source_verification": {},
                "verified": True,
                "failures": [],
            }),
            patch.object(
                release_deploy,
                "extra_gate_pathspecs",
                return_value=((), ()),
            ),
            patch.object(release_deploy, "tracked_release_files", return_value=self.files),
            patch.object(release_deploy, "source_commit", return_value="abc123"),
            patch.object(release_deploy, "build_committed_manifest", return_value=manifest),
            patch.object(release_deploy, "destination_is_protected", return_value=True),
            patch.object(release_deploy, "unprotect_destination"),
            patch.object(release_deploy, "sync_destination", side_effect=ValueError("primary deploy failure")),
            patch.object(
                release_deploy,
                "protect_destination",
                side_effect=[OSError("first protection failure"), None],
            ) as protect,
        ):
            with self.assertRaisesRegex(ValueError, "primary deploy failure"):
                release_deploy.main([
                    "--source", str(self.source),
                    "--destination", str(self.destination),
                    "--destination", str(second),
                    "--apply",
                ])

        self.assertEqual(protect.call_count, 2)

    def test_manifest_modes_come_from_the_commit_even_when_worktree_mode_is_ignored(self) -> None:
        runner = self.source / "scripts" / "runner.py"
        runner.chmod(0o755)
        subprocess.run(["git", "init", "-q", str(self.source)], check=True)
        subprocess.run(["git", "-C", str(self.source), "config", "user.name", "Test"], check=True)
        subprocess.run(["git", "-C", str(self.source), "config", "user.email", "test@example.invalid"], check=True)
        subprocess.run(["git", "-C", str(self.source), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.source), "commit", "-qm", "fixture"], check=True)
        commit = release_deploy.source_commit(self.source)
        subprocess.run(["git", "-C", str(self.source), "config", "core.fileMode", "false"], check=True)
        runner.chmod(0o644)

        manifest = release_deploy.build_committed_manifest(
            self.source,
            self.files,
            commit,
        )

        self.assertEqual(manifest["modes"]["scripts/runner.py"], 0o755)

    def test_verify_rejects_an_executable_mode_mismatch(self) -> None:
        runner = self.source / "scripts" / "runner.py"
        runner.chmod(0o755)
        manifest = release_deploy.build_manifest(self.source, self.files, "abc123")
        release_deploy.sync_destination(
            self.source,
            self.destination,
            manifest,
            apply=True,
        )
        (self.destination / "scripts" / "runner.py").chmod(0o644)

        with self.assertRaisesRegex(ValueError, "mode mismatch"):
            release_deploy.verify_destination(self.destination, manifest)

    def _init_git(self, repo: Path) -> None:
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        subprocess.run(
            ["git", "-C", str(repo), "config", "user.name", "Test"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(repo), "config", "user.email", "test@example.invalid"],
            check=True,
        )

    def _parent_repo_source(self) -> Path:
        repo = self.root / "parent"
        source = repo / "core" / "mingli-master"
        source.mkdir(parents=True)
        (source / "scripts").mkdir()
        (source / "SKILL.md").write_text("release\n", encoding="utf-8")
        (source / "scripts" / "runner.py").write_text(
            "print('v2')\n", encoding="utf-8"
        )
        closure = source / release_deploy.RUNTIME_CLOSURE_RELATIVE
        closure.parent.mkdir(parents=True, exist_ok=True)
        closure.write_text(
            json.dumps(
                {
                    "schema_version": release_deploy.RUNTIME_CLOSURE_SCHEMA,
                    "files": [
                        "SKILL.md",
                        release_deploy.RUNTIME_CLOSURE_RELATIVE,
                        "scripts/runner.py",
                    ],
                    "patterns": [],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        sibling = repo / "web" / "page.tsx"
        sibling.parent.mkdir(parents=True)
        sibling.write_text("dirty sibling\n", encoding="utf-8")
        self._init_git(repo)
        subprocess.run(["git", "-C", str(repo), "add", "core"], check=True)
        subprocess.run(
            ["git", "-C", str(repo), "commit", "-qm", "source"],
            check=True,
        )
        return source

    def test_require_clean_source_on_parent_git_ignores_sibling_paths(self) -> None:
        source = self._parent_repo_source()
        release_deploy.require_clean_source(source)

        (source / "scripts" / "runner.py").write_text("dirty\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "must be clean"):
            release_deploy.require_clean_source(source)

    def test_require_clean_source_can_limit_pathspecs_to_release_files(self) -> None:
        source = self._parent_repo_source()
        (source / "unrelated.md").write_text("unrelated dirty\n", encoding="utf-8")
        release_deploy.require_clean_source(
            source,
            pathspecs=[
                "SKILL.md",
                "scripts/runner.py",
                release_deploy.RUNTIME_CLOSURE_RELATIVE,
            ],
        )

        (source / "scripts" / "runner.py").write_text("dirty\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "must be clean"):
            release_deploy.require_clean_source(
                source,
                pathspecs=["SKILL.md", "scripts/runner.py"],
            )

    def test_tracked_release_files_and_committed_modes_use_source_prefix_in_parent_repo(
        self,
    ) -> None:
        source = self._parent_repo_source()
        runner = source / "scripts" / "runner.py"
        runner.chmod(0o755)
        subprocess.run(["git", "-C", str(source), "add", "scripts/runner.py"], check=True)
        subprocess.run(
            ["git", "-C", str(source), "commit", "-qm", "mode"],
            check=True,
        )
        files = release_deploy.tracked_release_files(source)
        self.assertEqual(
            files,
            [
                "SKILL.md",
                release_deploy.RUNTIME_CLOSURE_RELATIVE,
                "scripts/runner.py",
            ],
        )
        commit = release_deploy.source_commit(source)
        modes = release_deploy.committed_release_modes(source, files, commit)
        self.assertEqual(modes["scripts/runner.py"], 0o755)
        self.assertEqual(len(commit), 40)


class ProductionLauncherModeContractTests(unittest.TestCase):
    """The signed direct entrypoint must remain directly spawnable."""

    def test_committed_launcher_modes_match_the_production_spawn_contract(self) -> None:
        source = Path(__file__).resolve().parents[1]
        paths = (
            "scripts/run_reading_transaction.sh",
            "scripts/runtime_launcher.py",
        )

        modes = release_deploy.committed_release_modes(
            source,
            paths,
            release_deploy.source_commit(source),
        )

        self.assertEqual(modes["scripts/run_reading_transaction.sh"], 0o755)
        self.assertEqual(modes["scripts/runtime_launcher.py"], 0o644)


class ReleaseSourceVerificationTests(unittest.TestCase):
    """The release gate must audit the checkout being released."""

    def test_gate_derives_all_thirteen_audits_from_the_source_registry(self) -> None:
        # The registry is the single source of truth; the gate must cover
        # exactly the same provider set as the completeness audit.
        from pathlib import Path

        repo = Path(__file__).resolve().parents[1]
        scripts_dir = repo / "scripts"
        sys.path.insert(0, str(scripts_dir))
        try:
            from audit_provider_completeness import DEDICATED_AUDIT_MODULES
        finally:
            try:
                sys.path.remove(str(scripts_dir))
            except ValueError:
                pass
        expected = {
            system: module.__name__
            for system, module in DEDICATED_AUDIT_MODULES.items()
        }
        self.assertEqual(len(expected), 13)
        for module_name in expected.values():
            self.assertTrue(
                (repo / "scripts" / f"{module_name}.py").is_file(),
                f"audit module missing: {module_name}",
            )

    def test_gate_loads_audits_from_source_not_interpreter_path(self) -> None:
        # Point --source at the repo; the gate must resolve every provider
        # audit from that checkout, so a different cwd/sys.path cannot make
        # it audit A while deploying B.
        from pathlib import Path

        repo = Path(__file__).resolve().parents[1]
        result = release_deploy._verify_release_sources(repo, None)
        self.assertEqual(len(result["provider_source_verification"]), 13)
        self.assertFalse(result["verified"])  # no research root -> fail closed
        self.assertTrue(
            all(
                result["provider_source_verification"][system] == "skipped"
                for system in result["provider_source_verification"]
            )
        )


# Audit modules that name a checkout: their ``source_verification.status`` is
# the recognisable marker for which checkout the gate actually audited.  These
# are test fixtures only; they never run a real fulltext audit.
_VERIFIED_AUDIT_SOURCE = """\
def {module_name}(research_root=None):
    return {{"source_verification": {{"status": "verified"}}}}
"""

_SKIPPED_AUDIT_SOURCE = """\
def {module_name}(research_root=None):
    return {{"source_verification": {{"status": "skipped"}}}}
"""

_REGISTRY_SOURCE = """\
import {mod_a}
import {mod_b}

DEDICATED_AUDIT_MODULES = {{
    "{sys_a}": {mod_a},
    "{sys_b}": {mod_b},
}}
"""


def _write_stub_checkout(
    root: Path,
    *,
    registry_systems: tuple[str, ...],
    module_names: tuple[str, ...],
    marker: str,
) -> Path:
    """Write a minimal checkout whose stub audits carry ``marker`` statuses."""
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    for module_name in module_names:
        source = _SKIPPED_AUDIT_SOURCE if marker == "skipped" else _VERIFIED_AUDIT_SOURCE
        (scripts / f"{module_name}.py").write_text(
            source.format(module_name=module_name),
            encoding="utf-8",
        )
    (scripts / "audit_provider_completeness.py").write_text(
        _REGISTRY_SOURCE.format(
            mod_a=module_names[0],
            mod_b=module_names[1],
            sys_a=registry_systems[0],
            sys_b=registry_systems[1],
        ),
        encoding="utf-8",
    )
    return root


class ReleaseCheckoutIsolationTests(unittest.TestCase):
    """The release gate must be immune to the parent interpreter's caches."""

    def setUp(self) -> None:
        self._clear_parent_stub_modules()

    def _prepare_checkouts(self) -> tuple[Path, Path]:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        base = Path(temporary.name)
        checkout_a = _write_stub_checkout(
            base / "checkout-a",
            registry_systems=("alpha", "beta"),
            module_names=("audit_alpha_marker_a", "audit_beta_marker_a"),
            marker="skipped",
        )
        checkout_b = _write_stub_checkout(
            base / "checkout-b",
            registry_systems=("alpha", "beta"),
            module_names=("audit_alpha_marker_b", "audit_beta_marker_b"),
            marker="verified",
        )
        return checkout_a, checkout_b

    @staticmethod
    def _clear_parent_stub_modules() -> None:
        # The isolation tests deliberately preload stub audits into the parent
        # interpreter.  Drop every module they touch before and after each test
        # so the selected fixture checkout is always the import authority.
        prefixes = (
            "audit_alpha_marker_",
            "audit_beta_marker_",
        )
        for name in [name for name in sys.modules if name.startswith(prefixes)]:
            del sys.modules[name]
        sys.modules.pop("audit_provider_completeness", None)

    def tearDown(self) -> None:
        self._clear_parent_stub_modules()

    def test_gate_audits_checkout_b_even_when_a_is_preloaded(self) -> None:
        checkout_a, checkout_b = self._prepare_checkouts()
        # Preload checkout A's audits into the parent interpreter, exactly the
        # situation the current gate is vulnerable to: same module names stay
        # cached in sys.modules after the first checkout is verified.
        sys.path.insert(0, str(checkout_a / "scripts"))
        try:
            from audit_provider_completeness import DEDICATED_AUDIT_MODULES as A_REGISTRY
            from audit_alpha_marker_a import audit_alpha_marker_a  # noqa: F401
            from audit_beta_marker_a import audit_beta_marker_a  # noqa: F401

            self.assertEqual(len(A_REGISTRY), 2)
        finally:
            try:
                sys.path.remove(str(checkout_a / "scripts"))
            except ValueError:
                pass

        research = checkout_b / "research"
        research.mkdir()
        result = release_deploy._verify_release_sources(checkout_b, research)

        # The gate must verify checkout B's audits, not the cached A modules.
        self.assertTrue(result["verified"], result["failures"])
        self.assertEqual(
            set(result["provider_source_verification"]),
            {"alpha", "beta"},
        )
        self.assertTrue(
            all(
                status == "verified"
                for status in result["provider_source_verification"].values()
            ),
            result["provider_source_verification"],
        )

    def test_gate_streams_provider_stages_and_returns_timing_and_resource_evidence(
        self,
    ) -> None:
        _, checkout = self._prepare_checkouts()
        research = checkout / "research"
        research.mkdir()
        progress = io.StringIO()

        result = release_deploy._verify_release_sources(
            checkout,
            research,
            progress_stream=progress,
        )

        self.assertTrue(result["verified"], result)
        self.assertEqual(result["failures"], [])
        self.assertEqual(result["provider_count"], 2)
        self.assertEqual(result["verified_count"], 2)
        self.assertEqual(set(result["provider_metrics"]), {"alpha", "beta"})
        self.assertGreaterEqual(result["elapsed_seconds"], 0)
        self.assertGreater(result["resource"]["process_peak_rss_bytes"], 0)
        events = [
            json.loads(
                line.removeprefix(
                    release_deploy.SOURCE_VERIFICATION_PROGRESS_PREFIX
                )
            )
            for line in progress.getvalue().splitlines()
            if line.startswith(release_deploy.SOURCE_VERIFICATION_PROGRESS_PREFIX)
        ]
        self.assertTrue(
            any(
                event.get("event") == "provider_stage"
                and event.get("provider") == "alpha"
                and event.get("stage") == "provider_fulltext_audit"
                for event in events
            ),
            events,
        )
        self.assertEqual(events[-1]["event"], "subprocess_complete")

    def test_gate_cancels_the_process_group_and_fails_closed_at_sixty_minute_cap(
        self,
    ) -> None:
        _, checkout = self._prepare_checkouts()
        module = checkout / "scripts" / "audit_alpha_marker_b.py"
        module.write_text(
            "import time\n"
            "def audit_alpha_marker_b(*, research_root=None):\n"
            "    time.sleep(10)\n"
            "    return {'source_verification': {'status': 'verified'}}\n",
            encoding="utf-8",
        )
        research = checkout / "research"
        research.mkdir()
        progress = io.StringIO()

        result = release_deploy._verify_release_sources(
            checkout,
            research,
            timeout_seconds=0.1,
            progress_stream=progress,
        )

        self.assertEqual(release_deploy.SOURCE_VERIFICATION_TIMEOUT_SECONDS, 3600)
        self.assertFalse(result["verified"])
        self.assertEqual(result["cancellation"]["reason"], "timeout")
        self.assertEqual(result["cancellation"]["provider"], "alpha")
        self.assertEqual(
            result["cancellation"]["stage"],
            "provider_fulltext_audit",
        )
        self.assertIn("exceeded 0.1 seconds", result["failures"][0])
        self.assertIn("timeout_cancel_requested", progress.getvalue())
        self.assertIn("cancel_received", progress.getvalue())

    def test_gate_without_research_root_validates_origin_without_running_audits(
        self,
    ) -> None:
        _, checkout = self._prepare_checkouts()
        for module in checkout.glob("scripts/audit_*_marker_b.py"):
            module.write_text(
                f"def {module.stem}(*, research_root=None):\n"
                "    raise AssertionError('audit must not run without research root')\n",
                encoding="utf-8",
            )

        result = release_deploy._verify_release_sources(checkout, None)

        self.assertFalse(result["verified"], result)
        self.assertEqual(
            result["provider_source_verification"],
            {"alpha": "skipped", "beta": "skipped"},
        )
        self.assertTrue(
            all("pass --research-root" in failure for failure in result["failures"]),
            result,
        )

    def test_gate_fails_closed_when_an_audit_module_escapes_the_source(self) -> None:
        # A registry that references a module whose real file lives outside
        # the selected checkout must make the gate fail closed.  The parent
        # interpreter has already cached that foreign module, so only a gate
        # that verifies the loaded file's real path can detect the escape.
        checkout_a, checkout_b = self._prepare_checkouts()
        sys.path.insert(0, str(checkout_a / "scripts"))
        try:
            from audit_alpha_marker_a import audit_alpha_marker_a  # noqa: F401
        finally:
            try:
                sys.path.remove(str(checkout_a / "scripts"))
            except ValueError:
                pass
        # B's registry points ``alpha`` at a module that only exists in A.
        registry_source = _REGISTRY_SOURCE.format(
            mod_a="audit_alpha_marker_a",
            mod_b="audit_beta_marker_b",
            sys_a="alpha",
            sys_b="beta",
        )
        (checkout_b / "scripts" / "audit_provider_completeness.py").write_text(
            registry_source, encoding="utf-8"
        )
        research = checkout_b / "research"
        research.mkdir()
        result = release_deploy._verify_release_sources(checkout_b, research)
        self.assertFalse(result["verified"])
        self.assertTrue(
            any("outside" in failure or "source" in failure for failure in result["failures"]),
            result["failures"],
        )

    def test_gate_does_not_retry_an_internal_type_error_without_research_root(
        self,
    ) -> None:
        """An audit bug is a failed release, never an old-signature retry."""

        _, checkout = self._prepare_checkouts()
        module = checkout / "scripts" / "audit_alpha_marker_b.py"
        module.write_text(
            "def audit_alpha_marker_b(*, research_root=None):\n"
            "    if research_root is not None:\n"
            "        raise TypeError('internal source verification bug')\n"
            "    return {'source_verification': {'status': 'verified'}}\n",
            encoding="utf-8",
        )
        research = checkout / "research"
        research.mkdir()

        result = release_deploy._verify_release_sources(checkout, research)

        self.assertFalse(result["verified"], result)
        self.assertEqual(
            result["provider_source_verification"].get("alpha"),
            "error",
            result,
        )
        self.assertTrue(
            any("TypeError" in failure for failure in result["failures"]),
            result,
        )


if __name__ == "__main__":
    unittest.main()
