"""PHASE 18-3-A: verify series scores vs per-game winners (side-swap and
identity-representation aware) for the newly acquired Playoffs / Road to MSI
fixtures, using the shared scripts/lib/series_score.py helper.

Root cause fixed here (see scripts/lib/series_score.py docstring): series
team1/team2 may use full team names while game blue/red use Leaguepedia team
codes; the previous exact-string comparison produced three false mismatches.
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.series_score import (  # noqa: E402
    SeriesScoreStatus,
    TeamIdentityResolver,
    compute_series_score,
    iter_series_with_games,
)

FIXTURES = [
    ROOT / "raw" / "leaguepedia" / "page_data_lck_season_playoffs_scheduled.wikitext",
    ROOT / "raw" / "leaguepedia" / "page_data_lck_road_to_msi_scheduled.wikitext",
]


def check(wikitext_path: pathlib.Path, resolver: TeamIdentityResolver) -> None:
    wikitext = pathlib.Path(wikitext_path).read_text(encoding="utf-8")

    total = 0
    consistent = 0
    unknown = 0
    score_sums = set()
    for context, args, games in iter_series_with_games(wikitext):
        team1 = (args.get("team1") or "").strip()
        team2 = (args.get("team2") or "").strip()
        s1 = int((args.get("team1score") or "0").strip() or 0)
        s2 = int((args.get("team2score") or "0").strip() or 0)
        score_sums.add(s1 + s2)
        result = compute_series_score(team1, team2, games, resolver, s1, s2)
        total += 1
        if result.status is SeriesScoreStatus.OK:
            consistent += 1
        elif result.status is SeriesScoreStatus.UNKNOWN:
            unknown += 1
            print(f"  UNKNOWN  {team1} vs {team2} ({context.get('tab', '')}): {result.reason}")
        else:
            print(f"  MISMATCH {team1} vs {team2} ({context.get('tab', '')}): "
                  f"declared {s1}-{s2}, {result.reason}")

    print(f"{wikitext_path.name}: series={total} consistent={consistent} "
          f"unknown={unknown} score_sums={sorted(score_sums)}")
    if consistent != total:
        raise SystemExit(1)


def main() -> None:
    resolver = TeamIdentityResolver()
    for fixture in FIXTURES:
        check(fixture, resolver)


if __name__ == "__main__":
    main()
