---
name: organize-claude-md
description: CLAUDE.md를 Lazy Loading 참조 구조 + 프레임워크 특화 템플릿 + Mermaid 아키텍처로 재구성. Monorepo 분기 + CHANGELOG 분리 + ADR 자동 생성 안내. **반드시 사용:** "CLAUDE.md 정리", "CLAUDE.md 재구성", "claude.md 비대화", "오늘 개발 사항 정리", "Last Updated 정리", "참조 문서 만들어줘", "reference docs", "monorepo CLAUDE 분리", "프로젝트 문서 organize", "AI agent 문서 구조 개선", "organize claude md" 등의 요청. CLAUDE.md 가 120줄(단일) / 150줄(monorepo root) 초과, Last Updated 라인이 3K 토큰 또는 5회 closure 누적, sub-project 추가 후 root 구조 갱신, 기존 reference 가 구식화된 경우에도 트리거. 단일 프로젝트 / monorepo 모두 지원. Spring Boot (Java/Kotlin) / Vue / Nuxt / React / Next.js / Flutter / NestJS / FastAPI / Django / Go 프레임워크별 특화 스캔.
---

# Organize CLAUDE.md

CLAUDE.md 를 **Lazy Loading 참조 구조** + **프레임워크 특화 템플릿** + **Mermaid 아키텍처** 로 재구성합니다.

## 인자 (사용자가 함께 전달)

| 인자 | 동작 |
|------|------|
| `(빈 값)` | **git diff 기반 증분**: 마지막 organize (Last Updated 기준) 이후 변경된 파일만 감지하여 영향받는 reference 만 선택적 갱신. CLAUDE.md 부재 또는 Last Updated 없으면 `full` 동일 |
| `full` | 전체 재구성 (CLAUDE.md + 모든 reference — git diff 무시) |
| `main` | CLAUDE.md 만 재구성 |
| `references` | reference 만 생성/갱신 |
| `module:<name>` | 특정 모듈의 reference 만 (monorepo 는 `module:<sub>/<name>`) |
| `scan` | 현황 분석만 (변경 없이 리포트) |
| `diff` | 기존 vs 제안 차이점만 표시 |
| `gap` | 기존 reference GAP 분석 (품질 점수 + 누락/구식 리포트) |
| `<경로>` | 지정 경로만 스캔 + 해당 영역 reference 만 갱신 |

## 왜 이 구조가 필요한가

CLAUDE.md 는 매 세션 시작 시 전체가 컨텍스트에 로드된다. 다음을 알면 결정이 쉬워진다:

- **120줄 이상**이면 에이전트가 핵심을 놓치고 지시 compliance 가 떨어진다 (monorepo root 는 150줄)
- **금지형 규칙 ("NEVER do X")**이 권장형 ("Always prefer Y") 보다 compliance 가 높다
- 상세 정보는 `.claude/docs/reference/` 에 분리 → 작업 맥락에 따라 lazy loading
- 스캔 (Phase 1) 결과가 생성 (Phase 5) 으로 **명시적으로 매핑**되어야 빈약한 문서 생성을 방지
- **Monorepo 는 본질이 다르다** — 단일 CLAUDE.md 가 모든 sub 의 NEVER 를 담으면 sub 단독 작업 시 노이즈. root + sub 분리가 표준 — `references/monorepo.md` 참조

## 실행 흐름

```
Phase 0: 전제 조건 + 신규 생성 여부
Phase 1: 프로젝트 분석 (현황 + 프레임워크 감지 + 딥 스캔 + 매핑)
Phase 2: 콘텐츠 분류 (메인 vs 분리, 규모 분류)
Phase 3: Mermaid 아키텍처 생성
Phase 4: 메인 CLAUDE.md 작성
Phase 5: reference 생성/갱신 + 병합
Phase 6: 사용자 확인 (실행 전 변경 계획 제시)
Phase 7: 검증 + 최종 리포트
Phase 8: 구조 결정 ADR 작성 (해당 시)
```

---

## Phase 0: 전제 조건 확인

### 0-1. 기존 AI 설정 파일 감지

다음 파일이 존재하면 읽어서 Key Rules 이관 후보로 활용:
- `.cursorrules` / `.cursor/rules/*.mdc` → Cursor AI
- `.windsurfrules` → Windsurf AI
- `.aider.conf.yml` → Aider
- `copilot-instructions.md` → GitHub Copilot

감지 시:
1. 규칙 추출 + 프레임워크 감지 단서로 활용
2. 충돌 규칙은 사용자에게 알림
3. 원본 삭제 여부는 사용자 확인

### 0-2. CLAUDE.md 부재 시 신규 생성

