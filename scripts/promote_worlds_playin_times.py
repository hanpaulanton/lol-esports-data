"""PHASE 18-24: fill scheduledAt for the six Worlds Play-In scheduled rows.

In-place, schedule-time-only promotion (PHASE 18-24 approved audit):
- exactly the six audited Worlds Play-In rows
- scheduledAt: null -> the audited UTC values (rule: PST + dst=yes -> UTC-07,
  verified twice: Leaguepedia Module:TimeUtil source code + 63 EMEA
  same-label/dst empirical joins)
- _provisional.timeRaw: date/time/timezone/dst UNCHANGED (source has no
  drift); utcConversion: PENDING_TIMEZONE_REVIEW -> CONVERTED
- lastUpdatedAt: refreshed on the six rows only
- ids/teams/scores/status/bestOf/rpgid provenance: UNCHANGED

Fail-closed: every row is located by its explicit match id; any deviation
from the audited state (status, null scheduledAt, timezone, dst, bestOf,
teams, score, rpgid, provenance) aborts before writing. The computed value
must equal the audited expected value AND the value produced by the existing
curated timezone logic (lib.timezones via config/timezone_offsets.json) —
two independent derivations must agree.
"""

from __future__ import annotations

import datetime
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.timezones import normalize_local_to_utc  # noqa: E402

CANONICAL = ROOT / "data" / "matches.json"
MATCH_ID_PREFIX = "lp:Worlds 2026 Play-In:"

# Audited source constants (PHASE 18-24): the six rows with their raw source
# values and the expected UTC under the verified rule (PST + dst=yes -> -7).
AUDITED_ROWS = [
    {"match_id": "lp:Worlds 2026 Play-In:2026-10-15:EMPTY:EMPTY",
     "date": "2026-10-15", "time": "11:00", "expected_utc": "2026-10-15T18:00:00Z"},
    {"match_id": "lp:Worlds 2026 Play-In:2026-10-15:EMPTY:EMPTY:02",
     "date": "2026-10-15", "time": "16:00", "expected_utc": "2026-10-15T23:00:00Z"},
    {"match_id": "lp:Worlds 2026 Play-In:2026-10-16:EMPTY:EMPTY",
     "date": "2026-10-16", "time": "16:00", "expected_utc": "2026-10-16T23:00:00Z"},
    {"match_id": "lp:Worlds 2026 Play-In:2026-10-16:EMPTY:EMPTY:02",
     "date": "2026-10-16", "time": "11:00", "expected_utc": "2026-10-16T18:00:00Z"},
    {"match_id": "lp:Worlds 2026 Play-In:2026-10-17:EMPTY:EMPTY",
     "date": "2026-10-17", "time": "11:00", "expected_utc": "2026-10-17T18:00:00Z"},
    {"match_id": "lp:Worlds 2026 Play-In:2026-10-18:EMPTY:EMPTY",
     "date": "2026-10-18", "time": "11:00", "expected_utc": "2026-10-18T18:00:00Z"},
]

OLD_DATAVERSION = "2026.10.02.01"


