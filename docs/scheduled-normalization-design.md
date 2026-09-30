# Scheduled Canonical Normalization Design (PHASE 18-4)

- 작성: 2026-09-30, PHASE 18-4 (설계 전용 단계 — 구현 없음)
- 근거: `docs/scheduled-match-schema.md` (18-2 / 18-3-A/B/C/D-EMEA 관측 기록),
  `docs/leaguepedia-schema.md`, `docs/policy-event-model.md`,
  `docs/team-code-mapping-verification.md`, `config/team_mappings.json`,
  `config/timezone_offsets.json`, `scripts/lib/validator.py`,
  `scripts/lib/timezones.py`, `scripts/lib/series_score.py`,
  `scripts/normalize_sample.py`, 전체 tests
- 네트워크 요청: **0회** (기존 raw fixture와 문서만 사용)
- Classification 태그: `[OBSERVED]` raw fixture에서 직접 확인 / `[OBSERVED_ABSENT]`
  해당 필드가 fixture에서 실제로 비어 있음 / `[UNKNOWN]` 증거 부족 / `[INFERENCE]`
  관찰에 기반한 합리적 추론 (직접 확인 아님) / `[DESIGN]` 향후 구현 제안

---

## 1. Scope

이 문서는 **설계안**이다. 다음을 하지 않는다:

- production normalization (`normalize_sample.py`), parser, validator,
  `series_score.py`, `team_mappings.json`, `timezone_offsets.json`,
  `matches.sample.json` 변경 — 전부 무변경 [OBSERVED: 본 단계 종료 시점까지 무변경]
- canonical scheduled data 생성/승격 없음
- 새 status 값 추가 없음 (아래 3-1에서 검토)
- 네트워크 요청 없음

대상: Leaguepedia `Data:` 페이지의 scheduled(미경기) MatchSchedule row를
canonical record로 승격하기 위한 분류/검증/변환 설계.

성공 조건: 18-3까지의 실제 증거만으로 구현 가능한 설계를 제시하고,
확정되지 않은 부분을 명확히 분리하는 것.

---

## 2. Evidence Baseline

설계의 입력이 되는 핵심 관측 (모두 `docs/scheduled-match-schema.md` 섹션 참조):

| # | 관측 | 태그 | 근거 fixture |
|---|---|---|---|
| E1 | scheduled row는 completed와 동일한 MatchSchedule 구조를 쓰며, 결과 필드(team1score/team2score/winner)가 빈 채로 존재한다 | OBSERVED | Worlds Play-In (6행), Worlds Main Event (40행), EMEA R5 (14행) |
| E2 | known-team scheduled: team1/team2가 실제 값으로 채워진 미경기 row 존재 (예: `team1=BIG`, `team2=SNSH`) | OBSERVED | EMEA 2026 Summer Main Event rows 65–78 |
| E3 | team 표현은 혼재: 코드(`BIG`) / 풀네임(`Bushido Wildcats`) / 축약(`Barca`) / 혼합(`G2 NORD`) — 한 row 내에서도 다름 (row 66, row 73) | OBSERVED | EMEA 동일 페이지 |
| E4 | pre-created Game block: BO1→1개, BO3→3개 (행별 effective bestof와 일치) | OBSERVED | EMEA rows 65–78 (총 30블록) |
| E5 | scheduled Game block의 `riot_platform_game_id` 전부 empty (0/30, 0/94, 0/96) | OBSERVED_ABSENT | EMEA / Worlds ME / Worlds PI |
| E6 | completed row는 rpgid 존재 (`LOLTMNT05_*` 등) — empty는 페이지 전체 관습이 아니라 사전 경기 상태 | OBSERVED | EMEA rows 1–64 |
| E7 | row-level `bestof`가 Start-level bestof를 덮어쓴다 (Start 1 + row 3 → game block 3개) | OBSERVED | EMEA rows 61–64, 71–78 (completed+scheduled 양쪽) |
| E8 | `team1=TBD` / `team2=TBD` 리터럴 플레이스홀더 존재 | OBSERVED | EMEA rows 79–93 |
| E9 | Worlds 페이지는 team1/team2 empty 슬롯 사용 | OBSERVED | Worlds Play-In/Main Event |
| E10 | status 전용 필드는 어느 페이지에서도 관측되지 않음 (postponed/cancelled 표기 포함) | OBSERVED_ABSENT | 전체 fixture |
| E11 | `dst` 값 변이: `yes`(KST/PST), `spring`, `no` — 의미 미확정 | OBSERVED / 의미 UNKNOWN | Worlds ME rows 17–40 |
| E12 | `timezone` 약어: `KST`, `PST` — `PST`는 curated mapping에 없어 현재 변환 불가 | OBSERVED | 전체 fixture |
| E13 | forfeit 완료행: series-level `ff=2` + `team2footnote`("failed to show up" 인용) + winner + score + Game block 0개 | OBSERVED | EMEA row 9 |
| E14 | scheduled 행의 `scheduledAt` 후보 시간(date/time/timezone/dst)은 존재하나 dst 의미가 UNKNOWN이라 UTC 변환 근거가 불완전 | OBSERVED + UNKNOWN | 전체 |
| E15 | identity resolution 실패는 row 파싱 실패와 다른 계층 (resolver가 UNKNOWN을 반환해도 scheduled 상태 자체는 유효) | OBSERVED | EMEA (mapping이 LCK 전용이라 14행 전부 UNKNOWN) |

