# Monorepo / Multi-Project CLAUDE.md 정책

> 참조 시점: 루트 아래 2개 이상의 독립 sub-project (각자 빌드 파일 + 코드베이스) 가 감지된 경우, 혹은 같은 코드베이스 안에 여러 언어/프레임워크 스택이 섞여 있는 경우
> 갱신 트리거: sub-project 추가/삭제, root 정책 vs sub 정책 충돌 발생, CLAUDE.md 비대화

## 개요

단일 프로젝트와 monorepo 는 **CLAUDE.md 구조 전략이 본질적으로 다르다**. 단일 프로젝트는 1개 파일 + 1개 reference 디렉토리로 충분하지만, monorepo 는 (1) root 공통 규칙과 (2) sub-project 전용 규칙을 분리하지 않으면 다음 문제가 발생한다:

- 매 세션마다 모든 sub-project 의 CLAUDE.md 를 전부 컨텍스트에 로드 → 토큰 낭비
- BE/FE 처럼 스택이 다른데 같은 파일에 섞이면 NEVER 규칙끼리 충돌 (`@Entity` 규칙과 `<script setup>` 규칙이 한 페이지에 공존)
- Sub-project 단독 작업 시 root 의 인프라/배포 정보가 노이즈

## 1. Monorepo 감지

다음 중 하나 이상 충족 시 monorepo 로 판단:

1. **루트 + sub 빌드 파일 동시 존재**: 루트에 `package.json` 이 있고 `apps/<name>/package.json`, `packages/<name>/package.json` 도 존재 (Nx, Turbo, Yarn workspaces, pnpm workspaces)
2. **이종 스택 디렉토리**: 루트 아래 `frontend/package.json` + `backend/build.gradle` 처럼 빌드 파일이 다른 언어/프레임워크
3. **`apps/` / `packages/` / `services/` / `modules/` 표준 디렉토리**: 각 하위에 자체 빌드 파일
4. **명시적 workspace 설정**: `pnpm-workspace.yaml`, `lerna.json`, `nx.json`, `turbo.json`, `Cargo.toml` 의 `[workspace]`, `go.work`

**판정 명령어:**
```bash
# 루트 + 하위 빌드 파일 동시 존재 확인
find . -maxdepth 3 -type f \( -name package.json -o -name build.gradle -o -name pom.xml -o -name Cargo.toml -o -name go.mod -o -name pyproject.toml \) | head -20
```

루트에만 빌드 파일이 있고 하위는 그냥 소스 디렉토리면 **단일 프로젝트** (예: `src/views/` 는 sub-project 가 아님).

## 2. 책임 분리 — 무엇이 root, 무엇이 sub 로 가는가

**Root CLAUDE.md 의 책임:**
- 프로젝트 전체 한 줄 설명 (전체 시스템이 무엇인지)
- 전체 아키텍처 다이어그램 (sub-project 간 데이터 흐름 + 경계)
- Sub-project 인덱스 테이블 (각 sub 의 stack + CLAUDE.md 링크)
- 모노레포 차원의 정책 (브랜치 전략, push 정책, 통합 commit 규칙)
- 인프라 (DB / Redis / 외부 도메인 — 공유 자원)
- Cross-cutting 규칙 (전체 sub 가 따라야 할 NEVER)
- Skills / Agents 인덱스 (skill 트리거는 root 에서 로드됨)
- 환경 정보 (각 sub 가 공유하는 SDK 경로, 서버 URL)

**Sub CLAUDE.md 의 책임:**
- 해당 sub 의 stack + 버전 ("Spring Boot 3.3.8 / Java 21")
- 해당 sub 의 디렉토리/모듈 구조
- 해당 sub 의 빌드/테스트/실행 명령어
- 해당 sub 만의 NEVER 규칙 (Q-class 재생성, `import type` 금지 등)
- 해당 sub 의 reference docs 인덱스 (별도 `.claude/docs/reference/` 보유 시)
- 해당 sub 의 Last Updated / CHANGELOG 링크

