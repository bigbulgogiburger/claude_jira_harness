# Reference Docs — Decision Matrix / 후보 / 템플릿 / 병합

> 참조 시점: Phase 5 (참조 문서 생성/업데이트) 시 — 어떤 reference 를 만들지, 어떻게 쓸지, 어떻게 병합할지
> 갱신 트리거: 새 프레임워크의 reference 후보 추가, 품질 체크리스트 변경, 병합 정책 변경

## 5-1. Decision Matrix — 생성 판단 기준

모든 기준은 **grep/ls 로 확인 가능한 관찰 기준**이다. 사후 판단 ("오류가 발생하는 영역") 은 사용하지 않는다 — 검증 불가능.

### 필수 생성 — 다음 중 하나라도 해당

**Rule 1 (커스텀 전역 함수):**
`window.*`, `Vue.prototype.*`, `$fn*` 형태의 커스텀 전역이 3개 이상인가?
→ 확인: `grep -r "window\.\w\+\s*=" src/utils/ | wc -l`
→ YES → `error-handling.md` 또는 해당 영역 문서 필수

**Rule 2 (라이브러리 버전 갭):**
주요 라이브러리가 현재 major 에서 2+ 버전 뒤처지는가?
→ 확인: `package.json` 버전 vs `npm info [pkg] version`
→ YES → 해당 라이브러리 전용 reference 필수 (예: ag-grid v29 → `grid-library.md`)

**Rule 3 (패턴 반복 빈도):**
동일 함수/컴포넌트/패턴이 5개 이상 뷰에서 import 되는가?
→ 확인: `grep -rl "import.*ModalPopup" src/views/ | wc -l`
→ YES → 해당 패턴의 reference 필수

**Rule 4 (복수 모드 분기):**
동일 목적의 함수가 2개 이상 존재하며 선택 기준이 필요한가?
→ 확인: 같은 API 파일에 `getApi`, `bypassGetApi`, `noAuthApi` 공존
→ YES → `auth-flow.md` 필수

**Rule 5 (프레임워크 기본과 다른 패턴):**
공식 문서가 권장하는 방식과 다른 패턴을 사용하는가?
→ 확인: `console.log` 대신 커스텀 로깅, `useI18n()` 대신 `i18n.global.t` 등
→ YES → 해당 영역 문서에 "NEVER" 규칙 포함 필수

### 권장 생성

- **Rule 6**: Rule 3 기준이 2-4개 파일인 경우
- **Rule 7**: `.env` 파일이 3개 이상 (dev/staging/prod 분리) → `build-config.md`
- **Rule 8**: i18n 네임스페이스가 10개 이상 → `i18n.md`

### 생성 불필요

- 위 Rule 중 해당 없음
- 프레임워크 기본 동작을 그대로 사용 (context7 / 공식 docs 로 보완 가능)
- 단일 파일에서만 사용되는 유틸리티

## 5-2. 프레임워크별 reference 후보

각 프레임워크의 candidate 와 생성 조건. 자세한 스캔 항목은 `references/frameworks.md` 참조.

### Vue / Nuxt (15개 후보)

| # | 문서 | 참조 시점 | 생성 조건 |
|---|------|----------|----------|
| 1 | `architecture.md` | 구조 파악 시 | 항상 |
| 2 | `api-layer.md` | API 호출 작성 시 | 항상 |
| 3 | `css-system.md` | 스타일 작성 시 | CSS 변수 시스템 또는 커스텀 |
| 4 | `testing.md` | 테스트 작성 시 | 항상 |
| 5 | `state-management.md` | 상태 관리 시 | Rule 4: Vuex+Pinia 공존 또는 5+ store |
| 6 | `routing.md` | 라우트 수정 시 | Rule 3: 50+ 라우트 또는 커스텀 가드 |
| 7 | `auth-flow.md` | 인증 수정 시 | Rule 4: 인증 모드 2종 이상 |
| 8 | `error-handling.md` | 에러 처리 시 | Rule 1: 커스텀 전역 3+ 또는 Rule 5 |
| 9 | `i18n.md` | 다국어 작업 시 | Rule 8: 10+ 네임스페이스 |
| 10 | `component-library.md` | UI 컴포넌트 사용 시 | Rule 3: 5+ 뷰에서 사용 |
| 11 | `grid-library.md` | 목록 페이지 개발 시 | Rule 2: 그리드 버전 갭 |
| 12 | `form-patterns.md` | 폼 개발 시 | Rule 5: 폼 라이브러리 미사용 |
| 13 | `responsive-layout.md` | 반응형 UI 작업 시 | Rule 5: 커스텀 반응형 분기 |
| 14 | `build-config.md` | 빌드 설정 수정 시 | Rule 7: 환경별 분기 또는 커스텀 프록시 |
| 15 | `domain-[name].md` | 해당 도메인 수정 시 | Phase 5-B 트리거 조건 |

