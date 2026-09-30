"""PHASE 17 fixture structure re-check (read-only, prints observed facts)."""
import re
import pathlib

p = pathlib.Path(__file__).resolve().parents[1] / "raw" / "leaguepedia" / "page_data_lck_rounds34.wikitext"
t = p.read_text(encoding="utf-8")

starts = re.findall(r"\{\{MatchSchedule/Start\|([^}]*)\}\}", t)
series_blocks = re.findall(r"\{\{MatchSchedule\|", t)
game_blocks = re.findall(r"\{\{MatchSchedule/Game", t)

print("MatchSchedule/Start blocks:", len(starts))
for s in starts:
    print("  Start args:", " ".join(s.split()))
print("MatchSchedule series blocks:", len(series_blocks))
print("MatchSchedule/Game blocks:", len(game_blocks))

# rows without winner/score (potential scheduled rows)
series_raw = re.findall(r"\{\{MatchSchedule\|(.*?)\n\}\}", t, flags=re.S)
no_winner = 0
no_score = 0
for b in series_raw:
    flat = " ".join(b.split())
    has_winner = re.search(r"\|winner=\s*\d", flat)
    has_scores = re.search(r"\|team1score=\s*\d", flat) and re.search(r"\|team2score=\s*\d", flat)
    if not has_winner:
        no_winner += 1
    if not has_scores:
        no_score += 1
print("series without winner:", no_winner)
print("series without numeric scores:", no_score)

# distinct team codes
codes = re.findall(r"\|team1=([^|\n]+)\||\|team2=([^|\n]+)\|", t)
flat_codes = sorted({(a or b).strip() for a, b in codes})
print("distinct team codes observed:", flat_codes)

# distinct timezones
tzs = sorted(set(re.findall(r"\|timezone=([^|\n]+)", t)))
print("distinct timezones:", tzs)
dst = sorted(set(re.findall(r"\|dst=([^|\n]+)", t)))
print("distinct dst flags:", dst)