---

## 3. Raw Classification

### 3-1. Raw scheduled 상태 3분류 [DESIGN]

raw `team1`/`team2` 값 상태에 따라 (team1, team2 각각 독립 판정):

| Raw state | 판정 조건 (원문 기준, trim 후) | 예 |
|---|---|---|
| `KNOWN_TEAMS_SCHEDULED` | 값이 non-empty **AND** `TBD` 아님 | `BIG`, `Bushido Wildcats` |
| `TBD_TEAMS_SCHEDULED` | 값이 리터럴 `TBD` (대소문자 보존 비교는 exact, 비교는 case-sensitive exact만) | `TBD` |
| `EMPTY_TEAMS_SCHEDULED` | 값이 empty | (빈 문자열) |

[E8], [E9], [E2]가 각각의 근거. 세 상태는 raw에서 실제로 공존하므로 하나로
뭉개면 정보 손실이 확정된다 [OBSERVED].

### 3-2. canonical `status` 매핑 [DESIGN]

현행 canonical status 집합 (`validator.py::ALLOWED_STATUSES`, 불변):
`scheduled, in_progress, completed, postponed, cancelled, unknown`.

설계 원칙: **status 체계를 확장하지 않는다.** raw 3상태는 status가 아니라
**team slot의 raw state**로 보존한다 (3-6 참조).

| Raw 상태 | canonical status | 조건 |
|---|---|---|
| KNOWN_TEAMS_SCHEDULED | `scheduled` | date/time 파싱 성공 시 |
| TBD_TEAMS_SCHEDULED | `scheduled` | 동일 |
| EMPTY_TEAMS_SCHEDULED | `scheduled` | 동일 |
| (date/time/timezone 파싱 불가) | `unknown` | 승격 보류, excluded 사유 기록 |

근거: raw 소스에 status 필드가 없으므로 [E10] status는 파이프라인의 도출값이며,
도출값의 어휘는 기존 validator 어휘에 맞춘다. TBD/empty 구분은 status가 아니라
아래 3-6의 `_provisional.teamSlotState`로 보존 — 이렇게 하면 Android 소비 스키마와
validator를 건드리지 않고 정보를 보존한다 [INFERENCE].

주의: `scheduled` 승격은 **관측 시점 대비 미래 date/time이 확인된 row에 한정**한다
(18-3-B/C/D 보고서의 판정 기준 준수). 관측 시점이 지나면 재수집 전까지
status를 재판정하지 않는다 (stale 데이터는 그대로 발행 — policy-event-model의
원칙과 동일).

---

## 4. Team Identity Design

기존 exact resolver (`series_score.TeamIdentityResolver`) 재사용 [DESIGN].

- 허용: exact code, exact name, 이미 승인된 case-insensitive exact
  (18-3-A 결정 사항 — `Dplus KIA`→`DPLUS` 등), config에 기재된 값만