### Spring Boot (10개 후보)

| # | 문서 | 참조 시점 | 생성 조건 |
|---|------|----------|----------|
| 1 | `architecture.md` | 구조 파악 시 | 항상 |
| 2 | `api-layer.md` | Controller/DTO 작업 시 | 항상 |
| 3 | `data-access.md` | Repository/JPA/QueryDSL 시 | 항상 |
| 4 | `security.md` | 인증/인가/외부연동 시 | Security 설정 존재 |
| 5 | `testing.md` | 테스트 작성 시 | 항상 |
| 6 | `build-config.md` | Gradle/프로파일 수정 시 | Rule 7: 3+ 프로파일 |
| 7 | `kotlin-patterns.md` | Kotlin 프로젝트 시 | 언어가 Kotlin 인 경우만 |
| 8 | `domain-[name].md` | 도메인 수정 시 | Phase 5-B 트리거 조건 |
| 9 | `caching.md` | 캐시 설정 수정 시 | Redis/Caffeine 의존성 존재 |
| 10 | `async-scheduling.md` | 비동기/스케줄러 시 | @Async/@Scheduled/ShedLock 존재 |

### React / Next.js (8개 후보)

| # | 문서 | 참조 시점 | 생성 조건 |
|---|------|----------|----------|
| 1 | `architecture.md` | 구조 파악 시 | 항상 |
| 2 | `api-layer.md` | API 호출 작성 시 | 항상 |
| 3 | `state-management.md` | 상태 관리 시 | 복수 상태관리 또는 커스텀 |
| 4 | `css-system.md` | 스타일 작성 시 | Tailwind 외 커스텀 시스템 |
| 5 | `routing.md` | 라우트 수정 시 | 50+ 라우트 또는 커스텀 미들웨어 |
| 6 | `testing.md` | 테스트 작성 시 | 항상 |
| 7 | `build-config.md` | 빌드 설정 시 | Rule 7 |
| 8 | `domain-[name].md` | 도메인 수정 시 | Phase 5-B 트리거 조건 |

### Flutter (7개 후보)

| # | 문서 | 참조 시점 | 생성 조건 |
|---|------|----------|----------|
| 1 | `architecture.md` | 구조 파악 시 | 항상 |
| 2 | `state-management.md` | BLoC/Provider/Riverpod 시 | 항상 |
| 3 | `data-layer.md` | API/로컬 저장소/모델 시 | 항상 |
| 4 | `navigation.md` | 라우팅/딥링크 수정 시 | 커스텀 라우팅 존재 |
| 5 | `testing.md` | 테스트 작성 시 | 항상 |
| 6 | `build-config.md` | 빌드 설정 시 | Rule 7 |
| 7 | `domain-[name].md` | 도메인 수정 시 | Phase 5-B 트리거 조건 |

### 기타 (FastAPI / Django / Go)

핵심 4개 (`architecture`, `api-layer`, `testing`, `build-config`) 는 모든 프레임워크 공통. 나머지는 Decision Matrix Rule 1-8 적용 결과에 따라:
- `data-access.md`: ORM/Repository 존재 시
- `auth-flow.md`: 인증 미들웨어/가드 존재 시
- `domain-[name].md`: Phase 5-B 트리거 조건

## 5-3. 핵심 reference 별 스캔 경로 + 최소 포함 항목

각 reference 에 **무엇을 담을지** 구체 지침.

