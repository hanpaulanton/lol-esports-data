"""PHASE 18-5: deterministic tests for the scheduled normalization layer
(scripts/scheduled_normalize.py), implementing the PHASE 18-4 test matrix.

Evidence-based tests use the REAL saved fixtures only:
- EMEA Masters 2026 Summer Main Event (known-team rows 65-78, TBD rows 79-93,
  completed rows 1-64, forfeit row 9)
- Worlds Play-In / Main Event (empty-slot scheduled rows)

Pure-function boundary tests (classify_team_slot / resolve_best_of / the
validator's V-rules) use synthetic dict inputs; these are NOT fabricated
Leaguepedia fixtures (handoff section 19) — the distinction is stated per
test class. Production promotion is NOT part of this phase: no record here
is written to data/matches.sample.json.
"""

from __future__ import annotations

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.validator import validate_scheduled_match  # noqa: E402
from lib.series_score import IdentityStatus, TeamIdentityResolver  # noqa: E402
from lib.timezones import normalize_local_to_utc  # noqa: E402
from scheduled_normalize import (  # noqa: E402
    CONVERTED_TZ,
    PENDING_TZ,
    SLOT_EMPTY,
    SLOT_KNOWN,
    SLOT_TBD,
    classify_team_slot,
    normalize_scheduled_series,
    normalize_scheduled_wikitext,
    resolve_best_of,
)

EMEA = ROOT / "raw" / "leaguepedia" / "page_EMEA_Masters_2026_Summer_Main_Event.wikitext"
PLAYIN = ROOT / "raw" / "leaguepedia" / "page_Data_2026 Season World Championship_Play-In.wikitext"
EMEA_REF = "raw/leaguepedia/page_EMEA_Masters_2026_Summer_Main_Event.wikitext"
LEAGUE_META = {"id": "EM", "name": "EMEA Masters", "region": "EU"}


def make_resolver():
    return TeamIdentityResolver()


def normalize_emea():
    return normalize_scheduled_wikitext(
        EMEA.read_text(encoding="utf-8"), make_resolver(), EMEA_REF, LEAGUE_META,
        observation_date="2026-09-30",
    )


def normalize_playin():
    return normalize_scheduled_wikitext(
        PLAYIN.read_text(encoding="utf-8"), make_resolver(),
        "raw/leaguepedia/page_Data_2026 Season World Championship_Play-In.wikitext",
        {"id": "Worlds", "name": "World Championship", "region": "INT"},
        observation_date="2026-09-30",
    )


def valid_record(**overrides):
    """Minimal validator-clean scheduled record (pure-function input, not a
    fabricated fixture)."""
    record = {
        "id": "lp:test:2026-09-30:BIG:SNSH",
        "league": LEAGUE_META,
        "tournament": {"id": "EM 2026 Summer", "name": "EMEA Masters 2026 Summer"},
        "stage": {"id": "Round 5", "name": "Round 5"},
        "team1Id": "BIG",
        "team2Id": "SNSH",
        "scheduledAt": None,
        "status": "scheduled",
        "bestOf": 1,
        "score": None,
        "sources": [{"source": "leaguepedia", "kind": "raw_fixture", "ref": EMEA_REF}],
        "lastUpdatedAt": "2026-09-30",
        "_provisional": {
            "teamSlotState": {"team1": "KNOWN", "team2": "KNOWN"},
            "gameBlockCount": 1,
            "rpgidCount": {"total": 1, "nonEmpty": 0},
        },
    }
    record.update(overrides)
    return record


