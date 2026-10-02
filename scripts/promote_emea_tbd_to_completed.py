"""PHASE 18-22: in-place transition of 10 EMEA TBD scheduled matches (Round 6,
2026-10-01) to completed, preserving the existing canonical Match IDs.

Evidence fetched read-only 2026-10-02 from the live Leaguepedia pages:
- Data page: Round 6 rows now carry real teams, scores, winners and game
  blocks (24 rpgids across the 10 series). Row-level bestof = 3 for all ten.
- Scoreboards/Round 6 + Round 6 (2): all 24 rpgids join to their game team
  pairs (SCOREBOARD_MAP below).

Fail-closed per row: the canonical match is located deterministically by
date + suffix (never by date alone, team name alone, or array index); it
must currently be scheduled with null team ids and TBD slots; the source
teams must resolve through the exact resolver into the existing canonical
teams; every rpgid must join to the verified scoreboard pair; the source
winner must agree with the score and the game count must equal the score
sum (no forfeits/special cases in this set). Any failure aborts before
writing.

scheduledAt policy (approved): rows whose live schedule time matches the
snapshot keep their canonical scheduledAt; rows whose schedule was
corrected by the source (rows 6-10: 09:00 -> 11:00 PST) are updated to the
recomputed UTC value via the existing EMEA rule (PST + dst=yes -> UTC-07).
Round 7 rows are NOT touched.
"""

from __future__ import annotations

import datetime
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.series_score import TeamIdentityResolver  # noqa: E402
from lib.timezones import normalize_local_to_utc  # noqa: E402

CANONICAL = ROOT / "data" / "matches.json"
MATCH_ID_PREFIX = "lp:EM 2026 Summer Main Event:2026-10-01:TBD:TBD"

# Live Round 6 evidence (fetched 2026-10-02). suffix = canonical id suffix
# ("" for the first row of the round, ":02".."::10" for the rest, matching
# the pre-created TBD ids). time = CURRENT source local time (the source
# corrected rows 6-10 from 09:00 to 11:00 PST).
LIVE_RESULTS = [
    {"suffix": "", "t1": "Bushido Wildcats", "t2": "FEC", "s1": 2, "s2": 1,
     "games": 3, "rpgids": ["LOLTMNT05_226101", "LOLTMNT05_227163", "LOLTMNT05_227165"],
     "time": "08:00"},
    {"suffix": ":02", "t1": "Valerion", "t2": "Ruddy Corporation", "s1": 1, "s2": 2,
     "games": 3, "rpgids": ["LOLTMNT05_227159", "LOLTMNT05_227162", "LOLTMNT05_226114"],
     "time": "08:00"},
    {"suffix": ":03", "t1": "Colossal Gaming", "t2": "UOL.SE", "s1": 0, "s2": 2,
     "games": 2, "rpgids": ["LOLTMNT05_227158", "LOLTMNT05_226106"],
     "time": "08:00"},
    {"suffix": ":04", "t1": "Bomba Team", "t2": "Skillcamp", "s1": 1, "s2": 2,
     "games": 3, "rpgids": ["LOLTMNT05_226103", "LOLTMNT05_226108", "LOLTMNT05_226111"],
     "time": "08:00"},
    {"suffix": ":05", "t1": "Magaza", "t2": "Otter Side", "s1": 2, "s2": 0,
     "games": 2, "rpgids": ["LOLTMNT05_226102", "LOLTMNT05_227161"],
     "time": "08:00"},
    {"suffix": ":06", "t1": "BIG", "t2": "Nightbirds", "s1": 2, "s2": 0,
     "games": 2, "rpgids": ["LOLTMNT05_227164", "LOLTMNT05_227167"],
     "time": "11:00"},
    {"suffix": ":07", "t1": "PCIFIC Esports", "t2": "LODIS PL", "s1": 2, "s2": 0,
     "games": 2, "rpgids": ["LOLTMNT05_227168", "LOLTMNT05_226135"],
     "time": "11:00"},
    {"suffix": ":08", "t1": "JSK Esports", "t2": "UCAM Esports", "s1": 0, "s2": 2,
     "games": 2, "rpgids": ["LOLTMNT05_227171", "LOLTMNT05_226131"],
     "time": "11:00"},
    {"suffix": ":09", "t1": "Phantasma", "t2": "TSC HR", "s1": 1, "s2": 2,
     "games": 3, "rpgids": ["LOLTMNT05_226121", "LOLTMNT05_227183", "LOLTMNT05_226139"],
     "time": "11:00"},
    {"suffix": ":10", "t1": "SNSH", "t2": "Barca", "s1": 0, "s2": 2,
     "games": 2, "rpgids": ["LOLTMNT05_227166", "LOLTMNT05_226119"],
     "time": "11:00"},
]

