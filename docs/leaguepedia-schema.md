# Leaguepedia Observed Schema

- 조사: 2026-09-29, 실제 HTTP 응답 기반 (raw/leaguepedia/ 참조)
- Confidence 정의:
  - **CONFIRMED** — API/페이지 응답에서 직접 관측된 필드/동작
  - **OBSERVED** — 실제 응답에서 관측되었으나 의미는 커뮤니티 문서 기반 해석
  - **INFERRED** — 관측되지 않았으며 커뮤니티 문서로부터 추론
  - **UNKNOWN** — 확인 불가

## 관측 경로 요약 (PHASE 16 실측)

| 경로 | 결과 | Confidence |
|---|---|---|
| `api.php?action=cargotables` | HTTP 200, Cargo 테이블 목록 JSON 반환 (`MatchSchedule`, `MatchScheduleGame`, `ScoreboardGames`, `ScoreboardPlayers`, `Leagues`, `RosterChanges`, `Players` 등) | CONFIRMED |
| `api.php?action=cargoquery&tables=...` | HTTP 200 + JSON `{"error":{"code":"ratelimited",...}}` 반복 관측(백오프 후에도). **row 데이터 미확보** | CONFIRMED (제한 자체) |
| `api.php?action=query` (opensearch/search/allpages/revisions) | HTTP 200, 정상 동작 — **데이터 페이지 wikitext 확보에 성공** | CONFIRMED |
| 일반 웹페이지/robots.txt | HTTP 403 (HTTP 클라이언트 차단) | CONFIRMED |

`cargoquery`의 row 스키마는 미확보. 대신 **데이터 페이지 wikitext**(`Data:` 네임스페이스)에서
Cargo 테이블을 채우는 실제 템플릿 인자를 관측했다 — 아래 표는 그 관측 결과다.

## MatchSchedule (시리즈/경기 예정·결과)

데이터 소스 페이지: `Data:<Tournament>` (ns 10008), 예: `Data:LCK/2026 Season/Rounds 3-4`
(raw/leaguepedia/page_data_lck_rounds34.wikitext, 54,964 bytes).
`{{MatchSchedule/Start}}` 블록 안에 `{{MatchSchedule}}`(시리즈)가 나열되고,
각 시리즈 안에 `{{MatchSchedule/Game}}`(게임)가 내장된다.

### 시리즈 레벨 — `{{MatchSchedule/Start}}`

| Field | Type | Example | Meaning | Confidence |
|---|---|---|---|---|
| tab | string | `Week 10` | 주차/탭 구분 | OBSERVED |
| bestof | int | `3` | 이 탭(블록) 경기의 기본 BO | OBSERVED (탭 단위임에 주의 — 시리즈별 필드 아님) |
| shownname | string | `LCK 2026 Rounds 3-4` | 표시명 | OBSERVED |

### 시리즈 레벨 — `{{MatchSchedule}}`

| Field | Type | Example | Meaning | Confidence |
|---|---|---|---|---|
| team1 | string(코드) | `KRX` | 팀1 **축약 코드** (팀명→ID 매핑 필요) | OBSERVED |
| team2 | string(코드) | `NS` | 팀2 축약 코드 | OBSERVED |
| team1score | int | `0` | 시리즈 팀1 스코어 | OBSERVED |
| team2score | int | `2` | 시리즈 팀2 스코어 | OBSERVED |
| winner | int | `2` | 시리즈 승자(1/2). 완료 경기에서만 관측 | OBSERVED |
| date | string | `2026-07-29` | 경기 날짜(현지) | OBSERVED |
| time | string | `17:00` | 경기 시각(현지) | OBSERVED |
| timezone | string | `KST` | 위 기입자 기준 시간대 | OBSERVED |
| dst | yes/no | `yes` | 서머타임 플래그 | OBSERVED |
| initialorder | int | `1` | 페이지 내 표기 순번 | OBSERVED |
| mvp / with / pbp / color | string | `Scout` | MVP/해설 등 부가 메타 | OBSERVED |
| stream / reddit / vodinterview / vodhl | URL | ... | 스트림/하이라이트 링크 | OBSERVED |
| status 전용 필드 | — | — | **관측되지 않음.** 예정 경기는 score/winner가 비어 있거나 미래 date일 것으로 추정 | INFERRED — 실제 예정 경기 row 미관측(UNKNOWN) |

### 게임 레벨 — `{{MatchSchedule/Game}}` (canonical은 시리즈 레벨; 게임 데이터는 raw 보존)

| Field | Type | Example | Meaning | Confidence |
|---|---|---|---|---|
| blue / red | string(코드) | `KRX` / `NS` | 블루/레드 팀 | OBSERVED |
| winner | int | `2` | 게임 승자(1/2) | OBSERVED |
| riot_platform_game_id | string | `LOLTMNT02_442746` | **Riot 플랫폼 게임 ID** (match-v5 등 Riot 기록과 연결 가능) | OBSERVED |
| first_sel / ssel / pick_sel / first_pick | string(코드) | `KRX` | 사이드/선픽 정보 | OBSERVED |
| ff | string | (빈 값 관측) | 포페이트 여부 | OBSERVED |
| vod / vodpb / vodstart / vodpost / vodhl | URL | ... | VOD 타임스탬프들 | OBSERVED |