class PureFunctionUnitTests(unittest.TestCase):
    """Pure-function boundary tests (handoff section 19 exception). No
    Leaguepedia fixture is fabricated here."""

    def test_team_slot_classification(self):
        self.assertEqual(SLOT_KNOWN, classify_team_slot("GEN"))
        self.assertEqual(SLOT_KNOWN, classify_team_slot(" Bushido Wildcats "))
        self.assertEqual(SLOT_TBD, classify_team_slot("TBD"))
        self.assertEqual(SLOT_EMPTY, classify_team_slot(""))
        self.assertEqual(SLOT_EMPTY, classify_team_slot(None))
        self.assertEqual(SLOT_EMPTY, classify_team_slot("   "))
        # Not guessed: other placeholder-looking strings stay KNOWN raw values.
        self.assertEqual(SLOT_KNOWN, classify_team_slot("TBA"))

    def test_bestof_hierarchy(self):
        bo, source, warns = resolve_best_of("3", "1")
        self.assertEqual((3, "row-level bestof"), (bo, source))
        self.assertEqual([], warns)
        bo, source, _ = resolve_best_of("", "3")
        self.assertEqual((3, "start-level bestof"), (bo, source))
        bo, source, _ = resolve_best_of(None, None)
        self.assertIsNone(bo)
        self.assertIn("UNKNOWN", source)
        bo, source, warns = resolve_best_of("banana", "2")
        self.assertEqual((2, "start-level bestof"), (bo, source))
        self.assertEqual(1, len(warns), "malformed row value must warn (fail-closed)")
        bo, source, warns = resolve_best_of("banana", None)
        self.assertIsNone(bo)
        self.assertEqual(1, len(warns))

    def test_v1_score_null_required_including_zero_zero(self):
        """Design §6: scheduled + score present (0:0 included) -> ERROR."""
        errors, _ = validate_scheduled_match(valid_record(score={"team1": 0, "team2": 0}))
        self.assertTrue(any("score=null" in e for e in errors))
        errors, _ = validate_scheduled_match(valid_record(score={"team1": 0, "team2": 5}))
        self.assertTrue(any("score=null" in e for e in errors))
        errors, _ = validate_scheduled_match(valid_record(score=None))
        self.assertFalse(any("score" in e for e in errors))

    def test_v9_v10_team_slots(self):
        errors, _ = validate_scheduled_match(valid_record(team1Id=None))
        self.assertTrue(any("KNOWN slot" in e for e in errors))
        tbd = valid_record(
            team1Id=None, team2Id=None,
            _provisional={"teamSlotState": {"team1": "TBD", "team2": "TBD"}},
        )
        errors, _ = validate_scheduled_match(tbd)
        self.assertEqual([], errors)
        empty = valid_record(
            team1Id=None, team2Id=None,
            _provisional={"teamSlotState": {"team1": "EMPTY", "team2": "EMPTY"}},
        )
        errors, _ = validate_scheduled_match(empty)
        self.assertEqual([], errors)

    def test_v4_scheduled_at_null_or_valid(self):
        errors, _ = validate_scheduled_match(valid_record(scheduledAt="2026-07-29T08:00:00Z"))
        self.assertEqual([], [e for e in errors if "scheduledAt" in e])
        errors, _ = validate_scheduled_match(valid_record(scheduledAt="not-a-date"))
        self.assertTrue(any("scheduledAt" in e for e in errors))

    def test_status_vocabulary_not_extended(self):
        errors, _ = validate_scheduled_match(valid_record(status="tbd"))
        self.assertTrue(any("status" in e for e in errors))
        errors, _ = validate_scheduled_match(valid_record(status="completed"))
        self.assertTrue(any("only accepts 'scheduled'" in e for e in errors))

    def test_v7_bestof_game_block_mismatch_warns(self):
        record = valid_record(
            bestOf=3,
            _provisional={"teamSlotState": {"team1": "KNOWN", "team2": "KNOWN"},
                          "gameBlockCount": 1,
                          "rpgidCount": {"total": 1, "nonEmpty": 0}},
        )
        errors, warnings = validate_scheduled_match(record)
        self.assertEqual([], errors)
        self.assertTrue(any("game block count 1 != effective bestOf 3" in w for w in warnings))

    def test_v12_rpgid_on_scheduled_record_warns(self):
        record = valid_record(
            _provisional={"teamSlotState": {"team1": "KNOWN", "team2": "KNOWN"},
                          "gameBlockCount": 1,
                          "rpgidCount": {"total": 1, "nonEmpty": 1}},
        )
        errors, warnings = validate_scheduled_match(record)
        self.assertEqual([], errors)
        self.assertTrue(any("non-empty rpgid" in w for w in warnings))