- 금지: substring/prefix/약어 추측/edit distance/fuzzy/사람 추측 매핑 (기존 원칙 유지)
- team1/team2는 **각각 독립** RESOLVED/UNKNOWN [DESIGN]

핵심 구분 (18-3-D-EMEA에서 확립):

```
identity resolution failure != match parsing failure
```

`team1=BIG → UNKNOWN, team2=SNSH → UNKNOWN`이어도 그 row는 정상적으로
관찰된 scheduled match다 [E15]. 따라서:

- identity UNKNOWN → canonical record는 생성 가능하되, `team1Id/team2Id`는
  provisional raw 값을 그대로 쓰고(기존 `teamIdSource: leaguepedia-team-code`
  관례의 연장) `_provisional.identityStatus: "UNKNOWN"` 부착
- 매핑이 확정되면 재정규화로 치환 (deterministic id는 raw 값 기반이므로
  id 안정성은 15장 구현 계획에서 다룸)

EMEA 팀들은 현 config에 없으므로 전부 UNKNOWN이며, **이번 단계에서 새 매핑을
만들지 않는다** (18-3-D-EMEA 결정 유지).

---

## 5. BestOf Resolution

hierarchy [DESIGN — E7에서 유도, 구현은 승인 후]:

```
1. row-level bestof      (정수이면 채택)
2. Start-level bestof    (row absent 시)
3. UNKNOWN               (둘 다 없거나 비정수)
```

game block count는 **별도 evidence**로 기록하며 bestof 자체로 취급하지 않는다:

| row bestof | Start bestof | game blocks | 판정 |
|---|---|---|---|
| 3 | 1 | 3 | row로 해석, 일치 → OK [E7] |
| 3 | 1 | 1 | CONFLICT (completed) / WARNING (scheduled — EMEA R5에서 row bo=3이 3블록이었으므로 scheduled에서 불일치는 비정상) |
| absent | 3 | 3 | Start로 해석, 일치 → OK |
| absent | absent | n | bestOf=null + validation WARNING |
| 3 | 3 | 3 | OK |
| row 3 / blocks 5 (BO5 경기 중 3플레이 등) | — | — | completed에서는 정상 (played ≤ bestof 규칙, 기존 normalize_sample 로직과 동일) |

scheduled 행의 game block count는 "예상 최대 경기 수"의 관측값일 뿐이며,
completed 행은 **플레이된 경기 수**와 일치했다 [OBSERVED: EMEA row 61(0-2)→2블록,
row 62(1-2)→3블록, LCK fixture 40행]. 두 상태에서 block count의 의미가 다르므로
검증 규칙도 분리한다 (9장 V7/V8).

---

## 6. Score / Winner Handling

[E1]에 따라 scheduled row의 `team1score/team2score/winner`는 **키는 존재하고
값이 비어** 있다 [OBSERVED_ABSENT].

절대 규칙 [DESIGN]:

- empty score/winner를 `0`이나 `0:0`으로 채우지 않는다
- scheduled canonical: `score: null`, winner 정보는 status에서만 표현
  (`status="scheduled"`이면 winner 없음이 자명)
- 추후 경기가 끝난 뒤 재수집되면 동일 id로 completed record가 대체 —
  0:0이 남아 "안 친 경기"로 오기되는 것을 방지

`score: null`의 스키마 영향: 현행 `validator.validate_match`는 score를
non-negative int 쌍으로 요구한다. 설계상 scheduled record는 **validator 확장이
필요**하며(15장), 확정 전에는 어떤 scheduled record도 canonical에 승격하지
않는다. 이는 validator 변경이 승인된 구현 단계의 일부임을 의미한다.

---

## 7. RPG ID Handling

[E5] scheduled Game block의 rpgid는 전부 empty였다 (3개 페이지, 총 220 블록).

- **synthetic rpgid 생성 금지** [DESIGN]
- canonical: Match 레벨 스키마에는 rpgid 필드를 넣지 않는다. Game 레벨 데이터가
  canonical로 승격될 때(현재 설계상 시리즈 레벨만 승격) rpgid는
  `null`(OBSERVED_ABSENT 보존)이며 raw에만 남는다
