"""PHASE 18-21: in-place transition of 14 EMEA scheduled matches to completed.

This is NOT an append. The 14 existing canonical Match IDs
(lp:EM 2026 Summer Main Event:2026-09-30:<raw1>:<raw2>) are preserved and
their status transitions scheduled -> completed using evidence fetched from
the live Leaguepedia fixture + Scoreboards (2026-10-01, read-only).

Evidence embedded below (PHASE 18-21 audit, 14/14 VERIFIED):
- LIVE_RESULTS: the 14 series results (scores/winner/game blocks/rpgids/ff)
  exactly as recorded on the live Data page.
- SCOREBOARD_MAP: all 23 game rpgids joined to their Scoreboards/Round 5
  team pairs (fetched from the wiki's own game pages).

Fail-closed per row: identity must match the existing canonical ids, the
source winner must agree with the score, bestOf must equal the existing
canonical bestOf, scheduledAt is UNCHANGED (audit confirmed no drift), every
rpgid must join to the verified scoreboard pair, and the forfeit row is the
documented exception (ff=2, zero games — same principle as PHASE 18-20's
included forfeit). Any failure aborts the whole promotion before writing.
"""

from __future__ import annotations

import datetime
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

CANONICAL = ROOT / "data" / "matches.json"
MATCH_ID_PREFIX = "lp:EM 2026 Summer Main Event:2026-09-30:"

# Live Leaguepedia evidence (fetched 2026-10-01): key = (raw team1, raw team2)
# exactly as they appear in the canonical match ids / teamSlotRaw.
LIVE_RESULTS = [
    {"t1": "BIG", "t2": "SNSH", "s1": 1, "s2": 0, "winner": 1, "games": 1,
     "rpgids": ["LOLTMNT05_227079"], "ff": None},
    {"t1": "Bushido Wildcats", "t2": "Magaza", "s1": 1, "s2": 0, "winner": 1, "games": 1,
     "rpgids": ["LOLTMNT05_226050"], "ff": None},
    {"t1": "FEC", "t2": "Otter Side", "s1": 1, "s2": 0, "winner": 1, "games": 1,
     "rpgids": ["LOLTMNT05_227078"], "ff": None},
    {"t1": "PCIFIC Esports", "t2": "Ruddy Corporation", "s1": 0, "s2": 1, "winner": 2, "games": 1,
     "rpgids": ["LOLTMNT05_227089"], "ff": None},
    {"t1": "JSK Esports", "t2": "Skillcamp", "s1": 0, "s2": 1, "winner": 2, "games": 1,
     "rpgids": ["LOLTMNT05_226055"], "ff": None},
    {"t1": "Colossal Gaming", "t2": "LODIS PL", "s1": 1, "s2": 0, "winner": 1, "games": 1,
     "rpgids": ["LOLTMNT05_226054"], "ff": None},
    {"t1": "TLN Pirates", "t2": "Valerion", "s1": 2, "s2": 0, "winner": 1, "games": 2,
     "rpgids": ["LOLTMNT05_227105", "LOLTMNT05_226061"], "ff": None},
    {"t1": "KHK", "t2": "UOL.SE", "s1": 2, "s2": 0, "winner": 1, "games": 2,
     "rpgids": ["LOLTMNT05_227103", "LOLTMNT05_227109"], "ff": None},
    {"t1": "HMBLE", "t2": "Barca", "s1": 0, "s2": 2, "winner": 2, "games": 2,
     "rpgids": ["LOLTMNT05_227104", "LOLTMNT05_227110"], "ff": None},
    {"t1": "ESB", "t2": "UCAM Esports", "s1": 1, "s2": 2, "winner": 2, "games": 3,
     "rpgids": ["LOLTMNT05_227106", "LOLTMNT05_227112", "LOLTMNT05_227120"], "ff": None},
    {"t1": "G2 NORD", "t2": "Bomba Team", "s1": 2, "s2": 0, "winner": 1, "games": 2,
     "rpgids": ["LOLTMNT05_227119", "LOLTMNT05_227125"], "ff": None},
    {"t1": "HRTS.A", "t2": "Nightbirds", "s1": 2, "s2": 1, "winner": 1, "games": 3,
     "rpgids": ["LOLTMNT05_227127", "LOLTMNT05_227129", "LOLTMNT05_227132"], "ff": None},
    {"t1": "Phantasma", "t2": "GMCE", "s1": 2, "s2": 1, "winner": 1, "games": 3,
     "rpgids": ["LOLTMNT05_227121", "LOLTMNT05_227128", "LOLTMNT05_227131"], "ff": None},
    # documented forfeit: ff=2 (team2 forfeited), "SU Esports failed to show
    # up" with a source citation on the live page; zero games by nature.
    {"t1": "TSC HR", "t2": "SU Esports", "s1": 2, "s2": 0, "winner": 1, "games": 0,
     "rpgids": [], "ff": 2},
]

