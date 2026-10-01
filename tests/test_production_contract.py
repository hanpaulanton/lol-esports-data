"""PHASE 18-17: production canonical data contract regression gate.

Reads the ACTUAL production document (data/matches.json) directly and fails
loudly on accidental corruption, regression, rollback, or contract drift.

Three-tier design (docs/production-contract-gate.md):

1. IMMUTABLE INVARIANTS — corruption detection; never relaxed to make data
   pass (envelope keys, schemaVersion, unique ids, dangling references,
   existing validator passing, scheduled score rules, source shape,
   synthetic-provenance safety, EMEA timezone provenance preservation).
2. CURRENT PRODUCTION BASELINE — the BASELINE block below records the
   approved production state (counts, distributions, EMEA/Worlds splits).
   These are NOT universal invariants: a legitimate, approved promotion
   updates this block as part of its checklist. The baseline must never be
   silently changed merely to make a failing test pass.
3. INTENTIONALLY MUTABLE VALUES — dataVersion is checked with an explicit
   YYYY.MM.DD.NN parser for format + monotonic (>= baseline) behaviour, so a
   legitimate future bump passes without editing this file while an
   accidental rollback fails. generatedAt is format-checked only.

Offline by design: stdlib only, reads local data/, no network. Reuses the
existing validator (lib.validator) and the existing DST-aware timezone logic
(lib.timezones) instead of duplicating them.
"""

from __future__ import annotations

import datetime
import json
import pathlib
import re
import sys
import unittest
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.timezones import normalize_local_to_utc  # noqa: E402
from lib.validator import (  # noqa: E402
    ISO_UTC_RE,
    validate_envelope,
    validate_match,
    validate_scheduled_match,
)

PRODUCTION = ROOT / "data" / "matches.json"

# =====================================================================
# CURRENT PRODUCTION BASELINE
# Approved at PHASE 18-17 (commit b67121e, dataVersion 2026.10.01.02).
# NOT universal invariants. Update ONLY as part of an approved production
# promotion (docs/production-contract-gate.md §promotion workflow).
# =====================================================================
BASELINE = {
    "dataVersion": "2026.10.01.02",
    "leagueCount": 3,
    "teamCount": 38,
    "matchCount": 75,
    "completedCount": 40,
    "scheduledCount": 35,
    "bestOfDistribution": {1: 6, 3: 63, 5: 6},
    "leagueIds": {"LCK21", "EM", "Worlds"},
    "leagueMatchCounts": {"LCK": 40, "EMEA Masters": 29, "World Championship": 6},
    "teamRegionCounts": {"KR": 10, "EMEA": 28},
    # scheduled rows: known-team vs TBD split (EMEA) and Worlds unresolved rows
    "emeaKnown": 14,
    "emeaTbd": 15,
    "worldsRows": 6,
    # known legacy condition: lastUpdatedAt is mixed-format (audit 18-17)
    "lastUpdatedAtDateOnly": 46,
    "lastUpdatedAtIsoZ": 29,
}

DATE_ONLY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
VERSION_RE = re.compile(r"^(\d{4})\.(\d{2})\.(\d{2})\.(\d{2})$")


def parse_version(value: str) -> tuple[int, int, int, int] | None:
    """Explicit parser for the project's YYYY.MM.DD.NN dataVersion format.

    Returns None for malformed versions so callers can fail closed instead of
    comparing raw strings.
    """
    match = VERSION_RE.match(value or "")
    if not match:
        return None
    return tuple(int(group) for group in match.groups())


def load_production() -> dict:
    return json.loads(PRODUCTION.read_text(encoding="utf-8"))


# ----------------------------------------------------------------------
# Granular contract checks. Each returns a list of human-readable problem
# strings (empty == pass) so the unittest gate stays debuggable and the
# remote release check can reuse the exact same logic.
# ----------------------------------------------------------------------