def next_version(current: str, today: datetime.date) -> str:
    """Repository policy: every promotion increases dataVersion. Same UTC day
    increments the trailing NN; a new day starts at 01."""
    year, month, day, seq = (int(x) for x in current.split("."))
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

    worlds_scheduled = [
        m for m in matches
        if m["league"]["name"] == "World Championship" and m["status"] == "scheduled"
    ]
    assert len(worlds_scheduled) == 6, len(worlds_scheduled)

    lck_before = [m for m in matches if m["league"]["name"] == "LCK"]
    emea_before = [m for m in matches if m["league"]["name"] == "EMEA Masters"]
    assert len(lck_before) == 40 and len(emea_before) == 93

    # ---- locate and verify the six targets (no write yet) ----
    updated = []
    for row in AUDITED_ROWS:
        found = [m for m in worlds_scheduled if m["id"] == row["match_id"]]
        assert len(found) == 1, f"target missing or duplicated: {row['match_id']}"
        m = found[0]
        assert m["status"] == "scheduled", f"{m['id']}: status {m['status']!r}"
        assert m["scheduledAt"] is None, f"{m['id']}: scheduledAt unexpectedly non-null"
        assert m["score"] is None, f"{m['id']}: score unexpectedly non-null"
        assert m["bestOf"] == 5, f"{m['id']}: bestOf {m['bestOf']!r}"
        assert m["team1Id"] is None and m["team2Id"] is None, f"{m['id']}: team ids populated"
        provisional = m["_provisional"]
        time_raw = provisional["timeRaw"]
        assert time_raw["date"] == row["date"], f"{m['id']}: raw date drifted"
        assert time_raw["time"] == row["time"], f"{m['id']}: raw time drifted"
        assert time_raw["timezone"] == "PST", f"{m['id']}: timezone {time_raw['timezone']!r}"
        assert time_raw["dst"] == "yes", f"{m['id']}: dst {time_raw['dst']!r}"
        assert time_raw["utcConversion"] == "PENDING_TIMEZONE_REVIEW", (
            f"{m['id']}: utcConversion {time_raw['utcConversion']!r}"
        )
        assert provisional["teamSlotState"] == {"team1": "EMPTY", "team2": "EMPTY"}
        assert provisional["rpgidCount"]["nonEmpty"] == 0, f"{m['id']}: rpgid present"

        # two independent derivations must agree
        converted = normalize_local_to_utc(row["date"], row["time"], "PST", "yes")
        assert converted is not None, f"{m['id']}: curated PST conversion unavailable"
        assert converted.utc_iso == row["expected_utc"], (
            f"{m['id']}: curated conversion {converted.utc_iso} != audited {row['expected_utc']}"
        )
        updated.append((m, row, row["expected_utc"]))

    assert len(updated) == 6, len(updated)

    # ---- apply (schedule-time fields only) ----
    generated_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for m, row, expected_utc in updated:
        m["scheduledAt"] = expected_utc
        m["_provisional"]["timeRaw"]["utcConversion"] = "CONVERTED"
        m["lastUpdatedAt"] = generated_at
    data["dataVersion"] = new_version
    data["generatedAt"] = generated_at

    # ---- immutability + regression assertions (before writing) ----
    assert {m["id"] for m in data["matches"]} == match_ids_before, "match ids changed"
    assert [m for m in data["matches"] if m["league"]["name"] == "LCK"] == lck_before, "LCK changed"
    assert [m for m in data["matches"] if m["league"]["name"] == "EMEA Masters"] == emea_before, "EMEA changed"
    worlds_after = [m for m in data["matches"] if m["league"]["name"] == "World Championship"]
    assert len(worlds_after) == 6
    for m in worlds_after:
        assert m["status"] == "scheduled" and m["score"] is None, f"{m['id']}: status/score changed"
        assert m["team1Id"] is None and m["team2Id"] is None, f"{m['id']}: teams changed"
        assert m["bestOf"] == 5, f"{m['id']}: bestOf changed"
        assert m["scheduledAt"] is not None, f"{m['id']}: scheduledAt still null"
        assert m["_provisional"]["timeRaw"]["utcConversion"] == "CONVERTED"
        assert m["_provisional"]["rpgidCount"] == {"total": 5, "nonEmpty": 0}, f"{m['id']}: rpgid provenance changed"
    total_scheduled = sum(1 for m in data["matches"] if m["status"] == "scheduled")
    assert total_scheduled == 11, total_scheduled

    CANONICAL.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"dataVersion: {old_version} -> {new_version}")
    print(f"transitions: {len(updated)}/6 Worlds Play-In rows (schedule-time only)")
    print(f"generatedAt: {generated_at}")
    for m, row, expected in updated:
        print(f"  {m['id']}: {row['date']} {row['time']} PST dst=yes -> {expected}")


if __name__ == "__main__":
    main()