- 일반화 금지: "모든 scheduled match는 rpgid가 없다"고 단언하지 않는다 —
  관측된 범위에서 preassignment는 **한 번도 관측되지 않았다**는 표현이 정확하다
  [UNKNOWN: preassignment 존재 여부]
- completed [E6]와 scheduled [E5]의 차이는 검증 규칙으로 활용:
  scheduled 상태의 record에 rpgid가 나타나면 (재수집 지연 등) WARNING

---

## 8. TBD vs Empty

[E8] vs [E9]: raw에서 두 가지 다른 "미정" 표현이 공존한다 [OBSERVED].

[DESIGN] canonical 보존 방식 — status를 늘리지 않고 `_provisional` 메타로 보존:

```json
"_provisional": {
  "teamSlotState": {"team1": "KNOWN", "team2": "KNOWN"},
  "teamSlotRaw":   {"team1": "BIG",  "team2": "SNSH"}
}
```

- KNOWN / TBD / EMPTY 세 값을 그대로 기록 (3-1의 raw 판정 결과)
- `team1=TBD` → identity로는 UNKNOWN일 수 있지만 raw state가 `TBD`임을 보존
- `team1=""` → raw state가 `EMPTY`임을 보존
- 이유: TBD와 empty는 **raw 소스의 다른 표기이며**, 어느 쪽이 어떤 맥락에서
  쓰이는지(대진 확정 전후, 이벤트별 관습) 아직 UNKNOWN이므로 정규화 단계에서
  뭉개면 나중에 되돌릴 수 없다
- Android 노출 여부: canonical 소비자는 `team1Id=null`만 보면 되고(아래 13장),
  raw state는 진단/재현용 메타로 유지

---

## 9. Date / Time / DST Policy

현황: date/time/timezone/dst는 scheduled 행에 존재 [E14], dst 의미는
UNKNOWN [E11], `PST`는 curated mapping에 없음 [E12].

정책 비교 [DESIGN]:

| 선택지 | 채택 | 이유 |
|---|---|---|
| A. raw date/time/timezone/dst 보존 | **채택** | 손실 없음, 재해석 가능 |
| B. 검증 가능한 timezone만 UTC 변환 | **채택** (기존 KST 방식 연장) | `timezone_offsets.json`에 인간 검증 항목이 있을 때만 변환 — 기존 정책과 충돌 없음 |
| C. dst 의미 추측 | **거부** | [E11] `yes/spring/no` 의미 UNKNOWN |
| D. 변환 불가 시 처리 | **채택: 승격 보류 + excluded 기록** (정규화 실패 아님) | 기존 `normalize_sample.py`의 "UNKNOWN timezone → excluded" 정책과 동일. scheduled는 재수집으로 회복 가능하므로 하드 fail보다 보류가 적합 |

구체적으로: `PST`는 미국 태평양 표준시로 널리 알려져 있으나, **dst=yes/spring/no
변이가 관측되는 한 어떤 오프셋(UTC-8 vs UTC-7)이 맞는지 raw 증거만으로 확정할 수
없다.** 따라서 `PST`를 `timezone_offsets.json`에 추가하는 것조차 인간 검증
절차(18-2의 KST 추가 방식: IANA 대조 + fixture 검증)를 거쳐야 하며, 본 설계는
그 절차가 완료될 때까지 PST 행의 `scheduledAt`을 null로 두고 raw 값을 보존한다.

`dst` 플래그 자체는 변환에 사용하지 않는다 (timezones.py의 현행 동작 유지:
fixed-offset zone에서 dst 플래그는 warning으로 기록).

---

## 10. Forfeit / Postponed / Cancelled

- Forfeit [E13, OBSERVED]: series-level `ff` + `team*footnote` + winner +
  score + Game block 0개. **완료된 경기의 한 형태**로 취급하며
  postponed/cancelled와 다른 상태다. canonical에서는 `status="completed"`
  (winner/score가 관측됨) + `_provisional.forfeit` 메타로 보존을 제안 [DESIGN].
  단 ff의 정확한 어휘(1/2 외 값 존재 여부)는 관측 1건뿐이므로 구현 시
  `ff not in {"1","2", ""}` → WARNING으로 fail-closed.