def envelope_problems(doc: dict) -> list[str]:
    problems: list[str] = []
    for key in ("schemaVersion", "dataVersion", "generatedAt", "leagues", "teams", "matches"):
        if key not in doc:
            problems.append(f"envelope: missing required key {key!r}")
    if doc.get("schemaVersion") != 1:
        problems.append(f"envelope: schemaVersion must be 1, got {doc.get('schemaVersion')!r}")
    if parse_version(doc.get("dataVersion", "")) is None:
        problems.append(f"envelope: dataVersion {doc.get('dataVersion')!r} is not YYYY.MM.DD.NN")
    if not isinstance(doc.get("generatedAt"), str) or not ISO_UTC_RE.match(doc.get("generatedAt", "")):
        problems.append(f"envelope: generatedAt {doc.get('generatedAt')!r} is not ISO-UTC Z")
    for key in ("leagues", "teams", "matches"):
        if not isinstance(doc.get(key), list):
            problems.append(f"envelope: {key} must be a list")
    return problems


def version_problems(doc: dict) -> list[str]:
    """Rollback gate: dataVersion must parse and never fall below the baseline."""
    problems: list[str] = []
    current = parse_version(doc.get("dataVersion", ""))
    baseline = parse_version(BASELINE["dataVersion"])
    if current is not None and baseline is not None and current < baseline:
        problems.append(
            f"dataVersion {doc.get('dataVersion')!r} is below the approved baseline "
            f"{BASELINE['dataVersion']!r} — accidental rollback or unapproved data change"
        )
    return problems


def distribution_problems(doc: dict) -> list[str]:
    problems: list[str] = []
    matches = doc.get("matches", [])
    teams = doc.get("teams", [])
    if len(doc.get("leagues", [])) != BASELINE["leagueCount"]:
        problems.append(f"baseline: league count {len(doc.get('leagues', []))} != {BASELINE['leagueCount']}")
    if len(teams) != BASELINE["teamCount"]:
        problems.append(f"baseline: team count {len(teams)} != {BASELINE['teamCount']}")
    if len(matches) != BASELINE["matchCount"]:
        problems.append(f"baseline: match count {len(matches)} != {BASELINE['matchCount']}")
    status = Counter(m.get("status") for m in matches)
    if status.get("completed", 0) != BASELINE["completedCount"]:
        problems.append(f"baseline: completed {status.get('completed', 0)} != {BASELINE['completedCount']}")
    if status.get("scheduled", 0) != BASELINE["scheduledCount"]:
        problems.append(f"baseline: scheduled {status.get('scheduled', 0)} != {BASELINE['scheduledCount']}")
    best_of = Counter(m.get("bestOf") for m in matches)
    if best_of != Counter(BASELINE["bestOfDistribution"]):
        problems.append(f"baseline: bestOf distribution {dict(best_of)} != {BASELINE['bestOfDistribution']}")
    league_ids = {l.get("id") for l in doc.get("leagues", [])}
    if league_ids != BASELINE["leagueIds"]:
        problems.append(f"baseline: league ids {league_ids} != {BASELINE['leagueIds']}")
    by_league = Counter(m.get("league", {}).get("name") for m in matches)
    for name, expected in BASELINE["leagueMatchCounts"].items():
        if by_league.get(name, 0) != expected:
            problems.append(f"baseline: {name} match count {by_league.get(name, 0)} != {expected}")
    by_region = Counter(t.get("region") for t in teams)
    for region, expected in BASELINE["teamRegionCounts"].items():
        if by_region.get(region, 0) != expected:
            problems.append(f"baseline: {region} team count {by_region.get(region, 0)} != {expected}")
    return problems


def id_problems(doc: dict) -> list[str]:
    problems: list[str] = []
    league_ids = [l.get("id") for l in doc.get("leagues", [])]
    if len(set(league_ids)) != len(league_ids):
        problems.append("ids: duplicate league ids")
    team_ids = [t.get("id") for t in doc.get("teams", [])]
    if len(set(team_ids)) != len(team_ids):
        problems.append("ids: duplicate team ids")
    match_ids = [m.get("id") for m in doc.get("matches", [])]
    if len(set(match_ids)) != len(match_ids):
        problems.append("ids: duplicate match ids")
    team_id_set = set(team_ids)
    dangling = [
        (m.get("id"), side)
        for m in doc.get("matches", [])
        for side in ("team1Id", "team2Id")
        if m.get(side) is not None and m.get(side) not in team_id_set
    ]
    if dangling:
        problems.append(f"ids: dangling team references {dangling[:5]}")
    # current semantics: each league maps to exactly one tournament id
    per_league: dict[str, set] = {}
    for m in doc.get("matches", []):
        per_league.setdefault(m.get("league", {}).get("id"), set()).add(
            (m.get("tournament") or {}).get("id")
        )
    for league_id, tournament_ids in per_league.items():
        if len(tournament_ids) != 1:
            problems.append(f"baseline: league {league_id!r} spans tournaments {sorted(tournament_ids)}")
    return problems