CLAUDE.md 가 없으면:
1. `README.md` 가 있으면 → 프로젝트 설명, 명령어, 환경 정보 추출
2. `package.json` / `build.gradle` 등 → Phase 1-2 와 동일한 프레임워크 감지
3. 최소 골격: Project Overview + Architecture (Mermaid) + Commands + Key Rules (3개) + Reference Docs
4. 사용자에게 "신규 생성 모드입니다. 기존 팀 규칙이 있으면 알려주세요" 안내

### 0-3. CLAUDE.local.md 분리 판단

개인별 차이 있는 설정 (Swagger URL, 로컬 포트, 테스트 계정 등) 이 있으면:
1. `CLAUDE.local.md` 로 분리 제안
2. `.gitignore` 추가 확인

---

## Phase 1: 프로젝트 분석

### 1-1. 기존 상태 확인

1. 기존 CLAUDE.md 전체 읽기 (없으면 Phase 0-2 신규 생성)
2. 기존 `.claude/docs/reference/` 파일 목록 + 각 파일 줄 수
3. `.gitignore` 에서 `.claude/docs/reference/` 차단 여부
4. 기존 `.claude/rules/` 파일
5. **작업 산출물 감지** — 다음 경로에 최근 MD 가 있으면 읽어서 Phase 5 병합 활용:
   - `.claude/workflow/dev-guide-*.md`
   - `.claude/workflow/sprint-contract-*.md`
   - `.claude/docs/dev-guide/`
6. **git diff 기반 변경 감지** (`(빈 값)` 인자의 핵심):
   - CLAUDE.md 에 `Last Updated` 가 있으면:
     ```bash
     git log --since="<Last Updated 날짜>" --name-only --pretty=format:""
     ```
     → 변경 파일 목록 → `references/frameworks.md § git diff 역매핑` 으로 영향받는 reference 결정
   - Last Updated 없거나 CLAUDE.md 부재 → `full` 모드
   - `<경로>` 인자 시 → 해당 경로 하위만 스캔 대상

### 1-2. 프레임워크 + 언어 감지

`references/frameworks.md § 프레임워크 + 언어 감지 우선순위` 참조.

핵심:
- 언어 단독 분류 X — 항상 프레임워크와 함께 (`Spring Boot 3.3.8 (Java 21)`)
- **JVM 은 Java vs Kotlin 필수 구분** (Lombok ↔ data class 충돌)
- **복수 스택 감지 → Monorepo** → `references/monorepo.md` 적용

### 1-3. 프레임워크별 딥 스캔

`references/frameworks.md` 의 해당 프레임워크 섹션을 읽고 스캔. 추측 금지, 실제 코드 분석.

### 1-4. 스캔 결과 → reference 매핑

`references/frameworks.md` 의 각 프레임워크별 매핑 테이블 적용. 매핑되지 않은 항목은 `architecture.md` 에 요약 포함.

---

## Phase 2: 콘텐츠 분류

### 프로젝트 규모 분류

reference 최소 개수 결정을 위해 5개 지표를 합산:

| 지표 | 0점 | 1점 | 2점 |
|------|-----|-----|-----|
| 뷰/페이지 수 | ~15개 | 16-60개 | 61개+ |
| 라우트 수 | ~30개 | 31-100개 | 101개+ |
| API 함수 수 | ~20개 | 21-80개 | 81개+ |
| 상태관리 | 단일 store | 복수 store | 복수 라이브러리 |
| i18n 복잡도 | 없거나 단일 | 2-10 NS | 11개+ |

- **0-2점 → Small**: 최소 4-5개 reference
- **3-5점 → Medium**: 최소 7-10개 reference
- **6-10점 → Large**: 최소 12-16개 reference

### 메인 vs 분리 판단

**메인에 남길 조건 (ALL 충족):**
1. 전체 프로젝트 수준 정보
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
- 핵심 명령어 (build/test/run)
- 필수 규칙 3-5개 (금지형 우선)
- Git 컨벤션 (2-3줄)
- 환경 정보 (프로파일, SDK 경로, URL 등)
- Skills 테이블 (있으면 반드시 메인 유지)
- Reference 인덱스 테이블

> Reference 테이블이 20줄 초과 시 별도 `DOC_INDEX.md` 분리 권장

### 분리할 것 (On Demand → `.claude/docs/reference/`)

Phase 5 의 Decision Matrix 와 후보 테이블에 따라 결정. `references/reference-docs.md` 참조.

---

## Phase 3: Mermaid 아키텍처 다이어그램

