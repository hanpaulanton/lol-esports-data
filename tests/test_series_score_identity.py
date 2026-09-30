"""PHASE 18-3-A: identity-aware series score verification tests.

Covers the shared resolver/aggregation helper (scripts/lib/series_score.py):

- code <-> code
- full name <-> code
- full name <-> full name
- side swap across games
- unknown identity stays UNKNOWN (never guessed)
- invalid winner value -> CONFLICT
- blue == red -> CONFLICT
- mixed Road to MSI representations (series full names vs game codes)
- declared score matching / declared score mismatch

Plus the fixture-level checks the HANDOFF requires: Rounds 3-4 40/40,
Season Playoffs 10/10, Road to MSI 5/5, and the three previously reported
Road to MSI mismatches explicitly asserted as correct.
"""

from __future__ import annotations

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
    series_score_matches_declared,
)

RAW = ROOT / "raw" / "leaguepedia"
ROUNDS34 = RAW / "page_data_lck_rounds34.wikitext"
PLAYOFFS = RAW / "page_data_lck_season_playoffs_scheduled.wikitext"
ROAD_TO_MSI = RAW / "page_data_lck_road_to_msi_scheduled.wikitext"


def game(blue: str, red: str, winner: str) -> tuple[str, dict[str, str]]:
    return "game1", {"blue": blue, "red": red, "winner": winner}


def evaluate(team1: str, team2: str, games, declared=None, resolver=None):
    resolver = resolver or TeamIdentityResolver()
    d1, d2 = declared if declared is not None else (None, None)
    return compute_series_score(team1, team2, games, resolver, d1, d2)


class ResolverTests(unittest.TestCase):
    def setUp(self):
        self.resolver = TeamIdentityResolver()

    def test_code_resolves_to_itself(self):
        resolved = self.resolver.resolve("DPLUS")
        self.assertIs(IdentityStatus.RESOLVED, resolved.status)
        self.assertEqual("DPLUS", resolved.canonical)

    def test_full_name_resolves_to_configured_code(self):
        for raw, expected in [
            ("Dplus Kia", "DPLUS"),
            ("Hanwha Life Esports", "HLE"),
            ("Gen.G", "GEN"),
            ("KT Rolster", "KT"),
            ("HANJIN BRION", "HANJIN BRION"),
            ("Kiwoom DRX", "KRX"),
            ("Nongshim RedForce", "NS"),
        ]:
            with self.subTest(raw=raw):
                resolved = self.resolver.resolve(raw)
                self.assertIs(IdentityStatus.RESOLVED, resolved.status)
                self.assertEqual(expected, resolved.canonical)

    def test_case_variant_of_configured_name_is_resolved(self):
        """"Dplus KIA" (raw Road to MSI series spelling) is the configured
        name "Dplus Kia" up to letter case."""
        resolved = self.resolver.resolve("Dplus KIA")
        self.assertIs(IdentityStatus.RESOLVED, resolved.status)
        self.assertEqual("DPLUS", resolved.canonical)

    def test_whitespace_is_trimmed(self):
        resolved = self.resolver.resolve("  DPLUS  ")
        self.assertIs(IdentityStatus.RESOLVED, resolved.status)
        self.assertEqual("DPLUS", resolved.canonical)

    def test_unconfigured_code_stays_unknown(self):
        """Human/common abbreviations are NOT auto-equivalent to Leaguepedia
        codes: DK/DNS/BFX/BRO are never observed in the fixture and must not
        be guessed (config keeps them as humanProvidedCode only)."""
        for raw in ["DK", "DNS", "BFX", "BRO", "G2", "Some Random Team"]:
            with self.subTest(raw=raw):
                resolved = self.resolver.resolve(raw)
                self.assertIs(IdentityStatus.UNKNOWN, resolved.status)
                self.assertIsNone(resolved.canonical)

    def test_empty_value_is_unknown(self):
        self.assertIs(IdentityStatus.UNKNOWN, self.resolver.resolve("").status)
        self.assertIs(IdentityStatus.UNKNOWN, self.resolver.resolve(None).status)