def validator_problems(doc: dict) -> list[str]:
    problems = list(validate_envelope(doc))
    if problems:
        problems = [f"validator(envelope): {p}" for p in problems]
    for m in doc.get("matches", []):
        if m.get("status") == "completed":
            result = validate_match(m)
            # validate_match returns a flat problem list (completed records
            # carry no warning tier); scheduled returns (errors, warnings).
            errors, warnings = (result, []) if isinstance(result, list) else result
        elif m.get("status") == "scheduled":
            errors, warnings = validate_scheduled_match(m)
        else:
            problems.append(f"validator: {m.get('id')!r} unknown status {m.get('status')!r}")
            continue
        for error in errors:
            problems.append(f"validator({m.get('id')}): {error}")
        for warning in warnings:
            problems.append(f"validator-warning({m.get('id')}): {warning}")
    return problems


def source_problems(doc: dict) -> list[str]:
    problems: list[str] = []
    for m in doc.get("matches", []):
        sources = m.get("sources")
        if not isinstance(sources, list) or not sources:
            problems.append(f"sources({m.get('id')}): must be a non-empty list")
            continue
        for entry in sources:
            for key in ("source", "kind", "ref"):
                if not isinstance(entry.get(key), str) or not entry.get(key):
                    problems.append(f"sources({m.get('id')}): {key!r} must be a non-empty string")
    return problems


def synthetic_problems(doc: dict) -> list[str]:
    problems: list[str] = []
    for m in doc.get("matches", []):
        if "rpgid" in m:
            problems.append(f"synthetic({m.get('id')}): top-level rpgid field exists")
        provisional = m.get("_provisional") or {}
        count = provisional.get("rpgidCount") or {}
        if isinstance(count, dict) and count.get("nonEmpty"):
            problems.append(f"synthetic({m.get('id')}): {count.get('nonEmpty')} non-empty rpgid(s) on a record")
    text_ids = [m.get("id", "") for m in doc.get("matches", [])]
    if any("sample" in mid.lower() for mid in text_ids):
        problems.append("synthetic: match ids contain 'sample' (SampleData contamination)")
    for t in doc.get("teams", []):
        if "sample" in (t.get("name") or "").lower() or "sample" in (t.get("id") or "").lower():
            problems.append(f"synthetic: team {t.get('id')!r} looks like SampleData contamination")
    if any((l.get("name") or "").lower() == "international" for l in doc.get("leagues", [])):
        problems.append("synthetic: SampleData placeholder league 'International' present")
    return problems


def team_problems(doc: dict) -> list[str]:
    problems: list[str] = []
    names = [t.get("name") for t in doc.get("teams", [])]
    if len(set(names)) != len(names):
        problems.append("teams: duplicate canonical identity names")
    for t in doc.get("teams", []):
        if not (t.get("id") or "").startswith("team-"):
            problems.append(f"teams: id {t.get('id')!r} does not use the team- convention")
        for key in ("name", "shortName", "region"):
            if not isinstance(t.get(key), str) or not t.get(key):
                problems.append(f"teams({t.get('id')}): {key} must be a non-empty string")
        if not isinstance(t.get("aliases"), list):
            problems.append(f"teams({t.get('id')}): aliases must be a list")
    return problems


def match_id_problems(doc: dict) -> list[str]:
    problems: list[str] = []
    for m in doc.get("matches", []):
        mid = m.get("id") or ""
        if not mid.startswith("lp:"):
            problems.append(f"baseline: match id {mid!r} does not use the established lp: convention")
        if "team-" in mid:
            problems.append(f"baseline: match id {mid!r} contains a rewritten canonical team id")
    return problems


