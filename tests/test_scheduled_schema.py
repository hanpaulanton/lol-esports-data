"""Regression tests locking the PHASE 18-2 scheduled-schema investigation
findings. These tests describe the CURRENT saved fixture (raw files must not
change); if the fixture is ever extended with new data, update these numbers
from fresh evidence — never guess."""

from __future__ import annotations

import pathlib
import sys
import unittest
from collections import Counter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

from lib.leaguepedia_parser import find_templates, find_nested_by_name  # noqa: E402
from lib.series_score import SeriesScoreStatus, TeamIdentityResolver, compute_series_score  # noqa: E402

DATA_PAGE = pathlib.Path(__file__).resolve().parents[1] / "raw" / "leaguepedia" / "page_data_lck_rounds34.wikitext"
TOURN_PAGE = pathlib.Path(__file__).resolve().parents[1] / "raw" / "leaguepedia" / "page_lck_rounds34.wikitext"
RESOLVER = TeamIdentityResolver()


class ScheduledSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.wikitext = DATA_PAGE.read_text(encoding="utf-8")
        cls.templates = find_templates(cls.wikitext)
        cls.series = [t for t in cls.templates if t.name == "MatchSchedule"]
        cls.starts = [t for t in cls.templates if t.name == "MatchSchedule/Start"]

    def test_series_count_is_40(self):
        self.assertEqual(40, len(self.series))

    def test_start_blocks_are_4_with_bestof_3(self):
        self.assertEqual(4, len(self.starts))
        for start in self.starts:
            self.assertEqual("3", start.args.named["bestof"])
        tabs = [s.args.named["tab"] for s in self.starts]
        self.assertEqual(["Week 10", "Week 11", "Week 12", "Week 13"], tabs)

    def test_every_series_has_winner_and_numeric_scores(self):
        """This is why all 40 series classify as COMPLETED."""
        for t in self.series:
            args = t.args.named
            self.assertIn(args["winner"], ("1", "2"), f"{args['team1']} vs {args['team2']}")
            self.assertTrue(args["team1score"].isdigit(), args["team1score"])
            self.assertTrue(args["team2score"].isdigit(), args["team2score"])

    def test_no_series_level_bestof_argument_observed(self):
        for t in self.series:
            for key in t.args.named:
                self.assertNotIn("bestof", key.lower())

    def test_start_scope_is_start_until_next_start(self):
        """Document order: each Start is immediately followed by its week's
        series; 4 Starts x 10 series = 40."""
        order = [(t.name, t) for t in self.templates if t.name in ("MatchSchedule/Start", "MatchSchedule")]
        seen: dict[str, int] = {}
        last_tab = None
        for name, t in order:
            if name == "MatchSchedule/Start":
                last_tab = t.args.named["tab"]
                seen.setdefault(last_tab, 0)
            else:
                self.assertIsNotNone(last_tab, "series appeared before any Start")
                seen[last_tab] += 1
        self.assertEqual({"Week 10": 10, "Week 11": 10, "Week 12": 10, "Week 13": 10}, seen)

    def test_series_scores_match_per_game_winners_with_side_swap(self):
        """{{MatchSchedule/Game}} winner is blue(1)/red(2) based and sides swap
        between games; series scores must equal per-game winner counts.
        PHASE 18-3-A: uses the shared identity-aware helper (the Rounds 3-4
        fixture uses codes on both levels, so this also pins code<->code
        resolution and side-swap aggregation)."""
        for t in self.series:
            args = t.args.named
            games = []
            for key, value in args.items():
                if key.lower().startswith("game"):
                    games.extend(find_nested_by_name(value, "MatchSchedule/Game"))
            result = compute_series_score(
                args["team1"],
                args["team2"],
                [(f"game{index + 1}", dict(g.args.named)) for index, g in enumerate(games)],
                RESOLVER,
                int(args["team1score"]),
                int(args["team2score"]),
            )
            self.assertIs(SeriesScoreStatus.OK, result.status,
                          f"{args['team1']} vs {args['team2']}: {result.reason}")
            self.assertEqual(int(args["team1score"]), result.computed_team1_wins)
            self.assertEqual(int(args["team2score"]), result.computed_team2_wins)

    def test_no_scheduled_candidate_in_fixture(self):
        """No series lacks winner/scores, and no scheduling marker arg exists."""
        for t in self.series:
            args = t.args.named
            self.assertTrue(args["winner"].isdigit() and args["team1score"].isdigit())
            for key in args:
                self.assertNotIn("schedul", key.lower())

    def test_game_templates_use_a_consistent_key_set(self):
        key_sets = set()
        for t in self.series:
            for key, value in t.args.named.items():
                if key.lower().startswith("game"):
                    for g in find_nested_by_name(value, "MatchSchedule/Game"):
                        key_sets.add(tuple(sorted(g.args.named.keys())))
        self.assertEqual(1, len(key_sets), f"multiple game arg key sets: {key_sets}")

    def test_exactly_one_game_missing_riot_platform_game_id(self):
        missing = []
        for t in self.series:
            for key, value in t.args.named.items():
                if key.lower().startswith("game"):
                    for g in find_nested_by_name(value, "MatchSchedule/Game"):
                        if not g.args.named.get("riot_platform_game_id", "").strip():
                            missing.append((t.args.named["team1"], t.args.named["team2"], key))
        self.assertEqual(
            [("GEN", "DPLUS", "game1")],
            missing,
            "the single empty riot_platform_game_id belongs to GEN vs DPLUS (2026-08-01) game1",
        )

    def test_tournament_page_has_no_matchschedule(self):
        templates = find_templates(TOURN_PAGE.read_text(encoding="utf-8"))
        self.assertEqual([], [t.name for t in templates if t.name == "MatchSchedule"])


if __name__ == "__main__":
    unittest.main()
