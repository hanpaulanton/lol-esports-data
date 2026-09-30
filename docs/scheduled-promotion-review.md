# Scheduled Promotion Review & Android Consumer Compatibility (PHASE 18-6)

- 작성: 2026-09-30, PHASE 18-6 (검토 전용 단계 — production/Android 무변경)
- 근거: `docs/scheduled-normalization-design.md` (18-4 설계), 18-5 구현
  (`scripts/scheduled_normalize.py`, `scripts/lib/validator.py`),
  실제 normalization 출력 (18-5 모듈을 로컬 실행한 결과 — 네트워크 0회),
  Android 저장소 `LolEsportsApp` 소스 전수 확인 (읽기 전용)
- Classification: [OBSERVED] 실제 코드/출력에서 확인 / [OBSERVED_ABSENT] /
  [UNKNOWN] / [INFERENCE] / [DESIGN]

---

## 1. Scope

18-5에서 구현된 scheduled normalization의 실제 출력(29 + 6 record)을 검토하고,
사용자가 승인한 UI 정책(null teamId → "TBD", null score → blank,
null scheduledAt → blank)을 현재 Android 코드가 지원할 수 있는지 확인한다.
**이번 단계에서 production data와 Android 코드는 변경하지 않는다.**

## 2. Phase 18-5 Baseline

- 121 → 146 tests PASS [OBSERVED: 본 단계 시작 시 `Ran 146 tests in 7.143s, OK` 재확인]
- EMEA: 93 rows → 29 scheduled records (14 known-team + 15 TBD), 64 completed 제외
- Worlds Play-In: 6 scheduled records (전부 EMPTY slot)
- Production promotion: NOT DONE / `matches.sample.json` 무변경 / Android 무변경

## 3–6. 실제 Scheduled Samples (합성 데이터 아님, 18-5 모듈 출력 그대로)

전체 JSON은 `phase18-3a-test/scheduled_samples_18_6.json`에 저장했다
(이번 단계에서 유일하게 추가한 데이터 파일 — 검토용 산출물이며 canonical이 아니다).

### 4. Known-team sample [OBSERVED]

```json
{
  "id": "lp:EM 2026 Summer Main Event:2026-09-30:BIG:SNSH",
  "league": {"id": "EM", "name": "EMEA Masters", "region": "EU"},
  "tournament": {"id": "EM 2026 Summer Main Event", "name": "EM 2026 Summer Main Event"},
  "stage": {"id": "Round 5", "name": "Round 5"},
  "team1Id": "BIG", "team2Id": "SNSH",
  "scheduledAt": null, "status": "scheduled", "bestOf": 1,
  "score": null,
  "sources": [{"source": "leaguepedia", "kind": "raw_fixture", "ref": "raw/leaguepedia/page_EMEA_Masters_2026_Summer_Main_Event.wikitext"}],
  "lastUpdatedAt": "2026-09-30",
  "_provisional": {
    "teamSlotState": {"team1": "KNOWN", "team2": "KNOWN"},
    "teamSlotRaw": {"team1": "BIG", "team2": "SNSH"},
    "identityStatus": {"team1": "UNKNOWN", "team2": "UNKNOWN"},
    "bestOfSource": "row-level bestof",
    "gameBlockCount": 1,
    "rpgidCount": {"total": 1, "nonEmpty": 0},
    "timeRaw": {"date": "2026-09-30", "time": "06:00", "timezone": "PST", "dst": "yes", "utcConversion": "PENDING_TIMEZONE_REVIEW"}
  }
}
```

### 5. TBD sample [OBSERVED]

`id: lp:EM 2026 Summer Main Event:2026-10-01:TBD:TBD` — `team1Id/team2Id: null`,
`teamSlotState: {"team1": "TBD", "team2": "TBD"}`, `bestOf: 3`, `gameBlockCount: 3`.

### 6. EMPTY sample [OBSERVED]

`id: lp:Worlds 2026 Play-In:2026-10-15:EMPTY:EMPTY` — `team1Id/team2Id: null`,
`teamSlotState: {"team1": "EMPTY", "team2": "EMPTY"}`, `bestOf: 5` (start-level),
`gameBlockCount: 5`.

세 레코드의 키 집합은 완전히 동일하다 [OBSERVED].

## 7. Canonical JSON Review

- `status="scheduled"`는 Android `MatchStatus.SCHEDULED`의 `@SerialName("scheduled")`와
  정확히 일치한다 [OBSERVED — 어휘 호환].
