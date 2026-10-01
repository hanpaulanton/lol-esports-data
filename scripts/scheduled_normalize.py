"""PHASE 18-5: scheduled normalization layer (pure-function oriented).

Implements the PHASE 18-4 design (docs/scheduled-normalization-design.md)
for Leaguepedia scheduled MatchSchedule rows. It does NOT replace or modify
scripts/normalize_sample.py (completed normalization is untouched), does not
create synthetic rpgids, does not guess DST semantics or the PST offset, and
does not promote anything into data/matches.sample.json.

Design decisions implemented here (see design doc for the evidence tags):

- Team slots are classified per side as KNOWN / TBD / EMPTY. The only TBD
  representation used is the literal "TBD" observed on EMEA rows 79-93;
  no other placeholder strings are guessed.
- Team identity uses the existing exact resolver. identity UNKNOWN does not
  fail the record: KNOWN slots keep their raw value as a provisional teamId,
  EMPTY/TBD slots get teamId=null.
- BestOf hierarchy: row-level bestof > Start-level bestof > UNKNOWN. A
  malformed (non-integer, non-positive) row value is surfaced as a warning
  and falls through to the Start value (fail-closed: never silently used).
- scheduled score/winner: empty raw fields -> score=null. Never 0:0. Rows
  with any result value present are NOT scheduled rows and are excluded
  here (they belong to the completed pipeline).
- rpgid: counted as evidence only; never synthesized; no rpgid field is
  added to the canonical Match.
- Date/time: converted via the existing curated timezone mapping only
  (normalize_local_to_utc). Unknown abbreviations (e.g. PST) or dst
  semantics are NOT guessed: scheduledAt=null and
  _provisional.timeRaw.utcConversion="PENDING_TIMEZONE_REVIEW". Malformed
  date/time -> excluded (design V4 ERROR).
- status vocabulary is unchanged; scheduled rows get status="scheduled".
"""

from __future__ import annotations

from lib.series_score import IdentityStatus, TeamIdentityResolver, iter_series_with_games
from lib.timezones import normalize_local_to_utc

# The only TBD representation observed so far (EMEA 2026 Summer rows 79-93).
TBD_LITERAL = "TBD"

SLOT_KNOWN = "KNOWN"
SLOT_TBD = "TBD"
SLOT_EMPTY = "EMPTY"

PENDING_TZ = "PENDING_TIMEZONE_REVIEW"
CONVERTED_TZ = "CONVERTED"  # success path: normalize_local_to_utc produced a verified UTC value


def classify_team_slot(raw: str | None) -> str:
    """KNOWN (non-empty, not the observed TBD literal) / TBD / EMPTY."""
    value = (raw or "").strip()
    if not value:
        return SLOT_EMPTY
    if value == TBD_LITERAL:
        return SLOT_TBD
    return SLOT_KNOWN


def resolve_best_of(row_bestof: str | None, start_bestof: str | None) -> tuple[int | None, str, list[str]]:
    """Design §5 hierarchy. Returns (effectiveBestOf, source, warnings).

    A malformed non-empty row value produces a warning and falls through to
    the Start value; a malformed Start value likewise warns and yields None.
    """
    warnings: list[str] = []
    for raw, source in ((row_bestof, "row-level bestof"), (start_bestof, "start-level bestof")):
        value = (raw or "").strip()
        if not value:
            continue
        if value.isdigit() and int(value) > 0:
            return int(value), source, warnings
        warnings.append(f"malformed {source} value {value!r}; treated as absent (fail-closed)")
    return None, "UNKNOWN (no usable bestof on row or Start)", warnings


def _slot_record(raw: str | None, resolver: TeamIdentityResolver) -> dict:
    state = classify_team_slot(raw)
    value = (raw or "").strip()
    resolved = resolver.resolve(value) if state == SLOT_KNOWN else None
    if state == SLOT_KNOWN:
        status = IdentityStatus.RESOLVED if resolved and resolved.status is IdentityStatus.RESOLVED else IdentityStatus.UNKNOWN
        canonical = resolved.canonical if resolved and resolved.status is IdentityStatus.RESOLVED else None
    else:
        status = IdentityStatus.UNKNOWN
        canonical = None
    return {
        "rawValue": value,
        "slotState": state,
        "canonicalTeamId": canonical,
        "identityStatus": status.value,
    }


