---
name: harness-plan
description: "Jira 개발 가이드(dev-guide)를 읽고 Sprint Contract를 보충 생성합니다. /jira-plan 이후에 실행하여 DoD, Verify Targets, Out of Scope를 명시화합니다."
triggers:
  - "/harness-plan"
  - "Sprint Contract 만들어줘"
  - "harness plan"
  - "계획 보충"
---

# /harness-plan — Sprint Contract 보충 생성

> **직교 원칙**: /jira-plan의 dev-guide.md를 수정하지 않는다. 별도의 Sprint Contract를 생성하여 보충한다.
> **참조**: ~/.claude/docs/HARNESS-JIRA-ORTHOGONAL-ARCHITECTURE.md

## ⛔ Guard — HARNESS_MODE 확인 (최우선)

이 스킬의 모든 단계보다 **먼저** 실행한다. `HARNESS_MODE` 환경변수를 확인:

| HARNESS_MODE 값 | 동작 |
|-----------------|------|
| 미설정 / 빈값 / `off` | **즉시 중단**. 사용자에게 알림: "⛔ 이 프로젝트는 Harness가 설정되지 않았습니다 (HARNESS_MODE=$HARNESS_MODE). `/jira-*` 워크플로우를 사용하세요." 출력 후 **이후 단계를 절대 실행하지 않는다.** |
| `suggest` / `auto` | 정상 진행 |

---

## 절차

### Step 1. 프로젝트 감지 + 이슈 키 확인

현재 작업 디렉토리(cwd)를 기반으로 프로젝트를 식별한다. 알려진 프로젝트가 매칭되면 그 컨텍스트를 우선 사용하고, 매칭되지 않으면 스택 감지로 폴백하여 임의의 프로젝트(Flutter 앱, 다른 백엔드 등)에서도 동작하게 한다.

**알려진 프로젝트 (우선 매칭)**

| cwd 패턴 | 프로젝트 | 스택 | 비고 |
|----------|---------|------|------|
| `app-ha-back` | app-ha-back | Spring Boot | IdeaProjects 하위 |
| `cs-back` | cs-back | Spring Boot | newIdeaWorkSpace 하위 |
| `cs-front` | cs-front | Vue 3 | newIdeaWorkSpace 하위 |

**Fallback (cwd가 위에 매칭되지 않을 때) — 스택 감지**

| 감지 파일 | 스택 | 비고 |
|-----------|------|------|
| `pubspec.yaml` | Flutter/Dart | StudioProjects 하위 등 |
| `build.gradle` 또는 `pom.xml` | Spring Boot (일반) | |
| `package.json` + `vue` 의존성 | Vue.js (일반) | |
| `package.json` + `react`/`next` 의존성 | React/Next.js | |
| `go.mod` | Go | |
| `Cargo.toml` | Rust | |
| `pyproject.toml` 또는 `requirements.txt` | Python | |
| 기타 | unknown | 사용자에게 스택 확인 요청 |

이슈 키를 다음 순서로 탐색:
1. 사용자가 인자로 전달 (예: `/harness-plan PROJ-200`)
2. `.claude/runtime/workflow-state.json`의 `issue_key`
3. 현재 git 브랜치명에서 `[A-Z]+-[0-9]+` 패턴 추출 (예: `feature/PROJ-200-*` → `PROJ-200`). Jira project key는 프로젝트마다 다르므로(`PROJ`/`SCRUM`/`PROJ` 등) prefix를 고정하지 않는다.
4. 없으면 사용자에게 요청

### Step 2. dev-guide 탐색

dev-guide 파일은 프로젝트마다 위치 컨벤션이 다를 수 있어 다음 후보 경로를 순차 확인한다(첫 번째 존재하는 파일을 사용):

1. `docs/<ISSUE-KEY>-dev-guide.md` (cs-back 컨벤션 — 가장 흔함)
2. `.claude/docs/<ISSUE-KEY>-dev-guide.md` (cs-front 컨벤션)
3. `.claude/docs/reference/<ISSUE-KEY>-*.md` (app-ha-back 컨벤션)
4. `.claude/docs/<ISSUE-KEY>/dev-guide.md` (디렉토리 형식 컨벤션)

`<ISSUE-KEY>`는 Step 1에서 확정된 키 — prefix 무관하게 동작한다.

dev-guide가 없으면 경고 출력 후 Jira MCP에서 이슈 본문을 직접 읽어 Contract를 생성한다.

### Step 3. 프로젝트 에이전트 호출 (선택)