**둘 다 두면 안 되는 것:**
- 같은 규칙을 root 와 sub 양쪽에 복제 — 변경 시 한쪽만 갱신되어 drift 발생. 한쪽으로만.
- Sub-project 끼리 같은 규칙 (예: 양쪽 다 i18n 규칙) → root 로 끌어올려 통합

**판단 테스트:** "이 규칙을 sub-project A 만 따르면 되는가?" YES → sub. "모든 sub 가 동시에 따라야 하는가?" YES → root.

## 3. 줄수 상한

| 파일 | 상한 | 비고 |
|------|------|------|
| Root CLAUDE.md | **150줄** | 단일 프로젝트(120줄) 보다 30줄 여유 — sub 인덱스 테이블 + 아키텍처 도식이 들어가므로 |
| Sub CLAUDE.md | **120줄** | 단일 프로젝트와 동일 |
| Reference docs | 200줄 (기술), 400줄 (도메인) | 단일과 동일 |

Root 와 sub 의 줄수 합계가 너무 크면 (예: root 150 + sub 3 × 120 = 510), 컨텍스트 부담이 생긴다. 이때:
- 옵션 A: sub CLAUDE.md 를 90줄로 더 줄이고 디테일은 reference 로
- 옵션 B: Root 에 "단독 세션 시작은 root 에서만" 정책 명시 → sub 는 직접 진입 안 함

## 4. Reference 문서 위치 정책

`reference/` 디렉토리 위치는 3가지 패턴이 있다:

### 패턴 A — Sub 별 분산 (권장 — 기본)
```
.claude/docs/reference/         (root — cross-cutting, 선택)
<sub-a>/.claude/docs/reference/ (sub-a 전용)
<sub-b>/.claude/docs/reference/ (sub-b 전용)
```
- 장점: sub 단독 세션 시작 시 본인 ref 만 로드 → 토큰 효율
- 단점: cross-cutting 정책 (예: BE↔FE API contract) 을 어디 둘지 결정 필요
- **권장 시점**: sub 가 서로 독립 stack (BE Java + FE Vue 처럼)

### 패턴 B — Root 집중
```
.claude/docs/reference/         (모두 root 에)
  ├── backend/...
  └── frontend/...
```
- 장점: 한 곳에서 전체 조감
- 단점: sub 단독 세션이어도 모든 ref 가 로드 가능 (lazy loading 깨짐)
- **권장 시점**: sub 가 같은 stack (예: 둘 다 TypeScript) + 공유 라이브러리 많음

### 패턴 C — Hybrid (cross-project 공유 문서 + sub 분산)
```
.claude/docs/reference/         (root — cross-project.md 1-2개)
<sub-a>/.claude/docs/reference/ (sub-a 전용)
<sub-b>/.claude/docs/reference/ (sub-b 전용)
```
- 권장 — sub 간 sync 필요한 문서 (예: API contract, DTO sync 정책) 만 root 에 두고 나머지는 분산

## 5. Cross-cutting 문서 (Sync / Contract)

Sub-project 간 sync 가 필요한 영역 (BE/FE API contract, DTO 매칭, 환경변수, deferred 정책) 은 별도 `cross-project.md` 또는 도메인별 `contracts/` 디렉토리로 분리한다.

| 위치 | 적용 시점 |
|------|----------|
| `cross-project.md` (양쪽 sub refs 에 동일 이름 복사) | sub 단독 세션에서도 sync 정책을 즉시 봐야 할 때 |
| `<root>/.claude/docs/reference/cross-project.md` (단일 SSoT) | root 세션 위주, sub 단독 세션이 드물 때 |
| `docs/contracts/<feature>.md` (도메인별 분리) | API 종류가 많고 도메인 경계가 분명할 때 |

**복사 패턴 채택 시**: 둘이 byte-by-byte 동일해야 함. drift 감지 명령어를 `verification.md` 또는 hook 에 등록.

## 6. CHANGELOG 분리 정책 (Last Updated 비대화 방지)

세션 closure 마다 `Last Updated:` 한 줄에 누적하면 **수십 회 후 단일 라인이 컨텍스트 토큰 한계를 잡아먹는다**. 이 문제는 monorepo 가 아니어도 발생하지만, monorepo 에서는 root + sub 각자 누적되어 더 빨리 터진다.

