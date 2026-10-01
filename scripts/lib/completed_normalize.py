"""PHASE 18-20: completed-match normalization layer (league-generic).

Mirrors scheduled_normalize.py's pure-function design: the caller supplies
the wikitext context (league_meta, source_ref), the identity resolver, and
the verified code->canonical-id map; this module invents no identities and
no rpgids.

Fail-closed rules implemented here:
- Team identity: the existing exact resolver must resolve the raw value AND
  the resolved code must exist in the caller's verified code->id map.
  Otherwise the row is EXCLUDED (never guessed).
- Scores: both scores must be present integers. The source winner field must
  agree with the higher score. Otherwise EXCLUDED.
- scheduledAt: converted via the existing curated timezone logic
  (lib.timezones.normalize_local_to_utc). Unconvertible -> EXCLUDED.
- bestOf: existing resolve_best_of hierarchy (row-level > Start-level).
- rpgid: counted as provenance only (_provisional.rpgidCount), never
  synthesized. Forfeit rows (ff) legitimately have zero games/rpgids; the
  ff value itself is source commentary and is NOT added to the canonical
  schema (documented in the promotion report instead).
- Extra pre-created but unplayed game blocks are ignored: only observed
  rpgids count; the outcome comes from the series score.
"""

from __future__ import annotations

from lib.leaguepedia_parser import find_nested_by_name, find_templates
from lib.series_score import IdentityStatus, TeamIdentityResolver
from lib.timezones import normalize_local_to_utc
from scheduled_normalize import resolve_best_of

# provenance vocabulary reuse: completed rows distinguish themselves by
# carrying scores; rpgidCount reuses the existing scheduled provenance shape.


def _clean(value: str | None) -> str:
    return (value or "").strip()


def collect_completed_series(wikitext: str) -> list[dict]:
    """Collect completed-looking {{MatchSchedule}} series in document order,
    with tab context and row-level bestof. Self-contained: reuses only the
    generic parser (lib.leaguepedia_parser), not the LCK sample generator.

    A series is a candidate for the completed pipeline when a numeric
    team1score is present; the caller decides promotion per row.
    """
    series: list[dict] = []
    context: dict = {}
    for template in find_templates(wikitext):
        if template.name == "MatchSchedule/Start":
            context = {
                "tab": _clean(template.args.get("tab")),
                "bestof": _clean(template.args.get("bestof")),
                "shownname": _clean(template.args.get("shownname")),
            }
        elif template.name == "MatchSchedule":
            args = template.args
            games: list[dict] = []
            for arg_key, arg_value in args.named.items():
                if not arg_key.lower().startswith("game"):
                    continue
                for game_template in find_nested_by_name(arg_value, "MatchSchedule/Game"):
                    games.append(dict(game_template.args.named))
            series.append(
                {
                    "team1": _clean(args.get("team1")),
                    "team2": _clean(args.get("team2")),
                    "team1score": _clean(args.get("team1score")),
                    "team2score": _clean(args.get("team2score")),
                    "winner": _clean(args.get("winner")),
                    "date": _clean(args.get("date")),
                    "time": _clean(args.get("time")),
                    "timezone": _clean(args.get("timezone")),
                    "dst": _clean(args.get("dst")),
                    "bestof": _clean(args.get("bestof")),
                    "context": dict(context),
                    "games": games,
                }
            )
    return [s for s in series if s["team1score"].isdigit()]