- `score: null`, `scheduledAt: null`, `team1Id/team2Id: null`은 18-4 설계대로 [OBSERVED].
- `bestOf`는 현재 35개 record 전부 non-null 정수였으나 설계상 null 허용 [OBSERVED/DESIGN].
- `_warnings`, `_provisional`은 Android 파서에서 무시된다
  (`Json { ignoreUnknownKeys = true }` [OBSERVED — RemoteEsportsRepository.kt, LocalDataCache.kt 공통]).

## 8. Android Match Model Compatibility

`Model/Match.kt` [OBSERVED]:

```kotlin
val team1Id: String,        // non-null
val team2Id: String,        // non-null
val scheduledAt: String,    // non-null
val score: MatchScore,      // non-null
val bestOf: Int,            // non-null
```

| 필드 | Android 정의 | scheduled canonical | 판정 |
|---|---|---|---|
| team1Id | `String` (null 불가) | null (TBD/EMPTY) 또는 provisional raw 값 | **BLOCKER** |
| team2Id | 동일 | 동일 | **BLOCKER** |
| scheduledAt | `String` (null 불가) | null (PST 미확정) | **BLOCKER** |
| score | `MatchScore` (null 불가) | null | **BLOCKER** |
| bestOf | `Int` (null 불가) | 현재 전부 non-null (설계상 null 가능) | REQUIRES CHANGE (선제 대응 권장) |
| status | enum + `"scheduled"` SerialName | `"scheduled"` | **COMPATIBLE** |
| id / league / tournament / stage / lastUpdatedAt | non-null String/객체 | non-null | **COMPATIBLE** |

`MatchScore(team1: Int, team2: Int)` — scheduled에서는 아예 등장하지 않는 null이므로
`MatchScore?` 확장 또는 score 자체를 nullable로 변경해야 한다 [DESIGN — 구현은 별도 승인].

**기존 호환성 메모 (scheduled와 무관한 사전 발견)** [OBSERVED]:

- Android `League`는 `game: String`을 **필수**로 요구한다. data repo canonical
  (`normalize_sample.py` 및 scheduled 출력)의 league는 `game`이 없다.
- Android `Tournament`는 `leagueId: String`이 필수다. canonical tournament에는 없다.
- Android `MatchSource(name, fetchedAt)`는 canonical
  `sources: [{source, kind, ref}]`와 **필드명 자체가 다르고**, 필수 필드
  (`name`, `fetchedAt`)가 없어 `SerializationException`이 발생한다.

이 세 가지는 **completed record에도 동일하게 적용되는 기존 불일치**다
(18-5에서 새로 생긴 것이 아니다). 과거 Phase 10–12의 로컬 HTTP 테스트는 Android
모델에 맞춘 fixture를 사용했으므로 파이프라인 출력과 Android 모델의 차이가
드러나지 않았던 것으로 판단한다 [INFERENCE]. Promotion 전에 반드시 해소해야 한다.

## 9. Serialization / Repository Compatibility

데이터 흐름 단계별 판정 [OBSERVED 코드 기준]:

| 단계 | 판정 | 비고 |
|---|---|---|
| JSON → kotlinx.serialization | **BLOCKER** | 위 4개 non-null 필드에 null 입력 시 `SerializationException` → `RemoteDataException(PARSE)` |
| schemaVersion 검증 | COMPATIBLE | `schemaVersion: 1` 유지 |
| RemoteDataEnvelope | COMPATIBLE (구조상) | 모델 자체는 matches만 요구; 문제는 Match 내부 필드 |
| LocalDataCache | 동일 BLOCKER | 동일 `@Serializable` 모델 재사용 (`jsonFormat` ignoreUnknownKeys) |
| Repository → DataState | COMPATIBLE | null-safe 흐름, UI 노출 메시지만 사용 |

즉, **현재 Android 코드로는 scheduled record(그리고 위 모양 불일치 때문에
completed canonical 출력도) deserialize에 실패하고**, PARSE 예외 → 캐시 있으면
Stale / 없으면 Error로 처리된다 [OBSERVED — RemoteEsportsRepository.loadData].

## 10–12. UI Compatibility

Match List (`MatchListItem.kt`, `MatchListScreen.kt`):

| 항목 | 현재 동작 | 사용자 정책 | 판정 |
|---|---|---|---|
| 팀 이름 | `teamsById[team1Id]?.shortName ?: team1Id` — null이면 문자열 `"null"` 표시 위험 | null → "TBD" | REQUIRES CHANGE |
| 중앙 score | `centerLabel`: SCHEDULED/IN_PROGRESS/COMPLETED → `"${score.team1} : ${score.team2}"` | scheduled + null score → blank | REQUIRES CHANGE |
| 시간 | `formatMatchTime` 파싱 실패 → `"--:--"` | null scheduledAt → blank | REQUIRES CHANGE |
| 상태/BO 표시 | statusLabel/bestOfLabel | 동일 | COMPATIBLE |
| 날짜 필터 | `matchLocalDate` 파싱 실패(또는 null) 시 해당 경기가 날짜 필터에서 **제외**됨 | (정책 미지정) | REQUIRES CHANGE — scheduledAt=null 경기가 목록에 나타나지 않는 동작 결정 필요 [DESIGN] |