플래너/탐색 에이전트가 존재하면 Task tool로 위임하여 코드베이스 탐색을 격리한다. 에이전트 이름은 프로젝트 접두사 컨벤션을 따른다:

- **app-ha-back**: `haback-explorer` (haiku)
- **cs-back**: `cs-explorer` 또는 `cs-planner`
- **cs-front**: `cs-front-planner`
- **그 외 프로젝트 (Flutter 등)**: `.claude/agents/` 안에서 `*-explorer` 또는 `*-planner` 패턴으로 탐색하여 발견되면 사용

에이전트가 없으면 메인 세션에서 직접 탐색한다.

### Step 4. Sprint Contract 생성

dev-guide를 읽고 다음 고정 스키마의 Sprint Contract를 생성한다:

```markdown
# PROJ-XXX Sprint Contract

> 보충 문서 — 원본: [dev-guide 경로]
> 생성: /harness-plan
> 일시: YYYY-MM-DD

## Definition of Done
- [ ] 검증 가능한 행동 1 (테스트 또는 수동 검증으로 매핑)
- [ ] 검증 가능한 행동 2
- ...

## Files to Change (산출물 계약)
| Path | 변경 종류 | Risk |
|------|----------|------|
| src/.../XxxService.java | 수정 (+N/-M) | Medium |

## Verify Targets (Evaluator 지정)
> 프로젝트의 verify-* 스킬 중 해당되는 것 나열
- verify-cqrs-service-split (서비스 분리 대상 시)
- verify-n1-optimization (Repository 변경 시)
- ...

## Phase 분할 (dev-guide 기반)
> dev-guide의 구현 단계를 Phase로 매핑
- Phase 1: ...
- Phase 2: ...

## Out of Scope (스코프 드리프트 방지)
- 이 이슈에서 하지 않는 것을 명시

## Context Handoff
- Reference: [관련 레퍼런스 문서 경로]
- Memory: [관련 메모리 파일]
```

### Step 5. 파일 저장 + Shared State 갱신 (Read-Merge-Write 필수)

**5.1 Sprint Contract 파일 저장**
저장 경로: `.claude/runtime/sprint-contract/PROJ-XXX.md`

**5.2 workflow-state.json 갱신 (누락 금지)**

반드시 다음 3단계를 순서대로 실행:

1. **Read**: `.claude/runtime/workflow-state.json` 파일이 존재하면 Read로 읽는다.
2. **Merge**: 기존 필드를 보존하며 다음을 갱신한다:
   ```json
   {
     "issue_key": "PROJ-XXX",
     "stage": "plan-supplement",
     "dev_guide_path": "<감지된 dev-guide 경로>",
     "sprint_contract_path": ".claude/runtime/sprint-contract/PROJ-XXX.md",
     "updated_at": "YYYY-MM-DDTHH:MM:SS"
   }
   ```
3. **Write**: 병합한 전체 JSON을 Write로 저장.

파일이 **존재하지 않으면**: `.claude/runtime/workflow-state.template.json`을 읽어 템플릿 기반으로 새로 생성한 후 위 필드를 채운다.

**절대 원칙**: 이 스킬은 **workflow-state.json 갱신을 건너뛰지 않는다**. 갱신 없이 종료하면 /harness-gate와 /harness-resume이 stale 데이터를 읽게 되어 전체 Harness 무결성이 깨진다.

### Step 6. 사용자에게 요약 출력

Sprint Contract의 핵심 3가지만 요약:
1. DoD 항목 수 + 주요 항목
2. Verify Targets 목록
3. Phase 수

---

## 주의사항

- dev-guide.md를 **절대 수정하지 않는다** (Jira 레이어 침범 금지)
- Sprint Contract는 dev-guide의 **보충**이지 대체가 아니다
- 이미 Sprint Contract가 존재하면 **덮어쓰기 전 사용자 확인**
- Jira MCP 호출은 필요할 때만 (이슈 본문 참조 시)

## --subtasks Mode

사용자가 `/harness-plan <KEY> --subtasks` 로 호출 시:

1. 부모 Sprint Contract (`<runtime>/sprint-contract/<KEY>.md`) 작성 — 단일 contract 에 **slice 별 DoD 인라인** 구조 (### 통합 DoD + ### Slice 별 DoD)
2. `workflow-state.json` 에 `subtasks_mode: true` + `subtasks: [...]` + `slice_status: {...}` 기록
3. **하위 이슈에 댓글 추가하지 않음** (sprint-contract 는 부모 산출물 — 노이즈 방지)

자세한 정책: `~/.claude/skills/_subtasks-convention.md` § 3
