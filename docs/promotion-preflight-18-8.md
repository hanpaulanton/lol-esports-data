# Promotion Preflight Review (PHASE 18-8)

- 작성: 2026-09-30, PHASE 18-8 (promotion 실행 전 점검 — 실제 promotion 없음)
- 네트워크: **0회**
- 이 문서의 목적: PHASE 18-9에서 실행할 promotion의 데이터 범위/검증 gate/절차/
  rollback을 실제 코드 근거로 고정하고, 실행을 막는 항목을 명확히 분리한다.

---

## 1. Status

**PARTIAL — 1 blocker 확인 (GATE 1: envelope validator가 scheduled record를 거절함)**
blocker 해소 방법은 §5/§13에 포함. 해소 전 promotion 실행 불가.

## 2. Current repository state (실제 확인)

- Data repo: 146 tests PASS (본 단계 시작 시 재확인). `data/`에는
  `matches.sample.json` 하나뿐이며 `_meta.status`에
  "SAMPLE / PHASE 17 — NOT production canonical data"로 명시 [OBSERVED].
  **production canonical 파일은 아직 존재하지 않는다.**
- README: "A production canonical `matches.json` has NOT been produced yet" /
  "The Android app has NOT been connected" 명시 유지 [OBSERVED].
- Android: 62 tests PASS, `assembleDebug` 성공 (18-7 결과). MainActivity는
  여전히 `SampleEsportsRepository` (18-6/18-7에서 의도적 유지) [OBSERVED].
- `RemoteEsportsRepository.DEFAULT_DATA_URL`는 placeholder
  (`https://example.com/data/matches.json`) [OBSERVED].

## 3. Promotion candidate (§10 판정)

| 후보 | 원천 | production 사용 가능 여부 |
|---|---|---|
| LCK completed 10 records | `matches.sample.json` records (Week 10 스코프) | **주의** — sample 메타가 production임을 부정하고 있고 스코프가 첫 탭뿐. promotion에는 **새로 정규화한 full completed 세트**(동일 fixture 전체 40행 중 검증 통과분)를 사용해야 한다. sample 파일은 sample로 남긴다. |
| EMEA scheduled 29 records (14 KNOWN + 15 TBD) | 18-5 `scheduled_normalize` 출력 (raw fixture에서 재생성) | 가능 — validator 0 error 0 warning [OBSERVED: 18-5/18-8 재확인] |
| Worlds Play-In scheduled 6 records (EMPTY) | 동일 | 가능 — validator 통과 [OBSERVED] |
| EMEA forfeit row 9 | completed pipeline (미구현 분기) | **제외** — ff 처리는 18-4 §10의 WARNING 설계만 존재, 구현 전까지 승격 대상 아님 |
| Worlds Main Event 40 rows | 전부 EMPTY scheduled | 선택 사항 — 원하면 포함 가능(동일 스키마). 기본은 Play-In만으로 최소화 권장 [DESIGN] |

**판정**: "실제 production source가 없어서 BLOCKED"는 아니다 — raw fixture는
실제 수집된 Leaguepedia 응답이고 정규화·검증 체인이 전부 구현·테스트되어 있다.
다만 §5의 blocker(GATE 1) 해소가 선행 조건이다.

## 4. Canonical envelope plan

```json
{
  "schemaVersion": 1,
  "dataVersion": "<YYYY.MM.DD.NN> promotion 실행일 기준",
  "generatedAt": "<실행 시각 ISO-8601 Z>",
  "leagues": [ {"id": "LCK21", "name": "LCK", "region": "KR"},
               {"id": "EM", "name": "EMEA Masters", "region": "EU"},
               {"id": "Worlds", "name": "World Championship", "region": "INT"} ],
  "teams": [],
  "matches": [ <completed LCK records>, <EMEA scheduled 29>, <Worlds Play-In scheduled 6> ]
}
```

