---
name: harness-setup
description: "AI Agent Harness Engineering infrastructure auto-provisioner (2026-07-21 ADR-106 표준: hooks 3종·JSON deny 게이트·Stop/metrics 미배선). Detects project stack (Spring Boot, Vue, React, etc.) and generates project-scoped agents, hooks, settings, CLAUDE.md rules, and runtime directories. Idempotent — safely run on new or partially configured projects; only adds what's missing; upgrade scope detects legacy exit-1 gates and retired wiring. Use this skill whenever: the user says 'harness setup', 'set up harness', 'configure harness', 'harness-setup', 'add harness to project', 'init harness', 'harness 설정', 'harness 구성', 'harness 초기화', 'harness 세팅', 'new project harness', 'upgrade harness', 'check harness status', 'harness check'. Also trigger when user asks to add agents, hooks, or quality gates to a project even without explicitly saying 'harness'."
---

# /harness-setup — Harness Engineering 자동 구성

프로젝트에 AI Agent Harness Engineering 인프라를 자동으로 구성한다.
기존 구성이 있으면 감지하여 부족분만 보충한다. 기존 파일은 덮어쓰지 않는다.

> 설계 문서: `~/.claude/docs/HARNESS-SETUP-SKILL-DESIGN.md`

## Scope

사용자의 프롬프트에서 scope를 추출한다:

| Scope | 동작 |
|-------|------|
| **full** (기본) | 감지 → Gap 분석 → 부족분 전체 생성 |
| **check** | 감지 → 상태 보고만 (변경 없음) |
| **upgrade** | 감지 → 최신 표준 대비 diff → 사용자 확인 후 수정 |

scope가 명시되지 않으면 `full`로 간주한다.

## 자연어 파라미터

사용자가 함께 전달할 수 있는 정보. 명시되지 않은 항목은 Step 3 인터뷰에서 질문한다:
- **mode**: HARNESS_MODE 값 (`suggest` / `auto` / `off`)
- **prefix**: 에이전트 이름 접두사 (예: `myapp`, `cs`, `haback`)
- **stack**: 기술 스택 (자동 감지 기본)

### 인터뷰 원칙

이 스킬은 **파일 20개 이상을 생성/수정**하고 **settings.local.json을 변경**한다. 따라서 자동 기본값으로 조용히 넘어가지 않는다.

- 다음 3가지는 **반드시 사용자에게 확인**한다: **mode**, **prefix**, **생성 계획**
- 자동 감지한 값은 **보여주고 확인**을 받는다 (조용히 적용 금지)
- 질문은 **Step 3에서 한 번에 묶어** 물어본다 (drip-drip 금지)
- `scope=check`는 읽기 전용이므로 질문 없음

---

## Step 0. git 확인

```bash
git rev-parse --show-toplevel 2>/dev/null
```

git이 없으면 경고:
```
"⚠️ git 레포가 아닙니다. review-gate 의 worktree 루트 해석과 rollback 기능이 제한됩니다. 계속 진행할까요?"
```
사용자 확인 후 계속.

## Step 1. 스택 감지

아래 순서로 기술 스택을 자동 감지한다:

1. 사용자가 명시한 stack → 그대로 사용
2. 파일 기반 감지:

| 파일 | 스택 | Tier |
|------|------|------|
| `build.gradle` / `build.gradle.kts` | `spring-boot` | 1 (실전 검증) |
| `package.json` + `"vue"` 의존성 | `vue` | 1 (실전 검증) |
| `package.json` + `"react"` 의존성 | `react` | 1 (유사 구조) |
| `pom.xml` | `spring-boot-maven` | 2 |
| `package.json` + `"next"` | `next` | 2 |
| `package.json` + `"angular"` | `angular` | 2 |
| `Cargo.toml` | `rust` | 2 |
| `go.mod` | `go` | 2 |
| `pyproject.toml` / `requirements.txt` | `python` | 2 |
| 기타 | `unknown` | 2 |

3. 감지 불가 → 사용자에게 질문

**Tier 2 스택**은 전문 에이전트 템플릿이 없다. 안내:
```
"이 스택({stack})은 기본 에이전트 3종(explorer + security-reviewer + test-writer)으로 시작합니다.
 프로젝트 운영 후 도메인 에이전트를 추가하는 것을 권장합니다."
```

## Step 2. 기존 Harness 상태 감지