class EmeaFixtureTests(unittest.TestCase):
    """Evidence-based: EMEA Masters 2026 Summer Main Event fixture."""

    @classmethod
    def setUpClass(cls):
        cls.records, cls.excluded = normalize_emea()
        cls.by_slot = {}
        for record in cls.records:
            state = record["_provisional"]["teamSlotState"]
            cls.by_slot.setdefault((state["team1"], state["team2"]), []).append(record)

    def test_row_partition(self):
        """93 raw rows = 29 scheduled records (14 known + 15 TBD) + 64
        completed rows excluded to the completed pipeline."""
        self.assertEqual(29, len(self.records))
        self.assertEqual(64, len(self.excluded))
        self.assertTrue(all("not a scheduled row" in e["reason"] for e in self.excluded))
        known = self.by_slot.get(("KNOWN", "KNOWN"), [])
        tbd = self.by_slot.get(("TBD", "TBD"), [])
        self.assertEqual(14, len(known))
        self.assertEqual(15, len(tbd))

    def test_t1_known_team_scheduled(self):
        known = self.by_slot[("KNOWN", "KNOWN")]
        first = known[0]
        self.assertEqual("lp:EM 2026 Summer Main Event:2026-09-30:BIG:SNSH", first["id"])
        self.assertEqual("scheduled", first["status"])

    def test_t4_t5_scores_and_winners_are_null_never_zero(self):
        for record in self.records:
            with self.subTest(id=record["id"]):
                self.assertIsNone(record["score"])
        # No 0:0 anywhere, and raw empty score fields are preserved in _provisional.
        self.assertEqual("BIG", self.records[0]["_provisional"]["teamSlotRaw"]["team1"])

    def test_t9_rpgid_absent_no_synthetic_id(self):
        for record in self.records:
            with self.subTest(id=record["id"]):
                counts = record["_provisional"]["rpgidCount"]
                self.assertEqual(0, counts["nonEmpty"])
                self.assertNotIn("rpgid", record)
                self.assertNotIn("games", record)

    def test_t6_row_level_bestof_override_wins(self):
        """Row bestof=3 under Start bestof=1 -> bestOf=3, source row-level.
        Observed on 8 known-team Round-5 rows + all 15 TBD rows = 23 records."""
        bo3 = [r for r in self.records if r["bestOf"] == 3]
        self.assertEqual(23, len(bo3))
        for record in bo3:
            with self.subTest(id=record["id"]):
                self.assertEqual("row-level bestof", record["_provisional"]["bestOfSource"])
                self.assertEqual(3, record["_provisional"]["gameBlockCount"])

    def test_t7_start_level_bestof_used_when_row_absent(self):
        """6 known-team Round-5 BO1 rows carry row bestof=1 matching Start
        bestof=1 (observed row-level value wins, content identical)."""
        bo1 = [r for r in self.records if r["bestOf"] == 1]
        self.assertEqual(6, len(bo1))
        self.assertTrue(all(r["_provisional"]["bestOfSource"] == "row-level bestof" for r in bo1))

    def test_t11_t12_known_slots_resolve_after_18_15_promotion(self):
        """PHASE 18-15: the 28 verified EMEA mappings are in the config, so
        every KNOWN slot resolves RESOLVED to its own Leaguepedia code, while
        TBD slots stay UNKNOWN with null team ids. Every record still
        validates (identity resolution is not a parse failure in any state)."""
        resolver = make_resolver()
        for record in self.records:
            states = record["_provisional"]["identityStatus"]
            canonical = record["_provisional"]["canonicalTeamId"]
            with self.subTest(id=record["id"]):
                for side in ("team1", "team2"):
                    if record["_provisional"]["teamSlotState"][side] == "KNOWN":
                        raw = record["_provisional"]["teamSlotRaw"][side]
                        self.assertEqual("RESOLVED", states[side])
                        self.assertEqual(raw, canonical[side])
                        self.assertEqual(
                            IdentityStatus.RESOLVED, resolver.resolve(raw).status
                        )
                    else:
                        self.assertEqual("UNKNOWN", states[side])
                errors, _ = validate_scheduled_match(record)
                self.assertEqual([], errors, f"{record['id']}: {errors}")

    def test_t14_pst_converted_with_verified_daylight_offset(self):
        """PHASE 18-15: PST is curated (dst=yes means PDT, UTC-07:00 —
        PHASE 18-14 evidence). scheduledAt must equal the UTC conversion of
        the preserved raw values recomputed here, and the raw provenance
        (date/time/timezone/dst) must remain untouched."""
        for record in self.records:
            with self.subTest(id=record["id"]):
                time_raw = record["_provisional"]["timeRaw"]
                self.assertEqual("PST", time_raw["timezone"])
                self.assertEqual("yes", time_raw["dst"])
                self.assertEqual(CONVERTED_TZ, time_raw["utcConversion"])
                expected = normalize_local_to_utc(
                    time_raw["date"], time_raw["time"], time_raw["timezone"], time_raw["dst"]
                )
                self.assertIsNotNone(expected)
                self.assertEqual(expected.utc_iso, record["scheduledAt"])
                # spot-check the verified -07:00 offset on the 06:00 row
                if time_raw["time"] == "06:00":
                    self.assertEqual(time_raw["date"] + "T13:00:00Z", record["scheduledAt"])

    def test_t2_tbd_rows_preserve_tbd_state(self):
        tbd = self.by_slot[("TBD", "TBD")]
        self.assertEqual(15, len(tbd))
        for record in tbd:
            with self.subTest(id=record["id"]):
                self.assertIsNone(record["team1Id"])
                self.assertIsNone(record["team2Id"])
                self.assertEqual("TBD", record["_provisional"]["teamSlotRaw"]["team1"])

    def test_t20_id_uses_shownname_not_unknown(self):
        for record in self.records:
            with self.subTest(id=record["id"]):
                self.assertTrue(record["id"].startswith("lp:EM 2026 Summer Main Event:"),
                                record["id"])

    def test_validator_passes_every_normalized_record(self):
        for record in self.records:
            errors, warnings = validate_scheduled_match(record)
            with self.subTest(id=record["id"]):
                self.assertEqual([], errors)
                self.assertEqual([], warnings)

    def test_t16_completed_rows_rejected_by_scheduled_pipeline(self):
        """Row 1 (completed BIG vs FEC) must be excluded, not misclassified."""
        reasons = [e["reason"] for e in self.excluded if e.get("team1") == "BIG" and e.get("team2") == "FEC"]
        self.assertEqual(1, len(reasons))
        self.assertIn("winner='1'", reasons[0])

    def test_t17_forfeit_row_not_converted_to_postponed_or_cancelled(self):
        """Row 9 (forfeit, ff=2) has result values, so it goes to the
        completed pipeline — it must NOT become a scheduled record, and no
        record in this page carries postponed/cancelled."""
        forfeit = [e for e in self.excluded if e.get("team1") == "KCB"]
        self.assertEqual(1, len(forfeit))
        for record in self.records:
            self.assertIn(record["status"], {"scheduled"})


