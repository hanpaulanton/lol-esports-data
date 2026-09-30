# PHASE 18-NW — NamuWiki Source Feasibility Review

- checkedAt: 2026-09-30 01:46 (+03:00) / UTC 2026-09-29 22:46Z (조사 시작)
- timezone: 이 머신은 +03:00 표시(시스템 설정), UTC 기준 시각 병기
- 범위: feasibility review only — canonical data 생성/병합 없음, collector 구현 없음, Android 변경 없음
- 관측 증거: `phase18nw-test/` (robots 스냅샷, 정책 발췌, 렌더링 문서 스냅샷, 요청 로그)
- 표기: **[확인]** = 직접 관측 / **[주장]** = 문서·커뮤니티 주장 / **[미확인]**

---

## 1. Overall decision

```text
PENDING_POLICY_REVIEW
```

선택한 이유(사실 기반):
1. 라이선스는 **확인됨**: 나무위키 문서 기본 라이선스 = **CC BY-NC-SA 2.0 KR** [확인, 기본방침/표기방침 발췌].
   프로젝트는 비상업적이므로 NC 조항 자체는 상충하지 않지만, **SA(동일방식변경허락)** 때문에 나무위키
   파생 데이터를 우리 canonical JSON으로 재배포하면 해당 JSON의 라이선스가 CC BY-NC-SA 2.0 KR을 따라야
   하며, Leaguepedia(CC BY-SA 3.0 계열 [주장])/Riot 소유 데이터와의 **라이선스 혼합 문제**가 발생한다.
   이 판단은 법률 검토 대상 → `LEGAL_REVIEW_REQUIRED`.
2. **자동 수집에 대한 명시적 허가 조항을 확보하지 못함**: 기본방침·이용자 관리 방침에서 "API"·"크롤"·
   "스크래핑" 키워드 **미발견** [확인], 봇 계정 규정(4.2)은 **편집 자동화** 규율 [확인] — 읽기 수집에 대한
   허용/금지 조항은 확인되지 않음.
3. 이용약관(`/Policy`)은 클라이언트 렌더링 + 스페인어 본문이며, 이 환경에서는 조항 **1.1~2.5까지만
   렌더링**됨(스크롤 6회 시도, 이후 UNKNOWN) [확인]. 자동 수집/스크래핑 조항이 뒷부분에 있을 가능성
   포함 → 사람이 브라우저에서 전문 확인 필요.
4. robots.txt는 `/w/` 문서 열람을 허용하나 **`/api`는 allow 목록에 없음**(=차단) [확인].
5. 데이터 적합성: 팀 문서는 **산문형**(역사/구단명 변천 서술 존재 [확인])이며 구조화된 별칭/약칭/전적
   필드는 없음 → REFERENCE 이상의 근거 없음.

따라서 "REFERENCE로 제한적 사용"이라는 방향성은 확인했으나, **약관 전문 검토가 끝나지 않았으므로
채택 확정 상태가 아니라 PENDING_POLICY_REVIEW**가 정확한 판정이다.

## 2. Policy

### Terms
- status: PARTIALLY REVIEWED (sections 1.1–2.5 of /Policy) — 나머지 **UNKNOWN**
- evidence [확인]:
  - URL: https://namu.wiki/Policy (client-rendered, "Loading..." → 브라우저 렌더 필요)
  - 제목: "Política de privacidad y Términos de uso" — 운영사 **umanle S.R.L.**(파라과이) 표기 [확인]
  - 렌더된 조항: 1.1 접속 시 프라이버시 정책 자동 수용 / 1.2 기여의 묵시적 동의 /
    1.4 "namu.wiki는 **비영리 협업·기여 사이트**" / 1.5 정보의 저작권은 기여자에게 있고 사이트는
    정확성에 책임 없음 — 등 [확인, 발췌]
  - 조항 3.x 이후: 렌더링 스크롤 6회 시도에도 미확보 → 자동 수집/스크래핑 조항 여부 **UNKNOWN**