def emea_problems(doc: dict) -> list[str]:
    """Scoped to the current EMEA Masters production rows only. Other leagues
    are NOT required to use PST or the EMEA provenance shape."""
    problems: list[str] = []
    emea = [m for m in doc.get("matches", []) if m.get("league", {}).get("name") == "EMEA Masters"]
    if len(emea) != BASELINE["leagueMatchCounts"]["EMEA Masters"]:
        problems.append(f"baseline: EMEA row count {len(emea)} changed")
        return problems
    known = []
    for m in emea:
        provisional = m.get("_provisional") or {}
        time_raw = provisional.get("timeRaw")
        if not isinstance(time_raw, dict):
            problems.append(f"emea({m.get('id')}): timeRaw provenance lost")
            continue
        if time_raw.get("timezone") != "PST" or time_raw.get("dst") != "yes":
            problems.append(f"emea({m.get('id')}): unexpected raw timezone {time_raw.get('timezone')!r}/{time_raw.get('dst')!r}")
        if time_raw.get("utcConversion") != "CONVERTED":
            problems.append(f"emea({m.get('id')}): utcConversion {time_raw.get('utcConversion')!r} != CONVERTED")
        # the conversion must still match the existing DST-aware logic
        result = normalize_local_to_utc(
            time_raw.get("date", ""), time_raw.get("time", ""), time_raw.get("timezone", ""), time_raw.get("dst", ""),
        )
        if result is None:
            problems.append(f"emea({m.get('id')}): conversion no longer possible with curated config")
        elif result.utc_iso != m.get("scheduledAt"):
            problems.append(f"emea({m.get('id')}): scheduledAt {m.get('scheduledAt')!r} != recomputed {result.utc_iso}")
        slot_state = provisional.get("teamSlotState") or {}
        if slot_state.get("team1") == "KNOWN" and slot_state.get("team2") == "KNOWN":
            known.append(m)
        else:
            if m.get("team1Id") is not None or m.get("team2Id") is not None:
                problems.append(f"emea({m.get('id')}): TBD row carries team ids")
    if len(known) != BASELINE["emeaKnown"]:
        problems.append(f"baseline: EMEA known-team rows {len(known)} != {BASELINE['emeaKnown']}")
    tbd_count = len(emea) - len(known)
    if tbd_count != BASELINE["emeaTbd"]:
        problems.append(f"baseline: EMEA TBD rows {tbd_count} != {BASELINE['emeaTbd']}")
    return problems


def worlds_problems(doc: dict) -> list[str]:
    """Scoped to the current Worlds Play-In rows: unresolved + timezone still
    pending. A future approved Worlds timezone resolution updates BASELINE."""
    problems: list[str] = []
    worlds = [
        m for m in doc.get("matches", []) if m.get("league", {}).get("name") == "World Championship"
    ]
    if len(worlds) != BASELINE["worldsRows"]:
        problems.append(f"baseline: Worlds row count {len(worlds)} != {BASELINE['worldsRows']}")
        return problems
    for m in worlds:
        if m.get("status") != "scheduled":
            problems.append(f"worlds({m.get('id')}): status {m.get('status')!r}")
        if m.get("team1Id") is not None or m.get("team2Id") is not None:
            problems.append(f"worlds({m.get('id')}): unresolved row grew team ids")
        if m.get("score") is not None:
            problems.append(f"worlds({m.get('id')}): score is not null")
        if m.get("scheduledAt") is not None:
            problems.append(f"worlds({m.get('id')}): scheduledAt is not null (timezone still pending)")
        provisional = m.get("_provisional") or {}
        if (provisional.get("teamSlotState") or {}) != {"team1": "EMPTY", "team2": "EMPTY"}:
            problems.append(f"worlds({m.get('id')}): slot state is not EMPTY/EMPTY")
        if (provisional.get("timeRaw") or {}).get("utcConversion") != "PENDING_TIMEZONE_REVIEW":
            problems.append(f"worlds({m.get('id')}): utcConversion is not PENDING_TIMEZONE_REVIEW")
    return problems