def normalize_scheduled_series(
    context: dict,
    args: dict,
    games: list[tuple[str, dict]],
    resolver: TeamIdentityResolver,
    source_ref: str,
    league_meta: dict,
    occurrence: int = 1,
) -> tuple[dict | None, dict | None]:
    """Normalize one raw scheduled row into the 18-4 canonical proposal.

    Returns (record, None) on success or (None, excluded) with a machine
    readable reason. Rows carrying any result value are not scheduled rows
    and are excluded (completed pipeline's domain).
    """
    team1_raw = (args.get("team1") or "").strip()
    team2_raw = (args.get("team2") or "").strip()
    winner_raw = (args.get("winner") or "").strip()
    score1_raw = (args.get("team1score") or "").strip()
    score2_raw = (args.get("team2score") or "").strip()

    if winner_raw or score1_raw or score2_raw:
        return None, {
            "reason": "not a scheduled row: result field(s) present "
                      f"(winner={winner_raw!r}, scores={score1_raw!r}/{score2_raw!r})",
            "team1": team1_raw, "team2": team2_raw,
        }

    date_raw = (args.get("date") or "").strip()
    time_raw = (args.get("time") or "").strip()
    tz_raw = (args.get("timezone") or "").strip()
    dst_raw = (args.get("dst") or "").strip()
    if not date_raw or not time_raw:
        return None, {
            "reason": f"V4 ERROR: scheduled row without parsable date/time (date={date_raw!r}, time={time_raw!r})",
            "team1": team1_raw, "team2": team2_raw,
        }

    shownname = (context.get("shownname") or "").strip() or "unknown"
    tab = (context.get("tab") or "").strip() or "unknown"

    # V4 defense in depth: the time converter would raise on malformed input.
    warnings: list[str] = []
    scheduled_at: str | None = None
    utc_conversion = PENDING_TZ
    try:
        time_result = normalize_local_to_utc(date_raw, time_raw, tz_raw, dst_raw)
    except ValueError as exc:
        return None, {
            "reason": f"V4 ERROR: malformed date/time ({exc})",
            "team1": team1_raw, "team2": team2_raw,
        }
    if time_result is not None:
        scheduled_at = time_result.utc_iso
        utc_conversion = CONVERTED_TZ
        warnings.extend(time_result.warnings)
    # time_result None -> unknown abbreviation (e.g. PST): scheduledAt stays
    # null and the raw values are preserved; the offset is NOT guessed.

    slot1 = _slot_record(team1_raw, resolver)
    slot2 = _slot_record(team2_raw, resolver)

    best_of, best_of_source, best_of_warnings = resolve_best_of(
        args.get("bestof"), context.get("bestof")
    )
    warnings.extend(best_of_warnings)

    rpgid_total = len(games)
    rpgid_nonempty = sum(
        1 for _key, game_args in games if (game_args.get("riot_platform_game_id") or "").strip()
    )

    base_id = f"lp:{shownname}:{date_raw}:{team1_raw or 'EMPTY'}:{team2_raw or 'EMPTY'}"
    record_id = base_id if occurrence == 1 else f"{base_id}:{occurrence:02d}"

    record = {
        "id": record_id,
        "league": dict(league_meta),
        "tournament": {"id": shownname, "name": shownname},
        "stage": {"id": tab, "name": tab},
        "team1Id": team1_raw if slot1["slotState"] == SLOT_KNOWN else None,
        "team2Id": team2_raw if slot2["slotState"] == SLOT_KNOWN else None,
        "scheduledAt": scheduled_at,
        "status": "scheduled",
        "bestOf": best_of,
        "score": None,
        "sources": [{"source": "leaguepedia", "kind": "raw_fixture", "ref": source_ref}],
        "lastUpdatedAt": None,  # caller stamps the observation date
        "_warnings": list(warnings),
        "_provisional": {
            "teamIdSource": "leaguepedia raw value (identity resolution per exact resolver)",
            "teamSlotState": {"team1": slot1["slotState"], "team2": slot2["slotState"]},
            "teamSlotRaw": {"team1": slot1["rawValue"], "team2": slot2["rawValue"]},
            "identityStatus": {"team1": slot1["identityStatus"], "team2": slot2["identityStatus"]},
            "canonicalTeamId": {"team1": slot1["canonicalTeamId"], "team2": slot2["canonicalTeamId"]},
            "bestOfSource": best_of_source,
            "gameBlockCount": rpgid_total,
            "rpgidCount": {"total": rpgid_total, "nonEmpty": rpgid_nonempty},
            "timeRaw": {
                "date": date_raw, "time": time_raw,
                "timezone": tz_raw, "dst": dst_raw,
                "utcConversion": utc_conversion,
            },
        },
    }
    return record, None


def normalize_scheduled_wikitext(
    wikitext: str,
    resolver: TeamIdentityResolver,
    source_ref: str,
    league_meta: dict,
    observation_date: str | None = None,
) -> tuple[list[dict], list[dict]]:
    """Normalize every scheduled row of one raw Data page.

    Returns (records, excluded). Rows with result values are reported in
    `excluded` (they belong to the completed pipeline); the caller decides
    whether that is expected. league_meta must be supplied by the caller —
    this module never invents canonical league identities. observation_date
    (YYYY-MM-DD) is stamped into lastUpdatedAt when provided.
    """
    records: list[dict] = []
    excluded: list[dict] = []
    occurrence: dict[str, int] = {}
    for context, args, games in iter_series_with_games(wikitext):
        raw_id_base = (
            f"{(context.get('shownname') or '').strip()}:"
            f"{(args.get('date') or '').strip()}:"
            f"{(args.get('team1') or 'EMPTY').strip()}:"
            f"{(args.get('team2') or 'EMPTY').strip()}"
        )
        record, skip = normalize_scheduled_series(
            context, args, games, resolver, source_ref, league_meta,
            occurrence=occurrence.get(raw_id_base, 0) + 1,
        )
        if skip is not None:
            excluded.append(skip)
            continue
        occurrence[raw_id_base] = occurrence.get(raw_id_base, 0) + 1
        if observation_date:
            record["lastUpdatedAt"] = observation_date
        records.append(record)
    return records, excluded