**임계점:**
- `Last Updated:` 라인이 **3,000 토큰 / 5회 closure 누적** 도달 시 즉시 `CHANGELOG.md` 분리
- 또는 단일 CLAUDE.md 가 줄수 상한의 1.5배 도달 시

**분리 정책:**
- `CHANGELOG.md` 위치: CLAUDE.md 와 같은 디렉토리 (root 면 root, sub 면 sub 안에)
- 형식: 역시간순 (newest first), 날짜별 헤딩 + closure 단위 sub-heading
- CLAUDE.md 의 `Last Updated:` 는 **직전 1~5건의 한줄 요약 + CHANGELOG 링크** 만 유지
- 각 sub-project 가 본인 CHANGELOG 를 보유 (root 와 sub 분리)

**Monorepo 풀스택 commit 의 기록 위치:**
- BE/FE 동시 변경 → **root CHANGELOG 에 1건** 기록 + 각 sub CHANGELOG 에 본인 영역 한줄 요약
- BE 단독 변경 → BE CHANGELOG 만
- FE 단독 변경 → FE CHANGELOG 만

자세한 형식은 `references/adr-template.md` 의 ADR 패턴 참조 — closure 자체는 ADR 이 아니지만 구조 결정 (CHANGELOG 분리 결정 등) 은 ADR 로.

## 7. git diff 역매핑 (변경 → 영향받는 ref)

CLAUDE.md 의 `Last Updated` 날짜 이후 변경된 파일을 영향받는 reference 문서로 역매핑할 때, monorepo 는 **sub-project prefix 우선 매칭**한다:

```
src/...                       → ambiguous — 명시 위치 확인 필요
<sub-a>/src/...               → <sub-a>/.claude/docs/reference/ 만
<sub-b>/src/...               → <sub-b>/.claude/docs/reference/ 만
docs/...                      → root reference (만약 있으면)
.github/workflows/...         → root reference (build-config 또는 ci 영역)
```

**판정 명령어:**
```bash
# Last Updated 이후 변경 파일 + sub-project 그룹핑
git log --since="<date>" --name-only --pretty=format:"" \
  | sort -u \
  | awk -F/ '{print $1}' | sort | uniq -c
```

결과를 보고 sub 별로 영향받는 ref 결정.

## 8. `module:<name>` / `<path>` 인자 처리

Sub-project 지정 시 인자 형식:

| 인자 | 의미 |
|------|------|
| `module:repair` | (단일 프로젝트) `src/views/repair/` 도메인만 |
| `module:<sub>/repair` | (monorepo) sub-project 의 repair 도메인만 |
| `<sub>` | sub-project 전체 스캔 + 해당 sub 의 refs 만 갱신 |
| `<sub>/<path>` | sub 안의 특정 경로 |

**범위 우선순위:** 경로 지정 인자가 있으면 해당 sub 의 refs 만 갱신, root CLAUDE.md 는 건드리지 않는다 (root 영향 없는 변경 가정). 예외: sub 추가/삭제 → root 인덱스 테이블 갱신 필요 → 사용자에게 명시 확인.

## 9. 세션 시작 위치 정책

Monorepo 의 **세션 시작 위치** (작업 디렉토리) 가 어디인지에 따라 자동 로드 되는 CLAUDE.md / agents / hooks 가 달라진다. 도구별 차이 (nested config 미지원 등) 가 있으므로:

**기본 정책:** 세션은 **항상 root 에서 시작**. Sub 단독 작업이어도 root 시작 후 sub 디렉토리로 cd. 이유:
1. Root 의 agents/skills 가 항상 로드됨
2. Cross-cutting hook (push 차단, sync 검증) 이 동작
3. Sub 의 CLAUDE.md 는 의존 작업 시 (Read tool 또는 reference 링크로) 명시 로드

예외: sub 가 사실상 독립 (별도 git remote 까지 가진 경우) → sub 단독 세션 허용. 단 sub CLAUDE.md 에 "단독 세션 시 root agents 없음" 명시.

## 10. Sub-project 추가/삭제 절차