Match Detail (`MatchDetailScreen.kt`):

| 항목 | 현재 동작 | 판정 |
|---|---|---|
| 팀 이름 | `?: "Unknown"` | REQUIRES CHANGE (정책상 "TBD") |
| 중앙 score | centerLabel 재사용 | REQUIRES CHANGE |
| Date/Time | formatMatchDate `"-"` / formatMatchTime `"--:--"` fallback | REQUIRES CHANGE (blank 정책) |
| 나머지 상세 행 | tournament/stage/status | COMPATIBLE |

Team Detail (`TeamDetailScreen.kt`):

| 항목 | 현재 동작 | 판정 |
|---|---|---|
| 팀 경기 필터 | `it.team1Id == teamId \|\| it.team2Id == teamId` — null teamId는 매칭되지 않아 자연스럽게 제외 | **CURRENTLY COMPATIBLE** |
| upcoming 정렬 | `sortedBy { it.scheduledAt }` — scheduledAt nullable화 시 null 처리 필요 | REQUIRES CHANGE (모델 변경 시) |
| opponentLabel | `?: "Unknown"` | REQUIRES CHANGE (미미한 표시 문제) |

## 13. Nullability Findings 요약

**BLOCKER (promotion 시 즉시 파싱 실패)**:
1. `Match.team1Id/team2Id: String` ← null 입력
2. `Match.scheduledAt: String` ← null 입력
3. `Match.score: MatchScore` ← null 입력

**사전 존재 불일치 (scheduled 무관, completed에도 적용)**:
4. `League.game` 필수 vs canonical 미제공
5. `Tournament.leagueId` 필수 vs canonical 미제공
6. `MatchSource(name, fetchedAt)` vs canonical `{source, kind, ref}`

**REQUIRES CHANGE (파싱은 통과하나 UI 정책 위반/동작 결정 필요)**:
7. null teamId → "TBD" 표시 (현재 "null"/"Unknown" 문자열 위험)
8. scheduled + null score → blank (현재 "0 : 0" 표시 경로)
9. null scheduledAt → blank (현재 "--:--"/"-")
10. 날짜 필터에서 scheduledAt=null 경기의 노출 여부 결정
11. (선제 권장) `bestOf: Int?` — 설계가 null을 허용

## 14. User-Approved UI Policy 평가

사용자 승인 정책(null teamId → TBD / null score → blank / null scheduledAt → blank)은
18-4 설계와 **정합적**이다 [OBSERVED]:

- 18-5 구현에서 KNOWN raw + identity UNKNOWN은 `teamId=null`이 **아니라**
  provisional raw 값(예: `"BIG"`)이므로, `null teamId`는 raw 상태 TBD/EMPTY에서만
  발생한다 → UI가 null을 "TBD"로 표시하면 raw state 소실 우려(§9)가 실질적으로
  발생하지 않는다. KNOWN-but-unresolved는 raw 코드("BIG")가 그대로 표시되어
  오히려 정보가 유지된다 [OBSERVED — 18-5 `_slot_record` 동작].
- TBD raw와 EMPTY raw가 모두 null teamId가 되어 UI에서 구분 불가능해지는 것은
  사용자 승인 방향이 허용하며, raw 구분은 `_provisional.teamSlotState`에 보존된다
  [OBSERVED].

단, KNOWN 슬롯의 raw 값이 UI에 그대로 노출되는 것("BIG")은 팀 풀네임이 아니라는
점을 문서로 명시해 둔다 — identity 매핑이 확정되면 canonical 재생성으로 자연 해소
된다 [INFERENCE].

## 15. PST Handling

`scheduledAt=null` + `timeRaw.utcConversion=PENDING_TIMEZONE_REVIEW` 상태 유지
[OBSERVED]. Android는 사용자 정책대로 blank 표시하면 된다. 본 단계에서 PST/dst를
해석하지 않는다 (§16 UNKNOWN 유지).

## 16. Promotion Readiness

**PROMOTION_REQUIRES_ANDROID_CHANGE**