그 외 관측: `{{TournamentGroups|groups=Legend Group, Rise Group|...}}`에 실제 그룹/팀 목록
(HLE, KT, T1, Gen.G, DPLUS KIA / DN SOOPers, Kiwoom DRX, Nongshim RedForce, BNK FEARX, HANJIN BRION) —
팀 코드 정규화 매핑의 원천이 될 수 있음. CONFIRMED(관측).

## ScoreboardGames (완료 경기, 게임 단위 상세)

데이터 소스 페이지: `<Tournament>/Scoreboards` (예: `LCK/2026 Season/Rounds 3-4/Scoreboards`,
raw/leaguepedia/page_lck_scoreboards.wikitext, 102,584 bytes). `{{Scoreboard/Header|Team1|Team2}}` +
`{{Scoreboard/Season 16|...}}`(게임 헤더) + `{{Scoreboard/Player|...}}`(선수 10명) 구조.
**cargoquery의 ScoreboardGames row 필드명은 미확보** — 아래는 wikitext 템플릿 인자 관측.

### 게임 헤더 — `{{Scoreboard/Season 16}}`

| Field | Type | Example | Meaning | Confidence |
|---|---|---|---|---|
| tournament | string | `LCK 2026 Rounds 3-4` | 토너먼트명 | OBSERVED |
| patch | string | `16.14` | 패치 버전 | OBSERVED |
| winner | int | `2` | 게임 승자(1/2) | OBSERVED |
| gamelength | string | `27:28` | 게임 길이 | OBSERVED |
| timezone / date / time / dst | string | `CET` / `2026-07-29` / `10:05` / `yes` | 게임 시작 시각 — **시간대가 기입자별로 다를 수 있음(KST/CET 혼재 관측)** → normalizer에서 UTC 변환 필수 | OBSERVED |
| rpgid | string | `LOLTMNT02_442746` | Riot 게임 ID (MatchSchedule/Game의 riot_platform_game_id와 동일 값 관측) | OBSERVED |
| version | string | `5` | 템플릿 버전 | OBSERVED |
| vodlink | URL | ... | VOD | OBSERVED |
| team1 | string | `Kiwoom DRX` | 팀1 **풀네임** (MatchSchedule의 코드와 다른 표기!) | OBSERVED |
| team1g / team1k / team1t / team1b / team1rh / team1vg / team1d / team1i | int | `50079` / `13` / `1` / `0` / `1` / `3` | gold/kills/towers/barons/rift herald/vanguards?/dragons?/inhibitors — **약어 의미는 확정되지 않음(추정: g=gold, k=kills, t=towers, b=barons)** | OBSERVED(값) + INFERRED(의미) |
| team1ban1..team1ban5 | string | `Poppy` | 밴 목록 | OBSERVED |
| blue1..blue5 / red1..red5 | `{{Scoreboard/Player}}` | ... | 선수별 상세(champion/kills/deaths/assists/gold/cs/items/runes) | OBSERVED |

**canonical 매핑 시 주의**: 시리즈 스코어는 이 테이블에 직접 없음 — Scoreboard 템플릿은 게임 단위이고
시리즈 스코어는 MatchSchedule의 team1score/team2score가 원천. (cargoquery의 ScoreboardGames에는
Team1Score/Team2Score 필드가 있다는 커뮤니티 문서가 있으나 미확보 — UNKNOWN.)

## 관측되지 않은 것 (UNKNOWN)

- `cargoquery`의 실제 row JSON(필드명/타입) — rate limit으로 미확보
- MatchSchedule의 예정(미완료) 경기 row — 관측한 페이지는 완료 주차만 포함
- BestOf의 시리즈별 값(Start 탭 단위로만 관측; 시리즈가 기본값과 다른 경우 처리 방식)
- ScoreboardGames Cargo row의 필드명/스코어 필드
- Fandom API의 공식 rate limit 수치와 Terms of Use 상세(본문 fetch 403)

## 향후 canonical 매핑 계획 (확인된 필드만 기술)

- `{{MatchSchedule}} date + time + timezone (+dst)` → 정규화 → canonical `scheduledAt` (ISO-8601 UTC)
- `{{MatchSchedule}} team1/team2` (코드) → 팀 코드 매핑 사전 → canonical `team1Id/team2Id`
- `{{MatchSchedule}} team1score/team2score` → canonical `score.team1/team2`
- `{{MatchSchedule/Start}} bestof` → canonical `bestOf` (탭 단위 기본값 — 시리즈별 예외 처리 방식은 PHASE 17에서 결정)
- `{{MatchSchedule}} winner 유무 + score 유무 + 날짜` → canonical `status` 매핑(예정/완료/기타) — 예정 row 관측 후 확정
- `{{MatchSchedule}} tournament/shownname` (페이지/Start 인자) → canonical `tournament/stage`
  (페이지 상위 `{{Infobox Tournament}}`의 `CM_StandardName`, `region=KR`, `sdate/edate`도 관측됨 — 보조 메타로 활용)
- `{{MatchSchedule/Game}} riot_platform_game_id` → canonical `sources`의 원격 참조 ID로 기록 예정
- Scoreboard 템플릿(게임 상세)은 canonical Match에 넣지 않고 raw 보존 (PHASE 16 지시 STEP 5)
