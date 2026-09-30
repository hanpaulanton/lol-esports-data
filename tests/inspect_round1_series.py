import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.leaguepedia_parser import find_templates, find_nested_by_name  # noqa: E402

wikitext = (ROOT / "raw" / "leaguepedia" / "page_data_lck_season_playoffs_scheduled.wikitext").read_text(encoding="utf-8")

# find the Round 1 series: Dplus Kia vs HANJIN BRION
for t in find_templates(wikitext):
    if t.name == "MatchSchedule":
        team1 = (t.args.named.get("team1") or "").strip()
        team2 = (t.args.named.get("team2") or "").strip()
        if team1 == "Dplus Kia" and team2 == "HANJIN BRION":
            print(f"=== series: {team1} vs {team2} (Round 1) ===")
            print(f"series args: team1score={t.args.named.get('team1score')!r} "
                  f"team2score={t.args.named.get('team2score')!r} winner={t.args.named.get('winner')!r}")
            for key, value in t.args.named.items():
                if key.lower().startswith("game"):
                    for g in find_nested_by_name(value, "MatchSchedule/Game"):
                        print(f"\n[{key}]")
                        for arg_key, arg_value in g.args.named.items():
                            print(f"  {arg_key} = {arg_value!r}")
            break
