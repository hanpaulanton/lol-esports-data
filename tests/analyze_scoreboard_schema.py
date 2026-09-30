"""Extract all argument keys used by {{Scoreboard/Season 16}} and
{{Scoreboard/Player}} in the collected Scoreboards fixture. Observation only —
no semantic interpretation of keys."""

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.leaguepedia_parser import (  # noqa: E402
    find_nested_by_name,
    find_templates,
    find_templates_by_name,
)

RAW = ROOT / "raw" / "leaguepedia" / "page_lck_scoreboards.wikitext"
text = RAW.read_text(encoding="utf-8")

top = find_templates(text)
name_counts: dict[str, int] = {}
for t in top:
    name_counts[t.name] = name_counts.get(t.name, 0) + 1
print("=== top-level template name counts (this page) ===")
for name, count in sorted(name_counts.items(), key=lambda kv: -kv[1]):
    print(f"{count:4d}  {name}")

season16 = find_templates_by_name(text, "Scoreboard/Season 16")
print(f"\n=== Scoreboard/Season 16 templates found: {len(season16)} ===")

s16_keys: dict[str, dict] = {}
player_keys: dict[str, dict] = {}
player_template_count = 0

for t in season16:
    for key, value in t.args.named.items():
        entry = s16_keys.setdefault(key, {"count": 0, "example": None})
        entry["count"] += 1
        if entry["example"] is None:
            entry["example"] = value.strip()
        for player in find_nested_by_name(value, "Scoreboard/Player"):
            player_template_count += 1
            for pkey, pvalue in player.args.named.items():
                pentry = player_keys.setdefault(pkey, {"count": 0, "example": None})
                pentry["count"] += 1
                if pentry["example"] is None:
                    pentry["example"] = pvalue.strip()

def dump(title, keys_dict, extra_note):
    print(f"\n=== {title} (distinct keys: {len(keys_dict)}){extra_note} ===")
    for key, info in sorted(keys_dict.items()):
        example = info["example"]
        marker = ""
        if example is not None and "{{Scoreboard/Player" in example:
            marker = " [nested Scoreboard/Player]"
            example = example[:60].replace("\n", " ") + "...(nested template)"
        print(f"{key!r:24} count={info['count']:3d}  example={example!r}{marker}")

def level_s16(key: str) -> str:
    if key.startswith("team1"):
        return "Team-level (team1)"
    if key.startswith("team2"):
        return "Team-level (team2)"
    if key.startswith("blue"):
        return "Blue-side slot (contains Scoreboard/Player)"
    if key.startswith("red"):
        return "Red-side slot (contains Scoreboard/Player)"
    return "Game-level (neither team nor player)"

def level_player(key: str) -> str:
    return "Player-level"

dump("Scoreboard/Season 16 keys", s16_keys, "")
print("\n--- level classification (Season 16) ---")
levels: dict[str, list[str]] = {}
for key in s16_keys:
    levels.setdefault(level_s16(key), []).append(key)
for level, keys in levels.items():
    print(f"{level}: {len(keys)} keys -> {', '.join(sorted(keys))}")

print(f"\n=== Scoreboard/Player templates found (nested): {player_template_count} ===")
dump("Scoreboard/Player keys", player_keys, "")
print("\n--- level classification (Player) ---")
print("Player-level: all", len(player_keys), "keys ->", ", ".join(sorted(player_keys)))