아래 7개 항목을 검사하여 각각의 상태를 기록한다:

| # | 항목 | 확인 방법 |
|---|------|----------|
| D1 | `.claude/settings.local.json` | 파일 존재 + `HARNESS_MODE` + `hooks` 섹션 (**Stop hook 배선이 남아 있으면 legacy — upgrade 제안**) |
| D2 | `.claude/hooks/` (3종) | `harness-context-inject.sh`, `compile-check.sh`, `review-gate.sh` (persist-checkpoint 는 폐기 — 있어도 미배선이 표준) |
| D3 | `.claude/agents/` | 파일 목록 + 접두사 패턴 |
| D4 | `CLAUDE.md` | "Harness" 키워드 포함 섹션 존재 여부 |
| D5 | `.claude/runtime/` | 디렉토리 + 하위 구조 |
| D6 | legacy 잔재 | `harness-metrics/`(사장 — archive 이관 제안) · review-gate 에 `exit 1` 차단 분기(구 결함판 — upgrade 필수) |
| D7 | 글로벌 harness 스킬 | `~/.claude/skills/harness-workflow/SKILL.md` 존재 (유일 진입점 — ADR-106) |

## Step 3. 인터뷰 (분기)

### scope=check

읽기 전용. 보고서 출력 후 종료:

```
Harness Status: {project} ({stack}, {mode})
✅ settings  ✅ hooks(4/4)  ⚠️ agents(4/7)  ❌ rules  ✅ runtime  ✅ metrics
→ 부족: agents 3종, rules
→ /harness-setup full 실행 시 자동 보충됩니다
```

**추가 질문 없이 종료.**

### scope=full / upgrade — 통합 인터뷰

감지 결과와 제안을 한 번에 보여주고 사용자 확인을 받는다:

```
🔍 감지 결과
─────────────────────────────────────
Project:  {project_dir_name}
Stack:    {detected_stack} ({gradle/maven/vite 등})
Git:      ✅ (branch: {current_branch}) / ❌
기존 구성: settings={Y/N}, hooks={N/4}, agents={N}개 ({prefix}-*)

─────────────────────────────────────
📝 결정이 필요한 3가지 항목
─────────────────────────────────────

1️⃣ HARNESS_MODE (커밋 차단 여부를 결정합니다)
   ─ suggest: Hook이 제안만 합니다 (차단 없음) ← 초기 도입 권장
   ─ auto:    Hook이 강제 주입 + 품질게이트 미통과 시 커밋 차단
   ─ off:     Harness 비활성
   
   → 어떤 모드로 설정하시겠습니까? (기본: suggest)

2️⃣ 에이전트 접두사
   감지된 값: "{auto_detected_prefix}"
   (근거: {기존 agents에서 추출 / 디렉토리명 기반})
   
   → 이 접두사가 맞습니까? 다른 이름을 쓰시겠습니까?

3️⃣ 생성할 에이전트 목록 ({stack} 기준)
   [핵심 4종, 모두 생성 권장]
   - {prefix}-explorer
   - {prefix}-security-reviewer
   - {prefix}-test-writer
   - {prefix}-build-resolver
   
   [도메인 에이전트 (관련 코드 존재 시에만 생성)]
   - {prefix}-jpa-reviewer         ← entity/ 감지됨 ✓
   - {prefix}-cqrs-refactorer      ← service/ 감지됨 ✓
   - {prefix}-api-contract-reviewer ← controller/ 감지됨 ✓
   
   → 전부 생성할까요? 제외할 에이전트가 있습니까?
```

사용자 답변 수신 후 Step 4로.

### 인터뷰 생략 조건

사용자가 호출 시 이미 명시한 경우 해당 질문만 생략:
- "auto 모드로" 명시 → 1️⃣ 질문 생략
- "접두사 myapp으로" 명시 → 2️⃣ 질문 생략
- "에이전트는 핵심만" 명시 → 3️⃣ 핵심 4종만 선택

모든 값이 명시되어 있어도 **최종 "진행할까요?" 확인은 Step 5에서 반드시 받는다.**

## Step 4. 접두사 확정

인터뷰 답변을 반영하여 최종 접두사 결정. 사용자가 인터뷰에서 확인했으므로 추가 질문 불필요.

