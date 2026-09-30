"""PHASE 18-3-C: deterministic tests for the Worlds 2026 Main Event scheduled
fixture (all team slots empty) and the structural facts it adds beyond
PHASE 18-3-B.

Evidence: raw/leaguepedia/page_Data_2026 Season World Championship_Main
Event.wikitext (saved unmodified; log: phase18_3c_fetch_metadata.json).
These tests lock the observed schema only; they assert nothing about pages
not saved, and they do not touch production normalization."""

from __future__ import annotations

import datetime
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.series_score import (  # noqa: E402
    IdentityStatus,
    SeriesScoreStatus,
    TeamIdentityResolver,
    compute_series_score,
    iter_series_with_games,
)

MAIN_EVENT = ROOT / "raw" / "leaguepedia" / "page_Data_2026 Season World Championship_Main Event.wikitext"
OBSERVATION_DATE = datetime.date(2026, 9, 30)

VALUE_FIELDS = ("date", "time", "timezone", "dst", "initialorder", "stream")
EMPTY_FIELDS = (
    "team1", "team2", "team1score", "team2score", "winner",
    "pbp", "color", "vodinterview", "with", "mvp", "vodhl", "reddit", "qq",
)
GAME_KEY_SET = (
    "blue", "red", "winner", "riot_platform_game_id", "first_sel", "ssel",
    "pick_sel", "first_pick", "ff", "recap", "vodpb", "vodstart", "vodpost",
    "vodhl", "vodinterview", "with", "mvp",
)


class MainEventScheduledFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = list(iter_series_with_games(MAIN_EVENT.read_text(encoding="utf-8")))

    def test_forty_rows_all_future(self):
        self.assertEqual(40, len(self.rows))
        for _context, args, _games in self.rows:
            date = datetime.date.fromisoformat((args.get("date") or "").strip())
            with self.subTest(date=date.isoformat()):
                self.assertGreater(date, OBSERVATION_DATE)

    def test_no_row_carries_any_result_value(self):
        for field in ("winner", "team1score", "team2score"):
            for _context, args, _games in self.rows:
                with self.subTest(field=field):
                    self.assertEqual("", (args.get(field) or "").strip())

    def test_team_slots_empty_on_every_row(self):
        for field in ("team1", "team2"):
            for _context, args, _games in self.rows:
                with self.subTest(field=field):
                    self.assertIn(field, args)
                    self.assertEqual("", (args.get(field) or "").strip())

    def test_value_fields_populated_pst_timezone(self):
        for index, (_context, args, _games) in enumerate(self.rows, 1):
            for field in VALUE_FIELDS:
                with self.subTest(row=index, field=field):
                    self.assertTrue((args.get(field) or "").strip())
            self.assertEqual("PST", (args.get("timezone") or "").strip())

    def test_dst_observed_value_set_is_yes_spring_no(self):
        """Recorded verbatim, no interpretation (handoff section 20)."""
        observed = {(args.get("dst") or "").strip() for _c, args, _g in self.rows}
        self.assertEqual({"yes", "spring", "no"}, observed)

    def test_game_blocks_equal_applicable_bestof(self):
        """Game-block count equals the row's effective bestof: Start bestof,\nexcept rows carrying a series-level bestof override."""
        for index, (context, args, games) in enumerate(self.rows, 1):
            override = (args.get("bestof") or "").strip()
            effective = int(override) if override else int(context["bestof"])
            with self.subTest(row=index, tab=context["tab"], effective=effective):
                self.assertEqual(effective, len(games))

    def test_series_level_bestof_override_observed_on_four_round3_rows(self):
        """Rows 17, 18, 21, 22 (Round 3, Start bestof=3) carry bestof=1."""
        overrides = [
            (context["tab"], (args.get("bestof") or "").strip(), len(games))
            for context, args, games in self.rows
            if (args.get("bestof") or "").strip()
        ]
        self.assertEqual([("Round 3", "1", 1)] * 4, overrides)

    def test_qq_key_present_and_empty_on_all_rows(self):
        """New key first observed in this fixture; meaning UNKNOWN."""
        for _context, args, _games in self.rows:
            self.assertIn("qq", args)
            self.assertEqual("", (args.get("qq") or "").strip())

    def test_game_templates_use_main_event_key_set_and_are_empty(self):
        """Main Event game key set differs from LCK/Play-In fixtures: `recap`
        replaces `vod` (17 keys, single consistent set on this page)."""
        for index, (_context, _args, games) in enumerate(self.rows, 1):
            for game_key, game_args in games:
                with self.subTest(row=index, game=game_key):
                    self.assertEqual(set(GAME_KEY_SET), set(game_args))
                    for field in GAME_KEY_SET:
                        self.assertEqual("", (game_args.get(field) or "").strip())

    def test_riot_platform_game_id_not_preassigned(self):
        missing = [
            (index, game_key)
            for index, (_context, _args, games) in enumerate(self.rows, 1)
            for game_key, game_args in games
            if not (game_args.get("riot_platform_game_id") or "").strip()
        ]
        total_games = sum(len(games) for _c, _a, games in self.rows)
        self.assertEqual(total_games, len(missing))

    def test_identity_resolver_keeps_empty_slots_unknown(self):
        resolver = TeamIdentityResolver()
        for _context, args, games in self.rows:
            self.assertIs(IdentityStatus.UNKNOWN, resolver.resolve(args.get("team1")).status)
            self.assertIs(IdentityStatus.UNKNOWN, resolver.resolve(args.get("team2")).status)
            for _game_key, game_args in games:
                self.assertIs(IdentityStatus.UNKNOWN, resolver.resolve(game_args.get("blue")).status)

    def test_series_score_helper_fails_closed(self):
        resolver = TeamIdentityResolver()
        for _context, args, games in self.rows:
            result = compute_series_score(args.get("team1"), args.get("team2"), games, resolver)
            self.assertIs(SeriesScoreStatus.UNKNOWN, result.status)
            self.assertIsNone(result.computed_team1_wins)


if __name__ == "__main__":
    unittest.main()
