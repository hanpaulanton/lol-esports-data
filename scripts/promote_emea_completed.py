"""PHASE 18-20: promote verified EMEA Masters completed matches.

Follows the PHASE 18-12/18-15 promotion philosophy: fail-closed assertions,
deterministic ids, exact verified mappings only, no synthetic rpgid.

Evidence (PHASE 18-20):
- completed rows come from the in-repo fixture
  raw/leaguepedia/page_EMEA_Masters_2026_Summer_Main_Event.wikitext
  (64 completed rows, Round 1-4, 2026-09-26..29).
- identity: the 28 previously verified mappings + 4 newly verified
  representations (KCB via cargo documented alias; FSK via rpgid joins;
  Anubis Gaming / White Dragons are name-form teams confirmed by the wiki's
  own game records). See config/team_mappings.json humanVerification.
- every rpgid-bearing row is cross-checked against the Scoreboards pages
  (RPGID_SCOREBOARD_MAP below, fetched 2026-10-01): the row's two verified
  team names must equal the scoreboard pair (order-insensitive). The
  forfeit row has no games/rpgids by nature and is included per approved
  decision (score 1:0, winner consistent).
- scheduledAt conversion reuses the existing curated PST entry
  (PST + dst=yes -> UTC-07:00, PHASE 18-14/18-15 verified).
"""

from __future__ import annotations

import datetime
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.completed_normalize import collect_completed_series  # noqa: E402
from lib.series_score import TeamIdentityResolver  # noqa: E402
from lib.timezones import normalize_local_to_utc  # noqa: E402

CANONICAL = ROOT / "data" / "matches.json"
FIXTURE = ROOT / "raw" / "leaguepedia" / "page_EMEA_Masters_2026_Summer_Main_Event.wikitext"
SOURCE_REF = "raw/leaguepedia/page_EMEA_Masters_2026_Summer_Main_Event.wikitext"
LEAGUE_META = {"id": "EM", "name": "EMEA Masters", "region": "EU"}

OLD_DATAVERSION = "2026.10.01.02"
NEW_DATAVERSION = "2026.10.01.03"

# (schedule code / name form, verified full name, canonical id)
VERIFIED_NEW_TEAMS = [
    ("KCB", "Karmine Corp Blue", "team-kcb"),
    ("FSK", "Forsaken (Polish Team)", "team-fsk"),
    ("Anubis Gaming", "Anubis Gaming", "team-anubis-gaming"),
    ("White Dragons", "White Dragons", "team-white-dragons"),
]

