"""Normalize the LCK Rounds 3-4 fixture into a small PHASE 17 sample of
SERIES-LEVEL canonical records.

Reads raw/leaguepedia/page_data_lck_rounds34.wikitext, parses
{{MatchSchedule/Start}} / {{MatchSchedule}} / {{MatchSchedule/Game}} templates,
normalizes confirmed fields, writes data/matches.sample.json (explicitly
marked SAMPLE / PHASE 17 / not production), and prints a summary used for
docs/phase17-normalization-report.md.

Rules implemented (per PHASE 17 instructions):
- SERIES LEVEL only; Game templates are parsed for diagnostics, never promoted.
- status: only "completed" is mapped, and only for series that observably have
  a numeric winner plus both series scores. Anything else is excluded.
- bestOf: taken from the enclosing {{MatchSchedule/Start}} tab context ONLY when
  the context block is structurally unambiguous AND the played-game count is
  consistent with it (team1score+team2score <= bestof). Otherwise UNKNOWN.
- scheduledAt: date+time+timezone converted to UTC; only abbreviations present
  in config/timezone_offsets.json are converted, everything else is excluded.
- team ids: the observed Leaguepedia code is used as a provisional id
  (idSource: leaguepedia-team-code); canonical team IDs remain unresolved.
- ids: deterministic synthetic id "lp:<tournament>:<date>:<t1>:<t2>",
  disambiguated with an occurrence suffix when needed.
"""

from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.leaguepedia_parser import (  # noqa: E402
    Template,
    find_templates,
    find_templates_by_name,
    find_nested_by_name,
)
from lib.timezones import normalize_local_to_utc  # noqa: E402
from lib.validator import validate_match  # noqa: E402

RAW_PAGE = ROOT / "raw" / "leaguepedia" / "page_data_lck_rounds34.wikitext"
OUT_PATH = ROOT / "data" / "matches.sample.json"
MAPPING_PATH = ROOT / "config" / "team_mappings.json"

SAMPLE_TOURNAMENT = "LCK 2026 Rounds 3-4"  # the only tournament in this fixture


def _clean(value: str | None) -> str:
    return (value or "").strip()


def parse_series(t: Template, context: dict) -> dict:
    """Turn one {{MatchSchedule}} template into a raw series record."""
    series = {
        "team1": _clean(t.args.get("team1")),
        "team2": _clean(t.args.get("team2")),
        "team1score": _clean(t.args.get("team1score")),
        "team2score": _clean(t.args.get("team2score")),
        "winner": _clean(t.args.get("winner")),
        "date": _clean(t.args.get("date")),
        "time": _clean(t.args.get("time")),
        "timezone": _clean(t.args.get("timezone")),
        "dst": _clean(t.args.get("dst")),
        "initialorder": _clean(t.args.get("initialorder")),
        "context": dict(context),
        "games": [],
    }
    for arg_key, arg_value in t.args.named.items():
        if not arg_key.lower().startswith("game"):
            continue
        for game_template in find_nested_by_name(arg_value, "MatchSchedule/Game"):
            series["games"].append(dict(game_template.args.named))
    return series


def collect_series(wikitext: str) -> tuple[list[dict], list[dict]]:
    """Return (series, starts) in document order with tab context attached."""
    series: list[dict] = []
    starts: list[dict] = []
    context: dict = {}
    for template in find_templates(wikitext):
        if template.name == "MatchSchedule/Start":
            context = {
                "tab": _clean(template.args.get("tab")),
                "bestof": _clean(template.args.get("bestof")),
                "shownname": _clean(template.args.get("shownname")),
            }
            starts.append(dict(context))
        elif template.name == "MatchSchedule":
            record = parse_series(template, context)
            series.append(record)
    return series, starts


