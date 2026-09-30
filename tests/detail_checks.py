"""PHASE 18-2 corrected check: series score vs per-game winners, accounting
for the fact that {{MatchSchedule/Game}} winner is blue(1)/red(2) based and
sides SWAP between games within a series."""

from __future__ import annotations

import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.leaguepedia_parser import find_templates, find_nested_by_name  # noqa: E402

data_text = (ROOT / "raw" / "leaguepedia" / "page_data_lck_rounds34.wikitext").read_text(encoding="utf-8")

total = 0
consistent = 0
mismatch_rows = []
swapped_series = 0
games_total = 0
games_blue_is_series_team1 = 0

for t in find_templates(data_text):
    if t.name != "MatchSchedule":
        continue
    args = t.args.named
    team1 = (args.get("team1") or "").strip()
    team2 = (args.get("team2") or "").strip()
    s1 = int((args.get("team1score") or "0").strip() or 0)
    s2 = int((args.get("team2score") or "0").strip() or 0)
    winner = (args.get("winner") or "").strip()

    games = []
    for key, value in args.items():
        if key.lower().startswith("game"):
            for g in find_nested_by_name(value, "MatchSchedule/Game"):
                games.append(dict(g.args.named))
    total += 1

    # per-game winner expressed as SERIES team1/team2 code
    t1_wins = 0
    t2_wins = 0
    for g in games:
        blue = (g.get("blue") or "").strip()
        w = (g.get("winner") or "").strip()
        games_total += 1
        if blue == team1:
            games_blue_is_series_team1 += 1
        win_code = blue if w == "1" else (team2 if blue == team1 else team1)
        # resolve winner code: if blue == team1 -> winner 1 means team1; if blue == team2 -> winner 1 means team2
        if blue == team1:
            win_code = team1 if w == "1" else team2
        elif blue == team2:
            win_code = team2 if w == "1" else team1
        if win_code == team1:
            t1_wins += 1
        elif win_code == team2:
            t2_wins += 1

    if t1_wins == s1 and t2_wins == s2:
        consistent += 1
    else:
        mismatch_rows.append(f"{team1} vs {team2} ({args.get('date')}): score {s1}-{s2} vs game wins {t1_wins}-{t2_wins}")

    blues = {((g.get("blue") or "").strip()) for g in games}
    if len(games) >= 2 and len(blues) == 2:
        swapped_series += 1

print(f"series checked: {total}")
print(f"score consistent with per-game winners (side-swap aware): {consistent}/{total}")
for row in mismatch_rows:
    print("  MISMATCH:", row)
print(f"series with side swap (>=2 games, 2 distinct blue teams): {swapped_series}")
print(f"games total: {games_total}; games where blue == series team1: {games_blue_is_series_team1}")