# Scoreboards evidence fetched 2026-10-01 (read-only): rpgid -> [team1, team2]
# full names as recorded by the wiki's own game pages.
RPGID_SCOREBOARD_MAP = {
    "LOLTMNT05_223266": ["Berlin International Gaming", "Frites Esports Club"],
    "LOLTMNT05_223267": ["JSK Esports", "Barça eSports"],
    "LOLTMNT05_223269": ["TLN Pirates", "Magaza Esports"],
    "LOLTMNT05_223276": ["Forsaken (Polish Team)", "G2 NORD"],
    "LOLTMNT05_223279": ["Nightbirds", "Otter Side"],
    "LOLTMNT05_223284": ["The Secret Club", "Anubis Gaming"],
    "LOLTMNT05_223285": ["Gamespace Mediterranean College Esports", "Bomba Team"],
    "LOLTMNT05_223358": ["Bomba Team", "TLN Pirates"],
    "LOLTMNT05_223360": ["G2 NORD", "Nightbirds"],
    "LOLTMNT05_223370": ["LODIS (Polish Team)", "Frites Esports Club"],
    "LOLTMNT05_223377": ["UCAM Esports", "Karmine Corp Blue"],
    "LOLTMNT05_223385": ["Valerion", "Berlin International Gaming"],
    "LOLTMNT05_223390": ["Gamespace Mediterranean College Esports", "Magaza Esports"],
    "LOLTMNT05_223394": ["Bushido Wildcats", "eSuba"],
    "LOLTMNT05_223396": ["White Dragons", "HMBLE"],
    "LOLTMNT05_223441": ["UCAM Esports", "PCIFIC Esports"],
    "LOLTMNT05_223442": ["G2 NORD", "Frites Esports Club"],
    "LOLTMNT05_223446": ["Senshi eSports (Benelux Team)", "Kaufland Hangry Knights"],
    "LOLTMNT05_223449": ["JSK Esports", "TLN Pirates"],
    "LOLTMNT05_223452": ["Team Phantasma", "Otter Side"],
    "LOLTMNT05_223461": ["Berlin International Gaming", "Magaza Esports"],
    "LOLTMNT05_223464": ["Karmine Corp Blue", "Nightbirds"],
    "LOLTMNT05_223470": ["Colossal Gaming", "White Dragons"],
    "LOLTMNT05_223472": ["Unicorns of Love Sexy Edition", "HMBLE"],
    "LOLTMNT05_223481": ["Forsaken (Polish Team)", "Barça eSports"],
    "LOLTMNT05_225262": ["Colossal Gaming", "Skillcamp"],
    "LOLTMNT05_225263": ["Valerion", "LODIS (Polish Team)"],
    "LOLTMNT05_225270": ["Ruddy Corporation", "Kaufland Hangry Knights"],
    "LOLTMNT05_225271": ["UCAM Esports", "HMBLE"],
    "LOLTMNT05_225273": ["Senshi eSports (Benelux Team)", "Bushido Wildcats"],
    "LOLTMNT05_225304": ["eSuba", "Team Heretics Academy"],
    "LOLTMNT05_225307": ["Team Phantasma", "SU Esports"],
    "LOLTMNT05_225313": ["Unicorns of Love Sexy Edition", "PCIFIC Esports"],
    "LOLTMNT05_225368": ["Ruddy Corporation", "Colossal Gaming"],
    "LOLTMNT05_225369": ["Senshi eSports (Benelux Team)", "Team Heretics Academy"],
    "LOLTMNT05_225372": ["Team Phantasma", "Barça eSports"],
    "LOLTMNT05_225373": ["Kaufland Hangry Knights", "Skillcamp"],
    "LOLTMNT05_225376": ["JSK Esports", "SU Esports"],
    "LOLTMNT05_225380": ["The Secret Club", "PCIFIC Esports"],
    "LOLTMNT05_225383": ["Forsaken (Polish Team)", "Otter Side"],
    "LOLTMNT05_225389": ["Unicorns of Love Sexy Edition", "Anubis Gaming"],
    "LOLTMNT05_225423": ["Anubis Gaming", "Skillcamp"],
    "LOLTMNT05_225424": ["LODIS (Polish Team)", "eSuba"],
    "LOLTMNT05_225430": ["Bomba Team", "SU Esports"],
    "LOLTMNT05_225449": ["Valerion", "Team Heretics Academy"],
    "LOLTMNT05_225454": ["Ruddy Corporation", "Bushido Wildcats"],
    "LOLTMNT05_225455": ["Gamespace Mediterranean College Esports", "The Secret Club"],
    "LOLTMNT05_226015": ["Ruddy Corporation", "G2 NORD"],
    "LOLTMNT05_226016": ["Colossal Gaming", "SU Esports"],
    "LOLTMNT05_226017": ["Gamespace Mediterranean College Esports", "Frites Esports Club"],
    "LOLTMNT05_226026": ["Team Phantasma", "LODIS (Polish Team)"],
    "LOLTMNT05_226040": ["eSuba", "White Dragons"],
    "LOLTMNT05_226041": ["Anubis Gaming", "TLN Pirates"],
    "LOLTMNT05_226042": ["Team Heretics Academy", "Karmine Corp Blue"],
    "LOLTMNT05_226043": ["The Secret Club", "Forsaken (Polish Team)"],
    "LOLTMNT05_226045": ["Forsaken (Polish Team)", "The Secret Club"],
    "LOLTMNT05_227030": ["Magaza Esports", "Barça eSports"],
    "LOLTMNT05_227031": ["Valerion", "Skillcamp"],
    "LOLTMNT05_227036": ["Unicorns of Love Sexy Edition", "JSK Esports"],
    "LOLTMNT05_227037": ["Bomba Team", "Berlin International Gaming"],
    "LOLTMNT05_227041": ["PCIFIC Esports", "Nightbirds"],
    "LOLTMNT05_227043": ["Otter Side", "Kaufland Hangry Knights"],
    "LOLTMNT05_227044": ["Senshi eSports (Benelux Team)", "HMBLE"],
    "LOLTMNT05_227045": ["Bushido Wildcats", "UCAM Esports"],
    "LOLTMNT05_227056": ["The Secret Club", "Forsaken (Polish Team)"],
    "LOLTMNT05_227057": ["eSuba", "White Dragons"],
    "LOLTMNT05_227058": ["Anubis Gaming", "TLN Pirates"],
    "LOLTMNT05_227059": ["Team Heretics Academy", "Karmine Corp Blue"],
    "LOLTMNT05_227061": ["Team Heretics Academy", "Karmine Corp Blue"],
}