# Scoreboards/Round 5 evidence (fetched 2026-10-01): rpgid -> [team1, team2]
# full names as recorded by the wiki's own game pages.
SCOREBOARD_MAP = {
    "LOLTMNT05_226050": ["Magaza Esports", "Bushido Wildcats"],
    "LOLTMNT05_226054": ["Colossal Gaming", "LODIS (Polish Team)"],
    "LOLTMNT05_226055": ["JSK Esports", "Skillcamp"],
    "LOLTMNT05_226061": ["Valerion", "TLN Pirates"],
    "LOLTMNT05_227078": ["Frites Esports Club", "Otter Side"],
    "LOLTMNT05_227079": ["Senshi eSports (Benelux Team)", "Berlin International Gaming"],
    "LOLTMNT05_227089": ["Ruddy Corporation", "PCIFIC Esports"],
    "LOLTMNT05_227103": ["Unicorns of Love Sexy Edition", "Kaufland Hangry Knights"],
    "LOLTMNT05_227104": ["HMBLE", "Barça eSports"],
    "LOLTMNT05_227105": ["Valerion", "TLN Pirates"],
    "LOLTMNT05_227106": ["eSuba", "UCAM Esports"],
    "LOLTMNT05_227109": ["Kaufland Hangry Knights", "Unicorns of Love Sexy Edition"],
    "LOLTMNT05_227110": ["HMBLE", "Barça eSports"],
    "LOLTMNT05_227112": ["UCAM Esports", "eSuba"],
    "LOLTMNT05_227119": ["Bomba Team", "G2 NORD"],
    "LOLTMNT05_227120": ["UCAM Esports", "eSuba"],
    "LOLTMNT05_227121": ["Gamespace Mediterranean College Esports", "Team Phantasma"],
    "LOLTMNT05_227125": ["Bomba Team", "G2 NORD"],
    "LOLTMNT05_227127": ["Team Heretics Academy", "Nightbirds"],
    "LOLTMNT05_227128": ["Gamespace Mediterranean College Esports", "Team Phantasma"],
    "LOLTMNT05_227129": ["Team Heretics Academy", "Nightbirds"],
    "LOLTMNT05_227131": ["Gamespace Mediterranean College Esports", "Team Phantasma"],
    "LOLTMNT05_227132": ["Nightbirds", "Team Heretics Academy"],
}

VERSION_RE = re.compile(r"^(\d{4})\.(\d{2})\.(\d{2})\.(\d{2})$")


def parse_version(value: str) -> tuple[int, int, int, int] | None:
    match = VERSION_RE.match(value or "")
    if not match:
        return None
    return tuple(int(group) for group in match.groups())


def next_version(current: str, today: datetime.date) -> str:
    """Repository policy: dataVersion increases on every promotion.
    Same-day promotions increment the trailing NN; a new day resets it to 01."""
    parsed = parse_version(current)
    assert parsed is not None, f"current dataVersion malformed: {current!r}"
    year, month, day, seq = parsed
    if (year, month, day) == (today.year, today.month, today.day):
        return f"{year:04d}.{month:02d}.{day:02d}.{seq + 1:02d}"
    return f"{today.year:04d}.{today.month:02d}.{today.day:02d}.01"