- Postponed / cancelled: **raw 표현이 관측된 적 없음** [UNKNOWN, E10].
  새 status를 추측해 만들지 않는다. canonical 어휘에 이미 존재하는
  `postponed`/`cancelled`는 소스 증거가 확보될 때까지 사용하지 않는다.
- 게임 미실시 판정 규칙도 추측하지 않는다 (예: "date가 지났는데 score가 비면
  postponed" 같은 규칙은 근거 없음 — 재수집 지연/입력 지연과 구분 불가).

---

## 11. Validation Rules (proposed)

현행 `validate_match`는 completed 전제로 작성되어 있다. scheduled record를 위한
추가 규칙 제안 [DESIGN — 구현은 승인 후]:

| # | 규칙 | 분류 |
|---|---|---|
| V1 | status="scheduled"인데 winner/score에 non-empty 값 → **ERROR** (status와 결과 공존 불가; 소스 오류) | ERROR |
| V2 | scheduled score가 0:0으로 채워진 record → **ERROR** (6장 규칙 위반, 생성 자체를 금지) | ERROR |
| V3 | score 음수 → **ERROR** (기존 규칙 유지) | ERROR |
| V4 | date/time 형식 불량 (`YYYY-MM-DD`/`HH:MM` 위반) → **ERROR** | ERROR |
| V5 | timezone이 curated mapping에 없음 → **ERROR 아님**: scheduledAt=null + record를 canonical에서 제외하거나 `unknown` status로 격리 (9장 D) | WARNING + 제외 |
| V6 | dst 플래그가 mapping과 모순 (예: fixed zone에 dst=yes) → **WARNING** (기존 timezones.py 동작) | WARNING |
| V7 | scheduled: game block 수 ≠ effective bestof → **WARNING** (pre-creation 관습은 관측됐으나 보장은 아니므로) | WARNING |
| V8 | completed: game block 수 > effective bestof → **ERROR**; < 플레이된 경기 수 → **ERROR** | ERROR |
| V9 | team1/team2 raw empty → **유효한 scheduled-empty 상태** (ERROR 아님; `teamId=null` 허용 필요) | OK |
| V10 | team1/team2 = `TBD` → **유효한 explicit TBD 상태** (ERROR 아님) | OK |
| V11 | identity UNKNOWN → **parsing failure 아님** (4장) | OK + `_provisional` |
| V12 | scheduled record에 rpgid 존재 → **WARNING** (7장; 재수집 혼선 신호) | WARNING |
| V13 | row bestof=3 vs blocks=1 (scheduled) → **WARNING** (5장 표) | WARNING |
| V14 | synthetic rpgid 생성 시도 → **설계상 금지** (검증이 아니라 생성기에서 원천 차단) | 금지 |
| V15 | `ff` 값이 {1, 2} 외 → **WARNING** (10장, 관측 1건 한정) | WARNING |

분류 기준: ERROR = canonical 승격 불가 / WARNING = 승격 가능하나 기록 유지 /
OK = 정상 상태.

---

## 12. Conflict Detection

향후 다중 소스(Leaguepedia + Oracle's Elixir 등) 대조 시 [DESIGN]:

- 충돌 유형: scheduled↔completed 상태 충돌, 팀 불일치, 시간 불일치,
  bestof 불일치, score 불일치, winner 불일치
- 기록 방식: 충돌 발견 시 **어느 소스를 승자로 정하지 않는다** —
  `conflicts` 목록에 `{type, sources: [{source, value}], detectedAt}`를 남기고
  인간 리뷰 전까지 해당 record는 승격 보류. 이는 fail-closed 원칙
  (policy-event-model.md의 hard rules와 동일 계열) 및 18-1의
  "conflict = 0 검증 후 승격" 관행의 연장
- scheduled 특유 규칙: 한 소스가 scheduled, 다른 소스가 completed면
  시점 차이일 수 있으므로 즉시 충돌이 아니라 `observation-time mismatch`로
  분류 후 재수집으로 해소 시도 → 불해소 시 인간 리뷰
- team 비교는 양측 모두 exact resolver로만 수행 (fuzzy 금지)

---

## 13. Canonical JSON Proposal

scheduled match의 목표 형태 [DESIGN]. 기존 envelope/schema(Phase 10/17)와의
관계를 주석으로 표기:

```json
{
  "id": "lp:EM 2026 Summer Main Event:2026-09-30:BIG:SNSH",
  "league": {"id": "EM", "name": "EMEA Masters", "region": "EU"},
  "tournament": {"id": "EM 2026 Summer", "name": "EMEA Masters 2026 Summer"},
  "stage": {"id": "Round 5", "name": "Round 5"},
  "team1Id": "BIG",
  "team2Id": "SNSH",
  "scheduledAt": null,
  "status": "scheduled",
  "bestOf": 1,
  "score": null,
  "sources": [
    {
      "source": "leaguepedia",
      "kind": "raw_fixture",
      "ref": "raw/leaguepedia/page_EMEA_Masters_2026_Summer_Main_Event.wikitext"
    }
  ],
  "lastUpdatedAt": "2026-09-30",
  "_provisional": {
    "teamIdSource": "leaguepedia raw value (identity unresolved)",
    "teamSlotState": {"team1": "KNOWN", "team2": "KNOWN"},
    "bestOfSource": "row-level bestof (overrides Start bestof=1)",
    "timeRaw": {"date": "2026-09-30", "time": "06:00",
                "timezone": "PST", "dst": "yes",
                "utcConversion": "PENDING_TIMEZONE_REVIEW"}
  }
}
```

설계 질문에 대한 답:

- **team1Id/team2Id가 null일 수 있는가?** raw가 EMPTY 또는 TBD일 때는 null.
  KNOWN이지만 identity unresolved일 때는 raw 값을 provisional로 넣는다
  (빈 문자열 금지). 현행 validator는 non-empty string을 요구하므로
  스키마 확장이 필요함을 명시한다 (15장).
- **score가 null일 수 있는가?** scheduled에서는 null (6장).
- **bestOf가 null일 수 있는가?** row/Start 모두 absent일 때만 null (5장 3순위).
  관측상 null 사례는 없었으나 허용 [INFERENCE].
- **rpgid를 canonical Match에 넣는가?** 넣지 않는다 (7장). 게임 레벨 승격 시에만
  게임 record에 null로 등장.
- **raw representation 보존 범위**: `_provisional.timeRaw`에 date/time/timezone/dst
  원문, `_provisional.teamSlotRaw`에 team 원문. Canonical 본체는 정제된 값만.
- **TBD/empty 반영**: `_provisional.teamSlotState` (8장).

기존 스키마와의 관계: 필드 이름/구조는 completed record와 동일
(`normalize_sample.py` 출력 참조). 차이는 값의 nullability뿐이므로
Android `RemoteDataEnvelope` 소비자는 status/score null 처리만 추가하면 된다
(Android 변경은 본 프로젝트에서 하지 않음 — 승격 승인 후 별도 안내).

---

## 14. Test Matrix (proposed — 본 단계에서 구현하지 않음)

| # | 케이스 | 입력 근거 | 상태 |
|---|---|---|---|
| T1 | known-team scheduled | EMEA rows 65–78 | fixture 있음 |
| T2 | TBD scheduled | EMEA rows 79–93 | fixture 있음 |
| T3 | empty-team scheduled | Worlds Play-In / Main Event | fixture 있음 |
| T4 | empty score/winner | T1과 동일 | fixture 있음 |
| T5 | row-level bestof override | EMEA rows 61–64, 71–78 | fixture 있음 |
| T6 | Start-level bestof | LCK rounds34 / Worlds | fixture 있음 |
| T7 | unknown bestof (row+Start absent) | — | **fixture 필요** |
| T8 | bestof/game-block conflict | — | **fixture 필요** (합성 행은 금지 원칙 유지) |
| T9 | empty rpgid | T1 | fixture 있음 |
| T10 | resolved team | LCK codes (T1/GEN/…) | fixture 있음 |
| T11 | unresolved team | EMEA rows 65–78 | fixture 있음 |
| T12 | malformed team mapping | — | fixture 불필요 (config 단위 테스트로 가능) |
| T13 | invalid date | — | fixture 필요 (현 fixture의 date는 전부 정상) |
| T14 | unresolved DST (PST 보류) | Worlds/EMEA 전체 | fixture 있음 |
| T15 | completed | LCK rounds34 등 | fixture 있음 |
| T16 | forfeit | EMEA row 9 | fixture 있음 |
| T17 | postponed representation | — | **fixture 필요 (UNKNOWN)** |
| T18 | cancelled representation | — | **fixture 필요 (UNKNOWN)** |
| T19 | TBD≠empty≠known 보존 검증 | T1/T2/T3 조합 | fixture 있음 |
| T20 | identity failure ≠ parse failure | T11 | fixture 있음 |

원칙: 실제 fixture가 없는 항목(T7, T8, T13, T17, T18)은 합성 데이터로
억지로 채우지 않고 "fixture needed"로 표시한다 (기존 fail-closed 관행).

---

## 15. Implementation Plan (승인 후 별도 단계)

1. **스키마/validator 확장 승인** — `validate_match`에 scheduled 모드 추가
   (score null, teamId null 허용, V1–V15 규칙). 기존 completed 검증은 불변.
2. **`scripts/lib/scheduled_normalize.py` 신설** — normalize_sample.py는 건드리지
   않고 별도 모듈로 구현 (completed 파이프라인 무영향 보장).
   입력: raw series record / 출력: 13장 형태 + excluded 사유.
3. **bestof resolver**, **team slot classifier**를 순수 함수로 분리 → 단위 테스트.
4. **14장 테스트 매트릭스 중 fixture 있는 항목 구현** — 신규 테스트 파일
   (`test_scheduled_normalize.py` 예정), 합성 fixture 금지.
5. **PST timezone 리뷰** — 인간 검증 + IANA 대조 후 `timezone_offsets.json`에
   추가 (18-2의 KST 절차 재사용). 완료 전까지 scheduledAt=null 유지.
6. **EMEA scheduled 샘플 승격 여부 별도 결정** — 이 설계만으로 자동 승격 아님.
7. Android 측은 승격 승인 후 별도 안내 (본 저장소 작업 아님).

각 단계는 승인 게이트를 두고, 실패 시 fail-closed (승격 보류).

---

## 16. Explicit UNKNOWN List

- dst=yes/spring/no 의미 (E11)
- PST 오프셋 확정 (dst 변이 때문에 raw 증거만으로는 불가, E11/E14)
- rpgid preassignment 존재 여부 (관측 0건이나 부재 증명 아님)
- postponed/cancelled raw 표현 (E10)
- `initialorder` 의미
- `qq` 키 의미
- `recap` vs `vod` 키 차이의 적용 범위
- TBD vs empty 두 관습의 적용 맥락 (이벤트별? 시점별?)
- Worlds BO3 스윕 시 3블록 유지 여부 (블록 수 축소가 EMEA 편집 행위인지)
- `ff` 값 어휘 전체 (관측 1건)
- EMEA 팀 identity (config 미등재 — 본 단계에서 추가 안 함)
- Fandom 정책/라선스/레이트리밋 세부 (기존 문서 유지)

---

## 17. Open Questions Requiring Future Evidence

1. PST(또는 PDT) 행의 실제 오프셋을 확정할 수 있는 독립 증거 — 예: 이미 완료된
   PST 표기 경기의 공식 시작 시각 대조 (재수집 1회로 해소 가능)
2. Worlds Main Event 재수집 (2026-10-18 이후): known-team + rpgid 동시 확인,
   TBD/empty 사용 패턴 대조
3. postponed/cancelled 사례를 포함한 Data 페이지 확보 (네트워크 예산 내)
4. row bestof와 game block 수가 불일치하는 실제 사례 (V7/V13 튜닝용)
5. `ff`가 1/2 외 값을 가지는 사례
6. EMEA `Magaza`/`Magaza Esports`, `Barça eSports`/`Barca` 동일성 — 매핑은
   실제 증거(game-id 대조 등 18-1 방식)로만 확정
7. TBD 행이 경기 시작 후 어떻게 변하는지 (TBD → 실제팀 → completed 전이 관측)

---

## 설계 완료 선언

본 문서는 18-3까지의 관측만으로 작성되었으며, 구현은 포함하지 않는다.
여기서 중단한다 (handoff §8: 설계 완료 후 반드시 중단).
