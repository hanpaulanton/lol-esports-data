# Team Code Mapping Verification

- 최종 검증: 2026-09-30 (PHASE 18-1)
- 검증 도구: `tests/hle_dplus_gameid_matching.py` (riot_platform_game_id 매칭),
  `scripts/verify_team_mappings.py` (날짜별 제약 전파), `tests/analyze_scoreboard_schema.py` (key 추출)
- 원칙: 저장된 raw fixture만 사용. 신규 HTTP 요청 0건. 이름 유사성/일반 지식 기반 추론 금지.

## 1. 검증 경위 (1차 시도 → 반증 → 수정 → 확정)

1. **1차 시도 (PHASE 17)**: Scoreboards의 `Scoreboard/Header` 6건만으로 날짜별 순서 매칭 시도 →
   Header 순서가 MatchSchedule과 반대인 경기 다수로 실패 (`T1 vs KT` ↔ `KT Rolster vs T1`).
2. **2차 시도 (PHASE 18-1 첫 실행)**: `Scoreboard/Season 16`의 `team1/team2`(풀네임)로 날짜별
   게임 수 매칭 시도 → **게임 수 불일치** 발견: 07-29는 Scoreboard 4게임 vs Data 2시리즈.
   원인: Scoreboards는 **게임 단위**(BO3의 개별 게임), Data는 **시리즈 단위**.
3. **3차 시도 (성공)**: 각 게임은 `rpgid`(=MatchSchedule/Game의 `riot_platform_game_id`)를 가지므로
   **게임 ID로 직접 매칭**. 게임의 승자 방향(Data: winner 1=blue/2=red, Scoreboards: 1=team1/2=team2)과
   사이드 소속(blue gold 합 == team1g, red gold 합 == team2g — 14/14 게임 검증)을 결합하면
   각 게임에서 (승자 코드↔승자 이름), (패자 코드↔패자 이름) 페어가 확정된다.
   - 1차 실행에서 loser 코드 논리 버그(blue/red 반전)로 CONFLICT 오판 → 수정 후 재검증 →
     14/14 게임 일관. (1차 오판 경위도 기록 보존)

## 2. 게임 단위 증거 (14경기 전부)

| game id (rpgid) | date | Data codes (blue/red) | winner(Data) | Scoreboard names (team1/team2) | winner(SB) | 결정 페어 |
|---|---|---|---|---|---|---|
| LOLTMNT02_442746 | 07-29 | KRX / NS | 2 (NS) | Kiwoom DRX / Nongshim RedForce | 2 (Nongshim) | NS=Nongshim, KRX=Kiwoom |
| LOLTMNT02_441911 | 07-29 | KRX / NS | 2 (NS) | 동일 | 2 | 동일 |
| LOLTMNT02_441926 | 07-29 | T1 / KT | 2 (KT) | T1 / KT Rolster | 2 (KT) | KT=KT Rolster, T1=T1 |
| LOLTMNT02_441944 | 07-29 | KT / T1 | 1 (KT) | KT Rolster / T1 | 1 (KT) | 동일 (사이드 스왑) |
| LOLTMNT02_444167 | 07-30 | BNK FEARX / DN SOOPers | 1 (BFX측) | BNK FEARX / DN SOOPers | 1 | BNK FEARX=BNK FEARX, DN SOOPers=DN SOOPers |
| LOLTMNT02_444200 | 07-30 | 동일 | 1 | 동일 | 1 | 동일 |
| LOLTMNT02_443344 | 07-30 | **HLE / DPLUS** | 2 (DPLUS) | **Hanwha Life Esports / Dplus Kia** | 2 (Dplus Kia) | **DPLUS=Dplus Kia, HLE=Hanwha Life Esports** |
| LOLTMNT02_444234 | 07-30 | **DPLUS / HLE** (사이드 스왑) | 2 (HLE) | **Dplus Kia / Hanwha Life Esports** (사이드 스왑) | 2 (Hanwha) | **HLE=Hanwha Life Esports, DPLUS=Dplus Kia** (교차 일관) |
| LOLTMNT02_443370 | 07-30 | HLE / DPLUS | 2 (DPLUS) | Hanwha Life Esports / Dplus Kia | 2 | 동일 |
| LOLTMNT02_444480 | 07-31 | GEN / T1 | 2 (T1) | Gen.G / T1 | 2 (T1) | GEN=Gen.G, T1=T1 |
| LOLTMNT02_444494 | 07-31 | T1 / GEN | 1 (T1) | T1 / Gen.G | 1 (T1) | 동일 (사이드 스왑) |
| LOLTMNT02_444519 | 07-31 | KRX / HANJIN BRION | 2 (BRO측) | Kiwoom DRX / HANJIN BRION | 2 (HANJIN) | HANJIN BRION=HANJIN BRION, KRX=Kiwoom DRX |
| LOLTMNT02_443601 | 07-31 | KRX / HANJIN BRION | 1 (KRX) | Kiwoom DRX / HANJIN BRION | 1 (Kiwoom) | 동일 (사이드 스왑) |
| LOLTMNT02_443609 | 07-31 | KRX / HANJIN BRION | 1 | 동일 | 1 | 동일 |

`team1 == blue side` 검증: 14/14 게임에서 blue1~5 gold 합 == team1g, red1~5 gold 합 == team2g (CONFIRMED).

## 3. 최종 판정

| Leaguepedia code | 이름 (fixture) | HUMAN_PROVIDED | 판정 |
|---|---|---|---|
| T1 | T1 | T1 | OBSERVED (exact) |
| GEN | Gen.G | GEN.G | OBSERVED_CASE_VARIANT (fixture 철자 Gen.G가 정본) |
| KT | KT Rolster | KT | OBSERVED (exact) |
| HLE | Hanwha Life Esports | HLE | **OBSERVED — PHASE 18-1 승격** (게임 매칭으로 1:1 확정) |
| DPLUS | Dplus Kia | DK | **OBSERVED — PHASE 18-1 승격** (이름 페어링; 인간 코드 DK 자체는 fixture 미등장) |
| KRX | Kiwoom DRX | (없음) | OBSERVED |
| NS | Nongshim RedForce | (없음) | OBSERVED |
| DN SOOPers | DN SOOPers | DNS | OBSERVED (인간 코드 DNS는 fixture 미등장) |
| BNK FEARX | BNK FEARX | BFX | OBSERVED (인간 코드 BFX는 fixture 미등장) |
| HANJIN BRION | HANJIN BRION | BRO | OBSERVED (인간 코드 BRO는 fixture 미등장) |

- **CONFLICT: 0건**. 모든 10개 코드가 게임 단위 직접 매칭으로 확정됨.
- fixture 표기 특이사항: `Dplus Kia` (인간 제공 표기는 `Dplus KIA`) — 소문자 'i' 표기 변형은 fixture 철자를 정본으로 기록.

## 4. 함의

1. 인간 제공 코드와 Leaguepedia 코드는 **별개 체계**로 유지 (config/team_mappings.json의 두 필드 분리).
2. `DK/DNS/BFX/BRO`는 Leaguepedia 데이터에는 나타나지 않는 표기 — 향후 다른 소스(예: lolesports.com 계열)를
   도입할 때 해당 소스의 코드로는 나타날 수 있으므로 humanProvidedCode 필드에 보존.
3. canonical team ID는 여전히 미확정 (leaguepediaCode/humanProvidedCode 모두 임시 식별자).