> PHASE 18-7 UPDATE (2026-09-30): 상기 Android 변경이 구현·검증 완료되어
> **PROMOTION_READY (Android 측)** 로 갱신된다. 세부:
> - `Match.team1Id/team2Id/scheduledAt: String?`, `score: MatchScore?` nullable화 완료,
>   `bestOf`는 기존 의미 유지(non-null, canonical이 현재 null을 관측하지 않음).
> - 계약 정합화 3건 완료: `League.game`/`Tournament.leagueId` 기본값 수용,
>   `MatchSource`를 canonical `{source, kind, ref}` 스키마로 정렬(구 필드는 deprecated 기본값 유지),
>   `Match.provisional`에 `@SerialName("_provisional")` 매핑 추가(최초 구현 누락 버그 수정 —
>   이 매핑이 없으면 kotlinx가 `_provisional`을 unknown으로 무시해 raw state가 소실되었음).
> - UI 정책 구현: null teamId → "TBD", null score → blank, null scheduledAt → blank
>   (List/Detail/TeamDetail 전부; null을 "Unknown"/"--:--"/"-"로 표시하던 fallback 제거).
> - 날짜 필터 정책 구현: `scheduledAt == null`이면 `_provisional.timeRaw.date`와
>   selected date를 calendar-date 기준으로만 비교(임의 UTC 생성 없음), raw date 없으면 제외,
>   시간 정렬은 scheduledAt null을 뒤로 보냄.
> - 검증: Android 62 tests PASS (기존 54 + 신규 8: §11 CASE 1-4 직렬화 + 날짜 필터 4건),
>   `:app:assembleDebug` BUILD SUCCESSFUL, data repo 146 tests PASS (무회귀).
> - 실제 canonical scheduled envelope(EMEA known/TBD + Worlds EMPTY 3건)을 앱 캐시에
>   주입한 에뮬레이터 확인은 MainActivity가 아직 SampleEsportsRepository를 사용하므로
>   수행하지 못했다(캐시 파일은 앱이 무시). 이는 URL 확정 시 예정된 repository 교체 이슈이며
>   본 단계 범위 밖(§19.1 참조).

판정 근거: canonical scheduled record 자체는 18-4 설계/validator와 일치하고
어휘 호환(status)이지만, 현재 Android 모델은 `team1Id/team2Id/scheduledAt/score`
null을 수용하지 못해 **deserialize 단계에서 예외가 발생한다** (§13-1~3).
또한 promotion 전에 completed canonical 출력에도 적용되는 모양 불일치
(§13-4~6)를 반드시 함께 해소해야 한다 — 이것은 scheduled 문제가 아니라
data-repo canonical ↔ Android 모델 계약의 정합성 문제다.

## 17. Required Android Changes (구현은 별도 승인 단계)

1. `Match.team1Id/team2Id: String?` (또는 sealed/별도 scheduled 모델 — 단순 nullable 권장)
2. `Match.scheduledAt: String?`
3. `Match.score: MatchScore?`
4. (선제 권장) `Match.bestOf: Int?`
5. `MatchListItem.centerLabel`: scheduled + null score → blank
6. 팀 이름 fallback: null → "TBD" (List/Detail/TeamDetail opponentLabel)
7. `formatMatchTime/formatMatchDate`: null → blank
8. `MatchFilters.filterMatches`: scheduledAt=null 경기의 날짜 필터 동작 결정
   (예: 항상 표시 / 날짜 무관 섹션) — 사용자 결정 필요
9. **canonical↔모델 계약 정합화**: `League.game`, `Tournament.leagueId` 제공 방식,
   `sources` 필드명 매핑 — data repo 측 출력을 바꿀지 Android 모델을 바꿀지
   별도 결정 (completed에도 영향)

## 18. Remaining UNKNOWN (18-5에서 유지, 본 단계에서도 미해결)

dst=yes/spring/no 의미 / PST offset / rpgid preassignment / postponed·cancelled
표현 / initialorder / qq / recap-vod / TBD·empty 전체 의미론 / Worlds BO3 블록
행동 / EMEA identity / Fandom 정책 — **전부 유지** [OBSERVED: 본 단계에서
새로 해소된 UNKNOWN 없음]. 신규 발견은 UNKNOWN이 아니라 **모양 불일치 FACT**(§13-4~6)다.

## 19. Recommendation for Phase 18-7

1. **Android nullable 대응 승인/구현** (§17-1~8) — 사용자 정책을 UI에 반영
2. **canonical 계약 정합화 설계** (§17-9) — completed 포함 전체 record 대상
3. 두 작업 완료 후 재검토 → `PROMOTION_READY` 판정 → 실제 promotion 단계
4. 병행 가능: PST offset 인간 리뷰 (완료 시 scheduledAt 채움), 2026-10-18 후
   Worlds Main Event 재수집

본 단계는 여기서 중단한다 (handoff §20).