새 sub-project 추가 시:
1. Root CLAUDE.md 의 sub 인덱스 테이블에 행 추가
2. `<new-sub>/CLAUDE.md` 생성 (sub 템플릿)
3. `<new-sub>/.claude/docs/reference/` 디렉토리 생성 (필요 시)
4. Root architecture 다이어그램에 노드 추가
5. ADR 작성: "왜 이 sub 가 추가되었는가" — 미래 세션이 결정 맥락 이해

Sub-project 삭제 시:
1. 위 항목 역순으로 제거
2. ADR 작성: deprecation 사유 + 마이그레이션 경로
3. CHANGELOG 에 삭제 기록

## 11. NEVER 규칙 (monorepo 전용)

- **NEVER** 같은 NEVER 규칙을 root + sub 양쪽에 복제 — drift 위험. 한쪽으로
- **NEVER** Sub 의 `Last Updated` 에 다른 sub 의 변경을 기록 — 본인 sub 변경만
- **NEVER** Root CLAUDE.md 에 특정 sub 의 stack-specific NEVER (예: `import type 금지`) 를 넣음 — sub 로
- **NEVER** Sub CLAUDE.md 에 push/브랜치 정책 작성 — root 통합 정책
- **NEVER** 단일 sub 에만 영향 있는 변경을 root CHANGELOG 에 기록 (root CHANGELOG 비대화)
- **NEVER** Sub 가 추가/삭제됐는데 root architecture 다이어그램 미갱신 — `scan` 인자로 검증

## 12. 일반 사례 — 3계층 (root + BE + FE) 풀스택 모노레포

전형적인 풀스택 monorepo (백엔드 + 프런트엔드 + 계획문서) 구조 예시. 회사/도메인 무관하게 적용 가능한 일반 패턴.

**디렉토리:**
```
<root>/
├── CLAUDE.md                              ← 150줄 (전체 시스템 + sub 인덱스)
├── CHANGELOG.md                           ← 풀스택 closure 기록
├── docs/                                  ← 계획 문서 (PRD, ADR, sprint)
├── .claude/
│   ├── agents/                            ← 통합 에이전트 (root + BE-prefix + FE-prefix)
│   └── docs/reference/                    ← cross-project.md 만 (선택)
├── <backend-dir>/
│   ├── CLAUDE.md                          ← 120줄 (BE stack + NEVER)
│   ├── CHANGELOG.md                       ← BE 단독 closure
│   └── .claude/docs/reference/            ← BE 전용 7개 refs
└── <frontend-dir>/
    ├── CLAUDE.md                          ← 120줄 (FE stack + NEVER)
    ├── CHANGELOG.md                       ← FE 단독 closure
    └── .claude/docs/reference/            ← FE 전용 11개 refs
```

**책임 매핑:**
| 영역 | 위치 | 이유 |
|------|------|------|
| 전체 아키텍처 + sub 인덱스 | root CLAUDE.md | 두 sub 의 관계 |
| Push/브랜치 정책 | root CLAUDE.md | 모노레포 전체 |
| BE-only NEVER (Entity, JPA, Q-class) | BE CLAUDE.md | stack-specific |
| FE-only NEVER (script setup, i18n) | FE CLAUDE.md | stack-specific |
| BE/FE API contract sync | root `cross-project.md` 또는 양쪽 복사 | sync 필요 |
| Sprint/PRD docs | `<root>/docs/` | 계획은 root |
| 인프라 (DB, Redis, 외부) | root CLAUDE.md | 공유 자원 |
| BE 빌드/테스트 명령어 | BE CLAUDE.md | sub stack 별 |
| FE 빌드/테스트 명령어 | FE CLAUDE.md | sub stack 별 |

**세션 시작:** 항상 root. 풀스택 변경은 root 에서 양쪽 디렉토리 동시 수정. Sub 단독 변경도 root 에서 cd 로 진입.

**Agents 통합:** Nested config (sub 안의 `.claude/`) 가 자동 로드 안 되는 도구 한계 때문에, agents 는 root 의 `.claude/agents/` 로 통합하고 이름 prefix 로 영역 구분 (예: `<be-prefix>-*`, `<fe-prefix>-*`).
