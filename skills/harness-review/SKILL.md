---
name: harness-review
description: "코드 변경 사항에 대해 프로젝트별 전문 에이전트를 병렬 fan-out으로 리뷰하고 종합 verdict(PASS/ITERATE/ESCALATE)를 생성합니다. '/harness-review', 'harness review', 'harness 리뷰', '품질 리뷰' 요청 시 사용."
---

# /harness-review — Fan-out 리뷰 + Aggregate Verdict

> **직교 원칙**: 기존 quality-gate/jira-test 스킬과 독립 동작. 코드를 수정하지 않고 리포트만 생성.
> **참조**: ~/.claude/docs/HARNESS-JIRA-ORTHOGONAL-ARCHITECTURE.md

## ⛔ Guard — HARNESS_MODE 확인 (최우선)

> 이 스킬의 모든 단계보다 **먼저** 실행. SSoT: `~/.claude/skills/_harness-guard.md` — `HARNESS_MODE` 가 미설정/빈값/`off` 면 즉시 중단(안내 출력 후 이후 단계 실행 금지), `suggest`/`auto` 면 정상 진행.

---

## 절차

### Step 1. 프로젝트 감지 + 변경 파일 수집

```bash
git diff --name-only HEAD  # unstaged
git diff --name-only --cached  # staged
```

변경 파일이 없으면 마지막 커밋 대비 diff를 사용한다.

### Step 2. 프로젝트별 Dispatch Rule 적용

#### app-ha-back (Spring Boot)

| 변경 파일 패턴 | 담당 에이전트 |
|---------------|-------------|
| `**/entity/**/*.java` | `haback-jpa-reviewer` |
| `**/repository/**/*.java`, `**/*Repository*.java` | `haback-jpa-reviewer` |
| `**/service/*ReadService.java`, `**/service/*WriteService.java` | `haback-cqrs-refactorer` (판단만) |
| `Visit*.java`, `Broken*.java`, `RepairReport*.java` | `haback-price-bifurcation-guard` |
| `**/SecurityConfig*.java`, `**/filter/**/*.java` | `haback-security-reviewer` |
| `**/test/**/*.java` | `haback-test-writer` (패턴 리뷰) |
| 모든 .java 변경 | 기존 verify-* 스킬 (해당되는 것만) |

#### cs-back (Spring Boot)

| 변경 파일 패턴 | 담당 에이전트 |
|---------------|-------------|
| `**/entity/**/*.java` | `migration-guardian` → `jpa-query-auditor` |
| `**/repository/**/*.java` | `jpa-query-auditor` |
| `**/test/**/*.java` 또는 새 Service/Controller | `test-integrity-auditor` |
| `**/*FeignClient.java`, `**/scheduler/**`, `**/notification/**` | `integration-sentinel` |
| 모든 코드 변경 | `cs-reviewer` + `domain-trap-sentinel` (항상) |

#### cs-front (Vue 3)

| 변경 파일 패턴 | 담당 에이전트 |
|---------------|-------------|
| **Wave 1 (정적 리뷰, 항상)**: | |
| `src/**/*.vue`, `src/**/*.js`, `src/**/*.ts` | `cs-front-reviewer` |
| `src/**/*.vue` (i18n 사용) | `i18n-auditor` |
| `src/api/**` | `api-contract-auditor` |
| `**/*Modal*.vue`, `**/*Popup*.vue` | `modal-pattern-enforcer` |
| `src/**/*.vue`, `src/**/*.css` | `design-token-auditor` |
| **Wave 2 (런타임, Wave 1 Blocker 없을 때)**: | |
| `src/views/**`, `src/components/**` | `responsive-qa-agent` |
| 기능 AC 존재 시 | `cs-front-evaluator` |
| 디자인 AC 존재 시 | `design-verifier` |

#### Flutter (예: app_v2)

Flutter 앱은 도메인별 reviewer 에이전트가 잘 정의되어 있지 않을 수 있으므로, 프로젝트의 `.claude/agents/` 디렉토리를 글로빙하여 사용 가능한 에이전트를 발견하는 방식으로 동작한다.