### License
- status: **CONFIRMED (문서 라이선스)** / 재배포 조건: **PARTIAL**
- license: **CC BY-NC-SA 2.0 KR** — "나무위키의 문서는 기본적으로 CC BY-NC-SA 2.0 KR로 배포됩니다"
  [확인, 기본방침 발췌]
- exceptions: "문서에 삽입된 이미지는 별도 라이선스", "라이선스가 명시된 일부 문서 및 삽화 제외" [확인]
- attribution: 라이선스 자체 요건(CC BY-NC-SA = 저작자 표시 필요) 외 사이트의 별도 표기 요구 문구는
  관측되지 않음 [미확인 아님 — 문구 부재 관측]
- share-alike: NC-SA이므로 파생물은 동일 라이선스 유지 요건 발생 (라이선스 조항상)
- redistribution: 페이지에 재배포 전용 조항은 관측되지 않음 → **PENDING_LICENSE_REVIEW**
  (특히 C: 이미지 라이선스, E: 가공 JSON의 GitHub Pages 재배포, F: 팀명/별칭/역사의 canonical 저장)

### Robots
- status: **CONFIRMED** (2026-09-29 fetch, HTTP 200)
- URL: https://namu.wiki/robots.txt (sha256 6490ef1f...8d0be, 스냅샷 저장)
- relevant rules [확인 발췌]:
  - `User-agent: *` → `Disallow: /` + 화이트리스트 Allow: `/$`, `/ads.txt`, **`/w/`**, `/history/`,
    `/title_history/`, `/activity/`, `/backlink/`, `/Search`, `/discuss/`, `/js/`, `/img/`, `/css/`,
    `/skins/`, `/_nuxt/`, `/sidebar.json`, `/cdn-cgi/` 등
  - **`/api` 경로는 Allow 목록에 없음** → robots상 차단 대상
- 주의: robots는 이용약관/저작권 허가와 동일하지 않음 → 별도 항목으로 분리 기록(지시 §4 준수)

### Bot policy
- status: **CONFIRMED (편집 자동화 대상 규정 존재)** / 읽기 수집 대상 규정: **미발견**
- approval required: **예 (편집 봇 계정 기준)** — 이용자 관리 방침 4.2.1 [확인 발췌]:
  "봇 사용 승인을 얻으려는 자는 ... **문의 게시판에 승인을 요청**해야 합니다. 봇의 사용 목적. 봇의 사용 기간.
  소유자 입증 자료. 비정상 동작 중단/복구 기술적 수단 입증 자료." + 관리자의 승인 변경/취소/차단 조항 [확인]
- scope note: 4.2은 "**자동적인 방법으로 문서를 편집**하기 위하여" 봇 계정을 규율 — **읽기/API 수집**에
  대한 명시 조항은 기본방침·이용자 관리 방침에서 미발견 [확인] → UNKNOWN
- 봇 계정 제한 행위: 문서 편집/생성/이동/삭제, 이미지 업로드, 복구, 운영 행위(관리자 소유자 한정) [확인]

### API
- status: **NO OFFICIAL PUBLIC API FOUND** — 공식 문서화된 공개 API를 발견하지 못함
  (기본방침/이용자 관리 방침에서 "API" 키워드 0건 [확인]; 문서 엔진은 the seed [확인, 푸터])
- authentication/bot approval/rate limit: **UNKNOWN** (공개 문서 부재)
- 관측 부수 사실: `/w/` 문서는 HTTP 클라이언트로 200(정책 메타 문서) 또는 차단(인기 문서 — T1 문서는
  HTTP 클라이언트 403 계열 실패, 브라우저 렌더 시 정상) [확인] — **문서별 접근성이 불균일**
- 사이트 보호: 푸터에 reCAPTCHA/hCaptcha 보호 명시 [확인]

---

## 3. Data suitability

