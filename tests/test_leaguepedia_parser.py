"""Tests for the balanced wikitext template parser and the real LCK fixture."""

from __future__ import annotations

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

from lib.leaguepedia_parser import (  # noqa: E402
    find_nested_by_name,
    find_templates,
    find_templates_by_name,
    parse_template_args,
)

RAW = pathlib.Path(__file__).resolve().parents[1] / "raw" / "leaguepedia" / "page_data_lck_rounds34.wikitext"


class BasicParsingTests(unittest.TestCase):
    def test_simple_named_args(self):
        args = parse_template_args("|team1=KRX |team2=NS |team1score=0 |team2score=2")
        self.assertEqual({"team1": "KRX", "team2": "NS", "team1score": "0", "team2score": "2"}, args.named)
        self.assertEqual([], args.positional)

    def test_whitespace_is_normalized_around_keys_and_values(self):
        args = parse_template_args("|  team1 =   KRX   |\n|team2= NS\n")
        self.assertEqual("KRX", args.named["team1"])
        self.assertEqual("NS", args.named["team2"])

    def test_value_with_equals_keeps_everything_after_first_top_level_equals(self):
        args = parse_template_args("|vodinterview=https://youtu.be/x?t=8011")
        self.assertEqual("https://youtu.be/x?t=8011", args.named["vodinterview"])

    def test_pipes_inside_wikilinks_do_not_split_args(self):
        args = parse_template_args("|text=[[A|B]] |winner=1")
        self.assertEqual("[[A|B]]", args.named["text"])
        self.assertEqual("1", args.named["winner"])

    def test_comment_only_positional_argument_is_dropped(self):
        args = parse_template_args("|<!-- Do not change the order of team1 and team2!! -->|team1=T1")
        self.assertEqual({"team1": "T1"}, args.named)
        self.assertEqual([], args.positional)

    def test_positional_argument_without_equals_is_preserved(self):
        args = parse_template_args("|somepositional|key=v")
        self.assertEqual(["somepositional"], args.positional)
        self.assertEqual({"key": "v"}, args.named)

    def test_nested_templates_stay_verbatim_in_values(self):
        args = parse_template_args("|game1={{MatchSchedule/Game|blue=T1 |winner=1}} |team1=T1")
        self.assertIn("{{MatchSchedule/Game|blue=T1 |winner=1}}", args.named["game1"])
        self.assertEqual("T1", args.named["team1"])

    def test_unbalanced_template_raises(self):
        from lib.leaguepedia_parser import _find_balanced_close

        with self.assertRaises(ValueError):
            _find_balanced_close("{{MatchSchedule|team1=T1", 0)


class FindTemplatesTests(unittest.TestCase):
    def test_finds_top_level_templates_in_order_and_ignores_nested(self):
        text = "{{A|x={{B|inner=1}}}}\n{{C}}"
        templates = find_templates(text)
        self.assertEqual(["A", "C"], [t.name for t in templates])
        self.assertIn("{{B|inner=1}}", templates[0].args.named["x"])

    def test_find_nested_by_name(self):
        args = parse_template_args("|game1={{MatchSchedule/Game|blue=T1 |winner=1}}")
        games = find_nested_by_name(args.named["game1"], "MatchSchedule/Game")
        self.assertEqual(1, len(games))
        self.assertEqual("T1", games[0].args.named["blue"])

    def test_find_templates_by_name_filters(self):
        templates = find_templates_by_name("{{X}}{{Y}}{{X}}", "X")
        self.assertEqual(2, len(templates))


class RealFixtureTests(unittest.TestCase):
    """Uses the actual collected LCK fixture — no invented values."""

    @classmethod
    def setUpClass(cls):
        cls.wikitext = RAW.read_text(encoding="utf-8")
        cls.templates = find_templates(cls.wikitext)

    def test_fixture_parses_without_error(self):
        self.assertGreater(len(self.templates), 0)

    def test_fixture_has_match_schedule_start_blocks(self):
        starts = find_templates_by_name(self.wikitext, "MatchSchedule/Start")
        self.assertGreaterEqual(len(starts), 1)
        self.assertEqual("3", starts[0].args.named["bestof"])
        self.assertEqual("Week 10", starts[0].args.named["tab"])

    def test_fixture_series_record_matches_observed_raw_values(self):
        """First series of the fixture must expose the exact observed values:
        team1=KRX team2=NS team1score=0 team2score=2 winner=2
        date=2026-07-29 time=17:00 timezone=KST."""
        series = [t for t in self.templates if t.name == "MatchSchedule"]
        self.assertGreater(len(series), 0)
        first = series[0].args.named
        self.assertEqual("KRX", first["team1"])
        self.assertEqual("NS", first["team2"])
        self.assertEqual("0", first["team1score"])
        self.assertEqual("2", first["team2score"])
        self.assertEqual("2", first["winner"])
        self.assertEqual("2026-07-29", first["date"])
        self.assertEqual("17:00", first["time"])
        self.assertEqual("KST", first["timezone"])

    def test_fixture_series_contains_nested_game_with_riot_game_id(self):
        series = [t for t in self.templates if t.name == "MatchSchedule"]
        first = series[0]
        game_args = [v for k, v in first.args.named.items() if k.lower().startswith("game")]
        games = []
        for value in game_args:
            games.extend(find_nested_by_name(value, "MatchSchedule/Game"))
        self.assertGreater(len(games), 0)
        self.assertEqual("LOLTMNT02_442746", games[0].args.named["riot_platform_game_id"])

    def test_fixture_series_count_matches_earlier_structure_check(self):
        series = [t for t in self.templates if t.name == "MatchSchedule"]
        self.assertEqual(40, len(series))


if __name__ == "__main__":
    unittest.main()
