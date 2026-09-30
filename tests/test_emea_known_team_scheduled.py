"""PHASE 18-3-D-EMEA: deterministic tests for the first KNOWN-TEAM SCHEDULED
Leaguepedia MatchSchedule rows (EMEA Masters 2026 Summer Main Event).

Evidence: raw/leaguepedia/page_EMEA_Masters_2026_Summer_Main_Event.wikitext
(saved unmodified; log: phase18_3d_emea_fetch_metadata.json, 1 request).
Rows 65-78 (Round 5) are genuinely upcoming known-team scheduled rows at the
observation time (2026-09-30T11:51Z; their times 06:00-11:00 PST correspond
to 14:00-19:00 UTC, all after observation). These tests lock the observed
schema only; production normalization is untouched."""

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

EMEA = ROOT / "raw" / "leaguepedia" / "page_EMEA_Masters_2026_Summer_Main_Event.wikitext"

# Observation timestamp recorded in phase18_3d_emea_fetch_metadata.json.
OBSERVATION_UTC = datetime.datetime(2026, 9, 30, 11, 51, tzinfo=datetime.timezone.utc)
PST_OFFSET = datetime.timedelta(hours=-8)  # PST = UTC-8; used to classify rows. DST semantics UNKNOWN.
PDT_OFFSET = datetime.timedelta(hours=-7)  # alternate reading; classification must be robust to both.


def load_rows():
    return list(iter_series_with_games(EMEA.read_text(encoding="utf-8")))


def row_datetime(args, offset):
    date = datetime.date.fromisoformat((args.get("date") or "").strip())
    hh, mm = (args.get("time") or "00:00").split(":")
    return datetime.datetime(date.year, date.month, date.day, int(hh), int(mm), tzinfo=datetime.timezone.utc) - offset


class EmeaKnownTeamScheduledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = load_rows()
        # Rows 65-78: Round 5 known-team scheduled (by document order, verified below).
        cls.scheduled = cls.rows[64:78]

    def test_page_has_93_rows(self):
        self.assertEqual(93, len(self.rows))

    def test_selected_rows_are_all_round5_known_team_scheduled(self):
        for index, (context, args, _games) in enumerate(self.scheduled, 65):
            with self.subTest(row=index):
                self.assertEqual("Round 5", context["tab"])
                self.assertTrue((args.get("team1") or "").strip())
                self.assertTrue((args.get("team2") or "").strip())
                self.assertEqual("", (args.get("winner") or "").strip())
                self.assertEqual("", (args.get("team1score") or "").strip())
                self.assertEqual("", (args.get("team2score") or "").strip())

    def test_selected_rows_are_genuinely_future_under_both_dst_readings(self):
        """Classification must not depend on the unknown dst semantics:
        all 14 rows are future under PST (UTC-8) AND under PDT (UTC-7)."""
        for index, (_context, args, _games) in enumerate(self.scheduled, 65):
            with self.subTest(row=index):
                for offset, label in ((PST_OFFSET, "PST"), (PDT_OFFSET, "PDT")):
                    self.assertGreater(row_datetime(args, offset), OBSERVATION_UTC,
                                       f"row {index} must be future under {label} reading")

    def test_team_representation_is_mixed_including_within_one_row(self):
        """Q1: code / full-name / short-form representations coexist, even in
        one row (row 66: 'Bushido Wildcats' vs 'Magaza'). Verbatim values."""
        pairs = [((args.get("team1") or "").strip(), (args.get("team2") or "").strip())
                 for _c, args, _g in self.scheduled]
        self.assertIn(("Bushido Wildcats", "Magaza"), pairs)      # full name + short form
        self.assertIn(("BIG", "SNSH"), pairs)                     # code + code
        self.assertIn(("G2 NORD", "Bomba Team"), pairs)           # hybrid + full name
        self.assertIn(("HMBLE", "Barca"), pairs)                  # code + short form

    def test_scheduled_games_exist_with_bestof_block_count(self):
        """Q3/Q4: game blocks exist pre-match and equal the ROW-level bestof
        (which overrides the Start's bestof=1 on BO3 rows)."""
        for index, (context, args, games) in enumerate(self.scheduled, 65):
            row_bestof = int((args.get("bestof") or "").strip())
            with self.subTest(row=index, start_bestof=context["bestof"], row_bestof=row_bestof):
                self.assertEqual("1", context["bestof"])
                self.assertEqual(row_bestof, len(games))
        # 6 BO1 rows + 8 BO3 rows = 30 game blocks
        self.assertEqual(30, sum(len(games) for _c, _a, games in self.scheduled))

    def test_all_scheduled_game_fields_empty_including_rpgid(self):
        """Q2: riot_platform_game_id is OBSERVED_ABSENT pre-match (0/30), and
        blue/red are OBSERVED_ABSENT (no pre-match side assignment)."""
        checked = 0
        for _context, _args, games in self.scheduled:
            for game_key, game_args in games:
                for field in ("blue", "red", "winner", "riot_platform_game_id",
                              "first_sel", "ssel", "pick_sel", "first_pick", "ff"):
                    with self.subTest(game=game_key, field=field):
                        self.assertEqual("", (game_args.get(field) or "").strip())
                checked += 1
        self.assertEqual(30, checked)

    def test_completed_rows_on_same_page_do_have_rpgid(self):
        """Scoping check: emptiness is a pre-match state, not page-wide —
        completed rows carry LOLTMNT05_* rpgids."""
        for index in (1, 3, 62):
            _context, _args, games = self.rows[index - 1]
            for _game_key, game_args in games:
                rpgid = (game_args.get("riot_platform_game_id") or "").strip()
                self.assertTrue(rpgid.startswith("LOLTMNT05_"), f"row {index}: {rpgid!r}")

    def test_tbd_rows_use_literal_tbd_placeholder(self):
        """First observation of a non-empty placeholder: undetermined future
        rows (79-93) use team1=TBD / team2=TBD with empty results."""
        for index, (_context, args, games) in enumerate(self.rows[78:93], 79):
            with self.subTest(row=index):
                self.assertEqual("TBD", (args.get("team1") or "").strip())
                self.assertEqual("TBD", (args.get("team2") or "").strip())
                self.assertEqual("", (args.get("winner") or "").strip())
                self.assertEqual(3, len(games))

    def test_resolver_fails_closed_for_unmapped_emea_teams(self):
        """None of the EMEA teams are in team_mappings.json (LCK-only config):
        every scheduled team value must resolve UNKNOWN — no guessing."""
        resolver = TeamIdentityResolver()
        for _context, args, _games in self.scheduled:
            for field in ("team1", "team2"):
                with self.subTest(field=field, value=args.get(field)):
                    self.assertIs(IdentityStatus.UNKNOWN, resolver.resolve(args.get(field)).status)

    def test_series_score_helper_fails_closed_on_scheduled_rows(self):
        resolver = TeamIdentityResolver()
        for _context, args, games in self.scheduled:
            result = compute_series_score(args.get("team1"), args.get("team2"), games, resolver)
            self.assertIs(SeriesScoreStatus.UNKNOWN, result.status)
            self.assertIsNone(result.computed_team1_wins)

    def test_forfeit_representation_observed_on_completed_row(self):
        """Row 9: series-level ff=2 + team2footnote ('failed to show up' with
        an external citation). Verbatim; ff semantics not inferred."""
        _context, args, _games = self.rows[8]
        self.assertEqual("2", (args.get("ff") or "").strip())
        self.assertIn("failed to show up", (args.get("team2footnote") or ""))
        self.assertEqual("1", (args.get("winner") or "").strip())

    def test_dst_and_timezone_recorded_without_interpretation(self):
        for _context, args, _games in self.scheduled:
            self.assertEqual("PST", (args.get("timezone") or "").strip())
            self.assertEqual("yes", (args.get("dst") or "").strip())


if __name__ == "__main__":
    unittest.main()