| 변경 파일 패턴 | 담당 에이전트 (있을 때만) |
|---------------|---------------------------|
| `lib/**/*.dart` (위젯/화면 코드) | `*-explorer` (있으면), `*-security-reviewer` (있으면) |
| `lib/**/state/**` 또는 Riverpod/BLoC 사용 | 프로젝트 reviewer 에이전트 (있으면) |
| `test/**/*.dart` | `*-test-writer` (있으면) |
| `pubspec.yaml` 변경 | 메인 세션 직접 — 의존성 추가/버전 변경의 영향 평가 |
| 모든 .dart 변경 | `*-security-reviewer` 또는 메인 세션 (CLAUDE.md의 위젯 rebuild/상태격리 규칙 기반) |

도메인 에이전트가 부재한 경우 메인 세션이 dev-guide의 인수조건과 CLAUDE.md를 기반으로 직접 review한다. 이 경우 verdict는 generic하게 작성되지만 fan-out이 없어 깊이는 얕다.

#### 알려지지 않은 프로젝트 (스택 fallback)

cwd가 위 dispatch table의 어느 프로젝트와도 매칭되지 않으면 스택 감지(harness-plan Step 1과 동일)로 폴백한다:

| 감지 스택 | 기본 dispatch |
|----------|---------------|
| Spring Boot 일반 | cs-back/app-ha-back과 동일 패턴 적용. 단 프로젝트별 `{prefix}-*` 에이전트가 없으면 글로벌 reviewer만 사용 |
| Vue/React 일반 | cs-front 패턴 차용. 프로젝트 에이전트 부재 시 메인 세션이 직접 |
| Go/Rust/Python 등 | `.claude/agents/` 글로빙으로 발견된 에이전트만 호출. 부재 시 메인 세션이 직접 |
| unknown | 메인 세션이 직접 review (fan-out 없음, 깊이 얕음을 verdict에 명시) |

### Step 3. 에이전트 병렬 Fan-out

에이전트가 프로젝트에 **존재하면** Agent tool로 병렬 호출 — 한 메시지에서 여러 Agent 를 동시 spawn (2개씩 batching). 도메인 수가 많거나 반복적이면 `Workflow` 툴의 `parallel()` 로 fan-out 해도 된다 (각 도메인 결과를 barrier 로 모아 verdict 합성).
에이전트가 **존재하지 않으면** 해당 축은 스킵하고 메시지 출력.

각 에이전트에 전달할 컨텍스트:
- `git diff` 결과 (변경 파일 목록 + diff 내용)
- Sprint Contract 경로 (있으면)
- 이전 iteration의 Aggregate verdict (있으면)

### Step 4. 리포트 수집

각 에이전트의 출력을 수집. 에이전트가 파일로 저장했으면 경로만 수집.
에이전트가 텍스트로 반환했으면 `.claude/runtime/agent-outputs/<agent-name>/<timestamp>.md`에 저장.

### Step 5. Aggregate Verdict 생성 (Tier 3 측정 필수 필드 포함)

**측정 전제**: 이 스킬 진입 시점의 `date -Iseconds` 값을 `RUN_STARTED_AT`으로 기록. fan-out 완료 후 `RUN_ENDED_AT` 기록. 둘의 차이가 Duration.

모든 리포트를 종합하여 verdict를 결정:

| 조건 | Verdict |
|------|---------|
| Blocker 0건 | **PASS** (Advisory 있어도) |
| Blocker 1건 이상, iteration < 3 | **ITERATE** |
| iteration >= 3 이고 동일 Blocker 반복 | **ESCALATE** |
| iteration >= 5 | **ESCALATE** (hard cap) |

결과를 `.claude/runtime/aggregate-verdict.md`에 저장 (**확장 스키마**):