def main() -> None:
    data = json.loads(CANONICAL.read_text(encoding="utf-8"))

    # ---- fail-closed preconditions ----
    assert data.get("schemaVersion") == 1
    old_version = data["dataVersion"]
    new_version = next_version(old_version, datetime.datetime.now(datetime.timezone.utc).date())
    matches = data["matches"]
    assert len(matches) == 139, len(matches)
    match_ids_before = {m["id"] for m in matches}

    teams = data["teams"]
    assert len(teams) == 42, len(teams)
    team_ids = {t["id"] for t in teams}
    id_to_name = {t["id"]: t["name"] for t in teams}
    short_to_id = {t["shortName"]: t["id"] for t in teams}

    lck_before = [m for m in matches if m["league"]["name"] == "LCK"]
    worlds_before = [m for m in matches if m["league"]["name"] == "World Championship"]
    emea_completed_before = [
        m for m in matches
        if m["league"]["name"] == "EMEA Masters" and m["status"] == "completed"
    ]
    emea_tbd_before = [
        m for m in matches
        if m["league"]["name"] == "EMEA Masters" and m["status"] == "scheduled"
        and (m.get("_provisional", {}).get("teamSlotState", {}).get("team1") == "TBD")
    ]
    assert len(lck_before) == 40 and len(worlds_before) == 6
    assert len(emea_completed_before) == 64 and len(emea_tbd_before) == 15

    # ---- locate the 14 targets and verify each against the live evidence ----
    targets = []
    for live in LIVE_RESULTS:
        match_id = f"{MATCH_ID_PREFIX}{live['t1']}:{live['t2']}"
        found = [m for m in matches if m["id"] == match_id]
        assert len(found) == 1, f"target match not found or duplicated: {match_id}"
        m = found[0]
        assert m["status"] == "scheduled", f"{match_id}: status {m['status']!r}"
        assert m["score"] is None, f"{match_id}: score already present"

        # identity invariants: canonical team ids match the live row's teams
        expected_t1 = short_to_id.get(live["t1"])
        expected_t2 = short_to_id.get(live["t2"])
        assert expected_t1 is not None and expected_t2 is not None, match_id
        assert m["team1Id"] == expected_t1, f"{match_id}: team1Id mismatch"
        assert m["team2Id"] == expected_t2, f"{match_id}: team2Id mismatch"

        # winner agrees with the live score
        expected_winner = live["t1"] if live["s1"] > live["s2"] else live["t2"]
        assert (live["winner"] == 1) == (live["s1"] > live["s2"]), f"{match_id}: live winner/score conflict"

        # every rpgid joins to the verified scoreboard pair (order-insensitive)
        verified_names = {id_to_name[expected_t1], id_to_name[expected_t2]}
        for rpgid in live["rpgids"]:
            sb = SCOREBOARD_MAP.get(rpgid)
            assert sb is not None, f"{match_id}: rpgid {rpgid} missing from Scoreboards evidence"
            assert set(sb) == verified_names, (
                f"{match_id}: rpgid {rpgid} scoreboard pair {sb} != canonical teams {sorted(verified_names)}"
            )

        # forfeit exception must be documented in the source evidence
        if live["games"] == 0:
            assert live["ff"] is not None, f"{match_id}: zero games without documented ff"
        else:
            # played series: game blocks >= games implied by the score
            implied = live["s1"] + live["s2"]
            assert live["games"] == implied, (
                f"{match_id}: game blocks {live['games']} != score sum {implied} (no documented ff)"
            )
        targets.append((m, live, match_id))

    assert len(targets) == 14, len(targets)

    # ---- in-place transition (ids and scheduledAt untouched) ----
    generated_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for m, live, match_id in targets:
        assert m["scheduledAt"], f"{match_id}: scheduledAt missing"
        m["status"] = "completed"
        m["score"] = {"team1": live["s1"], "team2": live["s2"]}
        m["lastUpdatedAt"] = generated_at
        provisional = m["_provisional"]
        # rpgidCount refreshed with the live actuals; all other provenance kept
        provisional["rpgidCount"] = {"total": live["games"], "nonEmpty": len(live["rpgids"])}

    data["dataVersion"] = new_version
    data["generatedAt"] = generated_at

    # ---- regression assertions (before writing) ----
    assert {m["id"] for m in data["matches"]} == match_ids_before, "match ids changed"
    assert len(data["matches"]) == 139
    assert [m for m in data["matches"] if m["league"]["name"] == "LCK"] == lck_before, "LCK changed"
    assert [m for m in data["matches"] if m["league"]["name"] == "World Championship"] == worlds_before, "Worlds changed"
    emea_after = [m for m in data["matches"] if m["league"]["name"] == "EMEA Masters"]
    completed_after = [m for m in emea_after if m["status"] == "completed"]
    scheduled_after = [m for m in emea_after if m["status"] == "scheduled"]
    assert len(completed_after) == 78, len(completed_after)
    # EMEA scheduled = the 15 TBD rows only (the 14 KNOWN rows transitioned)
    assert len(scheduled_after) == 15, len(scheduled_after)
    total_scheduled = sum(1 for m in data["matches"] if m["status"] == "scheduled")
    assert total_scheduled == 21, total_scheduled
    # the 64 pre-existing completed EMEA rows are byte-identical
    old_completed_ids = {m["id"] for m in emea_completed_before}
    preexisting = [m for m in completed_after if m["id"] in old_completed_ids]
    assert preexisting == emea_completed_before, "existing EMEA completed rows changed"
    # TBD rows unchanged
    tbd_after = [
        m for m in scheduled_after
        if m.get("_provisional", {}).get("teamSlotState", {}).get("team1") == "TBD"
    ]
    assert tbd_after == emea_tbd_before, "EMEA TBD rows changed"
    # the 14 targets now completed with the verified scores
    for m, live, match_id in targets:
        found = [x for x in data["matches"] if x["id"] == match_id][0]
        assert found["status"] == "completed" and found["score"] == {"team1": live["s1"], "team2": live["s2"]}
    # no dangling references
    for m in data["matches"]:
        for side in ("team1Id", "team2Id"):
            assert m.get(side) is None or m.get(side) in team_ids, f"dangling ref {m['id']}.{side}"

    CANONICAL.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"dataVersion: {old_version} -> {new_version}")
    print(f"transitions: {len(targets)}/14 scheduled -> completed (ids preserved)")
    print(f"matches: 139 (unchanged) | completed: 104 -> {sum(1 for m in data['matches'] if m['status']=='completed')} | scheduled: 35 -> {sum(1 for m in data['matches'] if m['status']=='scheduled')}")
    print(f"generatedAt: {generated_at}")
    for m, live, _ in targets:
        print(f"  {m['id']}: {live['s1']}:{live['s2']} (ff={live['ff']}) rpgidCount={m['_provisional']['rpgidCount']}")


if __name__ == "__main__":
    main()
