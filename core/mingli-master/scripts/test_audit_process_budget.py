#!/usr/bin/env python3
"""Contracts for bounded process pools used by expensive audit tests."""

from __future__ import annotations

import os
import unittest
from unittest import mock

import test_v51_remaining_provider_replays as remaining


class AuditProcessBudgetTests(unittest.TestCase):
    def test_default_and_configured_jobs_are_bounded_by_task_count(self) -> None:
        for module in (remaining,):
            with self.subTest(module=module.__name__), mock.patch.dict(
                os.environ,
                {"MINGLI_AUDIT_JOBS": "99"},
            ):
                self.assertEqual(module._audit_jobs(6), 6)

    def test_invalid_job_configuration_fails_before_audits_start(self) -> None:
        for module in (remaining,):
            with self.subTest(module=module.__name__), mock.patch.dict(
                os.environ,
                {"MINGLI_AUDIT_JOBS": "0"},
            ):
                with self.assertRaisesRegex(ValueError, "MINGLI_AUDIT_JOBS"):
                    module._audit_jobs(6)


if __name__ == "__main__":
    unittest.main()
