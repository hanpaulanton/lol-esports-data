"""PHASE 18-2 — Scheduled Match Schema Investigation (offline, read-only).

Investigates EVERY {{MatchSchedule}} template in the saved Data fixture using
the balanced template parser, extracts ALL template arguments (including game
templates), attaches MatchSchedule/Start context, classifies each series
strictly by observed structural evidence, and writes a machine-readable result
used for docs/scheduled-match-schema.md.

Classification rules (strict):
- COMPLETED: numeric winner AND numeric team1score AND numeric team2score are
  all present in the template args (the only completion pattern observed).
- SCHEDULED_CANDIDATE: requires structural upcoming evidence OTHER than the
  absence of score/winner (e.g. an explicit scheduling marker argument).
  Absence of score/winner alone is NOT sufficient.
- UNKNOWN: everything else.
"""

from __future__ import annotations

import json
import pathlib
import sys
from collections import Counter, defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.leaguepedia_parser import (  # noqa: E402
    find_nested_by_name,
    find_templates,
)

RAW = ROOT / "raw" / "leaguepedia"
DATA_PAGE = RAW / "page_data_lck_rounds34.wikitext"
TOURN_PAGE = RAW / "page_lck_rounds34.wikitext"
SCORE_PAGE = RAW / "page_lck_scoreboards.wikitext"


def to_int(value: str | None):
    value = (value or "").strip()
    if value.isdigit():
        return int(value)
    return None


def collect_series(wikitext: str):
    """Yield series dicts in document order with Start context and offsets."""
    results = []
    context = None
    context_start = None
    series_index = 0
    for t in find_templates(wikitext):
        if t.name == "MatchSchedule/Start":
            context = {
                "tab": (t.args.named.get("tab") or "").strip(),
                "bestof": (t.args.named.get("bestof") or "").strip(),
                "shownname": (t.args.named.get("shownname") or "").strip(),
                "raw": t.raw,
                "start": t.start,
            }
            context_start = t.start
            results.append({"kind": "start", "context": context, "start": t.start, "end": t.end})
        elif t.name == "MatchSchedule":
            series_index += 1
            games = []
            for arg_key, arg_value in t.args.named.items():
                if not arg_key.lower().startswith("game"):
                    continue
                for g in find_nested_by_name(arg_value, "MatchSchedule/Game"):
                    games.append({
                        "argKey": arg_key,
                        "args": {k: v.strip() for k, v in g.args.named.items()},
                        "positional": [p.strip() for p in g.args.positional],
                    })
            results.append({
                "kind": "series",
                "index": series_index,
                "context": dict(context or {}),
                "contextStart": context_start,
                "start": t.start,
                "end": t.end,
                "args": {k: v.strip() for k, v in t.args.named.items()},
                "positional": [p.strip() for p in t.args.positional],
                "games": games,
            })
    return results


