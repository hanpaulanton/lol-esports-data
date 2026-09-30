"""PHASE 18-3-A: shared identity-aware series score verification.

Root cause this module addresses (verified against raw wikitext):

Leaguepedia Data pages mix team representations between series-level
{{MatchSchedule}} args (team1/team2 may use FULL TEAM NAMES, sometimes with
case variants such as "Dplus KIA") and game-level {{MatchSchedule/Game}}
args (blue/red use LEAGUEPEDIA TEAM CODES such as DPLUS). Comparing the two
with exact string equality ("blue == team1") is unsafe and produced the three
false Road to MSI mismatches.

Design (per PHASE 18-3-A handoff, section 21):

- TeamIdentityResolver loads config/team_mappings.json and resolves a raw
  string to the canonical Leaguepedia code using EXACT matches only:
  raw == leaguepediaCode, or raw == name, or raw equal to a configured
  code/name up to letter case (PHASE 18-3-A decision, documented below).
- No fuzzy matching: no prefix, substring, edit-distance or abbreviation
  guessing. Unresolvable values stay UNKNOWN (fail-closed).
- compute_series_score aggregates per-game winners into a series score and
  classifies the result as OK / UNKNOWN / CONFLICT.

Case-insensitive exact match decision (PHASE 18-3-A):

The Road to MSI fixture contains the series-level spelling "Dplus KIA"
while config/team_mappings.json registers the name "Dplus Kia". The two are
the same configured mapping up to letter case, so equality ignoring case
against explicitly configured code/name values counts as resolved. This is
NOT one of the prohibited heuristics (startswith/substring/edit-distance/
arbitrary abbreviation guessing): nothing resolves unless the exact string
(up to case) is present in the mapping config. Example, per handoff
section 28: "Dplus Kia" / "Dplus KIA" / "DPLUS" -> "DPLUS".

Failure semantics (fail-closed):

1. team1/team2/blue/red unresolvable            -> UNKNOWN
2. blue and red resolve to the same team        -> CONFLICT
3. series winner value not exactly "1" or "2"   -> CONFLICT
4. resolved game winner not one of the series
   teams                                        -> CONFLICT
5. any game UNKNOWN identity                    -> series UNKNOWN
6. any game CONFLICT                            -> series CONFLICT
7. otherwise compute exact team1/team2 wins
8. computed == declared (when declared given)   -> OK
9. computed != declared                         -> CONFLICT
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from .leaguepedia_parser import find_nested_by_name, find_templates

DEFAULT_MAPPING_PATH = Path(__file__).resolve().parents[2] / "config" / "team_mappings.json"


class IdentityStatus(Enum):
    RESOLVED = "RESOLVED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ResolvedTeam:
    raw: str
    canonical: str | None
    status: IdentityStatus


class TeamIdentityResolver:
    """Exact-match-only resolution against config/team_mappings.json.

    Indexes leaguepediaCode -> code (canonical) and name -> code. A raw value
    resolves when it equals either key exactly, or up to letter case (see the
    module docstring for the PHASE 18-3-A decision). Everything else stays
    UNKNOWN — never guessed.
    """

    def __init__(self, mapping_path: Path | str = DEFAULT_MAPPING_PATH) -> None:
        payload = json.loads(Path(mapping_path).read_text(encoding="utf-8"))
        self._by_code: dict[str, str] = {}
        self._by_name: dict[str, str] = {}
        for entry in payload.get("mappings", []):
            code = (entry.get("leaguepediaCode") or "").strip()
            name = (entry.get("name") or "").strip()
            if not code:
                continue
            self._by_code[code] = code
            if name:
                self._by_name[name] = code
        self._by_code_folded = self._fold_table(self._by_code)
        self._by_name_folded = self._fold_table(self._by_name)

    @staticmethod
    def _fold_table(table: dict[str, str]) -> dict[str, str]:
        folded: dict[str, str] = {}
        for key, target in table.items():
            f = key.casefold()
            previous = folded.get(f)
            if previous is not None and previous != target:
                # Ambiguous config (two entries differing only by case) must
                # fail closed at load time, not guess at resolve time.
                raise ValueError(f"ambiguous case-folded mapping key {f!r}: {previous!r} vs {target!r}")
            folded[f] = target
        return folded

    def resolve(self, raw: str | None) -> ResolvedTeam:
        value = (raw or "").strip()
        if not value:
            return ResolvedTeam(raw if raw is not None else "", None, IdentityStatus.UNKNOWN)
        canonical = self._by_code.get(value)
        if canonical is None:
            canonical = self._by_name.get(value)
        if canonical is None:
            folded = value.casefold()
            canonical = self._by_code_folded.get(folded)
            if canonical is None:
                canonical = self._by_name_folded.get(folded)
        if canonical is None:
            return ResolvedTeam(value, None, IdentityStatus.UNKNOWN)
        return ResolvedTeam(value, canonical, IdentityStatus.RESOLVED)


class SeriesScoreStatus(Enum):
    OK = "OK"
    UNKNOWN = "UNKNOWN"
    CONFLICT = "CONFLICT"


@dataclass(frozen=True)
class GameOutcome:
    game_key: str
    blue: ResolvedTeam
    red: ResolvedTeam
    winner_raw: str
    winner_team: str | None
    status: SeriesScoreStatus
    reason: str | None


@dataclass(frozen=True)
class SeriesScoreResult:
    team1: ResolvedTeam
    team2: ResolvedTeam
    computed_team1_wins: int | None
    computed_team2_wins: int | None
    status: SeriesScoreStatus
    reason: str | None
    games: tuple[GameOutcome, ...]


def _game_outcome(
    game_key: str,
    game_args: Mapping[str, str],
    resolver: TeamIdentityResolver,
    team1_canonical: str | None,
    team2_canonical: str | None,
) -> GameOutcome:
    blue = resolver.resolve(game_args.get("blue"))
    red = resolver.resolve(game_args.get("red"))
    winner_raw = (game_args.get("winner") or "").strip()

    unresolved = [
        f"{side}={team.raw!r}"
        for side, team in (("blue", blue), ("red", red))
        if team.status is IdentityStatus.UNKNOWN
    ]
    if unresolved:
        return GameOutcome(game_key, blue, red, winner_raw, None, SeriesScoreStatus.UNKNOWN,
                           "unresolved identity: " + ", ".join(unresolved))
    assert blue.canonical is not None and red.canonical is not None
    if blue.canonical == red.canonical:
        return GameOutcome(game_key, blue, red, winner_raw, None, SeriesScoreStatus.CONFLICT,
                           f"blue and red resolve to the same team ({blue.canonical})")
    if winner_raw not in ("1", "2"):
        return GameOutcome(game_key, blue, red, winner_raw, None, SeriesScoreStatus.CONFLICT,
                           f"invalid winner value {winner_raw!r} (expected 1=blue or 2=red)")
    winner_team = blue.canonical if winner_raw == "1" else red.canonical
    if team1_canonical is not None and team2_canonical is not None:
        if winner_team not in (team1_canonical, team2_canonical):
            return GameOutcome(game_key, blue, red, winner_raw, winner_team, SeriesScoreStatus.CONFLICT,
                               f"game winner {winner_team} matches neither series team "
                               f"({team1_canonical}, {team2_canonical})")
    return GameOutcome(game_key, blue, red, winner_raw, winner_team, SeriesScoreStatus.OK, None)


def compute_series_score(
    team1_raw: str | None,
    team2_raw: str | None,
    games: Sequence[tuple[str, Mapping[str, str]]],
    resolver: TeamIdentityResolver,
    declared_team1_wins: int | None = None,
    declared_team2_wins: int | None = None,
) -> SeriesScoreResult:
    """Aggregate per-game winners into an identity-aware series score.

    games is a sequence of (game_key, game_args) pairs; game_args maps
    {{MatchSchedule/Game}} argument names (blue/red/winner/...) to raw values.
    When declared scores are provided, a computed/declared difference is a
    CONFLICT (handoff section 21, rules 8-9).
    """
    team1 = resolver.resolve(team1_raw)
    team2 = resolver.resolve(team2_raw)
    outcomes = tuple(
        _game_outcome(key, args, resolver, team1.canonical, team2.canonical)
        for key, args in games
    )

    unresolved_series = [
        f"team{side}={team.raw!r}"
        for side, team in ((1, team1), (2, team2))
        if team.status is IdentityStatus.UNKNOWN
    ]
    if unresolved_series:
        return SeriesScoreResult(team1, team2, None, None, SeriesScoreStatus.UNKNOWN,
                                 "unresolved series identity: " + ", ".join(unresolved_series), outcomes)
    unknown_games = [g.game_key for g in outcomes if g.status is SeriesScoreStatus.UNKNOWN]
    if unknown_games:
        return SeriesScoreResult(team1, team2, None, None, SeriesScoreStatus.UNKNOWN,
                                 "games with unresolved identity: " + ", ".join(unknown_games), outcomes)
    conflict_games = [g for g in outcomes if g.status is SeriesScoreStatus.CONFLICT]
    if conflict_games:
        return SeriesScoreResult(team1, team2, None, None, SeriesScoreStatus.CONFLICT,
                                 "; ".join(f"{g.game_key}: {g.reason}" for g in conflict_games), outcomes)

    assert team1.canonical is not None and team2.canonical is not None
    computed1 = sum(1 for g in outcomes if g.winner_team == team1.canonical)
    computed2 = sum(1 for g in outcomes if g.winner_team == team2.canonical)

    if declared_team1_wins is not None or declared_team2_wins is not None:
        if (computed1, computed2) == (declared_team1_wins, declared_team2_wins):
            return SeriesScoreResult(team1, team2, computed1, computed2, SeriesScoreStatus.OK, None, outcomes)
        return SeriesScoreResult(
            team1, team2, computed1, computed2, SeriesScoreStatus.CONFLICT,
            f"computed score {computed1}-{computed2} differs from declared "
            f"{declared_team1_wins}-{declared_team2_wins}", outcomes)
    return SeriesScoreResult(team1, team2, computed1, computed2, SeriesScoreStatus.OK, None, outcomes)


def series_score_matches_declared(result: SeriesScoreResult, declared1: int, declared2: int) -> bool:
    """True only when the result is OK and equals the declared score."""
    return (
        result.status is SeriesScoreStatus.OK
        and result.computed_team1_wins == declared1
        and result.computed_team2_wins == declared2
    )


def iter_series_with_games(
    wikitext: str,
) -> Iterable[tuple[dict, Mapping[str, str], list[tuple[str, dict[str, str]]]]]:
    """Yield (context, series_args, games) in document order.

    context currently carries the enclosing {{MatchSchedule/Start}} tab/bestof.
    games is a list of (game_key, game_args) pairs; game_key follows the source
    argument key ("game1", "game2", ...), suffixed "#2", "#3", ... if one key
    nests multiple {{MatchSchedule/Game}} templates. Values are stripped.
    """
    context: dict = {}
    for template in find_templates(wikitext):
        if template.name == "MatchSchedule/Start":
            # PHASE 18-5: shownname added for scheduled normalization ids
            # (design §13). Consumers that ignore it are unaffected.
            context = {
                key: (template.args.named.get(key) or "").strip()
                for key in ("tab", "bestof", "shownname")
            }
        elif template.name == "MatchSchedule":
            games: list[tuple[str, dict[str, str]]] = []
            for arg_key, arg_value in template.args.named.items():
                if not arg_key.lower().startswith("game"):
                    continue
                nested = find_nested_by_name(arg_value, "MatchSchedule/Game")
                for index, game_template in enumerate(nested):
                    game_key = arg_key if index == 0 else f"{arg_key}#{index + 1}"
                    games.append((game_key, {k: v.strip() for k, v in game_template.args.named.items()}))
            yield context, template.args.named, games