### 공통 — 모든 reference 에 반드시 포함

1. 스캔 경로 명시 (어떤 파일을 분석했는지)
2. 최소 포함 항목 체크리스트
3. 금지사항 (NEVER 규칙)
4. 갱신 트리거

### auth-flow.md

스캔 경로:
- Vue: `src/api/interceptors*`, `src/store/modules/auth*`, `src/router/guards/*`, `src/composables/*auth*`
- Spring: `**/security/**`, `**/config/Security*`, `**/filter/Jwt*`
- FastAPI: `app/core/security.py`, `app/middleware/*`, `app/dependencies.py`
- Go: `middleware/auth*.go`, `internal/auth/`

최소 포함:
- [ ] 인증 모드 목록 + 각 모드의 사용 시점 (Decision Table 형식)
- [ ] 토큰 저장 위치 (sessionStorage, cookie, header 등)
- [ ] 토큰 갱신 플로우 (Mermaid)
- [ ] 인증 실패 시 동작 (리다이렉트, 세션 만료)
- [ ] 프레임워크별 플래그/어노테이션 (`_skipAuth`, `@PreAuthorize` 등)
- [ ] 사용자 역할 enum + 권한 범위

### error-handling.md

스캔 경로:
- Vue: `src/utils/*runtime*|*error*|*notify*`, `src/components/common/*Toast*|*Notification*`
- Spring: `**/exception/**`, `**/*ExceptionHandler*`, `**/ErrorResponse*`
- FastAPI: `app/core/exceptions.py`, `app/middleware/error*`

최소 포함:
- [ ] 에러 표시 함수/방법 (`window.appAlert`, `@ControllerAdvice`, `HTTPException` 등)
- [ ] 에러 코드 → 사용자 메시지 매핑 구조
- [ ] 로깅 규칙 (`console.log` 대체재가 있으면 반드시 명시)
- [ ] 이벤트/미들웨어 체인 흐름도 (Mermaid)

### state-management.md

스캔 경로:
- Vue: `src/store/**`, `src/stores/**`, `grep "defineStore\|createStore\|new Vuex" src/`
- React: `src/store/**`, `src/context/**`, `grep "create.*Store\|useReducer\|createContext"`

최소 포함:
- [ ] 사용 중인 상태관리 라이브러리 + 각각의 역할 분담
- [ ] store 모듈/슬라이스 목록 테이블 (이름, 책임, 영속화 여부)
- [ ] 라이브러리 간 선택 기준 ("언제 Vuex, 언제 Pinia?")
- [ ] 영속화 설정 (sessionStorage, localStorage, persist 플러그인)
- [ ] 캐시 무효화 패턴

### routing.md

스캔 경로:
- Vue: `src/router/**`, `grep "meta:" src/router/`
- React: `src/routes/**`, `src/app/(pages)/**`

최소 포함:
- [ ] 라우트 모듈 목록 + 각 모듈의 라우트 수
- [ ] meta 필드 스키마 (어떤 키가 어떤 의미인지)
- [ ] 가드/미들웨어 체인 실행 순서
- [ ] 팝업 라우트 vs 일반 라우트 구분 규칙 (해당 시)
- [ ] keep-alive 대상 라우트 + 캐시 갱신 패턴 (해당 시)

### form-patterns.md

스캔 경로:
- Vue: `package.json` (VeeValidate/Vuelidate/Zod 확인), `src/composables/*validation*`, `src/views/*/popup/*`
- React: `package.json` (react-hook-form/formik/zod), `src/hooks/*form*`

최소 포함:
- [ ] 검증 방식 (라이브러리 vs 수동) — 라이브러리 미사용 시 반드시 명시
- [ ] 검증 실패 시 UX 패턴 (alert+focus, inline error, toast)
- [ ] 폼 통신 패턴 (window.opener, emit, provide/inject, postMessage)
- [ ] 캐스케이딩 셀렉트 패턴 (해당 시)

## 5-4. 품질 체크리스트

각 reference 생성 후 아래를 확인.

### 필수 6개 (4개 이상 미충족 시 재작성, 1-3개 미충족 시 해당 항목만 보강)

