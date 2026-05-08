# Organize CLAUDE.md

> **인자**: $ARGUMENTS
> - `(빈 값)` — **git diff 기반 증분 업데이트**: 마지막 organize 이후 변경된 파일만 감지하여 영향받는 참조 문서만 선택적 업데이트. CLAUDE.md의 `Last Updated` 기준. `Last Updated`가 없거나 CLAUDE.md가 없으면 `full`과 동일하게 전체 재구성.
> - `full` — 전체 재구성 (CLAUDE.md + 모든 참조 문서 — git diff 무시하고 처음부터)
> - `main` — CLAUDE.md만 재구성
> - `references` — 참조 문서만 생성/업데이트
> - `module:<name>` — 특정 모듈의 참조 문서만 (예: `module:repair`)
> - `scan` — 현황 분석만 (변경 없이 리포트)
> - `diff` — 기존 CLAUDE.md vs 제안 변경사항 비교
> - `gap` — 기존 참조 문서 GAP 분석 (품질 점수 + 누락/구식 항목 리포트)
> - `<경로 또는 범위>` — 지정된 디렉토리/파일 범위만 스캔 후 해당 영역의 참조 문서 생성/업데이트 (예: `src/views/repair`, `src/api/domain`)

CLAUDE.md를 **Lazy Loading 참조 구조** + **프레임워크 특화 템플릿** + **Mermaid 아키텍처**로 재구성합니다.

---

## 왜 이 구조가 필요한가

CLAUDE.md는 매 세션 시작 시 전체가 컨텍스트에 로드된다.
- 120줄 이상이면 에이전트가 핵심을 놓치고 지시 compliance가 떨어진다
- 금지형 규칙("NEVER do X")이 권장형("Always prefer Y")보다 compliance가 높다 — 규칙 작성 시 금지형을 우선 사용
- 상세 정보는 `.claude/docs/reference/`에 분리 → 작업 맥락에 따라 lazy loading
- 스캔(Phase 1) 결과가 생성(Phase 5)으로 **명시적으로 매핑**되어야 빈약한 문서 생성을 방지

---

## Phase 0: 전제 조건 확인

### 0-1. 기존 AI 설정 파일 감지

아래 파일이 존재하면 읽어서 CLAUDE.md Key Rules 이관 후보로 활용:
- `.cursorrules` / `.cursor/rules/*.mdc` → Cursor AI
- `.windsurfrules` → Windsurf AI
- `.aider.conf.yml` → Aider
- `copilot-instructions.md` → GitHub Copilot

감지 시 처리:
1. 해당 파일에서 이관할 규칙 추출 + 프레임워크 감지 단서로 활용
2. 충돌 규칙은 사용자에게 명시적 알림
3. 원본 파일 삭제 여부는 사용자 확인

### 0-2. CLAUDE.md 부재 시 신규 생성

CLAUDE.md가 없을 때:
1. README.md가 있으면 → 프로젝트 설명, 명령어, 환경 정보 추출
2. package.json / build.gradle 등 → Phase 1-2와 동일한 프레임워크 감지
3. 최소 골격 생성: Project Overview + Architecture (Mermaid) + Commands + Key Rules (3개) + Reference Docs
4. 사용자에게 "신규 생성 모드입니다. 기존 팀 규칙이 있으면 알려주세요" 안내

### 0-3. CLAUDE.local.md 분리 판단

개인별 차이가 있는 설정(Swagger URL, 로컬 포트, 테스트 계정 등)이 있으면:
1. CLAUDE.local.md로 분리 제안
2. .gitignore에 CLAUDE.local.md 추가 여부 확인

---

## Phase 1: 프로젝트 분석

### 1-1. 기존 상태 확인

1. 기존 CLAUDE.md 전체 읽기 (없으면 Phase 0-2 신규 생성)
2. 기존 `.claude/docs/reference/` 파일 목록 + 각 파일 줄 수 확인
3. `.gitignore`에서 `.claude/docs/reference/` 차단 여부 확인
4. 기존 `.claude/rules/` 파일 확인
5. **작업 산출물 감지** — 아래 경로에 최근 MD가 있으면 읽어서 Phase 5 병합에 활용:
   - `.claude/workflow/dev-guide-*.md` → Jira 개발 가이드 (변경 명세)
   - `.claude/workflow/sprint-contract-*.md` → Sprint Contract
   - `.claude/docs/dev-guide/` → 별도 보관된 개발 가이드
6. **git diff 기반 변경 감지** — `(빈 값)` 인자의 핵심 동작:
   - CLAUDE.md에 `Last Updated`가 있으면:
     - `git log --since="[Last Updated 날짜]" --name-only --pretty=format:""` → 변경 파일 목록
     - 변경 파일 → Phase 1-4 매핑 테이블 역참조 → 영향받는 참조 문서만 선택적 재스캔
     - 전체 재스캔보다 효율적이고 정확
   - `Last Updated`가 없거나 CLAUDE.md 부재 시 → `full` 모드로 전체 재구성
   - `<경로>` 인자 시 → 해당 경로 하위 파일만 스캔 대상으로 제한

