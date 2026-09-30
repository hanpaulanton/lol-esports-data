"""PHASE 18-3-B: deterministic tests for the FIRST genuinely scheduled
Leaguepedia MatchSchedule example (Worlds 2026 Play-In).

Evidence: raw/leaguepedia/page_Data_2026 Season World Championship_Play-In.wikitext,
saved unmodified by the permitted PHASE 18-3-B request (log in
raw/leaguepedia/phase18_3b_fetch_metadata.json). These tests lock the observed
scheduled-row schema; they do not assert anything about Leaguepedia beyond
this saved fixture, and they do not touch production normalization.

Classification wording follows the handoff: a key present with a value is
OBSERVED; a key present but empty is OBSERVED_ABSENT.
"""

from __future__ import annotations

import datetime
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.leaguepedia_parser import find_nested_by_name, find_templates  # noqa: E402
from lib.series_score import (  # noqa: E402
    IdentityStatus,
    SeriesScoreStatus,
    TeamIdentityResolver,
    compute_series_score,
    iter_series_with_games,
)

PLAYIN = ROOT / "raw" / "leaguepedia" / "page_Data_2026 Season World Championship_Play-In.wikitext"

# Observation date for this phase (handoff section 7 / metadata file).
OBSERVATION_DATE = datetime.date(2026, 9, 30)

# Values observed with a non-empty value on every scheduled row.
OBSERVED_VALUE_FIELDS = ("date", "time", "timezone", "dst", "initialorder", "stream")
# Result-bearing fields observed as empty keys on every scheduled row.
OBSERVED_ABSENT_FIELDS = (
    "team1", "team2", "team1score", "team2score", "winner",
    "pbp", "color", "vodinterview", "with", "mvp", "vodhl", "reddit",
)
GAME_KEY_SET = (
    "blue", "red", "winner", "riot_platform_game_id", "first_sel", "ssel",
    "pick_sel", "first_pick", "ff", "vod", "vodpb", "vodstart", "vodpost",
    "vodhl", "vodinterview", "with", "mvp",
)


def load_series():
    wikitext = PLAYIN.read_text(encoding="utf-8")
    return list(iter_series_with_games(wikitext))


class PlayinScheduledFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.wikitext = PLAYIN.read_text(encoding="utf-8")
        cls.templates = find_templates(cls.wikitext)
        cls.series = [t for t in cls.templates if t.name == "MatchSchedule"]
        cls.starts = [t for t in cls.templates if t.name == "MatchSchedule/Start"]
        cls.rows = load_series()

    def test_page_has_three_round_starts_with_bestof_5(self):
        self.assertEqual(3, len(self.starts))
        for start in self.starts:
            self.assertEqual("5", start.args.named["bestof"])
        self.assertEqual(["Round 1", "Round 2", "Round 3"],
                         [s.args.named["tab"] for s in self.starts])

    def test_page_has_six_series_rows(self):
        self.assertEqual(6, len(self.series))

    def test_every_row_is_genuinely_future_relative_to_observation(self):
        """Handoff section 10: scheduled classification needs date support,
        not merely a missing winner."""
        for _context, args, _games in self.rows:
            date = datetime.date.fromisoformat((args.get("date") or "").strip())
            with self.subTest(date=date.isoformat()):
                self.assertGreater(date, OBSERVATION_DATE)

    def test_result_bearing_fields_are_present_keys_with_empty_values(self):
        for index, (_context, args, _games) in enumerate(self.rows, 1):
            for field in OBSERVED_ABSENT_FIELDS:
                with self.subTest(row=index, field=field):
                    self.assertIn(field, args, "key must be present (OBSERVED_ABSENT, not missing)")
                    self.assertEqual("", (args.get(field) or "").strip())

    def test_value_fields_are_populated(self):
        for index, (_context, args, _games) in enumerate(self.rows, 1):
            for field in OBSERVED_VALUE_FIELDS:
                with self.subTest(row=index, field=field):
                    self.assertTrue((args.get(field) or "").strip(), f"{field} should carry a value")
            self.assertRegex((args.get("date") or "").strip(), r"^\d{4}-\d{2}-\d{2}$")
            self.assertRegex((args.get("time") or "").strip(), r"^\d{2}:\d{2}$")

    def test_timezone_and_dst_observed_values(self):
        """Recorded without interpretation (handoff section 13)."""
        for _context, args, _games in self.rows:
            self.assertEqual("PST", (args.get("timezone") or "").strip())
            self.assertEqual("yes", (args.get("dst") or "").strip())

    def test_no_status_like_key_exists_in_any_row(self):
        for _context, args, _games in self.rows:
            for key in args:
                self.assertNotIn("status", key.lower())
                self.assertNotIn("postpon", key.lower())
                self.assertNotIn("cancel", key.lower())

    def test_no_series_level_bestof_argument(self):
        for _context, args, _games in self.rows:
            for key in args:
                self.assertNotIn("bestof", key.lower())

    def test_five_game_blocks_per_row_matching_start_bestof(self):
        """Outcome A+B: game blocks exist before the match but carry no values."""
        for index, (_context, _args, games) in enumerate(self.rows, 1):
            with self.subTest(row=index):
                self.assertEqual(5, len(games))
                self.assertEqual([f"game{n}" for n in range(1, 6)], [key for key, _ in games])

    def test_every_game_template_uses_the_completed_key_set_and_is_empty(self):
        for index, (_context, _args, games) in enumerate(self.rows, 1):
            for game_key, game_args in games:
                with self.subTest(row=index, game=game_key):
                    self.assertEqual(set(GAME_KEY_SET), set(game_args))
                    for field in GAME_KEY_SET:
                        self.assertEqual("", (game_args.get(field) or "").strip())

    def test_riot_platform_game_id_not_preassigned_on_this_page(self):
        """Outcome B for rpgid: blocks exist, no rpgid preassigned (0/30)."""
        missing = [
            (index, game_key)
            for index, (_context, _args, games) in enumerate(self.rows, 1)
            for game_key, game_args in games
            if not (game_args.get("riot_platform_game_id") or "").strip()
        ]
        self.assertEqual(30, len(missing), "all 30 scheduled game templates lack an rpgid here")

    def test_identity_resolver_does_not_guess_empty_team_slots(self):
        """Empty team slots must stay UNKNOWN — never resolved, never guessed."""
        resolver = TeamIdentityResolver()
        for _context, args, games in self.rows:
            for raw in (args.get("team1"), args.get("team2")):
                self.assertIs(IdentityStatus.UNKNOWN, resolver.resolve(raw).status)
            for _game_key, game_args in games:
                self.assertIs(IdentityStatus.UNKNOWN, resolver.resolve(game_args.get("blue")).status)
                self.assertIs(IdentityStatus.UNKNOWN, resolver.resolve(game_args.get("red")).status)

    def test_series_score_helper_fails_closed_on_scheduled_rows(self):
        """The PHASE 18-3-A helper must report UNKNOWN (not 0-0, not CONFLICT)
        for a row whose identity and results are all empty."""
        resolver = TeamIdentityResolver()
        for _context, args, games in self.rows:
            result = compute_series_score(args.get("team1"), args.get("team2"), games, resolver)
            self.assertIs(SeriesScoreStatus.UNKNOWN, result.status)
            self.assertIsNone(result.computed_team1_wins)
            self.assertIsNone(result.computed_team2_wins)


if __name__ == "__main__":
    unittest.main()