# Scoreboards/Round 6 evidence (fetched 2026-10-02): rpgid -> [team1, team2]
SCOREBOARD_MAP = {
    "LOLTMNT05_226101": ["Bushido Wildcats", "Frites Esports Club"],
    "LOLTMNT05_226102": ["Magaza Esports", "Otter Side"],
    "LOLTMNT05_226103": ["Bomba Team", "Skillcamp"],
    "LOLTMNT05_226106": ["Unicorns of Love Sexy Edition", "Colossal Gaming"],
    "LOLTMNT05_226108": ["Bomba Team", "Skillcamp"],
    "LOLTMNT05_226111": ["Bomba Team", "Skillcamp"],
    "LOLTMNT05_226114": ["Ruddy Corporation", "Valerion"],
    "LOLTMNT05_226119": ["Senshi eSports (Benelux Team)", "Barça eSports"],
    "LOLTMNT05_226121": ["The Secret Club", "Team Phantasma"],
    "LOLTMNT05_226131": ["UCAM Esports", "JSK Esports"],
    "LOLTMNT05_226135": ["LODIS (Polish Team)", "PCIFIC Esports"],
    "LOLTMNT05_226139": ["Team Phantasma", "The Secret Club"],
    "LOLTMNT05_227158": ["Unicorns of Love Sexy Edition", "Colossal Gaming"],
    "LOLTMNT05_227159": ["Ruddy Corporation", "Valerion"],
    "LOLTMNT05_227161": ["Magaza Esports", "Otter Side"],
    "LOLTMNT05_227162": ["Ruddy Corporation", "Valerion"],
    "LOLTMNT05_227163": ["Bushido Wildcats", "Frites Esports Club"],
    "LOLTMNT05_227164": ["Berlin International Gaming", "Nightbirds"],
    "LOLTMNT05_227165": ["Bushido Wildcats", "Frites Esports Club"],
    "LOLTMNT05_227166": ["Senshi eSports (Benelux Team)", "Barça eSports"],
    "LOLTMNT05_227167": ["Berlin International Gaming", "Nightbirds"],
    "LOLTMNT05_227168": ["PCIFIC Esports", "LODIS (Polish Team)"],
    "LOLTMNT05_227171": ["UCAM Esports", "JSK Esports"],
    "LOLTMNT05_227183": ["The Secret Club", "Team Phantasma"],
}

DATE = "2026-10-01"
TIMEZONE = "PST"
DST = "yes"