- `teams: []` 유지: canonical team identity가 아직 unresolved이고 Android `Team`
  참조는 `?: "TBD"` fallback으로 동작한다 (18-7 확정). 임의 Team 객체를 만들지 않는다 [DESIGN].
- Android `League.game`/`Tournament.leagueId`는 기본값 수용 (18-7 계약 정합화 완료) [OBSERVED].
- 파일명: `data/matches.json` (README가 예고한 이름). `matches.sample.json`은 그대로 보존.
- `dataVersion` 규칙: promotion마다 증가; Android는 `SUPPORTED_SCHEMA_VERSION = 1`만 확인하므로
  schemaVersion은 1 유지.

## 5. Validation gates

| Gate | 판정 | 근거 |
|---|---|---|
| G1 canonical envelope schema validation | **FAIL → 해소 필요** | `validate_envelope`가 모든 match에 `validate_match`만 적용 → scheduled의 null 필드를 전부 문제로 보고함 [OBSERVED: 본 단계에서 실제 probe로 확인]. 해소: envelope validator를 status-aware로 분기(status=="scheduled" → `validate_scheduled_match`, 그 외 → `validate_match`). 승인된 18-9 변경 사항. |
| G2 completed records validation | PASS | sample 10 records `validate_match` 0 문제 [OBSERVED probe] |
| G3 scheduled records validation | PASS | 35 records `validate_scheduled_match` 0 error 0 warning [OBSERVED] |
| G4 KNOWN/TBD/EMPTY 보존 | PASS | `_provisional.teamSlotState` 보존 테스트 존재 [OBSERVED] |
| G5 scheduled score == null | PASS | 35/35 null [OBSERVED] |
| G6 scheduledAt null → timeRaw.date 존재 | PASS | 35/35 `timeRaw.date` 존재 (`utcConversion=PENDING_TIMEZONE_REVIEW`) [OBSERVED] |
| G7 synthetic rpgid 없음 | PASS | canonical에 rpgid 필드 없음, 테스트 잠금 [OBSERVED] |
| G8 identity UNKNOWN ≠ parse failure | PASS | EMEA 전체 UNKNOWN 상태로 35 record 정상 생성 [OBSERVED] |
| G9 BestOf row > Start > UNKNOWN | PASS | 구현 + 테스트 [OBSERVED] |
| G10 completed regression | PASS | 146 tests [OBSERVED] |
| G11 Android deserialize | PASS | CASE 1–4 테스트 [OBSERVED] |
| G12 Android existing tests | PASS | 62 tests [OBSERVED] |
| G13 Data repo 146 tests | PASS | [OBSERVED] |
| G14 envelope 전체 ↔ Android 모델 호환 | **UNKNOWN → G1과 동일 해소 후 재판정** | Android는 scheduled null을 수용하지만, G1을 통과한 envelope이어야 end-to-end 의미가 성립. G1 수정 후 mixed envelope probe로 재확인 필요 [DESIGN] |

## 6. UNKNOWN classification

**Non-blocking (promotion 허용, canonical에서 의미 있게 사용하지 않음)**:
initialorder / qq / recap-vod / postponed·cancelled 미관측 (promotion 데이터에
해당 상태를 만들어 넣지 않으므로) / Worlds BO3 블록 행동 / Fandom 정책 세부
(정책 이벤트 모델이 fail-closed로 보호).

**Blocking (promotion 전 해소 또는 회피 필수)**:
- PST offset 미확정 → **회피됨**: scheduledAt=null + timeRaw 보존이 설계상 허용.
  UTC timestamp를 만들지 않으므로 promotion을 막지 않는다 [DESIGN, 18-4 §9 확정].
- GATE 1 envelope validator 미대응 → **해소 필요** (유일한 실 blocker).
- EMEA identity unresolved → **회피됨**: raw 값 provisional 보존 + Android TBD 정책
  으로 소비 가능. 매핑 추측은 계속 금지.

## 7. Timezone policy