def main() -> int:
    data_text = DATA_PAGE.read_text(encoding="utf-8")
    items = collect_series(data_text)
    series = [it for it in items if it["kind"] == "series"]
    starts = [it for it in items if it["kind"] == "start"]

    # ---- tournament page / scoreboards page: MatchSchedule presence check ----
    tourn_page = TOURN_PAGE.read_text(encoding="utf-8")
    tourn_matchschedule = [t.name for t in find_templates(tourn_page) if t.name == "MatchSchedule"]
    score_matchschedule = [t.name for t in find_templates(SCORE_PAGE.read_text(encoding="utf-8")) if t.name == "MatchSchedule"]

    # ---- classification + per-series findings ----
    completed, candidates, unknown = [], [], []
    arg_key_freq: Counter = Counter()
    game_arg_key_freq: Counter = Counter()
    games_missing_rpgid: list[str] = []
    duplicate_rpgids: dict[str, int] = defaultdict(int)
    played_sums = []
    game_counts = []
    per_series_rows = []

    for s in series:
        args = s["args"]
        arg_key_freq.update(args.keys())
        winner = to_int(args.get("winner"))
        s1 = to_int(args.get("team1score"))
        s2 = to_int(args.get("team2score"))
        game_count = len(s["games"])
        game_counts.append(game_count)
        rpgids = [g["args"].get("riot_platform_game_id", "") for g in s["games"]]
        rpgid_present = sum(1 for r in rpgids if r)
        for rid in rpgids:
            if rid:
                duplicate_rpgids[rid] += 1
            else:
                games_missing_rpgid.append(f"series[{s['index']}] ({args.get('team1')} vs {args.get('team2')}) game arg")
        played = (s1 + s2) if (s1 is not None and s2 is not None) else None
        if played is not None:
            played_sums.append(played)

        problems = []
        is_completed = winner is not None and s1 is not None and s2 is not None
        classification = "UNKNOWN"
        evidence = []
        if is_completed:
            classification = "COMPLETED"
            evidence.append(f"numeric winner={winner}, team1score={s1}, team2score={s2} observed in template args")
            evidence.append(f"{game_count} MatchSchedule/Game template(s) nested; rpgid present in {rpgid_present}")
        else:
            # structural upcoming evidence other than missing score/winner?
            structural_markers = [
                k for k in args
                if k.lower() in ("scheduled", "upcoming", "prematch") or "예정" in args[k]
            ]
            if structural_markers:
                classification = "SCHEDULED_CANDIDATE"
                evidence.append(f"explicit scheduling marker args: {structural_markers}")
            else:
                problems.append("no score/winner present AND no structural scheduling marker in template args")
                classification = "UNKNOWN"

        row = {
            "index": s["index"],
            "sourceFile": "raw/leaguepedia/page_data_lck_rounds34.wikitext",
            "charOffset": s["start"],
            "contextTab": s["context"].get("tab"),
            "contextBestOf": s["context"].get("bestof"),
            "team1": args.get("team1"),
            "team2": args.get("team2"),
            "team1score": args.get("team1score"),
            "team2score": args.get("team2score"),
            "winner": args.get("winner"),
            "date": args.get("date"),
            "time": args.get("time"),
            "timezone": args.get("timezone"),
            "dst": args.get("dst"),
            "gameCount": game_count,
            "rpgidPresent": rpgid_present,
            "classification": classification,
            "evidence": evidence,
            "problems": problems,
            "allArgs": args,
        }
        if classification == "COMPLETED":
            completed.append(row)
        elif classification == "SCHEDULED_CANDIDATE":
            candidates.append(row)
        else:
            unknown.append(row)
        per_series_rows.append(row)

    for g in [g for s in series for g in s["games"]]:
        game_arg_key_freq.update(g["args"].keys())

    summary = {
        "rawFilesExamined": sorted(p.name for p in RAW.glob("*")),
        "matchScheduleTotal": len(series),
        "startTotal": len(starts),
        "completed": len(completed),
        "scheduledCandidate": len(candidates),
        "unknown": len(unknown),
        "seriesLevelBestofArgObserved": sum(1 for s in series if any("bestof" in k.lower() for k in s["args"])),
        "startBestofValues": [s["context"].get("bestof") for s in starts],
        "seriesPerStart": {
            it["context"].get("tab"): sum(
                1 for s in series if s["context"].get("tab") == it["context"].get("tab")
            )
            for it in starts
        },
        "playedGameSums": played_sums,
        "playedSumExceeding3": sum(1 for v in played_sums if v > 3),
        "gameCounts": game_counts,
        "gamesMissingRpgid": games_missing_rpgid,
        "duplicateRpgids": {k: v for k, v in duplicate_rpgids.items() if v > 1},
        "tournamentPageMatchScheduleCount": len(tourn_matchschedule),
        "scoreboardsPageMatchScheduleCount": len(score_matchschedule),
        "seriesArgKeyFrequency": dict(arg_key_freq),
        "gameArgKeyFrequency": dict(game_arg_key_freq),
        "rows": per_series_rows,
    }

    out_json = ROOT / "tests" / "scheduled_schema_result.json"
    out_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"MatchSchedule total: {len(series)} (tournament page: {len(tourn_matchschedule)}, scoreboards page: {len(score_matchschedule)})")
    print(f"Start blocks: {len(starts)}; series per Start: {summary['seriesPerStart']}")
    print(f"COMPLETED={len(completed)} SCHEDULED_CANDIDATE={len(candidates)} UNKNOWN={len(unknown)}")
    print(f"series-level bestof arg observed: {summary['seriesLevelBestofArgObserved']}")
    print(f"played sums: min={min(played_sums)} max={max(played_sums)}; exceeding bestof3: {summary['playedSumExceeding3']}")
    print(f"game counts per series: min={min(game_counts)} max={max(game_counts)}")
    print(f"games missing rpgid: {len(games_missing_rpgid)} {games_missing_rpgid[:3]}")
    print(f"duplicate rpgids: {summary['duplicateRpgids'] or 'none'}")
    print("series arg keys:", dict(arg_key_freq))
    print("game arg keys:", dict(game_arg_key_freq))
    print(f"saved: {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