```markdown
# Aggregate Verdict — SURINP-XXX Phase N (Iteration M)

<!-- ═══ Metadata (Tier 3 측정) ═══ -->
- **Issue**: SURINP-XXX
- **Phase**: N
- **Verdict**: PASS | ITERATE | ESCALATE
- **Iteration**: M/3
- **Ran At**: YYYY-MM-DDTHH:MM:SSZ (ISO 8601, RUN_STARTED_AT)
- **Ended At**: YYYY-MM-DDTHH:MM:SSZ (RUN_ENDED_AT)
- **Duration**: Xm Ys (wall time, Ended - Ran)
- **Tokens (approx)**: ~85k (참여 에이전트 출력 합산 추정치 — 정확한 값이 아님을 명시)
- **Mode**: `auto` | `suggest` | `off` (HARNESS_MODE env var)
- **Shadow Run**: Y | N (이 실행이 shadow 프로토콜의 일부였는지)
- **Participants**: [cs-reviewer, jpa-query-auditor, ...]
- **Skipped**: [agent-name (사유), ...]
- **Target Commits**: HEAD~N..HEAD (or specific SHAs)

<!-- ═══ Body ═══ -->
## Blockers
| ID | Agent | 위치 | 요지 |
|---|------|------|------|

## Advisories
| ID | Agent | 요지 |
|---|------|------|

## Next Action
→ PASS: 커밋 진행 가능
→ ITERATE: Blocker 수정 후 /harness-review 재실행
→ ESCALATE: /harness-plan 재호출 (Sprint Contract v2)

<!-- ═══ Post-merge Scoring (7일+ 경과 후 /harness-score로 채움) ═══ -->
## Post-merge Scoring
> ⏰ **비워두세요.** 이 섹션은 머지 후 7일 이상 지난 뒤 **별도 세션**에서 `/harness-score`로만 채웁니다.
> 외부 증거(prod 로그, 새 버그 티켓, 수정 커밋 SHA) 없이 VALID 마킹 금지.

- **Scored At**: (empty)
- **Scored By**: (empty)
- **Days After Merge**: (empty)
- **Blocker Results**:
  | ID | Status | Evidence |
  |---|---|---|
  | (to be filled) | VALID/INVALID/UNCERTAIN | (외부 증거 경로) |
- **Advisory Results**:
  | ID | Actioned? | Evidence |
  |---|---|---|
- **Regression filed?**: (empty)
- **Production incident linked?**: (empty)
```

### Step 6. Shared State 갱신 (Read-Merge-Write 필수)

**반드시 aggregate-verdict.md 저장 후 즉시 실행한다.** 이 단계를 건너뛰면 workflow-state와 verdict가 drift하여 게이트 무결성이 깨진다 (과거 SURINP-190에서 66분 drift 발생 사례).

1. **Read**: `.claude/runtime/workflow-state.json` 파일을 Read로 읽는다.
2. **Merge**: 기존 필드를 보존하며 다음을 갱신:
   ```json
   {
     "aggregate_verdict": "<PASS|ITERATE|ESCALATE>",
     "stage": "reviewing-phase-N",
     "iteration": <현재 iteration 숫자>,
     "verdict_file": ".claude/runtime/aggregate-verdict.md",
     "reviewed_at": "YYYY-MM-DDTHH:MM:SS",
     "agent_outputs": {
       "<agent-name>": ".claude/runtime/agent-outputs/<agent>/<timestamp>.md"
     }
   }
   ```
3. **Write**: 병합한 전체 JSON을 Write로 저장.

**검증**: Write 후 Read로 다시 읽어 `aggregate_verdict`와 `iteration`이 verdict 파일과 일치하는지 확인한다.

### Step 7. 사용자 출력

verdict + Blocker 요약 출력.
- PASS → 다음 단계 진행 가능
- ITERATE → 수정 후 `/harness-review` 재실행
- ESCALATE → `/harness-plan` 재호출 권장

---

## 주의사항

- 코드를 **절대 수정하지 않는다** (Read-only 원칙)
- Wave 2(cs-front)는 Wave 1에 Blocker가 없을 때만 실행
- 에이전트 출력은 **500 토큰 이하** 요약으로 수신 (큰 내용은 파일로)
- 기존 quality-gate/jira-test와 **간섭하지 않는다** — 병렬 존재

## --subtasks Mode

사용자가 `/harness-review <KEY> --subtasks` 로 호출 시:

1. slice 별 verdict 가 의미 있을 때 (workspace 분리, 다른 fan-out 워커가 작성한 경우):
   - `<runtime>/aggregate-verdict/<KEY>-<SUB-KEY>.md` 별도 파일
   - 부모 verdict (`<runtime>/aggregate-verdict.md`) 에서 슬라이스 verdict 롤업 표 포함
2. 단일 세션에서 통합 구현한 경우 (워커 분리 X):
   - 부모 verdict 1장만 작성, slice 별 결과는 § "변경 사항 요약" 표에 인라인
3. **하위 이슈에 댓글 추가하지 않음** (verdict 는 부모 산출물 — 노이즈 방지)
4. `workflow-state.json` 의 `slice_status` 갱신 (slice 별 review-pass / iterate / escalate)

자세한 정책: `~/.claude/skills/_subtasks-convention.md` § 3