KST completed → 기존 검증된 변환 유지 [OBSERVED]. PST scheduled → `scheduledAt=null`
허용, raw는 `_provisional.timeRaw` 보존, UTC 생성 금지 [OBSERVED — 구현·테스트됨].
PST 확정은 promotion과 독립된 인간 리뷰 작업으로 유지.

## 8. Team identity policy

현 매핑 상태: `team_mappings.json`은 LCK 10개 코드만 포함 [OBSERVED]. EMEA 값은
전부 UNKNOWN(resolver exact-only)이며 KNOWN 슬롯은 raw 값을 provisional id로 보존
[OBSERVED]. TBD/EMPTY는 null. fuzzy 금지 원칙 유지. 매핑 추가는 game-id 대조 등
실증 절차(18-1 방식)로만 가능.

## 9. Android deployment plan (§11 순서 그대로 채택)

1. canonical production JSON 생성 → 2. G1–G14 재판정 → 3. static hosting 배포
(GitHub Pages) → 4. public URL 확인 → 5. `MainActivity`를
`RemoteEsportsRepository(LocalDataCache(context))`로 교체 + `DEFAULT_DATA_URL` 갱신
→ 6. build → 7. emulator install → 8. remote fetch → 9. cache 저장 확인 →
10. 재시작 시 cache-first 동작 → 11. network 차단 시 Stale 동작 → 12. scheduled UI E2E
(KNOWN/TBD/EMPTY × 날짜 필터) → 13. completed UI regression.

## 10. Rollback plan (기존 기능으로 충분 — 신규 구현 없음)

- 데이터: promotion은 `data/matches.json` 신규 생성(기존 파일 교체 아님) + git 커밋
  이력이 곧 rollback 경로. 문제 발생 시 이전 커밋의 파일로 되돌리거나 배포를 이전
  dataVersion으로 재배포.
- Android 캐시: `LocalDataCache.save`는 temp-file rename atomic write, 실패 시
  기존 파일 보존 시도 [OBSERVED]. `load`는 손상/미지원 schemaVersion을 null로 처리
  → 캐시 무시 후 정상 흐름 [OBSERVED].
- 원격 실패: `RemoteEsportsRepository`는 캐시 있으면 Stale, 없으면 Error [OBSERVED].
- schemaVersion은 1 유지되므로 앱 측 거부 리스크 없음. dataVersion만 롤백 대상.

## 11. Test matrix

| # | 항목 | 상태 |
|---|---|---|
| 1–4 | completed / KNOWN / TBD / EMPTY | Android 테스트로 PASS (CASE 1–4) |
| 5–8 | scheduledAt null/valid, raw date present/missing | Android 필터 테스트로 PASS |
| 9–12 | deserialize 4종 | PASS |
| 13–14 | 날짜 필터 일치/불일치 | PASS |
| 15–18 | null time/score UI, TBD UI, completed regression | NOT RUN (UI E2E — repository 전환 후 가능) |
| 19 | remote success → cache | NOT RUN (URL 미확정) |
| 20 | remote failure → stale | NOT RUN |
| 21 | no cache + failure → error | NOT RUN |

## 12. Files changed

- `docs/promotion-preflight-18-8.md` (본 문서) — 유일한 변경.
- 프로덕션 코드/데이터/Android: **무변경**.

## 13. Network

**0 requests.**

## 14. Approval required

**실제 production promotion은 사용자 승인 전까지 실행하지 않는다.**
18-9 실행 시에도 본 문서의 gate 재판정 결과를 먼저 보고한다.

## 15. Next step

PHASE 18-9 (사용자 승인 후):
1. G1 해소 — `validate_envelope`를 status-aware 분기로 확장 (유일한 blocker,
   사전 승인된 18-4 §11 설계의 자연스러운 완성) + mixed envelope probe 재판정
2. full-scope completed 정규화 (Rounds 3-4 fixture 40행 전체, sample은 sample로 유지)
3. `data/matches.json` 생성 + G1–G14 재판정
4. 이후 §9 배포/전환 절차