def to_int(value: str) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize(series_list: list[dict]) -> tuple[list[dict], list[dict]]:
    """Return (normalized_records, excluded_records_with_reason)."""
    with open(MAPPING_PATH, encoding="utf-8") as handle:
        mappings = json.load(handle)["mappings"]
    provisional_ids = {m["leaguepediaCode"] for m in mappings}

    normalized: list[dict] = []
    excluded: list[dict] = []

    occurrence: dict[str, int] = {}
    for series in series_list:
        problems: list[str] = []
        team1 = series["team1"]
        team2 = series["team2"]
        base_id = f"lp:{series['context'].get('shownname', SAMPLE_TOURNAMENT)}:{series['date']}:{team1}:{team2}"
        occurrence[base_id] = occurrence.get(base_id, 0) + 1
        record_id = base_id if occurrence[base_id] == 1 else f"{base_id}:{occurrence[base_id]:02d}"

        # time normalization
        time_result = normalize_local_to_utc(
            series["date"], series["time"], series["timezone"], series["dst"]
        )
        if time_result is None:
            problems.append(f"UNKNOWN timezone abbreviation: {series['timezone']!r}")        # status: completed only, and only with observable winner + scores
        winner = to_int(series["winner"])
        score1 = to_int(series["team1score"])
        score2 = to_int(series["team2score"])
        status: str | None = None
        if winner is None or score1 is None or score2 is None:
            problems.append(
                f"status UNKNOWN: missing/unparsable winner or scores "
                f"(winner={series['winner']!r}, score={series['team1score']!r}/{series['team2score']!r})"
            )
        else:
            status = "completed"

        # bestOf: tab context + played-game count consistency check
        best_of = to_int(series["context"].get("bestof", ""))
        if best_of is None:
            problems.append("UNKNOWN bestOf: enclosing MatchSchedule/Start has no numeric bestof")
        elif time_result is not None and score1 is not None and score2 is not None:
            played = score1 + score2
            if played > best_of:
                problems.append(
                    f"UNKNOWN bestOf: played games ({played}) exceed tab context bestof ({best_of})"
                )

        for code in (team1, team2):
            if code not in provisional_ids:
                problems.append(f"unmapped team code: {code!r}")

        if problems:
            excluded.append({"id": record_id, "series": series, "problems": problems})
            continue

        record_warnings = list(time_result.warnings)  # type: ignore[union-attr]

        normalized.append({
            "id": record_id,
            "league": {"id": "LCK21", "name": "LCK", "region": "KR"},
            "tournament": {"id": SAMPLE_TOURNAMENT, "name": SAMPLE_TOURNAMENT},
            "stage": {"id": "Rounds 3-4", "name": "Rounds 3-4"},
            "team1Id": team1,
            "team2Id": team2,
            "scheduledAt": time_result.utc_iso,  # type: ignore[union-attr]
            "status": status,
            "bestOf": best_of,
            "score": {"team1": score1, "team2": score2},
            "sources": [
                {
                    "source": "leaguepedia",
                    "kind": "raw_fixture",
                    "ref": "raw/leaguepedia/page_data_lck_rounds34.wikitext",
                }
            ],
            "lastUpdatedAt": "2026-09-29",
            "_warnings": record_warnings,
            "_provisional": {
                "teamIdSource": "leaguepedia-team-code (canonical team IDs unresolved)",
                "bestOfSource": "MatchSchedule/Start tab context (verified by played-game count)",
                "idType": "deterministic synthetic series id",
            },
        })

    return normalized, excluded


def main() -> int:
    wikitext = RAW_PAGE.read_text(encoding="utf-8")
    series, starts = collect_series(wikitext)

    # keep the sample small: only the first tab block (Week 10)
    first_tab = starts[0]["tab"] if starts else None
    scoped = [s for s in series if s["context"].get("tab") == first_tab]

    normalized, excluded = normalize(scoped)

    validator_problems: list[str] = []
    for record in normalized:
        validator_problems.extend(validate_match(record))

    document = {
        "_meta": {
            "status": "SAMPLE / PHASE 17 — NOT production canonical data",
            "scope": f"first tab block ({first_tab}) of fixture Data:LCK/2026 Season/Rounds 3-4",
            "source": "raw/leaguepedia/page_data_lck_rounds34.wikitext",
            "provisionalFields": [
                "team1Id/team2Id use observed Leaguepedia team codes (canonical team IDs unresolved)",
                "bestOf comes from the tab context, verified by played-game count",
                "status mapping limited to 'completed' (scheduled rows not observed in fixture)",
                "synthetic deterministic series ids (no official series id observed)",
            ],
            "envelopePromotion": "BLOCKED — canonical team IDs unresolved; do not feed this file to the app",
        },
        "generatedAt": "2026-09-29",
        "dataVersion": "sample-2026-09-29",
        "records": normalized,
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(f"starts={len(starts)} series_total={len(series)} scoped={len(scoped)}")
    print(f"normalized={len(normalized)} excluded={len(excluded)}")
    warning_count = sum(len(r["_warnings"]) for r in normalized)
    print(f"records_with_timezone_warnings={sum(1 for r in normalized if r['_warnings'])} warnings={warning_count}")
    for item in excluded:
        print(f"  EXCLUDED {item['id']}: {'; '.join(item['problems'])}")
    for record in normalized:
        for warning in record["_warnings"]:
            print(f"  WARNING {record['id']}: {warning}")
    print(f"validator_record_problems={len(validator_problems)}")
    for problem in validator_problems:
        print(f"  VALIDATOR: {problem}")
    print(f"output={OUT_PATH}")
    return 0 if not validator_problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