**접두사 후보 우선순위** (사용자 미지정 시):
1. 기존 `.claude/agents/` 파일명에서 추출 (예: `haback-jpa-reviewer.md` → `haback`)
2. 프로젝트 디렉토리명 변환 (예: `app-ha-back` → `haback`, `cs-front` → `csfront`, `my-cool-app` → `mycoolapp`)

## Step 5. 최종 실행 계획 + 확인

부족한 컴포넌트 목록을 보여주고 확인을 받는다:

```
다음 파일을 생성/수정합니다:

[새로 생성]
  .claude/hooks/harness-context-inject.sh
  .claude/hooks/compile-check.sh
  .claude/hooks/review-gate.sh
  .claude/agents/{prefix}-explorer.md
  .claude/agents/{prefix}-security-reviewer.md
  .claude/agents/{prefix}-test-writer.md
  .claude/agents/{prefix}-build-resolver.md

[수정]
  .claude/settings.local.json (HARNESS_MODE + hooks 3종 추가 — Stop hook 없음)
  CLAUDE.md (Harness Integration 섹션 추가)

[건너뜀]
  .claude/agents/existing-agent.md (이미 있음)

진행할까요?
```

## Step 6. 실행

### 6.1 settings.local.json

**수정 전 반드시 `.settings.local.json.bak` 백업**.

기존 파일이 있으면 Read → `env.HARNESS_MODE` 추가 + `hooks` 섹션 추가.
`permissions` 섹션은 **절대 건드리지 않는다**.

없으면 새로 생성. JSON 구조:

```json
{
  "env": { "HARNESS_MODE": "{mode}" },
  "hooks": {
    "UserPromptSubmit": [{"hooks": [{"type": "command", "command": "bash $CLAUDE_PROJECT_DIR/.claude/hooks/harness-context-inject.sh", "statusMessage": "Harness context injection..."}]}],
    "PostToolUse": [{"matcher": "Edit|Write", "hooks": [{"type": "command", "command": "bash $CLAUDE_PROJECT_DIR/.claude/hooks/compile-check.sh", "statusMessage": "Harness compile check..."}]}],
    "PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "bash $CLAUDE_PROJECT_DIR/.claude/hooks/review-gate.sh", "if": "Bash(git commit*)", "statusMessage": "Harness review gate..."}]}]
  }
}
```

> **함정 주의 1**: `hooks` 키는 이중 배열 — `[{ "hooks": [{ "type": "command", ... }] }]`. 단일 배열로 쓰면 동작하지 않는다.
> **함정 주의 2**: hook 경로는 반드시 `$CLAUDE_PROJECT_DIR` 절대경로 — 상대경로는 sub-dir cwd / worktree 에서 스크립트를 못 찾는다.
> **Stop hook 배선 금지 (2026-07-21, ADR-106 P3)**: 구 persist-checkpoint Stop hook 은 소비자(/harness-resume — 폐기됨) 없는 산출물이라 신규 배선하지 않는다. 재개 = workflow-state.json / phases/<KEY>/index.json 직독.

### 6.2 Hooks (4종)

`mkdir -p .claude/hooks` 후 4개 스크립트 생성.

#### harness-context-inject.sh (공통)

> 2026-07-21 단일 분기판 (ADR-106 §3.3 미러 — 구 3분기 폐기. 차단 책임은 review-gate 가 JSON deny 로 물리 수행하므로 주입은 시퀀싱 리마인드만).