| Data | Suitability | Role | 근거 |
|---|---|---|---|
| Team name | GOOD FIT (REFERENCE) | REFERENCE | T1 문서 존재, 팀명은 본문/제목에 관측 |
| Alias | PARTIAL FIT | REFERENCE | 구조화 필드 없음, 산문 속 표현만 관측("별칭" 1건 — 서술형) |
| Former name | PARTIAL FIT | REFERENCE | "전 팀명" 구조 필드 0건, 그러나 구단명 변천 서술 존재(SK텔레콤 42회, SK telecom T1 10회 관측) |
| Team code | POOR FIT | — | 앱용 코드(DK/DNS/BFX/BRO)와 대응되는 구조화 코드 필드 미관측 |
| Tournament | PARTIAL FIT | DISCOVERY | 대회 관련 서술 존재("대회" 2건, 우승 이력 산문) — 구조화 데이터 아님 |
| Match schedule | POOR FIT | — | 팀 문서/정책 문서에서 일정 데이터 구조 미관측 (T1 문서 스냅샷에서 스케줄 표 없음) |
| Match result | POOR FIT | — | 산문 언급("경기" 13건)은 있으나 구조화 결과 데이터 미관측 |
| Score | POOR FIT | — | "스코어" 0건 관측 |
| Game ID | POOR FIT | — | riot_platform_game_id 등 미관측 |

- 관측 방법: `/w/T1` 브라우저 렌더 스냅샷 76,560 bytes에서 키워드 빈도 실측
  (`SK텔레콤` 42, `SK telecom T1` 10, `LCK` 8, `우승` 27, `경기` 13, `BO` 11, `스코어` 0, `전 팀명` 0, `로스터` 0)

## 4. Recommended source role

```text
REFERENCE (제한적) — 근거 확인 단계까지만
```

이유:
1. 강점: 한국어 팀 문서에 **구단명 변천/역사/별칭 서술이 존재** [확인 — T1 문서 실측]. Leaguepedia가
   커버가 약한 한국어 명칭 변천을 보완할 수 있는 유일한 후보.
2. 한계: (a) 라이선스 NC+SA → canonical JSON 혼입 시 라이선스 오염(LEGAL_REVIEW_REQUIRED),
   (b) 구조화 데이터 부재 → PRIMARY/SECONDARY 근거 전무, (c) 약관 자동수집 조항 미확인, (d) 접근성 불균일.
3. 따라서 "REFERENCE(사람이 직접 열람해 명칭 변천을 확인하는 용도)"만 현재 근거로 정당화되며,
   자동화는 제약 전파 전까지 금지.

## 5. Automation decision

```text
PENDING (MANUAL_ONLY로 운영 권고)
```

- 이유: (a) 약관 조항 3.x 이후 미확인(자동 수집 조항 포함 가능성), (b) robots는 `/w/`만 Allow,
  (c) reCAPTCHA/hCaptcha 보호 명시 [확인], (d) 인기 문서의 HTTP 클라이언트 차단 관측.
- 자동화를 하려면 최소한: 약관 전문 사람 검토 + (필요시) 봇/API 승인 절차 확인 → 별도 승인.

## 6. Redistribution decision

```text
PENDING_LICENSE_REVIEW
```

- 나무위키 문서(CC BY-NC-SA 2.0 KR) 파생 데이터를 재배포하면 SA/NC 조항이 따라옴 → 우리 canonical JSON
  (Leaguepedia/OE/Riot 기반 혼합)과의 라이선스 혼합 → **LEGAL_REVIEW_REQUIRED**
- 팀명/별칭 등 "사실 자체"의 취급(F)은 사실 데이터 일반론과 별개 논점 — 판단하지 않고 기록만:
  "NamuWiki 서술을 그대로 저장하는 것"과 "사실(팀명)만 저장하는 것"은 구분되어야 하며, 전자는 SA 조항
  적용 가능성, 후자는 라이선스 파생 여부가 불확실 → LEGAL_REVIEW_REQUIRED 표기.

