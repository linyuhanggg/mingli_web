"""Direct contracts for the product-owned simplified-text canonical."""

from __future__ import annotations

import unittest
from unittest.mock import patch

import simplified_canonical
from simplified_canonical import canonical_metadata, canonicalize


class SimplifiedCanonicalTests(unittest.TestCase):
    def test_opencc_foundation_and_editorial_variant_are_applied(self) -> None:
        self.assertEqual(canonicalize("陰陽亥夘未木合"), "阴阳亥卯未木合")

    def test_canonicalization_is_idempotent(self) -> None:
        text = "本義乾縣象，阴阳亥卯未木合"
        self.assertEqual(canonicalize(canonicalize(text)), canonicalize(text))

    def test_foundation_version_mismatch_fails_closed(self) -> None:
        simplified_canonical._converter.cache_clear()
        try:
            with patch.object(simplified_canonical, "version", return_value="1.4.1"):
                with self.assertRaisesRegex(RuntimeError, "版本不匹配"):
                    canonicalize("陰陽")
        finally:
            simplified_canonical._converter.cache_clear()

    def test_provenance_names_the_exact_foundation_and_editorial_decision(self) -> None:
        metadata = canonical_metadata()

        self.assertEqual(metadata["canonical_id"], "mingli-product-simplified-v1")
        self.assertEqual(metadata["foundation"]["distribution"], "OpenCC")
        self.assertEqual(metadata["foundation"]["version"], "1.4.2")
        self.assertEqual(metadata["foundation"]["config"], "t2s")
        self.assertEqual(
            metadata["operation_order"],
            ["opencc:t2s_to_fixed_point", "project_editorial_rules"],
        )
        self.assertEqual(
            metadata["editorial_rules"],
            [
                {
                    "id": "MING-66-EDITORIAL-001",
                    "source": "夘",
                    "target": "卯",
                    "scope": "global",
                    "decision_ref": "Raft #mingli-dev task #22",
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
