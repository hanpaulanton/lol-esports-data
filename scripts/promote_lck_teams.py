"""PHASE 18-12: canonical LCK team identity promotion.

Adds verified LCK Team objects to the canonical envelope's `teams` array.
Evidence chain (all PHASE 18-1 game-id verified, CONFLICT 0):
    Leaguepedia code -> verified full name -> canonical Team.id

ID policy (user-approved mixed strategy, handoff section 3 + 7/13 reconciliation):
- Where an existing Android canonical id exists (SampleData), reuse it:
  T1 -> team-t1, GEN -> team-geng, HLE -> team-hle, DPLUS -> team-dk.
- Where none exists, a deterministic id `team-<lowercased leaguepedia code>`
  is introduced (team-kt, team-krx, team-ns, team-dn-soopers,
  team-bnk-fearx, team-hanjn-brion). No guesswork: ids are derived from the
  verified code, never from name similarity.

Team fields (Android Team model contract):
- id/name/shortName/region/aliases. name = fixture-authoritative full name.
- shortName = the Leaguepedia code itself (the only verified short form).
- aliases = the verified alternative spellings observed in this repository
  only (Leaguepedia code + humanProvidedCode where registered + name).
No logos/images/URLs/unverified aliases.

matches: unchanged 75 records. EMEA unresolved identities: untouched.
"""

from __future__ import annotations

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "data" / "matches.json"

# (leaguepedia code, verified full name, existing Android id or None)
VERIFIED_LCK_TEAMS = [
    ("T1", "T1", "team-t1"),
    ("GEN", "Gen.G", "team-geng"),
    ("KT", "KT Rolster", None),
    ("HLE", "Hanwha Life Esports", "team-hle"),
    ("DPLUS", "Dplus Kia", "team-dk"),
    ("KRX", "Kiwoom DRX", None),
    ("NS", "Nongshim RedForce", None),
    ("DN SOOPers", "DN SOOPers", None),
    ("BNK FEARX", "BNK FEARX", None),
    ("HANJIN BRION", "HANJIN BRION", None),
]


def build_teams() -> list[dict]:
    teams = []
    for code, name, existing_id in VERIFIED_LCK_TEAMS:
        team_id = existing_id if existing_id else "team-" + code.lower().replace(" ", "-")
        aliases = [code]
        if code != name:
            aliases.append(name)
        aliases = list(dict.fromkeys(aliases))  # dedupe, keep order
        teams.append(
            {
                "id": team_id,
                "name": name,
                "shortName": code,
                "region": "KR",
                "aliases": aliases,
            }
        )
    return teams


def main() -> None:
    data = json.loads(CANONICAL.read_text(encoding="utf-8"))

    assert data.get("teams") == [], "teams array is not empty: refusing blind merge"
    codes_in_matches = set()
    for m in data["matches"]:
        if m["status"] == "completed":
            codes_in_matches.add(m["team1Id"])
            codes_in_matches.add(m["team2Id"])
    expected = {code for code, _, _ in VERIFIED_LCK_TEAMS}
    assert codes_in_matches == expected, f"completed code set mismatch: {codes_in_matches ^ expected}"

    data["teams"] = build_teams()

    ids = [t["id"] for t in data["teams"]]
    assert len(ids) == len(set(ids)), "duplicate team ids"
    names = [t["name"] for t in data["teams"]]
    assert len(names) == len(set(names)), "duplicate team names"

    # every completed LCK reference must resolve to a promoted team id
    id_set = set(ids)
    # provisional raw values for LCK equal the codes; completed team1Id/team2Id
    # are the codes themselves, so map code -> canonical id and rewrite refs.
    code_to_id = {}
    for code, name, existing_id in VERIFIED_LCK_TEAMS:
        code_to_id[code] = existing_id if existing_id else "team-" + code.lower().replace(" ", "-")
    rewritten = 0
    for m in data["matches"]:
        if m["status"] == "completed":
            if m["team1Id"] in code_to_id:
                m["team1Id"] = code_to_id[m["team1Id"]]
                rewritten += 1
            if m["team2Id"] in code_to_id:
                m["team2Id"] = code_to_id[m["team2Id"]]
                rewritten += 1
    print(f"completed match team references rewritten to canonical ids: {rewritten}")

    CANONICAL.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"teams promoted: {len(data['teams'])}")
    for t in data["teams"]:
        print(f"  {t['id']}: {t['name']} ({t['shortName']}) aliases={t['aliases']}")


if __name__ == "__main__":
    main()