## 7. Source policy

- enabled: **false** (draft)
- role: REFERENCE
- canonicalDataAllowed: **false**
- teamIdentityVerification: false
- matchScheduleVerification: false
- matchResultVerification: false
- automatedCollection: **PENDING_POLICY_REVIEW**
- redistribution: **PENDING_LICENSE_REVIEW**
- humanReviewRequired: **true**
- files: `config/policies/namuwiki.json` (draft), `policy_snapshots/namuwiki/2026-09-30.json`
- source change policy(TERMS/LICENSE/ROBOTS/API_SCHEMA/RATE_LIMIT_CHANGED, SOURCE_UNAVAILABLE,
  BOT_POLICY_CHANGED) 적용 가능 여부: **적용 가능** — robots/약관 해시 스냅샷 구조가 이미
  `check_policies.py`와 호환. BOT_POLICY_CHANGED 항목은 이용자 관리 방침 4.2 해시를 추가 스냅샷으로
  추적하도록 PHASE 19에서 확장 권고.

## 8. Network

```text
HTTP requests: 10 (정책 검토 목적 최소 확인)
```

- count: 10
- domains: namu.wiki 뿐 (robots.txt 1, /w/ 정책 문서 4, /Search 1, /Policy 1, /w/T1 1, 기타 시도 실패 2 — 전부 기록: `phase18nw-test/http-requests.txt`)
- purpose: robots 확인, 이용약관/기본방침/이용자 관리 방침/봇 규정 검토, 팀 문서 1건 데이터 샘플
- User-Agent: `LoLEsportsFanDataPolicyReview/0.1 (...)` — UA 위장/우회 없음, retry storm 없음

## 9. Tests

- 명령: `.venv\Scripts\python.exe -m unittest discover -s tests`
- production code 변경 없음 → 기존 결과 유지: **total 48 / passed 48 / failed 0 / errors 0**
  (PHASE 18-1 종료 시점 결과를 그대로 재확인)

## 10. Files changed

**Added**:
- `docs/namuwiki-source-feasibility.md` (본 보고서의 영구 사본)
- `config/policies/namuwiki.json` (draft, enabled=false)
- `policy_snapshots/namuwiki/2026-09-30.json` (robots 해시 스냅샷)
- `tests/fetch_namu_policy.py`, `tests/fetch_namu_42.py`, `tests/fetch_namu_terms_link.py`,
  `tests/fetch_namu_footer.py`, `tests/fetch_namu_search.py`, `tests/fetch_namu_teamdoc.py`
  (정책 검토용 확인 스크립트 — 1회 실행 기록 목적, runner 아님)
- `phase18nw-test/*` (증거: robots 스냅샷, 정책 발췌, 렌더링 문서 스냅샷, 요청 로그)

**Modified**: 없음 (기존 production/test 코드 무변경)
**Removed**: 없음

## 11. Android changed
```text
NO
```

## 12. Remaining UNKNOWN
1. 나무위키 이용약관(`namu.wiki/Policy`) 조항 **3.x 이후 전부** — 브라우저 전문 검토 필요(스페인어)
2. 공식 API의 존재 여부 자체(문서 부재 확인은 했으나 "존재하지 않는다"는 증명은 아님)
3. 무인증/비로그인 반복 GET에 대한 공식 입장(차단/캡차 임계치)
4. 인기 문서의 HTTP 클라이언트 차단(403/429) 정확한 트리거와 정책 근거
5. CC BY-NC-SA 2.0 KR 데이터의 정적 JSON 재배포 시 라이선스 파생 판단(법률)
6. 팀 문서 간 구조 일관성(T1만 관측, 타 팀 문서 구조는 미확인)
7. 봇 승인 절차가 "읽기 전용 collector"에도 적용되는지(규정은 편집 봇 기준)
