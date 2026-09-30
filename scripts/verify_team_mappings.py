"""Verify HUMAN_PROVIDED team code mappings against saved Leaguepedia fixtures.

Offline only — reads the two raw fixtures collected in PHASE 16:
  raw/leaguepedia/page_data_lck_rounds34.wikitext   (MatchSchedule team codes + dates)
  raw/leaguepedia/page_lck_scoreboards.wikitext     (Scoreboard/Header team names + dates)

Method (revised after a first-order attempt was disproven by the data):
- The Scoreboards page often lists the SAME match with the teams in the
  OPPOSITE order (e.g. Data "T1 vs KT" appears as "KT Rolster vs T1"), so
  per-date ORDER matching is invalid.
- Instead: for each date where both fixtures have games, collect the SET of
  team codes and the SET of team names, then propagate constraints to a fixed
  point:
    1. literal string identity (code == name) confirms a pair;
    2. singletons within a game propagate;
    3. repeat until no new confirmation appears (cross-date chains resolve).
  Codes that appear in the fixture but cannot be paired 1:1 are recorded as
  PAIRING_UNCONFIRMED (never guessed).
- A code paired with two DIFFERENT names (case-insensitive) is a CONFLICT.

Classification of HUMAN_PROVIDED entries:
    OBSERVED                  code appears in fixture; fixture name matches the
                              claimed name exactly
    OBSERVED_CASE_VARIANT     matches except letter case; the fixture spelling
                              is recorded as the authoritative spelling
    PAIRING_UNCONFIRMED       code appears in fixture and the claimed pairing
                              does not contradict the fixture, but 1:1 pairing
                              could not be confirmed from the fixture alone
    NOT_OBSERVED              code never appears in fixture; the team itself
                              does appear under a different fixture identifier
    CONFLICT                  fixture pairs the code with a different team
"""

from __future__ import annotations

import json
import pathlib
import sys
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.leaguepedia_parser import find_templates  # noqa: E402

HUMAN_MAPPING = {
    "T1": "T1",
    "GEN": "GEN.G",
    "KT": "KT Rolster",
    "HLE": "Hanwha Life Esports",
    "DK": "Dplus KIA",
    "DNS": "DN SOOPers",
    "BFX": "BNK FEARX",
    "BRO": "HANJIN BRION",
}

data_text = (ROOT / "raw" / "leaguepedia" / "page_data_lck_rounds34.wikitext").read_text(encoding="utf-8")
score_text = (ROOT / "raw" / "leaguepedia" / "page_lck_scoreboards.wikitext").read_text(encoding="utf-8")

data_by_date: dict[str, list] = defaultdict(list)
score_by_date: dict[str, list] = defaultdict(list)

for t in find_templates(data_text):
    if t.name == "MatchSchedule":
        date = (t.args.named.get("date") or "").strip()
        data_by_date[date].append({
            "codes": {(t.args.named.get("team1") or "").strip(),
                      (t.args.named.get("team2") or "").strip()},
            "time": (t.args.named.get("time") or "").strip(),
        })

pending_header = None
for t in find_templates(score_text):
    if t.name == "Scoreboard/Header":
        names = t.args.positional
        pending_header = (
            names[0].strip() if len(names) > 0 else "",
            names[1].strip() if len(names) > 1 else "",
        )
    elif t.name == "Scoreboard/Season 16":
        date = (t.args.named.get("date") or "").strip()
        if pending_header is not None:
            score_by_date[date].append({"names": {pending_header[0], pending_header[1]}})
        pending_header = None

confirmed_code_to_name: dict[str, str] = {}
confirmed_name_to_code: dict[str, str] = {}
appeared_codes: set[str] = set()
per_game: list[dict] = []
unmatchable_dates: list[str] = []
matchable_games = 0