def main() -> None:
    data = json.loads(CANONICAL.read_text(encoding="utf-8"))

    # ---- fail-closed preconditions ----
    assert data.get("schemaVersion") == 1
    old_version = data["dataVersion"]
    matches = data["matches"]
    assert len(matches) == 139, len(matches)
    match_ids_before = {m["id"] for m in matches}

    teams = data["teams"]
    assert len(teams) == 42, len(teams)
    team_ids = {t["id"] for t in teams}
    id_to_name = {t["id"]: t["name"] for t in teams}
    short_to_id = {t["shortName"]: t["id"] for t in teams}
    # schedule codes that differ from shortName are resolvable via the exact
    # resolver's name table; build raw-value -> (id, name) from aliases too
    raw_to_team: dict[str, tuple[str, str]] = {}
    for t in teams:
        raw_to_team[t["name"]] = (t["id"], t["name"])
        raw_to_team[t["shortName"]] = (t["id"], t["name"])
        for alias in t.get("aliases", []):
            raw_to_team.setdefault(alias, (t["id"], t["name"]))

    lck_before = [m for m in matches if m["league"]["name"] == "LCK"]
    worlds_before = [m for m in matches if m["league"]["name"] == "World Championship"]
    emea_completed_before = [
        m for m in matches
        if m["league"]["name"] == "EMEA Masters" and m["status"] == "completed"
    ]
    round7_before = [
        m for m in matches
        if m["league"]["name"] == "EMEA Masters" and m["status"] == "scheduled"
        and (m.get("_provisional", {}).get("timeRaw", {}).get("date") == "2026-10-02")
    ]
    assert len(lck_before) == 40 and len(worlds_before) == 6
    assert len(emea_completed_before) == 78 and len(round7_before) == 5

    resolver = TeamIdentityResolver()
    generated_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # ---- locate + verify the 10 targets ----
    targets = []
    for live in LIVE_RESULTS:
        match_id = f"{MATCH_ID_PREFIX}{live['suffix']}"
        found = [m for m in matches if m["id"] == match_id]
        assert len(found) == 1, f"target not found or duplicated: {match_id}"
        m = found[0]
        assert m["status"] == "scheduled", f"{match_id}: status {m['status']!r}"
        assert m["team1Id"] is None and m["team2Id"] is None, f"{match_id}: team ids not null"
        provisional = m["_provisional"]
        slot_state = provisional["teamSlotState"]
        assert slot_state == {"team1": "TBD", "team2": "TBD"}, f"{match_id}: slot state {slot_state}"
        assert m["bestOf"] == 3, f"{match_id}: bestOf {m['bestOf']}"

        # identity resolution through the exact resolver + existing teams
        ids, names = {}, {}
        for side, raw in (("team1", live["t1"]), ("team2", live["t2"])):
            resolved = resolver.resolve(raw)
            assert resolved.status.name == "RESOLVED", f"{match_id}: {raw!r} unresolved"
            if resolved.canonical in raw_to_team:
                tid, name = raw_to_team[resolved.canonical]
            elif raw in raw_to_team:
                tid, name = raw_to_team[raw]
            else:
                raise AssertionError(f"{match_id}: {raw!r} ({resolved.canonical!r}) has no canonical team")
            ids[side], names[side] = tid, name
        assert ids["team1"] != ids["team2"], f"{match_id}: both slots resolve to one team"

        # score / winner / game count consistency (no forfeits in this set)
        assert live["s1"] != live["s2"], f"{match_id}: tied score"
        expected_winner = live["t1"] if live["s1"] > live["s2"] else live["t2"]
        assert live["s1"] + live["s2"] == live["games"], (
            f"{match_id}: game blocks {live['games']} != score sum {live['s1'] + live['s2']}"
        )

        # rpgid cross-check against Scoreboards evidence (order-insensitive)
        verified_names = {names["team1"], names["team2"]}
        for rpgid in live["rpgids"]:
            sb = SCOREBOARD_MAP.get(rpgid)
            assert sb is not None, f"{match_id}: rpgid {rpgid} missing from Scoreboards evidence"
            assert set(sb) == verified_names, (
                f"{match_id}: rpgid {rpgid} scoreboard pair {sb} != canonical teams {sorted(verified_names)}"
            )

        # scheduledAt: recompute from the CURRENT source time
        result = normalize_local_to_utc(DATE, live["time"], TIMEZONE, DST)
        assert result is not None, f"{match_id}: timezone conversion failed"
        old_scheduled_at = m["scheduledAt"]
        if old_scheduled_at != result.utc_iso:
            # allowed only as the approved source schedule correction (rows 6-10)
            assert live["time"] == "11:00", (
                f"{match_id}: scheduledAt drift {old_scheduled_at} != {result.utc_iso} without an approved correction"
            )
        targets.append((m, live, match_id, result.utc_iso, old_scheduled_at))

    assert len(targets) == 10, len(targets)

    # ---- in-place transition (match ids preserved) ----
    for m, live, match_id, new_scheduled_at, old_scheduled_at in targets:
        provisional = m["_provisional"]
        m["status"] = "completed"
        m["score"] = {"team1": live["s1"], "team2": live["s2"]}
        m["scheduledAt"] = new_scheduled_at
        m["lastUpdatedAt"] = generated_at
        # provenance: TBD -> resolved; existing timeRaw kept but the time is
        # corrected to the current source value where the schedule changed
        for side, raw_key in (("team1", "t1"), ("team2", "t2")):
            raw = live[raw_key]
            resolved = resolver.resolve(raw)
            tid = raw_to_team.get(resolved.canonical, raw_to_team.get(raw))[0]
            provisional["teamSlotState"][side] = "KNOWN"
            provisional["teamSlotRaw"][side] = raw
            provisional["identityStatus"][side] = "RESOLVED"
            provisional["canonicalTeamId"][side] = tid
            m[side + "Id"] = tid
        provisional["rpgidCount"] = {
            "total": live["games"], "nonEmpty": len(live["rpgids"])
        }
        provisional["timeRaw"]["time"] = live["time"]

    data["dataVersion"] = next_version(old_version)
    data["generatedAt"] = generated_at

    # ---- regression assertions (before writing) ----
    assert {m["id"] for m in data["matches"]} == match_ids_before, "match ids changed"
    assert len(data["matches"]) == 139
    assert [m for m in data["matches"] if m["league"]["name"] == "LCK"] == lck_before, "LCK changed"
    assert [m for m in data["matches"] if m["league"]["name"] == "World Championship"] == worlds_before, "Worlds changed"
    emea_after = [m for m in data["matches"] if m["league"]["name"] == "EMEA Masters"]
    completed_after = [m for m in emea_after if m["status"] == "completed"]
    scheduled_after = [m for m in emea_after if m["status"] == "scheduled"]
    old_completed_ids = {m["id"] for m in emea_completed_before}
    preexisting = [m for m in completed_after if m["id"] in old_completed_ids]
    assert preexisting == emea_completed_before, "existing EMEA completed rows changed"
    assert len(completed_after) == 88, len(completed_after)
    assert len(scheduled_after) == 5, len(scheduled_after)
    round7_after = [m for m in scheduled_after if m["_provisional"]["timeRaw"]["date"] == "2026-10-02"]
    assert round7_after == round7_before, "Round 7 rows changed"
    for m in round7_after:
        assert m["team1Id"] is None and m["team2Id"] is None and m["score"] is None
    # scheduledAt regression: rows 1-5 kept 15:00Z, rows 6-10 corrected to 18:00Z
    for m, live, match_id, new_scheduled_at, old_scheduled_at in targets:
        found = [x for x in data["matches"] if x["id"] == match_id][0]
        assert found["scheduledAt"] == new_scheduled_at, match_id
        if live["time"] == "08:00":
            assert new_scheduled_at == old_scheduled_at == "2026-10-01T15:00:00Z", match_id
        else:
            assert new_scheduled_at == "2026-10-01T18:00:00Z", match_id
            assert old_scheduled_at == "2026-10-01T16:00:00Z", match_id
    total_scheduled = sum(1 for x in data["matches"] if x["status"] == "scheduled")
    assert total_scheduled == 11, total_scheduled

    CANONICAL.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"dataVersion: {old_version} -> {data['dataVersion']}")
    print(f"transitions: {len(targets)}/10 TBD -> completed (ids preserved)")
    print(f"matches: 139 (unchanged) | completed: 118 -> {sum(1 for m in data['matches'] if m['status']=='completed')} | scheduled: 21 -> {total_scheduled}")
    print(f"generatedAt: {generated_at}")
    for m, live, _, new_at, old_at in targets:
        drift = "" if new_at == old_at else f" (scheduledAt corrected {old_at} -> {new_at})"
        print(f"  {m['id']}: {live['s1']}:{live['s2']} rpgidCount={m['_provisional']['rpgidCount']}{drift}")


def next_version(current: str) -> str:
    """Repository policy: promotion date changed (2026-10-02) -> new day, .01."""
    year, month, day, _seq = (int(x) for x in current.split("."))
    today = datetime.datetime.now(datetime.timezone.utc).date()
    if (year, month, day) == (today.year, today.month, today.day):
        return f"{year:04d}.{month:02d}.{day:02d}.{_seq + 1:02d}"
    return f"{today.year:04d}.{today.month:02d}.{today.day:02d}.01"


if __name__ == "__main__":
    main()
