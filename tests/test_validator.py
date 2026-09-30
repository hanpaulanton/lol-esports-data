"""Tests for the canonical validator (envelope + per-match rules)."""

from __future__ import annotations

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

from lib.validator import validate_envelope, validate_match  # noqa: E402


def valid_match(**overrides):
    match = {
        "id": "lp:x:2026-07-29:KRX:NS",
        "league": {"id": "LCK21", "name": "LCK", "region": "KR"},
        "tournament": {"id": "LCK 2026 Rounds 3-4", "name": "LCK 2026 Rounds 3-4"},
        "stage": {"id": "Rounds 3-4", "name": "Rounds 3-4"},
        "team1Id": "KRX",
        "team2Id": "NS",
        "scheduledAt": "2026-07-29T08:00:00Z",
        "status": "completed",
        "bestOf": 3,
        "score": {"team1": 0, "team2": 2},
        "sources": [],
        "lastUpdatedAt": "2026-09-29",
    }
    match.update(overrides)
    return match


def valid_envelope(**overrides):
    envelope = {
        "schemaVersion": 1,
        "dataVersion": "2026.09.29.01",
        "generatedAt": "2026-09-29T00:00:00Z",
        "leagues": [{"id": "LCK21", "name": "LCK", "region": "KR"}],
        "teams": [{"id": "KRX", "name": "Kiwoom DRX", "shortName": "KRX", "region": "KR", "aliases": []}],
        "matches": [valid_match()],
    }
    envelope.update(overrides)
    return envelope


class MatchValidatorTests(unittest.TestCase):
    def test_valid_match_has_no_problems(self):
        self.assertEqual([], validate_match(valid_match()))

    def test_missing_id_is_reported(self):
        match = valid_match()
        del match["id"]
        problems = validate_match(match)
        self.assertEqual(1, len(problems))
        self.assertIn(".id", problems[0])

    def test_empty_team_id_is_reported(self):
        problems = validate_match(valid_match(team1Id="  "))
        self.assertEqual(1, len(problems))
        self.assertIn("team1Id", problems[0])

    def test_bad_status_is_reported_with_allowed_values(self):
        problems = validate_match(valid_match(status="finished"))
        self.assertEqual(1, len(problems))
        self.assertIn("completed", problems[0])

    def test_bad_scheduledat_format_is_reported(self):
        problems = validate_match(valid_match(scheduledAt="2026-07-29 08:00:00"))
        self.assertEqual(1, len(problems))
        self.assertIn("scheduledAt", problems[0])

    def test_impossible_date_is_reported(self):
        problems = validate_match(valid_match(scheduledAt="2026-02-30T08:00:00Z"))
        self.assertEqual(1, len(problems))
        self.assertIn("not a real date", problems[0])

    def test_zero_or_negative_bestof_is_reported(self):
        problems = validate_match(valid_match(bestOf=0))
        self.assertEqual(1, len(problems))
        self.assertIn("bestOf", problems[0])

    def test_negative_score_is_reported(self):
        problems = validate_match(valid_match(score={"team1": -1, "team2": 0}))
        self.assertEqual(1, len(problems))
        self.assertIn("score", problems[0])


class EnvelopeValidatorTests(unittest.TestCase):
    def test_valid_envelope_has_no_problems(self):
        self.assertEqual([], validate_envelope(valid_envelope()))

    def test_wrong_schemaversion_is_reported(self):
        problems = validate_envelope(valid_envelope(schemaVersion=2))
        self.assertIn("schemaVersion: must be 1", problems)

    def test_missing_matches_list_is_reported(self):
        envelope = valid_envelope()
        del envelope["matches"]
        problems = validate_envelope(envelope)
        self.assertIn("matches: must be a list", problems)

    def test_invalid_nested_match_is_reported_with_index_and_id(self):
        envelope = valid_envelope()
        envelope["matches"].append({"id": "bad"})
        problems = validate_envelope(envelope)
        self.assertTrue(any("matches[1][id=bad]" in p for p in problems))

    def test_league_without_name_is_reported(self):
        envelope = valid_envelope(leagues=[{"id": "LCK21"}])
        problems = validate_envelope(envelope)
        self.assertTrue(any(p.startswith("leagues[0]") for p in problems))

    def test_scheduled_match_in_envelope_is_not_rejected(self):
        """PHASE 18-9 (GATE 1 fix): a scheduled record with the legitimate
        nulls (team ids / score / scheduledAt) must pass envelope validation
        via the scheduled branch, not be rejected by completed rules."""
        envelope = valid_envelope()
        envelope["matches"].append({
            "id": "lp:EM 2026 Summer Main Event:2026-10-01:TBD:TBD",
            "league": {"id": "EM", "name": "EMEA Masters", "region": "EU"},
            "tournament": {"id": "EM 2026 Summer Main Event", "name": "EM 2026 Summer Main Event"},
            "stage": {"id": "Round 6", "name": "Round 6"},
            "team1Id": None,
            "team2Id": None,
            "scheduledAt": None,
            "status": "scheduled",
            "bestOf": 3,
            "score": None,
            "lastUpdatedAt": "2026-09-30",
            "_provisional": {
                "teamSlotState": {"team1": "TBD", "team2": "TBD"},
                "gameBlockCount": 3,
                "rpgidCount": {"total": 3, "nonEmpty": 0},
            },
        })
        problems = validate_envelope(envelope)
        self.assertEqual([], [p for p in problems if "matches[1]" in p], problems)

    def test_scheduled_warning_in_envelope_is_reported_not_dropped(self):
        """Fail-closed: a scheduled record that triggers a V-rule warning must
        surface in envelope problems (never silently dropped)."""
        envelope = valid_envelope()
        envelope["matches"].append({
            "id": "lp:x:2026-09-30:BIG:SNSH",
            "league": {"id": "EM", "name": "EMEA Masters", "region": "EU"},
            "tournament": {"id": "t", "name": "t"},
            "stage": {"id": "s", "name": "s"},
            "team1Id": "BIG",
            "team2Id": "SNSH",
            "scheduledAt": None,
            "status": "scheduled",
            "bestOf": 3,
            "score": None,
            "lastUpdatedAt": "2026-09-30",
            "_provisional": {
                "teamSlotState": {"team1": "KNOWN", "team2": "KNOWN"},
                "gameBlockCount": 1,
                "rpgidCount": {"total": 1, "nonEmpty": 0},
            },
        })
        problems = validate_envelope(envelope)
        self.assertTrue(any("game block count 1 != effective bestOf 3" in p for p in problems))

    def test_completed_match_still_goes_through_completed_rules(self):
        """Regression guard: a completed record with null fields must still be
        rejected (it must NOT take the scheduled branch)."""
        envelope = valid_envelope()
        envelope["matches"][0]["score"] = None
        problems = validate_envelope(envelope)
        self.assertTrue(any("score" in p for p in problems))


if __name__ == "__main__":
    unittest.main()