```bash
#!/usr/bin/env bash
# Harness Context Injection — 단일 분기 (2026-07-21 표준판)
HARNESS_MODE="${HARNESS_MODE:-suggest}"
[[ "$HARNESS_MODE" == "off" ]] && exit 0
PROMPT=$(cat)

if echo "$PROMPT" | grep -qiE "/harness-workflow|harness.workflow|/jira-plan|jira-plan|/jira-execute|jira-execute"; then
  if [[ "$HARNESS_MODE" == "auto" ]]; then
    cat <<'EOF'
INSTRUCTION: HARNESS SEQUENCING (auto)
harness 워크플로 맥락이 감지되었습니다. 단계 결정표(~/.claude/skills/harness-workflow/SKILL.md)를 준수하세요:
- plan 후에는 반드시 /harness-plan (sprint-contract) — dev-guide 단독 종료 금지.
- 구현(Phase/레인) 완료마다 /harness-review — verdict=PASS 전 commit 금지 (review-gate 가 JSON deny 로 물리 차단).
- 병렬은 dynamic Workflow 레인만 (Agent Teams 금지) — 모든 agent() 에 opts.model 명시.
EOF
  else
    echo "RECOMMENDATION: harness-workflow 단계 결정표(plan→contract→execute→review→gate) 준수를 권장합니다."
  fi
fi

# commit 의도 감지 시 verdict 상태 INFO (차단은 review-gate.sh 책임)
if echo "$PROMPT" | grep -qiE "커밋|commit"; then
  ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  VF="$ROOT/.claude/runtime/aggregate-verdict.md"
  if [[ -f "$VF" ]]; then
    V=$(grep -m1 -oiE '^#+[[:space:]]*(PASS|ITERATE|ESCALATE)[[:space:]]*$' "$VF" | grep -oiE 'PASS|ITERATE|ESCALATE' | head -1)
    [[ -z "$V" ]] && V=$(grep -m1 -oiE 'Verdict[^A-Za-z]{0,6}(PASS|ITERATE|ESCALATE)' "$VF" | grep -oiE 'PASS|ITERATE|ESCALATE' | head -1)
    echo "INFO: 현재 aggregate-verdict.md verdict=${V:-UNKNOWN}"
  fi
fi
exit 0
```

#### compile-check.sh (스택별)

스택에 따라 내용이 다르다. **이 파일만 스택별로 다름.**

**spring-boot**: Entity 수정 감지 → `./gradlew compileJava -q`. `.java` 파일 변경 추적.
**vue**: `.vue/.ts/.tsx` 변경 추적만 (타입체크는 무거우므로 빌드 시에만).
**react**: vue와 동일 패턴.
**tier2/unknown**: 변경 파일 추적만.

compile-check.sh 생성 시 Read tool로 `references/agent-templates/{stack}.md`를 읽어 해당 스택의 compile-check 템플릿 섹션을 참조한다. **Tier 2/unknown 스택**은 아래 generic 버전 사용:

```bash
#!/usr/bin/env bash
# Generic compile-check — 변경 파일 추적만
HARNESS_MODE="${HARNESS_MODE:-suggest}"
[[ "$HARNESS_MODE" == "off" ]] && exit 0
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | grep -oE '"file_path"\s*:\s*"[^"]*"' | head -1 | sed 's/.*"\([^"]*\)".*/\1/' 2>/dev/null || echo "")
if [[ -n "$FILE_PATH" ]]; then
  mkdir -p .claude/runtime
  echo "$FILE_PATH" >> .claude/runtime/changed-files.txt
  sort -u .claude/runtime/changed-files.txt -o .claude/runtime/changed-files.txt
fi
exit 0
```

#### review-gate.sh (공통)

> ⚠️ **2026-07-21 전면 교체 (ADR-106 §5-1 미러)**: 구 템플릿의 `exit 1` 은 공식 hook 시맨틱상 **비차단**(non-blocking error — tool call proceeds)이라 게이트가 열려 있었다. 유효 차단 = `exit 0` + stdout JSON `permissionDecision:"deny"` (bypassPermissions 에서도 차단 보장, `exit 2`+stderr 와 상호 배타). 아래는 2차 하드닝판(jq/PCRE 명령 추출·토큰 기반 git commit 판정·verdict anchor 파싱·auto 모드 fail-closed) — 그대로 배포한다.