### 1-2. 프레임워크 + 언어 자동 감지

프로젝트 루트의 빌드 파일(package.json, build.gradle, pom.xml, pubspec.yaml, go.mod, Cargo.toml, requirements.txt, pyproject.toml 등)을 스캔하여 **프레임워크 + 언어 + 버전** 조합을 판별한다.

핵심 주의점:
- 언어 단독으로 분류하지 않는다 — 항상 프레임워크와 함께 감지
- **JVM 프로젝트는 Java vs Kotlin 필수 구분** — `src/main/kotlin/` 존재, `*.kt` 파일, `kotlin()` 플러그인 여부로 판별. 잘못 감지하면 Lombok ↔ data class 혼용이 발생
- 복수 스택 감지 시 → **Monorepo**: 루트 공통 CLAUDE.md + 각 패키지 디렉토리에 하위 CLAUDE.md
- 결과 예시: `Spring Boot 3.3.8 (Java 21)`, `Vue 3.4 (TypeScript)`, `Flutter 3.24 (Dart)`

### 1-3. 프레임워크별 딥 스캔

감지된 프레임워크에 따라 **실제 코드를 분석**한다 (추측 금지).
아래 영역을 프레임워크에 맞게 스캔한다:

**공통 스캔 영역:**
- 빌드 파일 → 버전, 의존성, 스크립트, 프로파일
- 디렉토리 구조 → 도메인/모듈 목록, 레이어 분리 방식
- 상태관리 → 사용 라이브러리, store 구조, 영속화 패턴
- 라우팅 → 라우트 구조, 가드/미들웨어, 메타 필드
- API 통신 → 클라이언트 설정, 인터셉터, 에러 핸들링
- 인증 → 인증 모드, 토큰 관리, 가드 체인, 커스텀 플래그
- 스타일링 → CSS 시스템, 변수, 반응형 분기
- 테스트 → 프레임워크, 설정, mock 패턴
- 린트/빌드 → ESLint/Prettier/분석 설정
- i18n → 메시지 구조, 네임스페이스
- 폼 → 검증 라이브러리 유무, 검증 패턴

**프레임워크 고유 스캔:**
- **Spring Boot**: Entity 상속/감사필드, Repository+QueryDSL CustomImpl, CQRS 분리, Swagger 어노테이션, @Scheduled/ShedLock, Feign/WebClient. **Java vs Kotlin 패턴 구분 필수**
- **Vue/Nuxt**: Composition vs Options API 비율, composables, Vuex vs Pinia 공존, keep-alive 캐시, window.open 팝업 패턴, axios 커스텀 플래그(_skipAuth 등)
- **React/Next.js**: App Router vs Pages Router, 커스텀 hooks, SSR/SSG 패턴
- **Flutter**: BLoC/Provider/Riverpod 패턴, freezed/json_serializable, build_runner, 플랫폼별 설정
- **NestJS**: 모듈/DI 구조, ORM, Guards/Pipes, 큐/이벤트

### 1-4. 스캔 결과 → 참조 문서 매핑

Phase 1-3 딥 스캔의 각 항목이 어떤 참조 문서로 흘러가는지 매핑한다.
**매핑되지 않은 스캔 결과는 architecture.md에 요약으로 포함한다.**

#### Vue / Nuxt 매핑

| 스캔 항목 | 기록 위치 |
|-----------|----------|
| package.json 의존성, 빌드 설정 | build-config.md |
| Vue 버전, Composition vs Options 비율 | architecture.md |
| views/ 구조 → 도메인 목록 | CLAUDE.md Architecture + domain-*.md |
| components/ 구조 | component-library.md |
| composables/ 목록 | 각 해당 참조 문서에 분산 기재 |
| store/ + stores/ → 상태관리 | state-management.md |
| router/ → 모듈 + 가드 + 메타 | routing.md |
| api/ → 인스턴스 + 인터셉터 | api-layer.md + auth-flow.md |
| 인증 인터셉터 + 라우터 가드 + 토큰 | auth-flow.md |
| locales/ → 네임스페이스 구조 | i18n.md |
| assets/css/ → 변수 + 브레이크포인트 | css-system.md + responsive-layout.md |
| 그리드 라이브러리 설정 | grid-library.md |
| 에러 핸들링 유틸 + Toast | error-handling.md |
| 폼 검증 패턴 | form-patterns.md |
| 팝업 패턴 (window.open) | component-library.md |
| keep-alive 캐시 관리 | routing.md |
| PrimeVue/Element/Vuetify 설정 | component-library.md |

#### Spring Boot 매핑