def main() -> None:
    data = json.loads(CANONICAL.read_text(encoding="utf-8"))

    # ---- fail-closed preconditions ----
    assert data.get("schemaVersion") == 1
    assert data.get("dataVersion") == OLD_DATAVERSION, data.get("dataVersion")
    existing_teams = data["teams"]
    assert len(existing_teams) == 38, len(existing_teams)
    existing_ids = {t["id"] for t in existing_teams}
    matches = data["matches"]
    assert len(matches) == 75, len(matches)
    match_ids_before = {m["id"] for m in matches}
    lck_before = [m for m in matches if m["league"]["name"] == "LCK"]
    worlds_before = [m for m in matches if m["league"]["name"] == "World Championship"]
    emea_scheduled_before = [
        m for m in matches
        if m["league"]["name"] == "EMEA Masters" and m["status"] == "scheduled"
    ]
    assert len(lck_before) == 40 and len(worlds_before) == 6 and len(emea_scheduled_before) == 29

    # shortName -> canonical name (existing teams) + new verified teams,
    # used to verify each row against the Scoreboards evidence.
    short_to_name = {t["shortName"]: t["name"] for t in existing_teams}
    name_to_id = {t["name"]: t["id"] for t in existing_teams}
    for code, name, team_id in VERIFIED_NEW_TEAMS:
        assert team_id not in existing_ids, team_id
        assert name not in name_to_id, name
        short_to_name[code] = name
        name_to_id[name] = team_id
    code_to_id = {t["shortName"]: t["id"] for t in existing_teams}
    for code, name, team_id in VERIFIED_NEW_TEAMS:
        code_to_id[code] = team_id

    resolver = TeamIdentityResolver()

    # ---- normalize + verify completed rows ----
    series_list = collect_completed_series(FIXTURE.read_text(encoding="utf-8"))
    promoted, excluded = [], []
    seen_ids = set(match_ids_before)
    generated_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for s in series_list:
        t1_raw, t2_raw = s["team1"], s["team2"]
        row_label = f"{s['date']} {t1_raw} vs {t2_raw}"

        # identity via resolver + verified map (fail-closed)
        ids, names, row_problems = {}, {}, []
        ok = True
        for side, raw in (("team1", t1_raw), ("team2", t2_raw)):
            resolved = resolver.resolve(raw)
            if resolved.status.name != "RESOLVED":
                ok = False
                row_problems.append(f"unresolved identity {raw!r}")
                continue
            team_id = code_to_id.get(resolved.canonical)
            team_name = short_to_name.get(resolved.canonical)
            for code, name, tid in VERIFIED_NEW_TEAMS:
                if resolved.canonical == code:
                    team_id, team_name = tid, name
            if team_id is None or team_name is None:
                ok = False
                row_problems.append(f"no verified canonical id for {raw!r} ({resolved.canonical!r})")
                continue
            ids[side] = team_id
            names[side] = team_name
        if not ok:
            excluded.append({"row": row_label, "reason": "; ".join(row_problems)})
            continue
        if ids["team1"] == ids["team2"]:
            excluded.append({"row": row_label, "reason": "both slots resolve to one team"})
            continue

        # scores / winner (fail-closed)
        s1, s2 = s["team1score"], s["team2score"]
        if not (s1.isdigit() and s2.isdigit()) or int(s1) == int(s2):
            excluded.append({"row": row_label, "reason": f"incomplete or tied score {s1}:{s2}"})
            continue
        winner = s["winner"]
        expected = "1" if int(s1) > int(s2) else "2"
        if winner and winner != expected:
            excluded.append({"row": row_label, "reason": f"winner {winner!r} contradicts score {s1}:{s2}"})
            continue

        # bestOf hierarchy (row-level > Start-level)
        best_of_source = "row-level bestof" if s["bestof"] else "start-level bestof"
        best_of = int(s["bestof"]) if s["bestof"] else int(s["context"]["bestof"] or 0)
        if best_of <= 0:
            excluded.append({"row": row_label, "reason": "no usable bestOf"})
            continue

        # scheduledAt via the existing curated timezone logic
        result = normalize_local_to_utc(s["date"], s["time"], s["timezone"], s["dst"])
        if result is None:
            excluded.append({"row": row_label, "reason": f"timezone {s['timezone']!r} not curated (fail-closed)"})
            continue

        # rpgid cross-check against Scoreboards evidence (order-insensitive)
        rpgids = [
            (g.get("riot_platform_game_id") or "").strip()
            for g in s["games"]
            if (g.get("riot_platform_game_id") or "").strip()
        ]
        verified_names = {names["team1"], names["team2"]}
        row_ok = True
        for rpgid in rpgids:
            sb = RPGID_SCOREBOARD_MAP.get(rpgid)
            if sb is None:
                excluded.append({"row": row_label, "reason": f"rpgid {rpgid} not found in Scoreboards evidence"})
                row_ok = False
                break
            if set(sb) != verified_names:
                excluded.append({
                    "row": row_label,
                    "reason": f"rpgid {rpgid} scoreboard pair {sb} != verified teams {sorted(verified_names)}",
                })
                row_ok = False
                break
        if not row_ok:
            continue

        match_id = f"lp:{s['context']['shownname']}:{s['date']}:{t1_raw}:{t2_raw}"
        if match_id in seen_ids:
            excluded.append({"row": row_label, "reason": f"duplicate match id {match_id}"})
            continue
        seen_ids.add(match_id)

        promoted.append({
            "id": match_id,
            "league": dict(LEAGUE_META),
            "tournament": {"id": s["context"]["shownname"], "name": s["context"]["shownname"]},
            "stage": {"id": s["context"]["tab"], "name": s["context"]["tab"]},
            "team1Id": ids["team1"],
            "team2Id": ids["team2"],
            "scheduledAt": result.utc_iso,
            "status": "completed",
            "bestOf": best_of,
            "score": {"team1": int(s1), "team2": int(s2)},
            "lastUpdatedAt": generated_at,
            "sources": [{"source": "leaguepedia", "kind": "raw_fixture", "ref": SOURCE_REF}],
            "_provisional": {
                "teamIdSource": "leaguepedia raw value (exact resolver + verified promotion map)",
                "teamSlotRaw": {"team1": t1_raw, "team2": t2_raw},
                "rpgidCount": {"total": len(s["games"]), "nonEmpty": len(rpgids)},
                "bestOfSource": best_of_source,
                "timeRaw": {
                    "date": s["date"], "time": s["time"], "timezone": s["timezone"],
                    "dst": s["dst"], "utcConversion": "CONVERTED",
                },
            },
        })

    # ---- new teams ----
    new_teams = [
        {"id": tid, "name": name, "shortName": code, "region": "EMEA", "aliases": [code, name]}
        for code, name, tid in VERIFIED_NEW_TEAMS
    ]

    # ---- post-assertions ----
    ids_all = [t["id"] for t in existing_teams] + [t["id"] for t in new_teams]
    assert len(ids_all) == len(set(ids_all)) == 42, "team id uniqueness broken"
    names_all = [t["name"] for t in existing_teams] + [t["name"] for t in new_teams]
    assert len(names_all) == len(set(names_all)), "duplicate team names"
    promoted_ids = {m["id"] for m in promoted}
    assert len(promoted_ids) == len(promoted), "duplicate promoted match ids"
    assert not (promoted_ids & match_ids_before), "promoted id collides with existing"

    # ---- apply ----
    data["matches"].extend(promoted)
    data["teams"].extend(new_teams)
    data["dataVersion"] = NEW_DATAVERSION
    data["generatedAt"] = generated_at

    # LCK / Worlds / existing EMEA scheduled rows must be byte-identical
    lck_after = [m for m in data["matches"] if m["league"]["name"] == "LCK"]
    worlds_after = [m for m in data["matches"] if m["league"]["name"] == "World Championship"]
    emea_sched_after = [
        m for m in data["matches"]
        if m["league"]["name"] == "EMEA Masters" and m["status"] == "scheduled"
    ]
    assert lck_after == lck_before, "LCK rows changed"
    assert worlds_after == worlds_before, "Worlds rows changed"
    assert emea_sched_after == emea_scheduled_before, "EMEA scheduled rows changed"
    for m in worlds_after:
        assert m["scheduledAt"] is None and m["team1Id"] is None and m["team2Id"] is None

    CANONICAL.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"dataVersion: {OLD_DATAVERSION} -> {NEW_DATAVERSION}")
    print(f"completed promoted: {len(promoted)} | excluded: {len(excluded)}")
    print(f"matches: 75 -> {len(data['matches'])} | teams: 38 -> {len(data['teams'])}")
    for e in excluded:
        print(f"  EXCLUDED {e['row']}: {e['reason']}")
    best_of_counts = {}
    for m in promoted:
        best_of_counts[m["bestOf"]] = best_of_counts.get(m["bestOf"], 0) + 1
    print("promoted bestOf distribution:", best_of_counts)
    print("sample:", json.dumps(promoted[0], ensure_ascii=False)[:240])


if __name__ == "__main__":
    main()