all_dates = sorted(set(data_by_date) | set(score_by_date))
for date in all_dates:
    d_games = data_by_date.get(date, [])
    s_games = score_by_date.get(date, [])
    if len(d_games) != len(s_games) or not d_games:
        unmatchable_dates.append(f"{date}: MatchSchedule rows={len(d_games)}, Scoreboard games={len(s_games)}")
        continue
    for d_game, s_game in zip(d_games, s_games):
        matchable_games += 1
        codes = set(d_game["codes"])
        names = set(s_game["names"])
        appeared_codes |= codes
        per_game.append({"date": date, "time": d_game["time"], "codes": codes, "names": names})

# constraint propagation to a fixed point
changed = True
while changed:
    changed = False
    for game in per_game:
        for code in game["codes"]:
            if code not in confirmed_code_to_name and code in game["names"]:
                confirmed_code_to_name[code] = code
                confirmed_name_to_code[code] = code
                changed = True
        unresolved_codes = game["codes"] - set(confirmed_code_to_name)
        unresolved_names = game["names"] - set(confirmed_name_to_code)
        if len(unresolved_codes) == 1 and len(unresolved_names) == 1:
            code = next(iter(unresolved_codes))
            name = next(iter(unresolved_names))
            confirmed_code_to_name[code] = name
            confirmed_name_to_code[name] = code
            changed = True
    for game in per_game:
        game["unresolved_codes"] = sorted(game["codes"] - set(confirmed_code_to_name))
        game["unresolved_names"] = sorted(game["names"] - set(confirmed_name_to_code))

print("=== per-game observed sets (matchable games only) ===")
for game in per_game:
    suffix = ""
    if game["unresolved_codes"]:
        suffix = f"  UNRESOLVED codes={game['unresolved_codes']} names={game['unresolved_names']}"
    print(f"  {game['date']} {game['time']}  codes={sorted(game['codes'])}  names={sorted(game['names'])}{suffix}")

print("\n=== unmatchable dates (no Scoreboard games in this fixture) ===")
for line in unmatchable_dates:
    print("  ", line)
print(f"matchable games: {matchable_games}; unmatchable dates: {len(unmatchable_dates)}")

print("\n=== CONFIRMED code -> name (raw fixture evidence) ===")
for code in sorted(confirmed_code_to_name):
    print(f"  {code!r} -> {confirmed_code_to_name[code]!r}")

print("\n=== HUMAN_PROVIDED verification ===")
results = []
for code, claimed in HUMAN_MAPPING.items():
    if code in confirmed_code_to_name:
        fixture_name = confirmed_code_to_name[code]
        if fixture_name == claimed:
            status = "OBSERVED"
            detail = f"exact fixture name {fixture_name!r}"
        elif fixture_name.casefold() == claimed.casefold():
            status = "OBSERVED_CASE_VARIANT"
            detail = f"case variant only; fixture spelling {fixture_name!r} is authoritative"
        else:
            status = "CONFLICT"
            detail = f"fixture pairs {code!r} with {fixture_name!r}"
    elif code in appeared_codes:
        status = "PAIRING_UNCONFIRMED"
        detail = "code appears in fixture but 1:1 pairing could not be confirmed from available games"
    else:
        status = "NOT_OBSERVED"
        detail = "code never appears in fixture (the team itself appears under a different fixture identifier)"
    results.append((code, claimed, status, detail))
    print(f"  {code:5} -> {claimed:22} {status:24} {detail}")

print("\n=== coverage ===")
print("fixture codes CONFIRMED:", sorted(confirmed_code_to_name))
print("fixture codes NOT confirmed:", sorted(appeared_codes - set(confirmed_code_to_name)))
print("human codes not present in fixture:", sorted(set(HUMAN_MAPPING) - appeared_codes))

# machine-readable output for the mapping file update
out = {"confirmed": confirmed_code_to_name, "results": results, "unmatchableDates": unmatchable_dates}
(ROOT / "tests" / "mapping_verification_result.json").write_text(
    json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
)
print("\nsaved: tests/mapping_verification_result.json")