| 스캔 항목 | 기록 위치 |
|-----------|----------|
| build.gradle 의존성, 프로파일 | build-config.md |
| 패키지 구조 → 도메인 모듈 | CLAUDE.md Architecture + domain-*.md |
| Entity + 상속 + 감사필드 | data-access.md |
| Repository + QueryDSL | data-access.md |
| Service CQRS 분리 여부 | architecture.md |
| Controller + Swagger | api-layer.md |
| Security + JWT | security-infra.md |
| application.yml 프로파일 | build-config.md |
| 스케줄러 + 외부연동 | async-scheduling.md |
| 테스트 설정 | testing.md |
| 캐시 (Redis/Caffeine) | caching.md |

#### 기타 프레임워크 (React/FastAPI/Django/Go)

스캔 결과를 아래 공통 카테고리로 매핑한다:

| 스캔 범주 | 기록 위치 |
|-----------|----------|
| 빌드/환경 설정 | build-config.md |
| 앱 구조/모듈/레이어 | architecture.md |
| ORM/데이터 접근 | data-access.md |
| 인증/미들웨어/가드 | auth-flow.md |
| API 스키마/직렬화/컨트롤러 | api-layer.md |
| 상태관리 | state-management.md |
| 테스트 구조 | testing.md |
| 도메인별 코드 | domain-[name].md |

#### git diff 기반 역매핑 (Phase 1-1과 연동)

변경 파일에서 영향받는 참조 문서를 빠르게 판별할 때 사용:

