"""PHASE 18-15: promote verified EMEA Masters identities + scheduled UTC times.

Follows the PHASE 18-12 promotion philosophy (promote_lck_teams.py):
fail-closed assertions, deterministic ids, exact verified mappings only.

Evidence: PHASE 18-14 research (docs team-identity research + RESEARCH REPORT):
- 28 schedule code -> full-name mappings, riot_platform_game_id joins vs
  Scoreboards pages (63 matched games, side-aware), CONFLICT 0.
- 'PST' + dst=yes on these rows means PDT (UTC-07:00), verified with the same
  63 same-game pairs. Conversion is performed by the generic
  lib.timezones.normalize_local_to_utc using config/timezone_offsets.json —
  no offsets are hardcoded here.

Changes to data/matches.json (everything else untouched):
- 29 EMEA scheduled rows: scheduledAt filled (UTC), _provisional.timeRaw
  preserved with utcConversion -> CONVERTED_VIA_CURATED_TIMEZONE,
  lastUpdatedAt refreshed. Match ids unchanged.
- 14 KNOWN rows: team1Id/team2Id rewritten from raw schedule codes to
  deterministic canonical ids (team-<code>), identityStatus -> RESOLVED,
  canonicalTeamId filled. _provisional.teamSlotRaw keeps the raw codes.
- 15 TBD rows: team slots stay null/TBD (only the time is converted).
- envelope teams: 10 -> 38 (28 new EMEA teams, aliases=[code, name]).
- dataVersion 2026.10.01.01 -> 2026.10.01.02, generatedAt refreshed.

Worlds rows and all completed LCK rows are untouched (asserted).
"""

from __future__ import annotations

import datetime
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.timezones import normalize_local_to_utc  # noqa: E402
from scheduled_normalize import CONVERTED_TZ  # noqa: E402

CANONICAL = ROOT / "data" / "matches.json"

# (schedule code, verified full name) — PHASE 18-14 VERIFIED, exact only.
VERIFIED_EMEA = [
    ("BIG", "Berlin International Gaming"),
    ("SNSH", "Senshi eSports (Benelux Team)"),
    ("Bushido Wildcats", "Bushido Wildcats"),
    ("Magaza", "Magaza Esports"),
    ("FEC", "Frites Esports Club"),
    ("Otter Side", "Otter Side"),
    ("PCIFIC Esports", "PCIFIC Esports"),
    ("Ruddy Corporation", "Ruddy Corporation"),
    ("JSK Esports", "JSK Esports"),
    ("Skillcamp", "Skillcamp"),
    ("Colossal Gaming", "Colossal Gaming"),
    ("LODIS PL", "LODIS (Polish Team)"),
    ("TLN Pirates", "TLN Pirates"),
    ("Valerion", "Valerion"),
    ("KHK", "Kaufland Hangry Knights"),
    ("UOL.SE", "Unicorns of Love Sexy Edition"),
    ("HMBLE", "HMBLE"),
    ("Barca", "Barça eSports"),
    ("ESB", "eSuba"),
    ("UCAM Esports", "UCAM Esports"),
    ("G2 NORD", "G2 NORD"),
    ("Bomba Team", "Bomba Team"),
    ("HRTS.A", "Team Heretics Academy"),
    ("Nightbirds", "Nightbirds"),
    ("Phantasma", "Team Phantasma"),
    ("GMCE", "Gamespace Mediterranean College Esports"),
    ("TSC HR", "The Secret Club"),
    ("SU Esports", "SU Esports"),
]

OLD_DATAVERSION = "2026.10.01.01"
NEW_DATAVERSION = "2026.10.01.02"
# the success-path vocabulary already defined by the existing normalizer
CONVERTED = CONVERTED_TZ


def slug(code: str) -> str:
    # PHASE 18-12 convention (team-<lowercased code>), extended with the same
    # deterministic rule for dots so UOL.SE / HRTS.A stay unambiguous.
    return "team-" + code.lower().replace(" ", "-").replace(".", "-")


def build_teams() -> list[dict]:
    teams = []
    for code, name in VERIFIED_EMEA:
        aliases = [code]
        if name != code:
            aliases.append(name)
        teams.append(
            {
                "id": slug(code),
                "name": name,
                "shortName": code,
                "region": "EMEA",
                "aliases": aliases,
            }
        )
    return teams


