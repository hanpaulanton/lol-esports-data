# PRE-IMPLEMENTATION REPORT (PHASE 18-12) — complete

## Evidence chain (data repo, PHASE 18-1 verified — docs/team-code-mapping-verification.md)
10 Leaguepedia codes, all game-id matched (14/14 games, CONFLICT 0), config/team_mappings.json consistent:

| Leaguepedia code (= canonical match team1Id/team2Id value) | verified full name (fixture spelling authoritative) |
|---|---|
| T1 | T1 |
| GEN | Gen.G |
| KT | KT Rolster |
| HLE | Hanwha Life Esports |
| DPLUS | Dplus Kia |
| KRX | Kiwoom DRX |
| NS | Nongshim RedForce |
| DN SOOPers | DN SOOPers |
| BNK FEARX | BNK FEARX |
| HANJIN BRION | HANJIN BRION |

## Android existing canonical Team.id values (SampleData.kt — evidence, not invention)
- team-t1 / T1 / T1 / KR
- team-geng / Gen.G / GEN / KR
- team-hle / Hanwha Life Esports / HLE / KR
- team-dk / Dplus KIA / DK / KR   ← NOTE: name spelling "Dplus KIA" vs fixture-authoritative "Dplus Kia"; shortName "DK" is the human code, NOT the Leaguepedia code DPLUS
- (team-blg, team-g2 = CN/EU teams, irrelevant to LCK)

## Identity resolution decision (per §3 rules)
- Match.team1Id/team2Id values in canonical = Leaguepedia codes. The exact chain
  code → verified full name → existing Android Team.id:
  - T1 → T1 → team-t1 ✓
  - GEN → Gen.G → team-geng ✓
  - KT → KT Rolster → NO existing SampleData team → **no existing id**
  - HLE → Hanwha Life Esports → team-hle ✓
  - DPLUS → Dplus Kia → team-dk exists but its name spelling ("Dplus KIA"/short "DK") conflicts with fixture-authoritative "Dplus Kia"; id itself exists.
  - KRX, NS, DN SOOPers, BNK FEARX, HANJIN BRION → no existing SampleData teams

## ID POLICY DECISION (blocking)
Handoff §3.2: "Prefer existing canonical IDs rather than inventing new IDs.
If an ID does not exist, STOP and report it."

Strict reading = only T1/GEN/HLE/DPLUS get entries; KT/KRX/NS/DN SOOPers/
BNK FEARX/HANJIN BRION have no existing id → STOP.

However §7 expects "teams: verified LCK identities" (plural, the full set) and
§13 requires "every completed LCK match team reference resolves" — impossible
with only 4 of 10 teams. The consistent, evidence-safe resolution (proposed
below) is the deterministic id `team-<leaguepedia code>` used ONLY where no
existing id exists, keeping existing ids for T1/GEN/HLE/DPLUS.