```bash
#!/usr/bin/env bash
# Review Gate — PreToolUse hook for git commit (2026-07-21 hardened 표준판)
HARNESS_MODE="${HARNESS_MODE:-suggest}"
[[ "$HARNESS_MODE" == "off" ]] && exit 0
INPUT=$(cat)

# ① command 추출 — jq 우선, escaped-quote 안전 PCRE 폴백, 최후 구식 ERE
CMD=""
if command -v jq >/dev/null 2>&1; then
  CMD=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // .command // empty' 2>/dev/null)
fi
if [[ -z "$CMD" ]]; then
  CMD=$(printf '%s' "$INPUT" | grep -oP '"command"\s*:\s*"\K(?:[^"\\]|\\.)*' 2>/dev/null | head -1)
fi
if [[ -z "$CMD" ]]; then
  CMD=$(printf '%s' "$INPUT" | grep -oE '"command"\s*:\s*"[^"]*"' | head -1 | sed 's/.*"\([^"]*\)".*/\1/' 2>/dev/null || echo "")
fi

# ② 토큰 기반 git commit 판정 (git 전역 옵션 -C/-c/--git-dir 등 인식)
if ! printf '%s' "$CMD" | grep -qiE '(^|[;&|][[:space:]]*)([A-Za-z_][A-Za-z0-9_]*=[^[:space:]]*[[:space:]]+)*git([[:space:]]+(-C|-c|--git-dir|--work-tree|--namespace)[[:space:]]+[^[:space:]]+|[[:space:]]+--?[^[:space:]]+)*[[:space:]]+commit([[:space:]]|$)'; then
  exit 0
fi

# ③ 프로젝트 루트: env → git worktree 루트 → pwd
ROOT="${CLAUDE_PROJECT_DIR:-}"
[[ -z "$ROOT" ]] && ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
VERDICT_FILE="$ROOT/.claude/runtime/aggregate-verdict.md"

deny() {
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$1"
  exit 0
}

if [[ ! -f "$VERDICT_FILE" ]]; then
  if [[ "$HARNESS_MODE" == "auto" ]]; then
    deny "[Harness] aggregate-verdict.md 없음 — /harness-review 를 먼저 실행하세요 (auto commit 차단)."
  fi
  echo "[Harness] ⚠️ /harness-review 미실행 (aggregate-verdict.md 없음)." >&2
  exit 0
fi

# ④ verdict anchor 파싱: `# PASS` 헤더 라인 → `Verdict: **PASS**` 필드 순
VERDICT=$(grep -m1 -oiE '^#+[[:space:]]*(PASS|ITERATE|ESCALATE)[[:space:]]*$' "$VERDICT_FILE" 2>/dev/null | grep -oiE 'PASS|ITERATE|ESCALATE' | head -1)
if [[ -z "$VERDICT" ]]; then
  VERDICT=$(grep -m1 -oiE 'Verdict[^A-Za-z]{0,6}(PASS|ITERATE|ESCALATE)' "$VERDICT_FILE" 2>/dev/null | grep -oiE 'PASS|ITERATE|ESCALATE' | head -1)
fi
VERDICT=$(printf '%s' "${VERDICT:-UNKNOWN}" | tr '[:lower:]' '[:upper:]')

if [[ "$VERDICT" == "PASS" ]]; then
  echo "[Harness] ✅ 품질 게이트 통과 (verdict=PASS)." >&2
  exit 0
fi
# auto 모드 fail-closed: ITERATE/ESCALATE/UNKNOWN(파싱 실패) 전부 차단
if [[ "$HARNESS_MODE" == "auto" ]]; then
  deny "[Harness] 품질 게이트 미통과 (verdict=$VERDICT) — 수정 후 /harness-review 재실행 (PASS 외 전부 차단)."
