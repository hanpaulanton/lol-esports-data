"""Tests for timezone normalization (KST regression from the real fixture)."""

from __future__ import annotations

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

from lib.timezones import normalize_local_to_utc  # noqa: E402

CONFIG = pathlib.Path(__file__).resolve().parents[1] / "config" / "timezone_offsets.json"


class TimezoneTests(unittest.TestCase):
    def test_kst_fixture_regression_2026_07_29_1700_becomes_0800z(self):
        """Real fixture values: date=2026-07-29 time=17:00 timezone=KST."""
        result = normalize_local_to_utc("2026-07-29", "17:00", "KST", "yes")
        self.assertIsNotNone(result)
        self.assertEqual("2026-07-29T08:00:00Z", result.utc_iso)

    def test_kst_dst_yes_flag_produces_warning_but_correct_offset(self):
        """KST has no DST; the fixture's dst=yes is an anomaly -> warning."""
        result = normalize_local_to_utc("2026-07-29", "17:00", "KST", "yes")
        self.assertEqual(1, len(result.warnings))
        self.assertIn("dst", result.warnings[0])

    def test_unknown_abbreviation_returns_none(self):
        self.assertIsNone(normalize_local_to_utc("2026-07-29", "17:00", "XYZ", "no"))

    def test_cet_is_deliberately_not_mapped_to_avoid_cet_cest_confusion(self):
        """CET/CEST confusion is called out by the instructions; CET stays
        unmapped until a human adds a verified entry with DST handling."""
        self.assertIsNone(normalize_local_to_utc("2026-07-29", "10:05", "CET", "yes"))

    def test_mapping_file_has_kst_entry_with_iana_candidates(self):
        import json

        data = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertIn("KST", data)
        self.assertEqual(540, data["KST"]["standardOffsetMinutes"])
        self.assertIn("Asia/Seoul", data["KST"]["ianaCandidates"])


if __name__ == "__main__":
    unittest.main()