| 변경 파일 패턴 | 영향받는 참조 문서 |
|---------------|------------------|
| src/api/domain/*.js | api-layer.md + domain-[name].md |
| src/api/api.js, src/api/interceptors.js | api-layer.md + auth-flow.md |
| src/store/**, src/stores/** | state-management.md |
| src/router/** | routing.md |
| src/views/[domain]/** | domain-[name].md |
| src/locales/*.json | i18n.md |
| src/assets/css/** | css-system.md |
| vue.config.js, .env* | build-config.md |
| src/components/common/** | component-library.md |
| src/utils/** | error-handling.md |
| package.json | build-config.md + 버전 변경 시 해당 문서 |

---

## Phase 2: 콘텐츠 분류

기존 CLAUDE.md와 스캔 결과를 합쳐서 두 계층으로 분류한다.

### 프로젝트 규모 분류

참조 문서 최소 개수를 결정하기 위해 5개 지표를 합산한다:

| 지표 | 0점 | 1점 | 2점 |
|------|-----|-----|-----|
| 뷰/페이지 수 | ~15개 | 16-60개 | 61개+ |
| 라우트 수 | ~30개 | 31-100개 | 101개+ |
| API 함수 수 | ~20개 | 21-80개 | 81개+ |
| 상태관리 | 단일 store | 복수 store | 복수 라이브러리 |
| i18n 복잡도 | 없거나 단일 | 2-10 NS | 11개+ |

합산 → 규모:
- **0-2점 → Small**: 최소 4-5개 참조 문서
- **3-5점 → Medium**: 최소 7-10개 참조 문서
- **6-10점 → Large**: 최소 12-16개 참조 문서

### 메인 vs 분리 판단

**메인에 남길 조건 (ALL 충족):**
1. 전체 프로젝트 수준 정보 (특정 도메인/영역이 아님)
2. 10줄 이하로 핵심 전달 가능
3. 위반 시 즉시 문제 발생 (빌드/런타임/보안)

**분리 대상 (ANY 충족):**
1. 특정 작업 유형에서만 필요
2. 코드 예시가 필요한 설명
3. 10줄 이상의 상세 설명
4. 주기적으로 변경되는 정보

### 메인에 남길 것 (Always Loaded)

- 프로젝트 한 줄 설명 + 프레임워크/언어/버전
- Mermaid 아키텍처 다이어그램
- 도메인 모듈 테이블 (해당 시)
- 핵심 명령어 (build/test/run — 코드블록)
- 필수 규칙 3-5개 (금지형 우선)
- Git 컨벤션 (2-3줄)
- 환경 정보 (프로파일, SDK 경로, Swagger/Storybook URL 등)
- Skills 테이블 (있으면 반드시 메인 유지)
- 참조 문서 인덱스 테이블

> 참조 문서 테이블이 20줄을 초과하면 별도 `DOC_INDEX.md` 분리를 권장

### 분리할 것 (On Demand → `.claude/docs/reference/`)

Phase 5의 Decision Matrix와 후보 테이블에 따라 결정한다.

**공통 (모든 프레임워크):**
- 테스트 전략 (단위/통합/E2E, 커버리지, Mock 패턴)
- 빌드/환경 설정
- 공통 이슈 & 트러블슈팅

**프레임워크별 참조 문서 후보** → Phase 5-2 참조

---

## Phase 3: Mermaid 아키텍처 다이어그램 생성

Phase 1-3 스캔 결과를 기반으로 실제 코드 구조를 반영한 Mermaid `graph TD` 다이어그램을 생성한다.
- 반드시 ` ```mermaid ` 코드펜스로 감싸기
- `subgraph`로 레이어 분리 (Web/Domain/Infra 또는 UI/Logic/Data 등)
- 실제 존재하는 레이어와 컴포넌트만 포함 — 프레임워크 기본 템플릿을 그대로 쓰지 않고 스캔 결과에 맞게 조정

---

## Phase 4: 메인 CLAUDE.md 작성

**120줄 이하**로 작성한다. 아래 구조를 기반으로 하되, 프레임워크에 없는 섹션은 생략한다.

```
# CLAUDE.md

## Project Overview
[프레임워크] [버전] ([언어] [버전]) — [프로젝트 한 줄 설명]
- **응답은 한국어로 해주세요** (해당 시)

## Architecture
[Mermaid 아키텍처 다이어그램 — Phase 3에서 생성한 것]

### Domain Modules (해당 시)
| Module | Purpose |
|--------|---------|

## Commands
[코드블록 — 프레임워크에 맞는 빌드/테스트/실행 명령어]

## Key Rules
[3-5개 — 금지형 우선, 가장 중요한 것만]

## Git Conventions (해당 시)
[브랜치/커밋 규칙 — 2-3줄]

## Environment (해당 시)
[프로파일, SDK 경로, URL 등]

## Skills (해당 시)
[스킬 테이블 — 에이전트 트리거 위해 반드시 메인에 유지]

## Reference Docs
작업에 따라 아래 문서를 참조하세요:

| 문서 | 참조 시점 | 경로 |
|------|----------|------|

---
Last Updated: [오늘 날짜]
```

### Key Rules 작성 가이드

규칙은 아래 우선순위로 선별:

1. **위반 시 빌드/런타임 오류** 발생하는 것 (예: Q-class 미생성, 코드 생성 누락)
2. **위반 시 데이터 손실/보안 문제** 생기는 것 (예: 소프트삭제 누락, XSS)
3. **위반 시 성능 문제** 생기는 것 (예: N+1, 불필요한 리렌더링)
4. **팀 컨벤션**으로 반복 위반되는 것

금지형으로 작성:
```
# Spring Boot (Java)
- **NEVER** Entity 수정 후 `clean build` 생략 — Q-class 재생성 필수
- **NEVER** 쿼리에서 소프트삭제 조건 누락 — `DeleteYnPredicates.isNotDeleted()` 사용

# Spring Boot (Kotlin)
- **NEVER** Entity에 data class 사용 — JPA 프록시와 충돌, 일반 class + copy 함수로 대체
- **NEVER** suspend fun 없이 코루틴 서비스 작성 — blocking 코드 혼입 방지

# Vue
- **NEVER** composable 바깥에서 `ref()`를 직접 export — 반응성 소실
- **NEVER** `<script setup>` 없이 Composition API 사용 — SFC 컨벤션 위반

# Flutter
- **NEVER** build() 안에서 비동기 호출 — initState 또는 상태관리 레이어에서 처리
- **NEVER** StatefulWidget 남용 — 상태관리 패키지로 분리
```

---

## Phase 5: 참조 문서 생성/업데이트

`.claude/docs/reference/` 디렉토리에 **기술 중심** 참조 문서를 생성한다.

### 5-1. Decision Matrix — 생성 판단 기준

모든 기준은 **grep/ls로 확인 가능한 관찰 기준**이다. 사후 판단("오류가 발생하는 영역")은 사용하지 않는다.

#### 필수 생성 — 다음 중 하나라도 해당:

**Rule 1 (커스텀 전역 함수):**
`window.*`, `Vue.prototype.*`, `$fn*` 형태의 커스텀 전역이 3개 이상인가?
→ 확인: `grep -r "window\.\w\+\s*=" src/utils/ | wc -l`
→ YES → error-handling.md 또는 해당 영역 문서 필수

**Rule 2 (라이브러리 버전 갭):**
주요 라이브러리가 현재 major에서 2+ 버전 뒤처지는가?
→ 확인: package.json 버전 vs `npm info [pkg] version`
→ YES → 해당 라이브러리 전용 참조 문서 필수 (예: ag-grid v29 → grid-library.md)

**Rule 3 (패턴 반복 빈도):**
동일 함수/컴포넌트/패턴이 5개 이상 뷰에서 import되는가?
→ 확인: `grep -rl "import.*ModalPopup" src/views/ | wc -l`
→ YES → 해당 패턴의 참조 문서 필수

**Rule 4 (복수 모드 분기):**
동일 목적의 함수가 2개 이상 존재하며 선택 기준이 필요한가?
→ 확인: 같은 API 파일에 getApi, bypassGetApi, noAuthApi 공존
→ YES → auth-flow.md 필수

**Rule 5 (프레임워크 기본과 다른 패턴):**
공식 문서가 권장하는 방식과 다른 패턴을 사용하는가?
→ 확인: `console.log` 대신 커스텀 로깅, `useI18n()` 대신 `i18n.global.t` 등
→ YES → 해당 영역 문서에 "NEVER" 규칙 포함 필수

#### 권장 생성:

**Rule 6:** Rule 3 기준이 2-4개 파일인 경우
**Rule 7:** .env 파일이 3개 이상 (dev/staging/prod 분리) → build-config.md
**Rule 8:** i18n 네임스페이스가 10개 이상 → i18n.md

#### 생성 불필요:
- 위 Rule 중 해당 없음
- 프레임워크 기본 동작을 그대로 사용 (context7로 보완 가능)
- 단일 파일에서만 사용되는 유틸리티

### 5-2. 참조 문서 후보 (프레임워크별)

#### Vue / Nuxt (15개)

| # | 문서 | 참조 시점 | 생성 조건 |
|---|------|----------|----------|
| 1 | architecture.md | 프로젝트 구조 파악 시 | 항상 |
| 2 | api-layer.md | API 호출 작성 시 | 항상 |
| 3 | css-system.md | 스타일 작성 시 | CSS 변수 시스템 또는 커스텀 패턴 |
| 4 | testing.md | 테스트 작성 시 | 항상 |
| 5 | state-management.md | 상태 관리 작업 시 | Rule 4: Vuex+Pinia 공존 또는 5+ store |
| 6 | routing.md | 라우트 수정 시 | Rule 3: 50+ 라우트 또는 커스텀 가드 |
| 7 | auth-flow.md | 인증 관련 수정 시 | Rule 4: 인증 모드 2종 이상 |
| 8 | error-handling.md | 에러 처리 작성 시 | Rule 1: 커스텀 전역 3+ 또는 Rule 5 |
| 9 | i18n.md | 다국어 작업 시 | Rule 8: 10+ 네임스페이스 |
| 10 | component-library.md | UI 컴포넌트 사용 시 | Rule 3: 5+ 뷰에서 사용 |
| 11 | grid-library.md | 목록 페이지 개발 시 | Rule 2: 그리드 버전 갭 |
| 12 | form-patterns.md | 폼 개발 시 | Rule 5: 폼 라이브러리 미사용 |
| 13 | responsive-layout.md | 반응형 UI 작업 시 | Rule 5: 커스텀 반응형 분기 |
| 14 | build-config.md | 빌드 설정 수정 시 | Rule 7: 환경별 분기 또는 커스텀 프록시 |
| 15 | domain-[name].md | 해당 도메인 수정 시 | Phase 5-B 트리거 조건 |

#### Spring Boot (10개)

| # | 문서 | 참조 시점 | 생성 조건 |
|---|------|----------|----------|
| 1 | architecture.md | 구조 파악 시 | 항상 |
| 2 | api-layer.md | Controller/DTO 작업 시 | 항상 |
| 3 | data-access.md | Repository/JPA/QueryDSL 시 | 항상 |
| 4 | security-infra.md | 인증/인가/외부연동 시 | Security 설정 존재 |
| 5 | testing.md | 테스트 작성 시 | 항상 |
| 6 | build-config.md | Gradle/프로파일 수정 시 | Rule 7: 3+ 프로파일 |
| 7 | kotlin-patterns.md | Kotlin 프로젝트 시 | 언어가 Kotlin인 경우만 |
| 8 | domain-[name].md | 도메인 수정 시 | Phase 5-B 트리거 조건 |
| 9 | caching.md | 캐시 설정 수정 시 | Redis/Caffeine 의존성 존재 |
| 10 | async-scheduling.md | 비동기/스케줄러 시 | @Async/@Scheduled/ShedLock 존재 |

#### React / Next.js (8개)

| # | 문서 | 참조 시점 | 생성 조건 |
|---|------|----------|----------|
| 1 | architecture.md | 구조 파악 시 | 항상 |
| 2 | api-layer.md | API 호출 작성 시 | 항상 |
| 3 | state-management.md | 상태 관리 시 | 복수 상태관리 또는 커스텀 패턴 |
| 4 | css-system.md | 스타일 작성 시 | Tailwind 외 커스텀 시스템 |
| 5 | routing.md | 라우트 수정 시 | 50+ 라우트 또는 커스텀 미들웨어 |
| 6 | testing.md | 테스트 작성 시 | 항상 |
| 7 | build-config.md | 빌드 설정 시 | Rule 7 |
| 8 | domain-[name].md | 도메인 수정 시 | Phase 5-B 트리거 조건 |

#### FastAPI / Django / Go — 공통 패턴

핵심 4개(architecture, api-layer, testing, build-config)는 모든 프레임워크에 공통.
나머지는 Decision Matrix Rule 1-8 적용 결과에 따라 결정:
- data-access.md: ORM/Repository 존재 시
- auth-flow.md: 인증 미들웨어/가드 존재 시
- domain-[name].md: Phase 5-B 트리거 조건

#### Flutter (7개)

| # | 문서 | 참조 시점 | 생성 조건 |
|---|------|----------|----------|
| 1 | architecture.md | 구조 파악 시 | 항상 |
| 2 | state-management.md | BLoC/Provider/Riverpod 시 | 항상 |
| 3 | data-layer.md | API/로컬 저장소/모델 시 | 항상 |
| 4 | navigation.md | 라우팅/딥링크 수정 시 | 커스텀 라우팅 존재 |
| 5 | testing.md | 테스트 작성 시 | 항상 |
| 6 | build-config.md | 빌드 설정 시 | Rule 7 |
| 7 | domain-[name].md | 도메인 수정 시 | Phase 5-B 트리거 조건 |

### 5-3. 참조 문서별 스캔 경로 + 최소 포함 항목

각 참조 문서에 **무엇을 담을지** 구체 지침. 모든 문서에 적용되는 공통 사항 후 핵심 문서를 상세 기술한다.

#### 공통 — 모든 참조 문서에 반드시 포함:

1. 스캔 경로 명시 (어떤 파일을 분석했는지)
2. 최소 포함 항목 체크리스트
3. 금지사항 (NEVER 규칙)
4. 갱신 트리거

#### auth-flow.md

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
- [ ] 프레임워크별 플래그/어노테이션 (_skipAuth, @PreAuthorize 등)
- [ ] 사용자 역할 enum + 권한 범위

#### error-handling.md

스캔 경로:
- Vue: `src/utils/*runtime*|*error*|*notify*`, `src/components/common/*Toast*|*Notification*`
- Spring: `**/exception/**`, `**/*ExceptionHandler*`, `**/ErrorResponse*`
- FastAPI: `app/core/exceptions.py`, `app/middleware/error*`

최소 포함:
- [ ] 에러 표시 함수/방법 (window.appAlert, @ControllerAdvice, HTTPException 등)
- [ ] 에러 코드 → 사용자 메시지 매핑 구조
- [ ] 로깅 규칙 (console.log 대체재가 있으면 반드시 명시)
- [ ] 이벤트/미들웨어 체인 흐름도 (Mermaid)

#### state-management.md

스캔 경로:
- Vue: `src/store/**`, `src/stores/**`, `grep "defineStore\|createStore\|new Vuex" src/`
- React: `src/store/**`, `src/context/**`, `grep "create.*Store\|useReducer\|createContext"`

최소 포함:
- [ ] 사용 중인 상태관리 라이브러리 + 각각의 역할 분담
- [ ] store 모듈/슬라이스 목록 테이블 (이름, 책임, 영속화 여부)
- [ ] 라이브러리 간 선택 기준 ("언제 Vuex, 언제 Pinia?")
- [ ] 영속화 설정 (sessionStorage, localStorage, persist 플러그인)
- [ ] 캐시 무효화 패턴

#### routing.md

스캔 경로:
- Vue: `src/router/**`, `grep "meta:" src/router/`
- React: `src/routes/**`, `src/app/(pages)/**`

최소 포함:
- [ ] 라우트 모듈 목록 + 각 모듈의 라우트 수
- [ ] meta 필드 스키마 (어떤 키가 어떤 의미인지)
- [ ] 가드/미들웨어 체인 실행 순서
- [ ] 팝업 라우트 vs 일반 라우트 구분 규칙 (해당 시)
- [ ] keep-alive 대상 라우트 + 캐시 갱신 패턴 (해당 시)

#### form-patterns.md

스캔 경로:
- Vue: `package.json` (VeeValidate/Vuelidate/Zod 확인), `src/composables/*validation*`, `src/views/*/popup/*`
- React: `package.json` (react-hook-form/formik/zod), `src/hooks/*form*`

최소 포함:
- [ ] 검증 방식 (라이브러리 vs 수동) — 라이브러리 미사용 시 반드시 명시
- [ ] 검증 실패 시 UX 패턴 (alert+focus, inline error, toast)
- [ ] 폼 통신 패턴 (window.opener, emit, provide/inject, postMessage)
- [ ] 캐스케이딩 셀렉트 패턴 (해당 시)

### 5-4. 품질 체크리스트

각 참조 문서 생성 후 아래를 확인한다.

#### 필수 6개 (4개 이상 미충족 시 재작성, 1-3개 미충족 시 해당 항목만 보강):

- [ ] **참조 시점 명시**: 문서 상단에 "어떤 작업을 할 때 이 문서를 읽는가"
- [ ] **선택 기준 명시**: "A를 쓸 때" vs "B를 쓸 때" 판단 기준
- [ ] **실제 코드 경로**: 패턴의 원본 파일 경로 (예: `src/api/api.js:42`)
- [ ] **코드 스니펫 또는 명령어**: 최소 1개의 실제 프로젝트 코드 (일반 예시 금지)
- [ ] **금지 사항**: 이 영역에서 하면 안 되는 것 (NEVER 규칙)
- [ ] **갱신 트리거**: 이 문서를 업데이트해야 하는 시점

#### 권장 4개:

- [ ] **Mermaid 다이어그램**: 복잡한 플로우 시각화
- [ ] **의존성 관계**: 다른 모듈/파일과의 의존
- [ ] **변경 시 사이드이펙트**: 수정하면 어디가 영향받는지
- [ ] **자주 하는 실수**: 과거 발생한 문제나 리뷰에서 자주 지적된 것

### 5-5. 기존 문서 병합 전략

기존 `.claude/docs/reference/`가 있으면 **덮어쓰지 않고 아래 절차에 따라 병합**한다.

#### A. GAP 분석 (선행 — `gap` 인자 시 이 단계만 실행)

기존 참조 문서 각각을 품질 체크리스트 대비 평가:

| 문서 | 줄수 | 필수 충족 | 누락 항목 | 구식화 | 액션 |
|------|------|----------|----------|--------|------|
| (각 문서별) | | /6 | | | 업데이트/신규/소폭보강/삭제검토 |

- **업데이트** → 기존 문서를 읽고 누락 항목만 추가
- **신규 생성** → Phase 5 정규 절차에 따라 생성
- **소폭 보강** → 누락 1-2항목만 추가
- **삭제 검토** → 해당 영역이 코드에서 제거됐으면 사용자 확인 후 삭제

#### B. 구식화 탐지

참조 문서 내의 구체적 사실을 현재 코드와 대조:

1. **숫자 검증**: 문서의 "15개 모듈" → `ls src/api/domain/*.js | wc -l` → 달라지면 구식
2. **경로 검증**: 문서에 언급된 파일 경로가 실제 존재하는지
3. **함수 검증**: 문서에 나열된 함수명이 실제 export 되는지
4. **패턴 검증**: 문서에 기술된 패턴이 여전히 사용되는지 (예: `grep "columnApi" src/views/`)

#### C. 섹션별 병합 방식

| 섹션 | 방식 | 이유 |
|------|------|------|
| > 참조 시점 / 갱신 트리거 | **교체** | 최신 판단 기준 반영 |
| ## 개요 | **교체** | 현재 상태가 기준 |
| ## 아키텍처 (Mermaid) | **교체** | 부분 수정 불가 |
| ## 핵심 패턴 | **누적 병합** | 기존 유지 + 새 패턴 추가 (중복 건너뜀) |
| ## 의존성 & 관계 | **교체** | 현재 상태가 진실 |
| ## 변경 시 주의사항 | **누적 병합** | 과거 이력 삭제 금지 |
| ## (테이블) | **행 단위 병합** | 기존 행 유지 + 새 행 추가 + 삭제 항목 제거 |

병합 절차:
1. 기존 문서를 `##` 기준으로 섹션 파싱
2. 각 섹션에 위 방식 적용
3. 병합 결과를 사용자에게 diff로 보여주고 확인

#### D. 작업 산출물(dev-guide) 흡수

Phase 1-1에서 감지한 작업 산출물 MD를 참조 문서에 반영:

| 작업 산출물 내용 | 흡수 대상 | 방식 |
|----------------|----------|------|
| Entity 필드 추가/변경 | data-access.md / domain-*.md | 주의사항에 추가 |
| API 엔드포인트 추가 | api-layer.md + domain-*.md | 테이블에 행 추가 |
| 새 컴포넌트 생성 | component-library.md | 목록에 추가 |
| 새 라우트 추가 | routing.md | 모듈에 반영 |
| 상태 전이 변경 | domain-*.md | stateDiagram 업데이트 |
| CSS 변수 추가 | css-system.md | 변수 테이블에 추가 |
| 새 인증 모드 추가 | auth-flow.md | Decision Table 업데이트 |

흡수하지 않는 것: 구현 계획, AC 체크리스트, 디버깅 로그.
흡수 완료 후 dev-guide 원본은 건드리지 않음.

### 5-6. 참조 문서 원칙 + 템플릿

#### 원칙

1. **실제 코드 기반**: 코드에서 패턴을 추출 — 추측/일반론 금지
2. **변경사항 강조**: 실수 발생 패턴을 명시
3. **단독 이해 가능**: 다른 참조 문서를 전제하지 않음. 크로스 참조 필요 시 `> 참조: [문서명]` 한 줄 링크로 처리하되, 핵심 내용은 해당 문서 내에서 중복 기술
4. **언어 일치**: Java ↔ Kotlin 혼용 금지

#### 줄 수 규칙

- 기술 참조 문서 (api-layer, routing, auth-flow 등): **200줄 이하**
- 도메인 참조 문서 (domain-*.md): **400줄 이하** (초과 시 `## 목차` 상단 추가)
- 200줄 초과 시 독립적 하위 주제가 있으면 별도 문서로 분리 검토

#### 템플릿

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

#### 작성 규칙

- 코드 예시는 실제 프로젝트 패턴 반영 (일반 예시 금지)
- `.claude/docs/reference/`는 git에 커밋 (에이전트 접근 보장)

---

## Phase 5-B: 도메인 모듈 참조 문서

### 생성 조건

다음을 모두 충족 (비즈니스 중요도가 높은 도메인 — 결제, 인증 등 — 은 뷰 수 관계없이 후보):

1. `src/views/[domain]/`에 3개 이상 파일 존재
2. 다음 중 하나 이상:
   a. API 파일에 5개 이상 export 함수
   b. 도메인 고유 상태 전이 존재 (상태 컬럼 + 상태 변경 API)
   c. 다른 도메인과 교차 데이터 흐름

### 트리거 판단 (실행 가능 명령어)

1. `ls src/views/` → 디렉토리 목록
2. 각 디렉토리: `find src/views/[dir] -name "*.vue" | wc -l` → 3 이상이면 후보
3. 후보: `grep -c "export" src/api/domain/[domain].js` → 5 이상이면 확정

### 생성 우선순위

1. 뷰 수 기준 내림차순 (가장 큰 도메인 먼저)
2. 최근 6개월 내 커밋 빈도 높은 도메인 우선 (`git log --since` 활용)
3. git log 불가 시 API 함수 수 기준

### 도메인 참조 문서 템플릿

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

### 생성 후 처리

1. `.claude/docs/reference/domain-[name].md`에 저장
2. CLAUDE.md Reference Docs 테이블에 행 자동 추가
3. Phase 7 검증에 포함

---

## Phase 6: 실행 전 확인

**사용자에게 변경 계획을 보여주고 확인 받은 후에만 실행한다.**

표시할 내용:
1. 감지된 프레임워크 + 언어 조합 (예: `Spring Boot 3.3.8 (Java 21)`)
2. 프로젝트 규모 분류 (Small/Medium/Large + 점수)
3. 실행 모드 표시:
   - `(빈 값)` → "증분 모드: Last Updated [날짜] 이후 변경 N개 파일 감지, 영향받는 참조 문서 M개"
   - `full` → "전체 재구성 모드"
   - `<경로>` → "범위 지정 모드: [경로] 하위 N개 파일 스캔"
4. 메인 CLAUDE.md 변경 요약 (추가/이동/유지 항목)
5. 생성/업데이트할 참조 문서 목록 + 각각의 Decision Matrix Rule 근거
6. 도메인 참조 문서 후보 목록 (Phase 5-B)
7. `scan` 인자 시: 리포트만 출력하고 종료
8. `diff` 인자 시: 현재 vs 제안 차이점만 보여주고 종료
9. `gap` 인자 시: GAP 분석 리포트만 출력하고 종료

---

## Phase 7: 검증

### 형식/구조 검증 (기존)

- [ ] 메인 CLAUDE.md가 **120줄 이하**인지 확인
- [ ] 기존 정보가 100% 메인 또는 참조 문서에 보존되었는지 확인
- [ ] 참조 테이블의 경로가 실제 파일과 일치하는지 확인
- [ ] Mermaid 다이어그램이 실제 코드 구조를 반영하는지 확인
- [ ] 빌드/테스트 명령어가 정확한지 확인 (빌드 설정 파일 대조)
- [ ] `.claude/docs/reference/`가 `.gitignore`에 포함되지 않았는지 확인
- [ ] Skills 섹션이 있으면 메인에 유지되었는지 확인
- [ ] Key Rules가 금지형 우선으로 작성되었는지 확인
- [ ] Java/Kotlin 언어가 정확히 반영되었는지 확인

### 내용 품질 검증 (신규)

- [ ] 참조 문서 수가 규모 분류 대비 최소 개수 이상인가
- [ ] 각 참조 문서가 품질 체크리스트 필수 6개 항목을 충족하는가
- [ ] Decision Matrix Rule 1-5에 해당하는 영역에 모두 문서가 있는가
- [ ] 도메인 트리거 조건을 충족하는 도메인에 domain-*.md가 있는가
- [ ] 참조 문서 간 내용 중복이 없는가 (크로스 참조 링크는 OK)
- [ ] 기술 참조 문서 200줄 이하, 도메인 참조 문서 400줄 이하인가

### 최종 리포트

```
줄 수 리포트:
- CLAUDE.md: N줄
- 참조 문서: M개 (총 L줄)
- 규모 분류: [Small/Medium/Large] (점수: X/10)
- 품질 점수: 평균 Y/6 필수 항목 충족
```

---

## 핵심 주의사항

- 기존 CLAUDE.md의 정보를 **절대 삭제하지 않음** — 메인 또는 참조 문서로 반드시 이동
- 기존 `.claude/docs/reference/`가 있으면 **Phase 5-5 병합 전략에 따라 병합**
- Skills 섹션은 메인 CLAUDE.md에 유지 (에이전트가 스킬 트리거 위해 항상 봐야 함)
- Screenshots, Notes 등 운영 관련 섹션도 메인에 유지
- 모노레포: 루트 CLAUDE.md (공통 규칙) + 각 패키지 디렉토리에 하위 CLAUDE.md (패키지 전용, lazy loaded)
- `module:<name>` 인자 사용 시: 해당 모듈만 딥 스캔 후 참조 문서 1개 생성/업데이트
- Java/Kotlin 혼동 금지: 감지된 언어에 맞는 패턴만 적용 (Lombok ↔ data class 혼용 불가)
- 빌드 파일 감지 순서: package.json → build.gradle(.kts) → pom.xml → Makefile → nx.json/turbo.json → Dockerfile
