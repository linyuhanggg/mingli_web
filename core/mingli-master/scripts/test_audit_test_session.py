#!/usr/bin/env python3
"""Contracts for the ephemeral full-suite audit report cache."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import audit_test_session


class AuditTestSessionTests(unittest.TestCase):
    def test_published_report_round_trips_only_in_expected_session(self) -> None:
        with tempfile.TemporaryDirectory() as temporary, mock.patch.dict(
            os.environ,
            {
                audit_test_session.SESSION_ENV: temporary,
                audit_test_session.MATRIX_EXPECTED_ENV: "1",
            },
        ):
            audit_test_session.mark_started("luming-nayin")
            audit_test_session.publish_report(
                "luming-nayin",
                {"provider_ready": True, "counts": {"cases": 30}},
            )
            loaded = audit_test_session.load_report("luming-nayin")

        self.assertEqual(
            loaded,
            {"provider_ready": True, "counts": {"cases": 30}},
        )

    def test_failed_or_absent_session_falls_back_without_stale_data(self) -> None:
        with tempfile.TemporaryDirectory() as temporary, mock.patch.dict(
            os.environ,
            {
                audit_test_session.SESSION_ENV: temporary,
                audit_test_session.MATRIX_EXPECTED_ENV: "1",
            },
        ):
            audit_test_session.mark_failed("qimen", "worker failed")
            self.assertIsNone(audit_test_session.load_report("qimen"))
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(audit_test_session.load_report("qimen"))


if __name__ == "__main__":
    unittest.main()
