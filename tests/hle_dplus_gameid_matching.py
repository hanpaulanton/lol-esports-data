"""PHASE 18-1: resolve HLE/DPLUS via riot_platform_game_id matching.

Observed facts used (no name-based inference):
- Data fixture MatchSchedule/Game: riot_platform_game_id + blue/red CODES + winner(1=blue,2=red)
- Scoreboards fixture Scoreboard/Season 16: rpgid + team1/team2 FULL NAMES + winner(1=team1,2=team2)
- Team1 is the blue side: verified per game by comparing sum(blue1..5 gold) == team1g.

If the same game id shows Data-blue winner == Scoreboard team1 winner, then
Data-blue code == Scoreboard team1 name. Repeated across games of the same
series and across series, a consistent code->name assignment confirms HLE/DPLUS.
"""

from __future__ import annotations

import pathlib
import sys
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.leaguepedia_parser import find_templates, find_nested_by_name  # noqa: E402

score_text = (ROOT / "raw" / "leaguepedia" / "page_lck_scoreboards.wikitext").read_text(encoding="utf-8")
data_text = (ROOT / "raw" / "leaguepedia" / "page_data_lck_rounds34.wikitext").read_text(encoding="utf-8")

# ---- Scoreboards: game-id -> (team1 name, team2 name, winner side, blue-gold-sum check) ----
score_games: dict[str, dict] = {}
for t in find_templates(score_text):
    if t.name != "Scoreboard/Season 16":
        continue
    rpgid = (t.args.named.get("rpgid") or "").strip()
    if not rpgid:
        continue
    team1 = (t.args.named.get("team1") or "").strip()
    team2 = (t.args.named.get("team2") or "").strip()
    winner = (t.args.named.get("winner") or "").strip()

    def gold_sum(prefix: str) -> int:
        total = 0
        for i in range(1, 6):
            slot = t.args.named.get(f"{prefix}{i}", "")
            players = find_nested_by_name(slot, "Scoreboard/Player")
            if players:
                g = players[0].args.named.get("gold", "0").strip()
                total += int(g) if g.isdigit() else 0
        return total

    blue_gold_sum = gold_sum("blue")
    red_gold_sum = gold_sum("red")
    team1g = int(t.args.named.get("team1g", "0").strip() or 0)
    team2g = int(t.args.named.get("team2g", "0").strip() or 0)

    blue_is_team1 = blue_gold_sum == team1g and red_gold_sum == team2g
    score_games[rpgid] = {
        "team1": team1,
        "team2": team2,
        "winner": winner,
        "blue_is_team1": blue_is_team1,
        "gold_check": (blue_gold_sum, team1g, red_gold_sum, team2g),
    }

print(f"Scoreboards games with rpgid: {len(score_games)}")
bad_gold = [gid for gid, g in score_games.items() if not g["blue_is_team1"]]
print(f"games where blue-gold-sum==team1g and red-gold-sum==team2g (team1==blue): {len(score_games) - len(bad_gold)}/{len(score_games)}")
if bad_gold:
    for gid in bad_gold[:5]:
        print("  GOLD-MISMATCH", gid, score_games[gid]["gold_check"])

# ---- Data: series -> games with codes ----
data_games: dict[str, dict] = {}
series_list = []
for t in find_templates(data_text):
    if t.name != "MatchSchedule":
        continue
    team1_code = (t.args.named.get("team1") or "").strip()
    team2_code = (t.args.named.get("team2") or "").strip()
    date = (t.args.named.get("date") or "").strip()
    s1 = (t.args.named.get("team1score") or "").strip()
    s2 = (t.args.named.get("team2score") or "").strip()
    series_list.append({"team1": team1_code, "team2": team2_code, "date": date, "score": (s1, s2), "games": []})
    for arg_key, arg_value in t.args.named.items():
        if not arg_key.lower().startswith("game"):
            continue
        for g in find_nested_by_name(arg_value, "MatchSchedule/Game"):
            gid = (g.args.named.get("riot_platform_game_id") or "").strip()
            blue = (g.args.named.get("blue") or "").strip()
            red = (g.args.named.get("red") or "").strip()
            winner = (g.args.named.get("winner") or "").strip()
            entry = {
                "series_team1": team1_code,
                "series_team2": team2_code,
                "date": date,
                "blue": blue,
                "red": red,
                "winner": winner,
            }
            series_list[-1]["games"].append(entry)
            if gid:
                data_games[gid] = entry

print(f"Data games with riot_platform_game_id: {len(data_games)}")

# ---- match games by id and derive code -> name evidence per game ----
code_to_names: dict[str, set] = defaultdict(set)
evidence_lines: list[str] = []
matched_ids = 0
for gid, dg in data_games.items():
    sg = score_games.get(gid)
    if sg is None:
        continue
    matched_ids += 1
    # winner side in Data: 1=blue, 2=red
    winner_code = dg["blue"] if dg["winner"] == "1" else dg["red"]
    loser_code = dg["red"] if dg["winner"] == "1" else dg["blue"]
    # winner side in Scoreboards: 1=team1, 2=team2 (team1==blue verified)
    winner_name = sg["team1"] if sg["winner"] == "1" else sg["team2"]
    loser_name = sg["team2"] if sg["winner"] == "1" else sg["team1"]
    code_to_names[winner_code].add(winner_name)
    code_to_names[loser_code].add(loser_name)
    evidence_lines.append(
        f"{dg['date']} game {gid}: data blue={dg['blue']}/red={dg['red']} winner={dg['winner']} "
        f"|| scoreboard teams=('{sg['team1']}', '{sg['team2']}') winner={sg['winner']} "
        f"=> winner-code {winner_code!r} == winner-name {winner_name!r}"
    )

print(f"matched games by riot_platform_game_id: {matched_ids}")
print("\n=== per-game evidence ===")
for line in evidence_lines:
    print("  " + line)

print("\n=== code -> names observed via game-id matching ===")
for code in sorted(code_to_names):
    names = sorted(code_to_names[code])
    status = "CONSISTENT" if len(names) == 1 else "CONFLICT"
    print(f"  {code!r}: {names} [{status}]")

print("\n=== HLE/DPLUS determination ===")
for code in ("HLE", "DPLUS", "KRX", "NS", "T1", "KT", "GEN"):
    names = sorted(code_to_names.get(code, []))
    if len(names) == 1:
        print(f"  {code}: RESOLVED -> {names[0]!r}")
    elif len(names) > 1:
        print(f"  {code}: CONFLICT -> {names}")
    else:
        print(f"  {code}: no game-level evidence")