fi
echo "[Harness] 🔴 verdict=$VERDICT — commit 전 재리뷰 권장." >&2
exit 0
```

#### ~~persist-checkpoint.sh~~ — **생성하지 않음 (2026-07-21 폐기, ADR-106 P3)**

구 Stop hook checkpoint 는 소비자가 없어 폐기됐다 (재개 SSoT = workflow-state.json / phases/<KEY>/index.json 직독). 신규 프로젝트에 파일을 생성하지도, settings 에 배선하지도 않는다. 기존 프로젝트에서 발견되면 upgrade 시 배선 제거를 제안한다 (파일 자체는 보존 가능).

### 6.3 Agents

**핵심 에이전트** (모든 스택, 반드시 생성): `{prefix}-explorer`, `{prefix}-security-reviewer`, `{prefix}-test-writer`, `{prefix}-build-resolver`

**도메인 에이전트** (Tier 1 스택만, 관련 코드 존재 시):
- Read tool로 `references/agent-templates/{stack}.md`를 읽어 해당 스택의 전체 에이전트 목록과 MD 템플릿을 확인한다.
- 각 도메인 에이전트의 "조건"을 확인하여 실제 코드가 있을 때만 생성한다.

모든 에이전트 공통 구조:
```markdown
---
name: {prefix}-{role}
description: "Use PROACTIVELY after {trigger}. {summary}. Provides analysis, never modifies code."
model: sonnet
tools: Read, Grep, Glob, Bash
---
# {prefix}-{role} — {title}
## 역할
...
## 필독 문서 (첫 턴에 Read)
- `CLAUDE.md`
{auto_detected_docs}
## 절대 금지
- 코드 수정 금지 (판단+제안만)
- 결과는 stdout 반환 (직접 Write 금지)
## 판단 기준
...
## 출력 형식
| ID | 위치 | 심각도 | 설명 | 제안 |
```

**필독 문서 자동 연결**: 에이전트 생성 시 프로젝트 내 `docs/`, `.claude/docs/`를 Glob으로 탐색하여 관련 .md 파일 경로를 `{auto_detected_docs}`에 채운다. 파일이 10개 이상이면 가장 관련성 높은 3개만 선택.

**플레이스홀더 치환 필수**: 에이전트 MD 생성 시 `{prefix}`, `{auto_docs}`, `{auto_detected_docs}` 등 모든 플레이스홀더를 실제 값으로 치환한다. 중괄호 플레이스홀더를 그대로 파일에 남기면 안 된다.

### 6.4 CLAUDE.md

기존 CLAUDE.md가 있으면 끝에 append. "Harness" 섹션이 이미 있으면 SKIP.

추가할 내용:
```markdown
## Harness Engineering Integration
### 운영 모드
- `HARNESS_MODE`는 `.claude/settings.local.json` 참조
- `auto`: Hook이 harness 단계를 강제 주입 + 커밋 게이트 차단
- `suggest`: Hook이 제안만
- `off`: Harness 비활성
### 워크플로 규칙
- /jira-plan 완료 후 /harness-plan 실행을 제안하라
- /jira-execute 각 Phase 완료 후 /harness-review를 제안하라
- commit 전(harness-workflow gate 단계 — 구 /jira-commit 폐기) aggregate-verdict.md 확인을 권장하라
### 에이전트 디스패치
- 프로젝트 에이전트({prefix}-*)는 글로벌 에이전트보다 우선
### 아티팩트 경로
- dev-guide: `docs/{ISSUE-KEY}-dev-guide.md`
- Sprint Contract: `.claude/runtime/sprint-contract/{ISSUE-KEY}.md`
- Verdict: `.claude/runtime/aggregate-verdict.md`
- State: `.claude/runtime/workflow-state.json` (이슈별 임시 산출물 — closure 시 `runtime/archive/{ISSUE-KEY}/` 이관)
```

### 6.5 Runtime 디렉토리

```bash
mkdir -p .claude/runtime/sprint-contract
mkdir -p .claude/runtime/agent-outputs
mkdir -p .claude/runtime/archive
```

### 6.6 ~~Metrics~~ — **생성하지 않음 (2026-07-21 사장, ADR-106 P0-3)**

harness-metrics(aggregate.py/scorecard.md)는 실사용 6주 정지로 사장 판정 — 완성도 루프(completeness-loop 스킬)의 scorecard 가 상위 호환이다. 신규 프로젝트에 생성하지 않는다. 기존 프로젝트에서 발견되면 upgrade 시 `runtime/archive/` 이관을 제안한다.

### 6.7 Manifest 기록

```json
// .claude/runtime/harness-setup-manifest.json
{
  "_generated_at": "<timestamp>",
  "_generator": "/harness-setup {scope}",
  "_stack": "{stack}",
  "_prefix": "{prefix}",
  "_mode": "{mode}",
  "created_files": [...],
  "modified_files": [...],
  "skipped_files": [...]
}
```

## Step 7. 검증

| # | 항목 | 방법 |
|---|------|------|
| V1 | 생성 파일 전부 존재 | `ls` 확인 |
| V2 | settings.local.json 유효 JSON | `python -m json.tool` |
| V3 | Hook 문법 | `bash -n .claude/hooks/*.sh` |
| V4 | HARNESS_MODE 유효값 | `suggest`/`auto`/`off` 중 하나 |
| V5 | Agent frontmatter | name, description, model 존재 |
| V6 | **review-gate 실차단 스모크 (필수 — 문법 검사만으로 게이트 신뢰 금지)** | 아래 3케이스를 hook 에 직접 주입해 기대 동작 확인 |

**V6 스모크 절차** (배포 직후 1회 — "게이트가 닫혀 있다"는 주장은 실측 후에만):

```bash
H=.claude/hooks/review-gate.sh; T=$(mktemp -d); mkdir -p "$T/.claude/runtime"
# a. verdict 없음 + auto → deny JSON 기대
printf '{"tool_input":{"command":"git commit -m x"}}' | HARNESS_MODE=auto CLAUDE_PROJECT_DIR="$T" bash $H | grep -q '"deny"' && echo "a PASS"
# b. ITERATE → deny 기대
printf '# ITERATE\n' > "$T/.claude/runtime/aggregate-verdict.md"
printf '{"tool_input":{"command":"git commit -m x"}}' | HARNESS_MODE=auto CLAUDE_PROJECT_DIR="$T" bash $H | grep -q '"deny"' && echo "b PASS"
# c. PASS → 허용(무 JSON) 기대
printf '# PASS\n' > "$T/.claude/runtime/aggregate-verdict.md"
printf '{"tool_input":{"command":"git commit -m x"}}' | HARNESS_MODE=auto CLAUDE_PROJECT_DIR="$T" bash $H | grep -q '"deny"' || echo "c PASS"
rm -rf "$T"
```

검증 통과 후 최종 보고:

```
✅ Harness Engineering 구성 완료
  Project: {project} ({stack})
  Mode: {mode}
  Agents: {count}종 ({prefix}-*)
  Hooks: 3/3 (context-inject·compile-check·review-gate — Stop/metrics 는 ADR-106 폐기)
  Gate smoke: a/b/c PASS (deny 실차단 확인)

  다음 단계: /harness-workflow {ISSUE-KEY} 로 첫 실전 실행
```

---

## 알려진 함정 (생성 시 반드시 확인)

| # | 함정 | 방지 |
|---|------|------|
| G1 | Hook JSON 이중 배열 | `[{"hooks":[{...}]}]` 구조 반드시 준수 |
| G2 | Verdict 파싱 — 파일 전체 첫 단어 매칭 금지 (`Previous PASS` 산문 오탐) | **anchor 파싱**: `^#+ (PASS\|ITERATE\|ESCALATE)$` 헤더 → `Verdict: **X**` 필드 순. auto 모드는 PASS 외 전부(UNKNOWN 포함) deny (fail-closed) |
| G3 | 에이전트 이름 불일치 | 접두사 감지 후 모든 곳에서 일관 사용 |
| G4 | Windows CRLF | `.gitattributes`에 `*.sh text eol=lf` 추가 |
| G5 | settings 백업 누락 | 수정 전 `.bak` 백업 필수 |
| G6 | 필독 문서 404 | 에이전트 생성 시 파일 존재 확인 |
| G7 | **차단 분기 `exit 1` 회귀 금지** | 공식 hook 시맨틱상 `exit 1` = 비차단(진행됨). 유효 차단 = exit 0 + JSON `permissionDecision:"deny"` 또는 exit 2 + stderr (상호 배타 — 혼용 금지) |
| G8 | hook 경로 상대경로 금지 | settings 의 command 는 `$CLAUDE_PROJECT_DIR` 절대경로 (sub-dir cwd/worktree 편차) |

---

## Upgrade Scope 추가 동작

`/harness-setup upgrade` 시 기존 파일도 수정할 수 있다 (2026-07-21 표준 기준 — ADR-106):

| 체크 | 최신 표준 | 동작 |
|------|----------|------|
| **Hook: review-gate 차단 메커니즘** | JSON `permissionDecision:"deny"` + fail-closed (구 `exit 1` 분기 발견 = **결함판 — 최우선 교체**) | §6.2 하드닝판으로 교체 제안 + V6 스모크 |
| Hook: verdict 파싱 | anchor 파싱 (G2) — 파일 전체 첫 단어 매칭이면 구식 | 자동 수정 |
| Hook: context-inject | 단일 분기판 (구 jira-plan/execute/commit 3분기 = 구식) | 교체 제안 |
| settings: Stop hook 배선 | 없음이 표준 (persist-checkpoint 폐기) | 배선 제거 제안 |
| settings: hook 경로 | `$CLAUDE_PROJECT_DIR` 절대경로 | 자동 수정 |
| Metrics 잔존 | 사장 — 생성 금지 | `runtime/archive/` 이관 제안 |
| Agent 부족 | 스택 기본 세트 대비 | 부족분만 제안 (기존 수정 안 함) |
| CLAUDE.md 거짓 경로 | 존재하지 않는 디렉토리 참조 | diff 보고 |
| CLAUDE.md 폐기 명령 참조 | `/jira-start`·`/jira-clarify`·`/jira-test`·`/jira-commit`·`/harness-resume` 언급 | `/harness-workflow` 단계 표기로 교정 제안 |
