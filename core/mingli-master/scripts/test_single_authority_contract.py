"""Only the explicitly selected capability adapter may run, exactly once."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from reading_engine.contracts import (
    AcceptedReading,
    PreparedReading,
    ReadingRequest,
)
from reading_engine.request_contract import (
    RequestContractError,
    validate_request_contract,
)
from reading_engine.storage import AtomicReadingStore
from reading_engine.turns import TurnEngine
from test_reading_engine_v2 import (
    CATALOG,
    StaticProvider,
    accept_prepared,
    provider_request,
)


def _engine(root: Path, *providers: StaticProvider) -> TurnEngine:
    return TurnEngine(
        store=AtomicReadingStore(root),
        providers={provider.system: provider for provider in providers},
        catalog=CATALOG,
    )


class SingleAuthorityContractTests(unittest.TestCase):
    def test_only_explicit_system_provider_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            liuren = StaticProvider("liuren")
            bazi = StaticProvider("bazi")
            engine = _engine(Path(temporary), liuren, bazi)

            turn = engine.prepare_turn(
                liuren.descriptor,
                provider_request("八字紫微六壬都写在句子里"),
            )

        self.assertIsInstance(turn.result, PreparedReading, turn.result)
        self.assertEqual(liuren.calls, 1)
        self.assertEqual(bazi.calls, 0)

    def test_no_invocation_means_no_state_or_provider_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            provider = StaticProvider("liuren")
            _engine(root, provider)
            ordinary_message = "帮我解释这段代码"

            self.assertEqual(ordinary_message, "帮我解释这段代码")
            self.assertEqual(provider.calls, 0)
            self.assertEqual(list((root / "readings").iterdir()), [])

    def test_invalid_action_identity_fails_before_provider(self) -> None:
        provider = StaticProvider("liuren")
        request = ReadingRequest(
            query="继续",
            action="continue",
            system="liuren",
            reading_id="a" * 32,
        )

        with self.assertRaises(RequestContractError):
            validate_request_contract(request)
        self.assertEqual(provider.calls, 0)

    def test_prepared_record_survives_engine_restart(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first_provider = StaticProvider("liuren")
            first_engine = _engine(root, first_provider)
            turn = first_engine.prepare_turn(
                first_provider.descriptor, provider_request("第一问")
            )
            self.assertIsInstance(turn.result, PreparedReading, turn.result)

            second_provider = StaticProvider("liuren")
            second_engine = _engine(root, second_provider)
            accepted = accept_prepared(second_engine, turn.result)

        self.assertIsInstance(accepted, AcceptedReading)
        self.assertEqual(accepted.reading_id, turn.result.reading_id)
        self.assertEqual(second_provider.calls, 0)


if __name__ == "__main__":
    unittest.main()
