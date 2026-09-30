"""Validator for canonical data structures.

Standard library only. Two entry points:
- validate_envelope(document) -> list[str]: validates the full
  RemoteDataEnvelope structure (the shape the Android app consumes).
- validate_match(record) -> list[str]: validates one canonical match record's
  required fields. Both return a list of human-readable problems; an empty
  list means valid.
"""

from __future__ import annotations

import datetime
import re

ALLOWED_STATUSES = {"scheduled", "in_progress", "completed", "postponed", "cancelled", "unknown"}

# PHASE 18-5: team-slot states from the 18-4 design (docs/scheduled-normalization-design.md §3-1/§8).
ALLOWED_SLOT_STATES = {"KNOWN", "TBD", "EMPTY"}
TBD_LITERAL = "TBD"
# V15: only forfeit values observed so far are "1"/"2" (EMEA row 9); anything
# else is a warning, never an invented status.
OBSERVED_FF_VALUES = {"1", "2", ""}

ISO_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def _is_nonempty_str(value) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _is_nonneg_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def validate_match(match, path: str = "matches") -> list[str]:
    problems: list[str] = []
    match_id = match.get("id") if isinstance(match, dict) else None
    where = f"{path}[id={match_id}]" if isinstance(match, dict) else path

    if not isinstance(match, dict):
        return [f"{where}: match must be an object"]

    for field in ("id", "team1Id", "team2Id"):
        if not _is_nonempty_str(match.get(field)):
            problems.append(f"{where}.{field}: must be a non-empty string")

    league = match.get("league")
    if not isinstance(league, dict) or not _is_nonempty_str(league.get("id")) or not _is_nonempty_str(league.get("name")):
        problems.append(f"{where}.league: must be an object with non-empty id and name")

    tournament = match.get("tournament")
    if not isinstance(tournament, dict) or not _is_nonempty_str(tournament.get("id")) or not _is_nonempty_str(tournament.get("name")):
        problems.append(f"{where}.tournament: must be an object with non-empty id and name")

    stage = match.get("stage")
    if not isinstance(stage, dict) or not _is_nonempty_str(stage.get("id")) or not _is_nonempty_str(stage.get("name")):
        problems.append(f"{where}.stage: must be an object with non-empty id and name")

    scheduled_at = match.get("scheduledAt")
    if not _is_nonempty_str(scheduled_at) or not ISO_UTC_RE.match(scheduled_at):
        problems.append(f"{where}.scheduledAt: must be ISO-8601 UTC like 2026-07-29T08:00:00Z")
    else:
        try:
            datetime.datetime.strptime(scheduled_at, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            problems.append(f"{where}.scheduledAt: not a real date/time")

    status = match.get("status")
    if status not in ALLOWED_STATUSES:
        problems.append(f"{where}.status: must be one of {sorted(ALLOWED_STATUSES)}")

    best_of = match.get("bestOf")
    if not isinstance(best_of, int) or isinstance(best_of, bool) or best_of <= 0:
        problems.append(f"{where}.bestOf: must be a positive integer")

    score = match.get("score")
    if not isinstance(score, dict) or not _is_nonneg_int(score.get("team1")) or not _is_nonneg_int(score.get("team2")):
        problems.append(f"{where}.score: must be an object with non-negative integer team1/team2")

    sources = match.get("sources")
    if sources is not None and not isinstance(sources, list):
        problems.append(f"{where}.sources: must be a list when present")

    if not _is_nonempty_str(match.get("lastUpdatedAt")):
        problems.append(f"{where}.lastUpdatedAt: must be a non-empty string")

    return problems


def validate_envelope(document) -> list[str]:
    problems: list[str] = []
    if not isinstance(document, dict):
        return ["document: must be an object"]

    if document.get("schemaVersion") != 1:
        problems.append("schemaVersion: must be 1")
    if not _is_nonempty_str(document.get("dataVersion")):
        problems.append("dataVersion: must be a non-empty string")
    if not _is_nonempty_str(document.get("generatedAt")):
        problems.append("generatedAt: must be a non-empty string")

    for field in ("leagues", "teams", "matches"):
        value = document.get(field)
        if not isinstance(value, list):
            problems.append(f"{field}: must be a list")
            continue
        if field == "matches":
            for index, match in enumerate(value):
                # PHASE 18-9 (GATE 1 fix): status-aware dispatch. Scheduled
                # records legitimately carry null team ids / score /
                # scheduledAt (18-4 design §11, V-rules); dispatching them to
                # validate_match would reject valid scheduled records.
                # Completed semantics via validate_match are unchanged.
                status = match.get("status") if isinstance(match, dict) else None
                if status == "scheduled":
                    errors, warnings = validate_scheduled_match(match, path=f"matches[{index}]")
                    problems.extend(errors)
                    # Scheduled warnings are promoted into envelope problems
                    # so they are never silently dropped (fail-closed).
                    problems.extend(warnings)
                else:
                    problems.extend(validate_match(match, path=f"matches[{index}]"))
        else:
            for index, item in enumerate(value):
                if not isinstance(item, dict) or not _is_nonempty_str(item.get("id")) or not _is_nonempty_str(item.get("name")):
                    problems.append(f"{field}[{index}]: must be an object with non-empty id and name")

    return problems


def validate_scheduled_match(match, path: str = "scheduled_matches") -> tuple[list[str], list[str]]:
    """PHASE 18-5: validation for canonical scheduled match records.

    Implements the PHASE 18-4 design rules V1-V15
    (docs/scheduled-normalization-design.md §11). The existing completed
    validation (validate_match) is intentionally untouched.

    Classification per design: ERROR = record must not be promoted;
    WARNING = promotable, problem recorded; OK states (V9/V10/V11) are not
    reported. Returns (errors, warnings).
    """
    errors: list[str] = []
    warnings: list[str] = []
    match_id = match.get("id") if isinstance(match, dict) else None
    where = f"{path}[id={match_id}]" if isinstance(match, dict) else path

    if not isinstance(match, dict):
        return ([f"{where}: match must be an object"], [])

    # Structural checks shared with the completed validator.
    for field in ("id",):
        if not _is_nonempty_str(match.get(field)):
            errors.append(f"{where}.{field}: must be a non-empty string")

    status = match.get("status")
    if status not in ALLOWED_STATUSES:
        errors.append(f"{where}.status: must be one of {sorted(ALLOWED_STATUSES)}")
    if status != "scheduled":
        # This validator only accepts scheduled records; anything else must
        # go through validate_match (fail-closed against vocabulary mixing).
        errors.append(f"{where}.status: validate_scheduled_match only accepts 'scheduled' (got {status!r})")
        return (errors, warnings)

    # V1: scheduled + any result value -> ERROR. score must be null; a
    # non-null dict (including a literal 0:0, which design §6 forbids) is an
    # error regardless of the values, and a non-dict/malformed dict too.
    score = match.get("score")
    if score is not None:
        errors.append(f"{where}.score: scheduled record must carry score=null (V1/V2); got {score!r}")

    # scheduledAt: either null (pending timezone review) or valid ISO-UTC.
    scheduled_at = match.get("scheduledAt")
    if scheduled_at is not None:
        if not _is_nonempty_str(scheduled_at) or not ISO_UTC_RE.match(scheduled_at):
            errors.append(f"{where}.scheduledAt: must be null or ISO-8601 UTC like 2026-07-29T08:00:00Z (V4)")
        else:
            try:
                datetime.datetime.strptime(scheduled_at, "%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                errors.append(f"{where}.scheduledAt: not a real date/time (V4)")

    # bestOf: positive int or null (both absent on row and Start).
    best_of = match.get("bestOf")
    if best_of is not None and (not isinstance(best_of, int) or isinstance(best_of, bool) or best_of <= 0):
        errors.append(f"{where}.bestOf: must be a positive integer or null (V4)")

    sources = match.get("sources")
    if sources is not None and not isinstance(sources, list):
        errors.append(f"{where}.sources: must be a list when present")

    if not _is_nonempty_str(match.get("lastUpdatedAt")):
        errors.append(f"{where}.lastUpdatedAt: must be a non-empty string")

    # Team slots: KNOWN slots need a non-empty provisional id; EMPTY/TBD
    # slots must be null (V9/V10 OK states; the inverse is an error).
    provisional = match.get("_provisional")
    slot_state = (provisional or {}).get("teamSlotState") if isinstance(provisional, dict) else None
    if not isinstance(slot_state, dict):
        warnings.append(f"{where}._provisional.teamSlotState: missing; scheduled records should carry team slot states (V9/V10 evidence)")
        slot_state = {}
    for side in ("team1", "team2"):
        team_id = match.get(f"{side}Id")
        state = slot_state.get(side)
        if state is not None and state not in ALLOWED_SLOT_STATES:
            warnings.append(f"{where}._provisional.teamSlotState.{side}: unknown state {state!r} (expected KNOWN/TBD/EMPTY)")
        if state == "KNOWN":
            if not _is_nonempty_str(team_id):
                errors.append(f"{where}.{side}Id: KNOWN slot must carry a non-empty provisional id (V9)")
        elif state in ("TBD", "EMPTY") and team_id is not None:
            errors.append(f"{where}.{side}Id: {state} slot must be null, got {team_id!r} (V9/V10)")

    # V12: rpgid evidence on a scheduled record -> WARNING.
    rpgid_count = (provisional or {}).get("rpgidCount") if isinstance(provisional, dict) else None
    if isinstance(rpgid_count, dict) and rpgid_count.get("nonEmpty"):
        warnings.append(
            f"{where}._provisional.rpgidCount: {rpgid_count.get('nonEmpty')} non-empty rpgid(s) on a scheduled record (V12)"
        )

    # V7: scheduled game-block count vs bestOf mismatch -> WARNING (the
    # pre-creation convention is observed but not guaranteed).
    block_count = (provisional or {}).get("gameBlockCount") if isinstance(provisional, dict) else None
    if isinstance(block_count, int) and isinstance(best_of, int) and block_count != best_of:
        warnings.append(
            f"{where}: scheduled game block count {block_count} != effective bestOf {best_of} (V7)"
        )

    return (errors, warnings)