- [ ] **참조 시점 명시**: 문서 상단에 "어떤 작업을 할 때 이 문서를 읽는가"
- [ ] **선택 기준 명시**: "A를 쓸 때" vs "B를 쓸 때" 판단 기준
- [ ] **실제 코드 경로**: 패턴의 원본 파일 경로 (예: `src/api/api.js:42`)
- [ ] **코드 스니펫 또는 명령어**: 최소 1개의 실제 프로젝트 코드 (일반 예시 금지)
- [ ] **금지 사항**: 이 영역에서 하면 안 되는 것 (NEVER 규칙)
- [ ] **갱신 트리거**: 이 문서를 업데이트해야 하는 시점

### 권장 4개

- [ ] **Mermaid 다이어그램**: 복잡한 플로우 시각화
- [ ] **의존성 관계**: 다른 모듈/파일과의 의존
- [ ] **변경 시 사이드이펙트**: 수정하면 어디가 영향받는지
- [ ] **자주 하는 실수**: 과거 발생한 문제나 리뷰에서 자주 지적된 것

## 5-5. 기존 문서 병합 전략

기존 `.claude/docs/reference/` 가 있으면 **덮어쓰지 않고 아래 절차에 따라 병합**.

### A. GAP 분석 (선행 — `gap` 인자 시 이 단계만 실행)

기존 reference 각각을 품질 체크리스트 대비 평가:

| 문서 | 줄수 | 필수 충족 | 누락 항목 | 구식화 | 액션 |
|------|------|----------|----------|--------|------|
| (각 문서별) | | /6 | | | 업데이트/신규/소폭보강/삭제검토 |

- **업데이트** → 기존 문서 + 누락 항목 추가
- **신규 생성** → Phase 5 정규 절차
- **소폭 보강** → 누락 1-2 항목만 추가
- **삭제 검토** → 해당 영역이 코드에서 제거됐으면 사용자 확인 후 삭제

### B. 구식화 탐지

reference 내의 구체적 사실을 현재 코드와 대조:

1. **숫자 검증**: 문서의 "15개 모듈" → `ls src/api/domain/*.js | wc -l` → 다르면 구식
2. **경로 검증**: 문서에 언급된 파일 경로가 실제 존재하는지
3. **함수 검증**: 문서에 나열된 함수명이 실제 export 되는지
4. **패턴 검증**: 문서에 기술된 패턴이 여전히 사용되는지

### C. 섹션별 병합 방식

| 섹션 | 방식 | 이유 |
|------|------|------|
| `> 참조 시점 / 갱신 트리거` | **교체** | 최신 판단 기준 반영 |
| `## 개요` | **교체** | 현재 상태가 기준 |
| `## 아키텍처 (Mermaid)` | **교체** | 부분 수정 불가 |
| `## 핵심 패턴` | **누적 병합** | 기존 유지 + 새 패턴 추가 (중복 건너뜀) |
| `## 의존성 & 관계` | **교체** | 현재 상태가 진실 |
| `## 변경 시 주의사항` | **누적 병합** | 과거 이력 삭제 금지 |
| `## (테이블)` | **행 단위 병합** | 기존 행 유지 + 새 행 추가 + 삭제 항목 제거 |

병합 절차:
1. 기존 문서를 `##` 기준으로 섹션 파싱
2. 각 섹션에 위 방식 적용
3. 병합 결과를 사용자에게 diff 로 보여주고 확인

### D. 작업 산출물 (dev-guide 등) 흡수

`.claude/workflow/dev-guide-*.md`, `.claude/workflow/sprint-contract-*.md`, `.claude/docs/dev-guide/` 등의 작업 산출물 MD 를 reference 에 반영:

| 작업 산출물 내용 | 흡수 대상 | 방식 |
|----------------|----------|------|
| Entity 필드 추가/변경 | `data-access.md` / `domain-*.md` | 주의사항에 추가 |
| API 엔드포인트 추가 | `api-layer.md` + `domain-*.md` | 테이블에 행 추가 |
| 새 컴포넌트 생성 | `component-library.md` | 목록에 추가 |
| 새 라우트 추가 | `routing.md` | 모듈에 반영 |
| 상태 전이 변경 | `domain-*.md` | stateDiagram 업데이트 |
| CSS 변수 추가 | `css-system.md` | 변수 테이블에 추가 |
| 새 인증 모드 추가 | `auth-flow.md` | Decision Table 업데이트 |