Phase 1-3 스캔 결과 기반으로 실제 코드 구조를 반영한 Mermaid `graph TD` 생성.
- ` ```mermaid ` 코드펜스로 감싸기
- `subgraph` 로 레이어 분리 (Web/Domain/Infra 또는 UI/Logic/Data)
- 실제 존재하는 레이어와 컴포넌트만 — 프레임워크 기본 템플릿을 그대로 쓰지 않음

---

## Phase 4: 메인 CLAUDE.md 작성

**단일 프로젝트는 120줄, monorepo root 는 150줄, sub 는 120줄 이하**로 작성. 프레임워크에 없는 섹션은 생략.

### 기본 구조

```markdown
# CLAUDE.md

## Project Overview
[프레임워크] [버전] ([언어] [버전]) — [프로젝트 한 줄 설명]
- **응답은 한국어로 해주세요** (해당 시)

## Architecture
[Mermaid 다이어그램]

### Domain Modules (해당 시)
| Module | Purpose |
|--------|---------|

### Sub-Projects (monorepo 만)
| Project | Path | Stack | CLAUDE.md |
|---------|------|-------|-----------|

## Commands
[코드블록 — 프레임워크별 빌드/테스트/실행]

## Key Rules
[3-5개 — 금지형 우선, 가장 중요한 것만]

## Git Conventions (해당 시)
## Environment (해당 시)
## Skills (해당 시)

## Reference Docs
| 문서 | 참조 시점 | 경로 |
|------|----------|------|