class ComputeSeriesScoreTests(unittest.TestCase):
    def setUp(self):
        self.resolver = TeamIdentityResolver()

    def test_code_to_code_with_side_swap(self):
        """KT vs DPLUS: KT wins games 1-2 (blue), loses 3-4, wins game 5."""
        games = [
            ("game1", {"blue": "KT", "red": "DPLUS", "winner": "1"}),
            ("game2", {"blue": "KT", "red": "DPLUS", "winner": "1"}),
            ("game3", {"blue": "DPLUS", "red": "KT", "winner": "1"}),
            ("game4", {"blue": "DPLUS", "red": "KT", "winner": "1"}),
            ("game5", {"blue": "KT", "red": "DPLUS", "winner": "2"}),
        ]
        result = evaluate("KT", "DPLUS", games, (2, 3), self.resolver)
        self.assertIs(SeriesScoreStatus.OK, result.status, result.reason)
        self.assertEqual((2, 3), (result.computed_team1_wins, result.computed_team2_wins))

    def test_full_name_to_code(self):
        games = [
            ("game1", {"blue": "DPLUS", "red": "HANJIN BRION", "winner": "1"}),
            ("game2", {"blue": "DPLUS", "red": "HANJIN BRION", "winner": "1"}),
            ("game3", {"blue": "DPLUS", "red": "HANJIN BRION", "winner": "1"}),
        ]
        result = evaluate("Dplus Kia", "HANJIN BRION", games, (3, 0), self.resolver)
        self.assertIs(SeriesScoreStatus.OK, result.status, result.reason)
        self.assertEqual((3, 0), (result.computed_team1_wins, result.computed_team2_wins))

    def test_full_name_to_full_name(self):
        games = [
            ("game1", {"blue": "Dplus Kia", "red": "KT Rolster", "winner": "1"}),
            ("game2", {"blue": "KT Rolster", "red": "Dplus Kia", "winner": "2"}),
        ]
        result = evaluate("Dplus Kia", "KT Rolster", games, (2, 0), self.resolver)
        self.assertIs(SeriesScoreStatus.OK, result.status, result.reason)
        self.assertEqual((2, 0), (result.computed_team1_wins, result.computed_team2_wins))

    def test_declared_score_mismatch_is_conflict(self):
        games = [("game1", {"blue": "DPLUS", "red": "KT", "winner": "1"})]
        result = evaluate("DPLUS", "KT", games, (0, 1), self.resolver)
        self.assertIs(SeriesScoreStatus.CONFLICT, result.status)
        self.assertIn("differs from declared", result.reason)
        self.assertFalse(series_score_matches_declared(result, 0, 1))

    def test_matching_declared_score_is_ok_for_predicate(self):
        games = [("game1", {"blue": "DPLUS", "red": "KT", "winner": "1"})]
        result = evaluate("DPLUS", "KT", games, (1, 0), self.resolver)
        self.assertTrue(series_score_matches_declared(result, 1, 0))

    def test_unknown_series_identity_does_not_guess(self):
        games = [("game1", {"blue": "DPLUS", "red": "KT", "winner": "1"})]
        result = evaluate("Dplus Kia", "Mystery Squad", games, (1, 0), self.resolver)
        self.assertIs(SeriesScoreStatus.UNKNOWN, result.status)
        self.assertIsNone(result.computed_team1_wins)
        self.assertIsNone(result.computed_team2_wins)
        self.assertIn("Mystery Squad", result.reason)

    def test_unknown_game_identity_makes_series_unknown(self):
        games = [("game1", {"blue": "DPLUS", "red": "Mystery Squad", "winner": "1"})]
        result = evaluate("DPLUS", "KT", games, None, self.resolver)
        self.assertIs(SeriesScoreStatus.UNKNOWN, result.status)
        self.assertIn("game1", result.reason)

    def test_invalid_winner_is_conflict(self):
        games = [("game1", {"blue": "DPLUS", "red": "KT", "winner": "3"})]
        result = evaluate("DPLUS", "KT", games, None, self.resolver)
        self.assertIs(SeriesScoreStatus.CONFLICT, result.status)
        self.assertIn("winner", result.reason)

    def test_missing_winner_is_conflict(self):
        games = [("game1", {"blue": "DPLUS", "red": "KT", "winner": ""})]
        result = evaluate("DPLUS", "KT", games, None, self.resolver)
        self.assertIs(SeriesScoreStatus.CONFLICT, result.status)

    def test_blue_equals_red_is_conflict(self):
        games = [("game1", {"blue": "DPLUS", "red": "Dplus Kia", "winner": "1"})]
        result = evaluate("DPLUS", "KT", games, None, self.resolver)
        self.assertIs(SeriesScoreStatus.CONFLICT, result.status)
        self.assertIn("same team", result.reason)

    def test_winner_not_matching_either_series_team_is_conflict(self):
        """Resolved winner that belongs to neither series side is a conflict
        (fail-closed), not silently attributed."""
        games = [("game1", {"blue": "GEN", "red": "HLE", "winner": "1"})]
        result = evaluate("DPLUS", "KT", games, None, self.resolver)
        self.assertIs(SeriesScoreStatus.CONFLICT, result.status)
        self.assertIn("neither series team", result.reason)

    def test_empty_game_list_computes_zero_zero(self):
        result = evaluate("DPLUS", "KT", [], (0, 0), self.resolver)
        self.assertIs(SeriesScoreStatus.OK, result.status, result.reason)
        self.assertEqual((0, 0), (result.computed_team1_wins, result.computed_team2_wins))