흡수하지 않는 것: 구현 계획, AC 체크리스트, 디버깅 로그. 흡수 완료 후 dev-guide 원본은 건드리지 않음.

## 5-6. 원칙 + 템플릿

### 원칙

1. **실제 코드 기반**: 코드에서 패턴을 추출 — 추측/일반론 금지
2. **변경사항 강조**: 실수 발생 패턴을 명시
3. **단독 이해 가능**: 다른 reference 를 전제하지 않음. 크로스 참조 필요 시 `> 참조: [문서명]` 한 줄 링크로 처리하되, 핵심 내용은 해당 문서 내에서 중복 기술
4. **언어 일치**: Java ↔ Kotlin 혼용 금지

### 줄 수 규칙

- 기술 reference (api-layer, routing, auth-flow 등): **200줄 이하**
- 도메인 reference (`domain-*.md`): **400줄 이하** (초과 시 `## 목차` 상단 추가)
- 200줄 초과 시 독립적 하위 주제가 있으면 별도 문서로 분리 검토

### 템플릿

```markdown
# [제목]

> 참조 시점: [어떤 작업을 할 때 이 문서를 읽으세요]
> 갱신 트리거: [이 문서를 업데이트해야 하는 시점]

## 개요
[핵심 구조와 기술적 결정 사항]

## 아키텍처
[Mermaid 다이어그램 또는 계층 구조]

## 핵심 패턴
[반복 사용되는 코드 패턴 — 실제 코드에서 추출한 예시]

## 의존성 & 관계
[다른 모듈/레이어와의 관계, 주입 방식, import 경로]

## 변경 시 주의사항
[수정 시 확인해야 할 것, 과거 문제 패턴]
[NEVER 규칙]
```

## 5-B. 도메인 모듈 reference

### 생성 조건

다음을 모두 충족 (비즈니스 중요도가 높은 도메인 — 결제, 인증 등 — 은 뷰 수 관계없이 후보):

1. `src/views/[domain]/` 에 3개 이상 파일 존재
2. 다음 중 하나 이상:
   - API 파일에 5개 이상 export 함수
   - 도메인 고유 상태 전이 존재 (상태 컬럼 + 상태 변경 API)
   - 다른 도메인과 교차 데이터 흐름

### 트리거 판단 (실행 가능 명령어)

```bash
# 1. 도메인 후보 디렉토리
ls src/views/

# 2. 각 디렉토리 파일 수 (3 이상이면 후보)
find src/views/<dir> -name "*.vue" | wc -l

# 3. API 함수 수 (5 이상이면 확정)
grep -c "export" src/api/domain/<domain>.js
```

### 생성 우선순위

1. 뷰 수 기준 내림차순 (가장 큰 도메인 먼저)
2. 최근 6개월 내 커밋 빈도 높은 도메인 우선 (`git log --since` 활용)
3. git log 불가 시 API 함수 수 기준

### 도메인 reference 템플릿

```markdown
# [도메인명] 도메인 가이드

> 참조 시점: [도메인] 관련 뷰/API 수정 시
> 갱신 트리거: [도메인]에 새 페이지/API/상태 추가 시

## 페이지 구조
| 페이지 | 파일 | 유형 | 라우트 |
|--------|------|------|--------|
(유형: Management/Detail/Register/Modal/Print/Mobile)

## API 함수
| 함수 | 메서드 | 엔드포인트 | 용도 |
|------|--------|-----------|------|

## 상태 전이 (해당 시)
[Mermaid stateDiagram]

## 크로스 도메인 연동 (해당 시)
[어떤 도메인에서 이 도메인을 참조하는지, 반대 방향도]

## 도메인 고유 패턴
[이 도메인에서만 사용하는 composable, mixin, 유틸리티]

## 주의사항
[수정 시 반드시 알아야 할 것, NEVER 규칙]
```