def normalize_completed_series(
    series: dict,
    resolver: TeamIdentityResolver,
    code_to_id: dict[str, str],
    source_ref: str,
    league_meta: dict,
    generated_at: str,
) -> tuple[dict | None, dict | None, list[str]]:
    """Normalize one completed {{MatchSchedule}} series.

    Returns (match, exclusion, problems):
    - match: canonical completed match dict, or None when excluded
    - exclusion: {"reason": ..., ...} when excluded, else None
    - problems: non-fatal observations (recorded by the caller)
    """
    problems: list[str] = []
    args = series

    date_raw = (args.get("date") or "").strip()
    time_raw = (args.get("time") or "").strip()
    tz_raw = (args.get("timezone") or "").strip()
    dst_raw = (args.get("dst") or "").strip()
    team1_raw = (args.get("team1") or "").strip()
    team2_raw = (args.get("team2") or "").strip()

    def exclude(reason: str) -> tuple[None, dict, list[str]]:
        return None, {
            "reason": reason,
            "date": date_raw,
            "team1": team1_raw,
            "team2": team2_raw,
        }, problems

    # ---- identity (exact resolver + verified map, fail-closed) ----
    ids: dict[str, str] = {}
    raw_by_side = {"team1": team1_raw, "team2": team2_raw}
    for side, raw in raw_by_side.items():
        resolved = resolver.resolve(raw)
        if resolved.status is not IdentityStatus.RESOLVED:
            return exclude(f"unresolved team identity: {raw!r}")
        canonical_id = code_to_id.get(resolved.canonical)
        if canonical_id is None:
            return exclude(
                f"resolved code {resolved.canonical!r} has no verified canonical id "
                f"(raw {raw!r})"
            )
        ids[side] = canonical_id
    if ids["team1"] == ids["team2"]:
        return exclude("both slots resolve to the same team")

    # ---- scores / winner (fail-closed) ----
    def to_int(value: str) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    s1, s2 = to_int(args.get("team1score") or ""), to_int(args.get("team2score") or "")
    if s1 is None or s2 is None:
        return exclude(f"incomplete score {args.get('team1score')!r}:{args.get('team2score')!r}")
    winner_raw = (args.get("winner") or "").strip()
    expected_winner = "1" if s1 > s2 else "2"
    if winner_raw and winner_raw != expected_winner:
        return exclude(f"winner {winner_raw!r} contradicts score {s1}:{s2}")
    if s1 == s2:
        return exclude(f"tie score {s1}:{s2} is not a decided completed series")

    # ---- bestOf (existing hierarchy) ----
    best_of, best_of_source, best_of_warnings = resolve_best_of(
        args.get("bestof"), (args.get("context") or {}).get("bestof")
    )
    problems.extend(best_of_warnings)
    if best_of is None:
        return exclude("no usable bestOf (row and Start both unusable)")

    # ---- scheduledAt via the existing curated timezone logic ----
    time_result = normalize_local_to_utc(date_raw, time_raw, tz_raw, dst_raw)
    if time_result is None:
        return exclude(f"timezone {tz_raw!r} is not curated (fail-closed)")
    problems.extend(time_result.warnings)

    # ---- rpgid provenance (observed values only, never synthesized) ----
    games = args.get("games") or []
    rpgids = [
        (g.get("riot_platform_game_id") or "").strip()
        for g in games
        if (g.get("riot_platform_game_id") or "").strip()
    ]
    match_id = f"lp:{(args.get('context') or {}).get('shownname', '')}:{date_raw}:{team1_raw}:{team2_raw}"

    match = {
        "id": match_id,
        "league": dict(league_meta),
        "tournament": {
            "id": (args.get("context") or {}).get("shownname", ""),
            "name": (args.get("context") or {}).get("shownname", ""),
        },
        "stage": {"id": (args.get("context") or {}).get("tab", ""), "name": (args.get("context") or {}).get("tab", "")},
        "team1Id": ids["team1"],
        "team2Id": ids["team2"],
        "scheduledAt": time_result.utc_iso,
        "status": "completed",
        "bestOf": best_of,
        "score": {"team1": s1, "team2": s2},
        "lastUpdatedAt": generated_at,
        "sources": [{"source": "leaguepedia", "kind": "raw_fixture", "ref": source_ref}],
        "_provisional": {
            "teamIdSource": "leaguepedia raw value (exact resolver + verified promotion map)",
            "teamSlotRaw": {"team1": team1_raw, "team2": team2_raw},
            "rpgidCount": {"total": len(games), "nonEmpty": len(rpgids)},
            "bestOfSource": best_of_source,
            "timeRaw": {
                "date": date_raw, "time": time_raw, "timezone": tz_raw,
                "dst": dst_raw, "utcConversion": CONVERTED_TZ,
            },
        },
    }
    return match, None, problems