class MixedRepresentationTests(unittest.TestCase):
    """The exact mixed representations observed in Data:LCK/2026 Season/Road
    to MSI (handoff sections 16-17)."""

    def setUp(self):
        self.resolver = TeamIdentityResolver()

    def _series(self, wikitext: str, team1: str, team2: str):
        for _context, args, games in iter_series_with_games(wikitext):
            if (args.get("team1") or "").strip() == team1 and (args.get("team2") or "").strip() == team2:
                return args, games
        raise AssertionError(f"series {team1} vs {team2} not found")

    def test_series_level_full_names_game_level_codes(self):
        """Raw source confirms: series team1=Dplus Kia / team2=HANJIN BRION,
        games blue=DPLUS / red=HANJIN BRION."""
        args, games = self._series(ROAD_TO_MSI.read_text(encoding="utf-8"), "Dplus Kia", "HANJIN BRION")
        self.assertEqual("DPLUS", (games[0][1].get("blue") or "").strip())
        result = evaluate(args["team1"], args["team2"], games,
                          (int(args["team1score"]), int(args["team2score"])), self.resolver)
        self.assertIs(SeriesScoreStatus.OK, result.status, result.reason)
        self.assertEqual((3, 0), (result.computed_team1_wins, result.computed_team2_wins))

    def test_series_level_case_variant_name(self):
        """Round 2 declares team2=Dplus KIA while games use DPLUS."""
        args, games = self._series(ROAD_TO_MSI.read_text(encoding="utf-8"), "KT Rolster", "Dplus KIA")
        result = evaluate(args["team1"], args["team2"], games,
                          (int(args["team1score"]), int(args["team2score"])), self.resolver)
        self.assertIs(SeriesScoreStatus.OK, result.status, result.reason)
        self.assertEqual((3, 2), (result.computed_team1_wins, result.computed_team2_wins))

    def test_series_and_game_levels_already_use_codes(self):
        args, games = self._series(ROAD_TO_MSI.read_text(encoding="utf-8"), "T1", "GEN")
        result = evaluate(args["team1"], args["team2"], games,
                          (int(args["team1score"]), int(args["team2score"])), self.resolver)
        self.assertIs(SeriesScoreStatus.OK, result.status, result.reason)
        self.assertEqual((3, 2), (result.computed_team1_wins, result.computed_team2_wins))


class RoadToMsiFixtureTests(unittest.TestCase):
    """Fixture-level verification (raw files unchanged)."""

    @classmethod
    def setUpClass(cls):
        cls.resolver = TeamIdentityResolver()

    def _results(self, path: pathlib.Path):
        wikitext = path.read_text(encoding="utf-8")
        results = []
        for context, args, games in iter_series_with_games(wikitext):
            results.append((
                context,
                args,
                evaluate(args.get("team1"), args.get("team2"), games,
                         (int((args.get("team1score") or "0").strip()),
                          int((args.get("team2score") or "0").strip())),
                         self.resolver),
            ))
        return results

    def test_road_to_msi_all_five_series_are_ok(self):
        results = self._results(ROAD_TO_MSI)
        self.assertEqual(5, len(results))
        statuses = [(r[1].get("team1"), r[1].get("team2"), r[2].status, r[2].reason) for r in results]
        self.assertEqual([SeriesScoreStatus.OK] * 5, [s[2] for s in statuses], statuses)
        self.assertEqual([(3, 0), (3, 2), (3, 1), (3, 0), (3, 2)],
                         [(r[2].computed_team1_wins, r[2].computed_team2_wins) for r in results])

    def test_the_three_previously_reported_mismatches_are_correct(self):
        """The three series the old exact-string code mis-scored."""
        by_pair = {
            (r[1].get("team1"), r[1].get("team2")): r[2]
            for r in self._results(ROAD_TO_MSI)
        }
        expected = {
            ("Dplus Kia", "HANJIN BRION"): (3, 0),
            ("Hanwha Life Esports", "T1"): (3, 1),
            ("Gen.G", "KT Rolster"): (3, 0),
        }
        for pair, score in expected.items():
            with self.subTest(pair=pair):
                result = by_pair[pair]
                self.assertIs(SeriesScoreStatus.OK, result.status, result.reason)
                self.assertEqual(score, (result.computed_team1_wins, result.computed_team2_wins))
                self.assertTrue(series_score_matches_declared(result, *score))

    def test_season_playoffs_all_ten_series_are_ok(self):
        results = self._results(PLAYOFFS)
        self.assertEqual(10, len(results))
        self.assertEqual([SeriesScoreStatus.OK] * 10, [r[2].status for r in results],
                         [r[2].reason for r in results])

    def test_rounds34_fixture_all_forty_series_are_ok(self):
        results = self._results(ROUNDS34)
        self.assertEqual(40, len(results))
        self.assertEqual([SeriesScoreStatus.OK] * 40, [r[2].status for r in results],
                         [r[2].reason for r in results])

    def test_no_fuzzy_or_guessed_identity_in_fixtures(self):
        """Every raw value in all three fixtures resolves and none of the
        human-only codes leak into resolution as guesses."""
        for path in (ROUNDS34, PLAYOFFS, ROAD_TO_MSI):
            for _context, args, games in iter_series_with_games(path.read_text(encoding="utf-8")):
                for raw in (args.get("team1"), args.get("team2")):
                    with self.subTest(path=path.name, raw=raw):
                        self.assertIs(IdentityStatus.RESOLVED, self.resolver.resolve(raw).status)
                for key, game_args in games:
                    for side in ("blue", "red"):
                        with self.subTest(path=path.name, game=key, side=side):
                            self.assertIs(IdentityStatus.RESOLVED,
                                          self.resolver.resolve(game_args.get(side)).status)


if __name__ == "__main__":
    unittest.main()