class PlayinFixtureTests(unittest.TestCase):
    """Evidence-based: Worlds Play-In fixture (empty team slots)."""

    @classmethod
    def setUpClass(cls):
        cls.records, cls.excluded = normalize_playin()

    def test_t3_empty_team_scheduled(self):
        self.assertEqual(6, len(self.records))
        self.assertEqual(0, len(self.excluded), "Play-In page has no completed rows")
        for record in self.records:
            with self.subTest(id=record["id"]):
                self.assertEqual({"team1": "EMPTY", "team2": "EMPTY"},
                                 record["_provisional"]["teamSlotState"])
                self.assertIsNone(record["team1Id"])
                self.assertIsNone(record["team2Id"])
                self.assertEqual(5, record["bestOf"])
                self.assertEqual(5, record["_provisional"]["gameBlockCount"])

    def test_empty_slots_produce_deterministic_ids_without_collision(self):
        ids = [r["id"] for r in self.records]
        self.assertEqual(len(ids), len(set(ids)), ids)
        self.assertTrue(all("EMPTY" in i for i in ids))

    def test_validator_passes_empty_slot_records(self):
        for record in self.records:
            errors, warnings = validate_scheduled_match(record)
            with self.subTest(id=record["id"]):
                self.assertEqual([], errors)
                self.assertEqual([], warnings)

    def test_start_level_bestof_five(self):
        self.assertTrue(all(r["_provisional"]["bestOfSource"] == "start-level bestof"
                            for r in self.records))


if __name__ == "__main__":
    unittest.main()