def main() -> None:
    data = json.loads(CANONICAL.read_text(encoding="utf-8"))

    # ---- fail-closed preconditions (before ANY mutation) ----
    assert data.get("schemaVersion") == 1, "unexpected schemaVersion"
    assert data.get("dataVersion") == OLD_DATAVERSION, f"unexpected dataVersion: {data.get('dataVersion')}"

    existing_teams = data["teams"]
    assert len(existing_teams) == 10, f"expected 10 canonical teams, got {len(existing_teams)}"
    existing_ids = {t["id"] for t in existing_teams}
    assert len(existing_ids) == 10

    new_ids = [slug(code) for code, _ in VERIFIED_EMEA]
    assert len(set(new_ids)) == 28, "deterministic id collision among EMEA codes"
    assert not existing_ids & set(new_ids), "EMEA id collides with an existing canonical id"
    names = [name for _, name in VERIFIED_EMEA]
    assert len(set(names)) == 28, "duplicate verified full names"
    assert len({code for code, _ in VERIFIED_EMEA}) == 28, "duplicate schedule codes"

    matches = data["matches"]
    assert len(matches) == 75, f"expected 75 matches, got {len(matches)}"
    match_ids_before = {m["id"] for m in matches}
    assert len(match_ids_before) == 75

    completed_lck = [
        m for m in matches if m["status"] == "completed" and m["league"]["name"] == "LCK"
    ]
    assert len(completed_lck) == 40, "unexpected completed LCK count"

    worlds = [m for m in matches if m["league"]["name"] == "World Championship"]
    assert len(worlds) == 6, "unexpected Worlds row count"
    for m in worlds:
        assert m["status"] == "scheduled" and m["scheduledAt"] is None
        assert m["team1Id"] is None and m["team2Id"] is None, "Worlds rows must stay unresolved"

    emea = [m for m in matches if m["league"]["name"] == "EMEA Masters"]
    assert len(emea) == 29, f"expected 29 EMEA scheduled rows, got {len(emea)}"
    known = []
    tbd = []
    for m in emea:
        slots = m["_provisional"]["teamSlotState"]
        if slots["team1"] == "KNOWN" and slots["team2"] == "KNOWN":
            known.append(m)
        else:
            assert slots == {"team1": "TBD", "team2": "TBD"}, f"unexpected slot state: {slots}"
            assert m["team1Id"] is None and m["team2Id"] is None
            tbd.append(m)
    assert len(known) == 14, f"expected 14 KNOWN rows, got {len(known)}"
    assert len(tbd) == 15, f"expected 15 TBD rows, got {len(tbd)}"

    code_to_id = {code: slug(code) for code, _ in VERIFIED_EMEA}
    raw_codes_in_rows = set()
    for m in known:
        raw_codes_in_rows.add(m["team1Id"])
        raw_codes_in_rows.add(m["team2Id"])
    assert raw_codes_in_rows == set(code_to_id), (
        "schedule codes in rows do not match the verified set: "
        f"{raw_codes_in_rows ^ set(code_to_id)}"
    )

    # ---- conversion (generic pipeline function, curated config) ----
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for m in emea:
        raw = m["_provisional"]["timeRaw"]
        assert raw["timezone"] == "PST" and raw["dst"] == "yes", f"unexpected timeRaw: {raw}"
        result = normalize_local_to_utc(raw["date"], raw["time"], raw["timezone"], raw["dst"])
        assert result is not None, f"PST must be curated before promotion (row {m['id']})"
        m["scheduledAt"] = result.utc_iso
        m["_provisional"]["timeRaw"]["utcConversion"] = CONVERTED
        m["lastUpdatedAt"] = now

    # ---- team reference rewrite (KNOWN rows only) ----
    for m in known:
        for side in ("team1", "team2"):
            raw = m[f"{side}Id"]
            m[f"{side}Id"] = code_to_id[raw]
            m["_provisional"]["identityStatus"][side] = "RESOLVED"
            m["_provisional"]["canonicalTeamId"][side] = code_to_id[raw]

    # ---- canonical teams promotion ----
    data["teams"].extend(build_teams())
    ids = [t["id"] for t in data["teams"]]
    assert len(ids) == len(set(ids)) == 38, "team id uniqueness broken"
    team_names = [t["name"] for t in data["teams"]]
    assert len(team_names) == len(set(team_names)), "duplicate team names"

    # ---- envelope ----
    data["dataVersion"] = NEW_DATAVERSION
    data["generatedAt"] = now

    # ---- post-conditions ----
    assert {m["id"] for m in data["matches"]} == match_ids_before, "match ids changed"
    for m in data["matches"]:
        if m["status"] == "scheduled":
            assert m["score"] is None, f"scheduled score not null: {m['id']}"
            assert m["scheduledAt"] is None or m["scheduledAt"].endswith("Z")
    for m in worlds:
        assert m["scheduledAt"] is None and m["team1Id"] is None and m["team2Id"] is None

    CANONICAL.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"dataVersion: {OLD_DATAVERSION} -> {NEW_DATAVERSION}")
    print(f"EMEA rows converted: {len(emea)} (KNOWN {len(known)}, TBD {len(tbd)})")
    sample = known[0]
    print(f"sample: {sample['id']}")
    print(f"  team1Id: {sample['team1Id']} | team2Id: {sample['team2Id']} | scheduledAt: {sample['scheduledAt']}")
    print(f"teams: 10 -> {len(data['teams'])}")
    for t in data["teams"][10:13]:
        print(f"  + {t['id']}: {t['name']} ({t['shortName']}) aliases={t['aliases']}")
    print("  ...")


if __name__ == "__main__":
    main()