---
Last Updated: [오늘 날짜]
```

### Key Rules 작성 가이드

우선순위:
1. **위반 시 빌드/런타임 오류** 발생 (Q-class 미생성, 코드 생성 누락)
2. **위반 시 데이터 손실/보안 문제** (소프트삭제 누락, XSS)
3. **위반 시 성능 문제** (N+1, 불필요한 리렌더링)
4. **팀 컨벤션으로 반복 위반**

금지형 우선. 프레임워크별 예시는 `references/frameworks.md` 의 각 섹션 "NEVER 후보" 참조.

### Monorepo Root CLAUDE.md

Sub-project 인덱스 + 전체 아키텍처 + cross-cutting 규칙만. 책임 분리 정책은 `references/monorepo.md § 2` 참조.

### Sub CLAUDE.md

해당 sub 의 stack-specific 만. Root 에 있는 규칙 복제 금지 — `references/monorepo.md § 11 NEVER` 참조.

---

## Phase 5: Reference 생성/갱신

`references/reference-docs.md` 전체를 참조.

핵심 요약:
- **5-1**: Decision Matrix (Rule 1-8) — grep/ls 로 확인 가능한 기준만
- **5-2**: 프레임워크별 후보 (Vue 15 / Spring Boot 10 / React 8 / Flutter 7)
- **5-3**: 각 reference 별 스캔 경로 + 최소 포함 항목 (auth-flow, error-handling, state-management, routing, form-patterns)
- **5-4**: 품질 체크리스트 (필수 6 + 권장 4)
- **5-5**: 병합 전략 (GAP 분석 → 구식화 탐지 → 섹션별 병합 → dev-guide 흡수)
- **5-6**: 원칙 + 줄 수 규칙 (기술 200, 도메인 400) + 템플릿
- **5-B**: 도메인 모듈 reference 트리거 조건 + 템플릿

---

## Phase 6: 실행 전 사용자 확인

**사용자에게 변경 계획을 보여주고 확인 받은 후에만 실행.**

표시할 내용:
1. 감지된 프레임워크 + 언어 (예: `Spring Boot 3.3.8 (Java 21)`)
2. **Monorepo 여부 + sub 목록** (해당 시)
3. 프로젝트 규모 (Small/Medium/Large + 점수)
4. 실행 모드:
   - `(빈 값)` → "증분 모드: Last Updated <날짜> 이후 변경 N개 파일, 영향받는 reference M개"
   - `full` → "전체 재구성"
   - `<경로>` → "범위 지정: <경로> 하위 N개 파일"
5. 메인 CLAUDE.md 변경 요약 (추가/이동/유지)
6. 생성/갱신할 reference 목록 + Decision Matrix Rule 근거
7. 도메인 reference 후보 (Phase 5-B)
8. **CHANGELOG 분리 제안 여부** — `Last Updated` 라인이 3K 토큰 또는 5회 closure 누적 도달 시
9. **ADR 작성 후보** (Phase 8 — 구조 결정 시)
10. 인자별 조기 종료:
    - `scan` → 리포트만 출력 후 종료
    - `diff` → 현재 vs 제안 차이만 보여주고 종료
    - `gap` → GAP 분석 리포트만 출력 후 종료

---

## Phase 7: 검증

### 형식/구조 검증

- [ ] 메인 CLAUDE.md 줄수 상한 충족 (단일 120, monorepo root 150, sub 120)
- [ ] 기존 정보 100% 보존 (메인 또는 reference 에)
- [ ] Reference 경로가 실제 파일과 일치
- [ ] Mermaid 다이어그램이 실제 코드 구조 반영
- [ ] 빌드/테스트 명령어가 빌드 설정 파일과 일치
- [ ] `.claude/docs/reference/` 가 `.gitignore` 에 포함 안 됨
- [ ] Skills 섹션이 메인에 유지 (있으면)
- [ ] Key Rules 가 금지형 우선
- [ ] Java/Kotlin 언어가 정확히 반영
- [ ] **Monorepo 의 경우**: root 와 sub 간 규칙 복제 0, sub 간 동일 규칙 0 (`references/monorepo.md § 11`)

### 내용 품질 검증

- [ ] Reference 수가 규모 분류 대비 최소 개수 이상
- [ ] 각 reference 가 품질 체크리스트 필수 6개 충족
- [ ] Decision Matrix Rule 1-5 해당 영역에 모두 문서 있음
- [ ] 도메인 트리거 조건 충족 도메인에 `domain-*.md` 존재
- [ ] Reference 간 내용 중복 0 (크로스 참조 링크는 OK)
- [ ] 기술 reference 200줄 이하, 도메인 reference 400줄 이하

### 최종 리포트

```
줄 수 리포트:
- CLAUDE.md: N줄
- Reference: M개 (총 L줄)
- 규모 분류: [Small/Medium/Large] (점수: X/10)
- 품질 점수: 평균 Y/6 필수 항목 충족
- (Monorepo) Sub 별: root N + sub-A M + sub-B L
```

---

## Phase 8: 구조 결정 ADR 작성 (해당 시)

다음 결정 중 하나라도 했으면 ADR 작성 — `references/adr-template.md` 참조:

1. CLAUDE.md 를 sub 별로 분할 (monorepo 첫 도입 시)
2. `CHANGELOG.md` 를 분리 (Last Updated 비대화 임계점 도달)
3. Reference 위치 패턴 채택 (A/B/C 중 어느 패턴 + 이유)
4. Cross-cutting 문서 위치 결정 (root 단일 SSoT vs 양쪽 복사)
5. Agents/hooks 통합 vs 분산 결정
6. Sub-project 추가/삭제
7. 줄수 상한 예외 적용

ADR 위치: 단일 프로젝트는 `docs/adr/` 또는 `.claude/adr/`, monorepo 는 `<root>/docs/adr/`. 자세한 템플릿과 예시는 `references/adr-template.md`.

ADR 작성 안 함:
- 단순 갱신 (Last Updated, 새 API 함수 추가, 키 추가)
- 새 도메인 reference 추가
- 코드만 보면 명백한 변경

---

## 핵심 주의사항

- 기존 CLAUDE.md 의 정보를 **절대 삭제 X** — 메인 또는 reference 로 반드시 이동
- 기존 `.claude/docs/reference/` 가 있으면 **`references/reference-docs.md § 5-5` 병합 전략** 적용
- **Skills 섹션은 메인 CLAUDE.md 유지** — 에이전트 트리거 위해 항상 봐야 함
- Screenshots, Notes 등 운영 관련 섹션도 메인 유지
- **Monorepo**: `references/monorepo.md` 의 책임 분리 정책 + sub 별 줄수 상한 적용
- `module:<name>` 인자: monorepo 는 `module:<sub>/<name>` 형식
- Java/Kotlin 혼동 금지: 감지된 언어에 맞는 패턴만 (Lombok ↔ data class 불가)
- 빌드 파일 감지 순서: `references/frameworks.md` 참조
- **거대 Last Updated 라인 발견 시** (3K 토큰 / 5회 closure 누적): CHANGELOG.md 분리 제안 + ADR 작성 — `references/monorepo.md § 6`

## 참조 문서 사용 가이드

이 skill 은 progressive disclosure 방식으로 구성됨. SKILL.md (본 문서) 는 워크플로 + 결정 포인트만 담고, 디테일은 references/ 에서 필요한 것만 읽음:

| references/ 파일 | 언제 읽는가 |
|------------------|------------|
| `monorepo.md` | Phase 1-2 에서 monorepo 감지 시, Phase 4 작성 시 책임 분리 결정, Phase 6 sub 추가 시 |
| `frameworks.md` | Phase 1-2 (감지 우선순위), Phase 1-3 (딥 스캔 항목), Phase 1-4 (매핑) |
| `reference-docs.md` | Phase 5 전체 — 어떤 reference 만들지 결정 + 템플릿 + 병합 |
| `adr-template.md` | Phase 8 — 구조 결정 ADR 작성 시 |