def timestamp_problems(doc: dict) -> list[str]:
    """generatedAt / scheduledAt must be ISO-UTC Z. lastUpdatedAt accepts the
    CURRENT production formats (date-only legacy OR ISO-Z) — the mixed state
    is a documented known condition, not a failure (46 date-only / 29 ISO-Z
    at PHASE 18-17)."""
    problems: list[str] = []
    if not ISO_UTC_RE.match(doc.get("generatedAt", "")):
        problems.append(f"timestamps: generatedAt {doc.get('generatedAt')!r} is not ISO-UTC Z")
    for m in doc.get("matches", []):
        scheduled_at = m.get("scheduledAt")
        if scheduled_at is not None and not ISO_UTC_RE.match(scheduled_at):
            problems.append(f"timestamps({m.get('id')}): scheduledAt {scheduled_at!r} is not ISO-UTC Z")
    date_only = iso_z = other = 0
    for m in doc.get("matches", []):
        value = m.get("lastUpdatedAt") or ""
        if DATE_ONLY_RE.match(value):
            date_only += 1
        elif ISO_UTC_RE.match(value):
            iso_z += 1
        else:
            other += 1
            problems.append(f"timestamps({m.get('id')}): lastUpdatedAt {value!r} is neither YYYY-MM-DD nor ISO-UTC Z")
    if other == 0 and (date_only, iso_z) != (
        BASELINE["lastUpdatedAtDateOnly"],
        BASELINE["lastUpdatedAtIsoZ"],
    ):
        problems.append(
            f"baseline: lastUpdatedAt mixed split {(date_only, iso_z)} changed from "
            f"{(BASELINE['lastUpdatedAtDateOnly'], BASELINE['lastUpdatedAtIsoZ'])} — "
            "document/normalize in an approved promotion if intended"
        )
    return problems


def collect_problems(doc: dict) -> list[str]:
    """Full offline contract gate. Used by the unittest class and by the
    manual remote release check (scripts/release_remote_check.py)."""
    problems: list[str] = []
    for check in (
        envelope_problems,
        version_problems,
        distribution_problems,
        id_problems,
        validator_problems,
        source_problems,
        synthetic_problems,
        team_problems,
        match_id_problems,
        emea_problems,
        worlds_problems,
        timestamp_problems,
    ):
        problems.extend(check(doc))
    return problems


class ProductionContractTests(unittest.TestCase):
    """Offline gate over the actual production document."""

    @classmethod
    def setUpClass(cls):
        cls.doc = load_production()

    def test_full_contract_gate_has_no_problems(self):
        self.assertEqual([], collect_problems(self.doc))

    def test_a_envelope_required_keys_and_schema_version(self):
        self.assertEqual([], envelope_problems(self.doc))

    def test_a_dataversion_format_is_valid(self):
        self.assertIsNotNone(parse_version(self.doc.get("dataVersion", "")))

    def test_a_dataversion_not_rolled_back_below_baseline(self):
        self.assertEqual([], version_problems(self.doc))

    def test_a_generatedat_is_iso_utc_z(self):
        self.assertTrue(ISO_UTC_RE.match(self.doc["generatedAt"]), self.doc["generatedAt"])

    def test_b_current_production_baseline_distribution(self):
        self.assertEqual([], distribution_problems(self.doc))

    def test_c_ids_unique_and_no_dangling_references(self):
        self.assertEqual([], id_problems(self.doc))

    def test_d_existing_validator_passes_all_production_matches(self):
        self.assertEqual([], validator_problems(self.doc))

    def test_e_source_metadata_shape(self):
        self.assertEqual([], source_problems(self.doc))

    def test_f_no_synthetic_provenance_or_sample_contamination(self):
        self.assertEqual([], synthetic_problems(self.doc))

    def test_g_emea_timezone_provenance_and_conversion_preserved(self):
        self.assertEqual([], emea_problems(self.doc))

    def test_h_worlds_rows_remain_unresolved_and_pending(self):
        self.assertEqual([], worlds_problems(self.doc))

    def test_i_timestamp_contract_including_known_legacy_lastupdatedat(self):
        self.assertEqual([], timestamp_problems(self.doc))

    def test_match_ids_lp_prefixed_and_stable_convention(self):
        self.assertEqual([], match_id_problems(self.doc))

    def test_team_contract_fields_and_identity_uniqueness(self):
        self.assertEqual([], team_problems(self.doc))


if __name__ == "__main__":
    unittest.main()
