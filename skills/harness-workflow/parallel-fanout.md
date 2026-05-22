# parallel-fanout.md — 다중 부모 이슈 병렬 실행 (2-tier fan-out)

> **위치**: `~/.claude/skills/harness-workflow/parallel-fanout.md` (SKILL.md 부속)
> **목적**: `/harness-workflow <KEY1>` … `<KEY5>` 를 **동시 실행** 해야 할 때, SKILL.md 의 단일-인스턴스 가정으로는 다루지 못하는 격리·직렬화·머지·복구 규칙을 정의한다.
> **단일 인스턴스만 돌리는 경우 본 문서를 읽을 필요 없음** — SKILL.md 만으로 충분.
> **관계**: SKILL.md 는 _부모 1 + 하위 N_ (Tier-2) 까지 다룬다. 본 문서는 그 위에 _부모 M + 각 부모 안 하위 N_ (Tier-1 × Tier-2) 를 얹는다.
> **선행 ADR**: ADR-070 (`/jira-execute --subtasks` Agent Teams) — 본 문서는 그 패턴의 외부 wrapping.

---

## 0. 적용 조건 (이걸 어겼다 = 사고)

본 문서의 절차는 **모든 항목이 참** 일 때만 안전.

| # | 조건 | 검증 방법 |
|---|------|-----------|
| 0-1 | 부모 이슈 ≥ 2 개를 동시에 진행하려고 함 | 사용자 의도 |
| 0-2 | 각 부모 이슈 사이의 **코드 영역 충돌이 사전 매트릭스로 분석됨** (§ 3) | 본 문서 § 3 표 작성 |
| 0-3 | `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` 활성 | `grep CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS $CLAUDE_PROJECT_DIR/.claude/settings.local.json` |
| 0-4 | `HARNESS_MODE=auto` 또는 `suggest` | `echo $HARNESS_MODE` |
| 0-5 | Flyway 시퀀스 (V14, V15, …) **사전 할당표** 가 § 7 에 작성됨 | 본 문서 § 7 |
| 0-6 | 5 인스턴스가 만질 **단일 공유 파일** 의 lock/직렬화 전략 합의 (§ 6 표) | 본 문서 § 6 |
| 0-7 | 사용자가 "5 동시 token cost 1.5–2× 단일×N" 을 인지·승인 | 사용자 명시 승인 |
| 0-8 | working tree clean (`git status` 깨끗) | `git status --porcelain` 무출력 |
| 0-9 | 모든 부모 이슈가 같은 main 베이스를 기준으로 분기 가능 | `git log -1 main` |
| 0-10 | (권장) Codex 가 설치되어 있고 sandbox 1385 우회 옵션 정착 (`memory/codex-windows-sandbox-1385.md`) | `codex --version` |

**위 중 1개라도 거짓 → 본 절차 진입 금지**. 단일 인스턴스 순차로 폴백 권고.

---

## 1. 2-Tier 병렬화 모델

```
Tier-1 (Outer)  ── 사용자가 직접 봄
┌────────────────────────────────────────────────────────────────────┐
│  Main Session = Orchestrator (lead-of-leads)                       │
│   │                                                                │
│   ├─ git worktree A  →  Agent("workflow-PROJ-214")  /harness-workflow PROJ-214 --subtasks
│   ├─ git worktree B  →  Agent("workflow-PROJ-215")  /harness-workflow PROJ-215 --subtasks
│   ├─ git worktree C  →  Agent("workflow-PROJ-216")  /harness-workflow PROJ-216 --subtasks
│   ├─ git worktree D  →  Agent("workflow-PROJ-217")  /harness-workflow PROJ-217 --subtasks
│   └─ git worktree E  →  Agent("workflow-PROJ-218")  /harness-workflow PROJ-218 --subtasks
└────────────────────────────────────────────────────────────────────┘

Tier-2 (Inner, 각 worktree 안)  ── ADR-070 표준
┌────────────────────────────────────────────────────────────────────┐
│  workflow-PROJ-2XX 가 Phase 5 (jira-execute) 에 들어가면            │
│   TeamCreate({team_name: "PROJ-2XX"})                               │
│   FOR each slice (3~4 하위태스크):                                 │
│     Agent({team_name: "PROJ-2XX", name: "slice-PROJ-NNN", ...})      │
│   teammate 들이 단일 worktree 안에서 파일 owned 분할 + 통합 빌드는 lead│
└────────────────────────────────────────────────────────────────────┘
```

**총 동시 에이전트 상한 추정** (5 부모, 평균 3.2 슬라이스):
- Tier-1 워크플로 5
- Tier-2 lead 5 (= Tier-1 자체가 lead 역할)
- Tier-2 teammate ≈ 5 × 3.2 ≈ 16
- harness-review fan-out (각 부모 안 inner loop) ≈ 5 × 4 stdback/stdfront agent = 20 (단, 동시 활성 보장 아님)

**Concurrency 실측 권장**: 처음엔 **3 인스턴스부터** 시작해서 OOM / rate-limit / hook race 확인 후 5로 늘릴 것.

---

## 2. 5 이슈 인벤토리 (2026-05-18 시점, PROJ-214 ~ PROJ-218)

| Key | Sprint | Parent Epic | Subtasks | 코드 영역 (PRIMARY) | FE? |
|-----|--------|-------------|----------|----------------------|-----|
| **PROJ-214** | W5 | PROJ-202 | PROJ-270/271/272/273 (BE×3 + QA×1) | `classification/service/`, `approval/callback/`, `security/anonymize/`, `e2e/tests/v12-*` | – |
| **PROJ-215** | W6 | PROJ-203 | PROJ-274/275/276 (BE×2 + QA×1) | `settlement/calc/`, `settlement/snapshot/` | – |
| **PROJ-216** | W6 | PROJ-203 | PROJ-277/278/279/280 (BE×2 + FE×1 + QA×1) | `settlement/kpi/`, `views/system/Kpi*`, `views/system/ProductGradeFeeView` | ✅ |
| **PROJ-217** | W6 | PROJ-203 | PROJ-281/282/283/284 (BE×2 + FE×1 + QA×1) | `settlement/adjustment/`, `settlement/policy/`, `views/settlement/Settlement*`, `views/settlement/ClosePolicy` | ✅ |
| **PROJ-218** | W6 | PROJ-203 | PROJ-285 (BE×1) | `promotion/service/`, `promotion/calc/`, `promotion/controller/`, seed `promotion_target` | – |

**Sprint 정책 경고**: 오늘 2026-05-18 기준, W5 시작은 2026-05-25 (7일 뒤), W6 = 2026-06-01 (14일 뒤). 5 이슈 중 4 개가 W6. 부모 에픽 PROJ-202/PROJ-203 모두 "해야 할 일" 상태 — W5 closure 전 W6 작업 진입은 sprint 컨벤션 위반. 위반을 감수하고 진행할지 사용자 명시 승인 필요.

---

## 3. 코드 영역 충돌 매트릭스 (5 × 5)

PRIMARY 패키지 + 참조 dependency (= "import 또는 호출 관계") 기준.

|   | 214 | 215 | 216 | 217 | 218 |
|---|-----|-----|-----|-----|-----|
| **214** | – | 0 | 0 | 0 | 0 |
| **215** |   | – | ⚠️ **REF**: `settlement/kpi/KpiCalculator` 가 `settlement/calc/SettlementCalculator` 호출 가능 | ⚠️ **REF**: `settlement/adjustment/SettlementAdjustmentService` 가 5지점 재계산 (= `SettlementCalculator.recalculate`) 호출 명시 (ADR-059) | ⚠️ **WEAK REF**: `promotion/calc/PromotionApplier` 가 Settlement 합산 hook 가능 |
| **216** |   |   | – | 0 (kpi/ vs adjustment/ 격리) | 0 |
| **217** |   |   |   | – | 0 |
| **218** |   |   |   |   | – |

### 충돌 등급 해설

- **0**: 패키지/디렉토리 분리 + 참조 없음 → 동시 작업 후 머지 자동
- **WEAK REF**: PromotionApplier 가 Settlement 합산 시점에 hook → 215 가 `SettlementCalculator` interface 만 노출하면 218 는 통과. interface 변경 시 충돌
- **REF**: 217/216 이 215 의 클래스를 import/호출. **215 가 먼저 main 에 머지** 되어야 217/216 의 통합 빌드가 통과 가능

### 결정: 머지 순서

```
1. PROJ-214 (격리)
2. PROJ-215 (foundation — settlement sealed)   ← 가장 먼저 끝나야 함
3. PROJ-218 (promotion 독립, WEAK REF 만)
4. PROJ-217 (215 REF 의존)
5. PROJ-216 (215 REF 의존)
```

**병렬 시작은 5 모두 동시 OK**, 단 PR 머지는 위 순서. 215 가 늦으면 217/216 의 머지가 대기.

---

## 4. 권장 실행 모드 (3 옵션)

| 옵션 | 동시 워크플로 수 | 워크트리 수 | 위험 | 시간 단축 | 권장 |
|------|-----------------|-------------|------|----------|------|
| **A. Wave 2-2-1** | wave1=2 (214+215) → wave2=2 (217+218 = 215 머지 후) → wave3=1 (216) | 2 (재사용) | 낮음 — 215 머지 후 REF 해소 보장 | ~40% | 🟢🟢 **권장** |
| **B. Full 5 동시** | 5 | 5 | 중-상 — 215 미완 상태로 216/217 가 빈 SettlementCalculator stub 참조 → 통합 빌드 실패 가능 | ~55% | 🟡 |
| **C. Full 5 + interface-first** | 5 | 5 | 중 — Tier-1 lead 가 사전에 `SettlementCalculator` sealed interface stub 을 main 에 1 커밋으로 먼저 푸시 → 5 worktree 가 stub 위에서 작업 | ~55% | 🟢 (스킬 있는 경우) |

본 문서는 **옵션 A 와 C 모두 안전** 하도록 § 5~12 절차를 기술. 옵션 B 는 § 11 "머지 conflict 대응" 비중이 큼.

---

## 5. Tier-1 — Worktree 격리 (외부 5 인스턴스)

### 5-1. 사전 준비 (orchestrator 책임, 1 회)

```powershell
# 1) working tree clean 확인
git -C D:\project status --porcelain
# (출력 없으면 OK)

# 2) main 최신화
git -C D:\project fetch origin
git -C D:\project checkout main
git -C D:\project pull --ff-only

# 3) (옵션 C 만) interface stub 사전 push
#    PROJ-215 의 SettlementCalculator sealed interface (메서드 시그니처만, 본문 throw new UnsupportedOperationException)
#    chore(PROJ-215): SettlementCalculator stub for parallel REF resolution
#    → git push origin main  (사용자 명시 승인 후)

# 4) worktree 5 개 생성
$BASE = "D:\project\.claude\worktrees"
foreach ($k in 214,215,216,217,218) {
  git -C D:\project worktree add "$BASE\PROJ-$k" -b "feat/PROJ-$k"
}

# 5) 결과 확인
git -C D:\project worktree list
```

각 worktree 는 **별도 working dir** 이고 `.claude/` 도 별도 복제됨. 단, `.claude/runtime/`, `.claude/hooks/`, `.claude/agents/`, `.claude/settings.local.json` 은 git tracked → worktree 마다 동일 복제 → hook 실측 동작 동일 → **자연스럽게 worktree 격리**.

### 5-2. Tier-1 Team 생성

```
ToolSearch({ query: "select:TeamCreate,TaskCreate,TaskList,TaskUpdate,TaskGet,SendMessage", max_results: 10 })

TeamCreate({
  team_name: "app-w6-parallel",
  agent_type: "orchestrator",
  description: "PROJ-214~218 다중 부모 병렬 워크플로 — wave 2-2-1 또는 full 5 동시"
})
```

### 5-3. Tier-1 Task 작성 + Agent spawn

```
FOR each key in [214, 215, 216, 217, 218]:
  TaskCreate({
    subject: "workflow-PROJ-<key>",
    description: """
      ## 목표
      /harness-workflow PROJ-<key> --subtasks 를 worktree D:\project\.claude\worktrees\PROJ-<key> 에서 실행.

      ## 제약
      - working dir: D:\project\.claude\worktrees\PROJ-<key>
      - 브랜치: feat/PROJ-<key>
      - 절대 main / 다른 worktree 의 파일 수정 금지
      - Flyway V 번호: § 7 표의 할당 사용
      - INDEX.md / LOG.md 직접 수정 금지 (§ 6 참조 — 모든 wiki append 는 orchestrator 에 SendMessage 로 위임)
      - 통합 빌드 (./gradlew build) 는 자기 worktree 안에서 OK (lock 격리됨)
      - Codex review 호출 시 SendMessage({to:"orchestrator", message:"codex-slot-request"}) 로 슬롯 요청 후 진행

      ## 완료 기준
      - feat/PROJ-<key> 푸시 + jira-complete QA 전이
      - aggregate-verdict PASS
      - SendMessage 로 orchestrator 에 머지 요청
    """,
    activeForm: "PROJ-<key> 워크플로 실행 중"
  })

# 머지 순서 DAG (옵션 A wave 2-2-1)
TaskUpdate({ taskId: "<task-id-of-217>", addBlockedBy: ["<task-id-of-215>"] })
TaskUpdate({ taskId: "<task-id-of-216>", addBlockedBy: ["<task-id-of-215>"] })
# 218 은 wave 2 시작이지만 코드 의존 없음 → 시작 시점만 wave1 완료 후로 게이트
TaskUpdate({ taskId: "<task-id-of-218>", addBlockedBy: ["<task-id-of-215>"] })
# (옵션 B/C 라면 위 3 줄 생략 — 동시 시작)
```

**Agent spawn** — 각 worktree 마다 1 명:

```
FOR each key in [214, 215, 216, 217, 218]:
  Agent({
    description: "PROJ-<key> 워크플로 실행",
    subagent_type: "general-purpose",
    team_name: "app-w6-parallel",
    name: "workflow-PROJ-<key>",
    isolation: "worktree",                         # ★ 핵심 — claude 가 자동으로 worktree 컨텍스트 잡음
    prompt: """
      당신은 팀 app-w6-parallel 의 workflow-PROJ-<key> 입니다.

      ## 시작 절차
      1. working dir 확인 (D:\project\.claude\worktrees\PROJ-<key> 이어야 함)
      2. TaskList → 자기 task (subject="workflow-PROJ-<key>") 의 description 정독
      3. TaskUpdate({ taskId, status: "in_progress" })

      ## 메인 작업
      Skill('harness-workflow', 'PROJ-<key> --subtasks')
      → 이 안에서 jira-start / jira-plan / harness-plan / 사용자 승인 / jira-execute (Agent Teams 자동) / harness-review (inner loop) / jira-test / harness-gate / jira-commit / jira-complete 전부 자동.

      ## 금지 사항
      - INDEX.md, LOG.md, 08-decision-log.md 직접 편집 금지 (wiki append 는 orchestrator 에 위임)
        → jira-plan §6 / jira-complete §4.4 의 ingest chain 이 트리거되면 SendMessage 로 orchestrator 에 알리고 lock 대기
      - 메인 working dir (D:\project) 의 파일 수정 금지
      - Codex review 동시 호출 금지 — SendMessage({to:"orchestrator", message:"codex-slot-request <KEY>"}) 보낸 뒤 ACK 받고 진행

      ## 완료 신고
      - jira-complete QA 전이 + push 끝나면
        SendMessage({to:"orchestrator", message:"merge-ready <KEY> sha=<HEAD>"})
      - TaskUpdate({ taskId, status: "completed" })

      ## Token 절약
      - dev-guide 작성 시 SKILL.md 의 평소 분량 그대로. 부모 Tier-1 토큰은 인스턴스마다 격리.
    """,
    mode: "default"
  })

  TaskUpdate({ taskId: "<task-id>", owner: "workflow-PROJ-<key>" })
```

> `isolation: "worktree"` 옵션이 worktree 컨텍스트를 잡아주지만, **claude code 의 worktree 자동 생성은 단일 임시 worktree** 만 만든다. 5 worktree 를 우리가 § 5-1 에서 명시 생성했으므로, agent prompt 에서 **working dir 을 명시** 하고 `isolation` 은 생략해도 무방. 두 경로 중 하나만 선택.
>
> **권장**: § 5-1 의 명시 worktree 사용 + agent prompt 의 `cd` 또는 working dir 지정 + `isolation` 옵션 미사용. 자동 worktree 생성은 cleanup 충돌 위험.

---

## 6. 공유 자원 매트릭스 — Phase 별 격리/직렬화

각 Phase 에서 5 인스턴스가 만지는 자원과 처리.

| Phase | 자원 | 격리 / 공유 | 처리 |
|-------|------|-------------|------|
| **0. 모드 확인** | env `HARNESS_MODE`, jira API | 글로벌 read-only | OK |
| **1. jira-start** | feature 브랜치 5 개, jira status transition | 각자 격리 | OK (jira API rate ≤ 100/sec 충분) |
| **2. jira-clarify** | dev-guide draft (없음 단계) | 격리 | OK |
| **3. jira-plan** | `docs/PROJ-<KEY>-dev-guide.md` + slice dev-guides | **부모별 격리** | OK |
| **3. jira-plan §6 ingest forecast** | **`docs/INDEX.md`, `docs/LOG.md`** | **단일 파일 공유** | ⚠️ **mutex 필요** — § 6-A 참조 |
| **4. harness-plan** | `.claude/runtime/sprint-contract/<KEY>.md` | 부모별 격리 (worktree 별 → 5 부) | OK |
| **5. 사용자 승인** | conversation stdout | 글로벌 (사용자 1명) | ⚠️ § 9 직렬화 참조 |
| **5. jira-execute** (Tier-2 Agent Teams) | 코드 파일 (slice 분할), `~/.claude/teams/PROJ-<KEY>/` | 부모별 격리 (team_name 다름) | OK |
| **5. harness-review inner loop** | `.claude/runtime/aggregate-verdict.md` (단일 파일 default) | ⚠️ worktree 별 격리되지만 **subagent 폭주 위험** | § 6-B 참조 |
| **5. compile-check hook** (`PostToolUse` Edit/Write) | `.claude/runtime/changed-files.txt` | worktree 별 격리 (hook 이 `pwd` 기준) | OK |
| **6. jira-test** | `./gradlew test`, `npm test`, **dev MySQL Flyway** | gradle/.gradle 격리, npm 격리, **MySQL 단일** | ⚠️ Flyway 직렬화 — § 7 참조 |
| **6. harness-gate** | `aggregate-verdict.md` read | worktree 별 격리 | OK |
| **7. jira-commit** | git commit, jira comment | 각자 격리 | OK |
| **7. PreToolUse `Bash(git commit*)` review-gate hook** | `.claude/runtime/aggregate-verdict.md` read | worktree 별 격리 | OK |
| **7. jira-complete** | jira QA 전이, `git push origin feat/PROJ-<KEY>` | 각자 격리 | OK (push 는 다른 브랜치라 충돌 없음) |
| **7. jira-complete §4.4 ingest closure** | **`docs/INDEX.md`, `docs/LOG.md`, `docs/08-decision-log.md`, `docs/sprint/weeks/*`** | **단일 파일 공유** | ⚠️ **mutex 필요** — § 6-A |
| **7. jira-complete §4.6 organize-claude-md** | `CLAUDE.md`, `CHANGELOG.md` | **단일 파일 공유** | ⚠️ **orchestrator 로 위임** — § 6-C |
| **7. jira-complete §4.7 wiki-lint** | wiki 전체 read-only | OK | (corpus-scoped, --subtasks 무관) |
| **Stop hook persist-checkpoint** | `.claude/runtime/checkpoint.md` | worktree 별 (pwd 기준) | OK |
| **PR / merge** | main 브랜치 | **글로벌, 직렬화 강제** | § 11 참조 |

### 6-A. Wiki append mutex (INDEX.md / LOG.md / 08-decision-log.md / sprint/weeks)

**문제**: 5 worktree 가 각자 `jira-ingest` 를 호출하면 같은 `D:\project\docs\INDEX.md` 를 동시 read-append-write → **데이터 손실**.

**해결**: 5 인스턴스는 직접 wiki 파일을 만지지 않고 **orchestrator 에 위임**.

각 worktree-agent 의 prompt 에 다음 규칙 추가 (§ 5-3 의 "금지 사항" 에 이미 명시):

```
jira-ingest chain 이 트리거되려는 시점:
1. STOP — jira-ingest 호출 직전
2. SendMessage({to: "orchestrator", message: "ingest-request <KEY> mode=forecast|closure payload=<json>"})
3. orchestrator ACK 까지 대기 (busy-wait 금지, 1 message exchange 로 충분)
4. orchestrator 가 본인 main worktree (D:\project) 에서 jira-ingest 를 순차 실행
5. 완료 후 ACK 받으면 다음 Phase 진행
```

orchestrator 측 처리:
```
on message "ingest-request <KEY>":
  1. mutex 획득 (메모리 상 큐 — orchestrator 가 single-threaded 라 자연 직렬화)
  2. cd D:\project  (메인 working dir)
  3. Skill('jira-ingest', '<KEY> --mode <mode>')   # 본 호출은 메인 worktree 에서 수행
  4. SendMessage({to: "workflow-PROJ-<KEY>", message: "ingest-ack"})
```

> 참고: jira-ingest 가 worktree 안에서 호출되어도 `docs/INDEX.md` 가 git tracked 이므로 worktree 별 동일 파일. 그러나 commit 시 5 worktree 가 같은 파일을 각자 수정 → merge conflict 폭증. orchestrator 가 메인에서 일괄 처리하는 게 안전.

### 6-B. harness-review subagent 폭주

5 인스턴스 × inner loop 평균 1.5 iteration × stdback/stdfront fan-out 평균 4 agent = **최대 30 동시 subagent**. 실측은 그보다 낮지만 위험.

**완화**:
- Tier-1 orchestrator 가 `codex-slot-request` 와 동일 패턴으로 `review-slot-request` 도입 — 동시 review 인스턴스 2 로 제한
- 또는 review 만 wave 직렬화: PROJ-214/215 의 review 가 끝난 뒤 216/217/218 review 시작

### 6-C. CLAUDE.md / CHANGELOG.md (organize-claude-md auto-chain)

`jira-complete §4.6` 이 임계점 도달 시 organize-claude-md 자동 호출. 5 worktree 가 동시 도달하면 `CLAUDE.md` 5번 덮어씀.

**해결**: 각 worktree-agent 가 organize-claude-md 직전에 § 6-A 와 동일하게 orchestrator 위임.

또는 더 단순: **모든 worktree 가 `jira-complete --skip-claude-md-organize` 로 호출**, organize-claude-md 는 5 워크플로 완료 후 orchestrator 가 1 회 호출.

> jira-complete 가 해당 flag 를 지원하지 않으면 본 plan 의 § 16 체크리스트 "사후 정리 — orchestrator 1 회 organize-claude-md 실행" 으로 대응.

---

## 7. Flyway V 번호 사전 할당 (반드시 §0 단계에서 확정)

현재 main 상태: 마지막 `V13__free_labor_fee_matrix.sql` (+ `V13.1__seed_free_labor_fee_matrix.sql`)

| Issue | 신규 V 번호 할당 | 신규 V 파일명 후보 |
|-------|------------------|---------------------|
| **PROJ-214** | V14 / V14.1 (시드) | `V14__code_master_tat_pass.sql` / `V14.1__seed_code_master_v12.sql` |
| **PROJ-215** | V15 | `V15__settlement_calc_d1d2d3.sql` (필요 시 material_usage_snapshot 컬럼 추가) |
| **PROJ-216** | V16 / V16.1 (kpi_grade_score_band 90행 시드) | `V16__kpi_summary_7p1.sql` / `V16.1__seed_kpi_grade_score_band.sql` |
| **PROJ-217** | V17 | `V17__settlement_adjustment_close_policy.sql` |
| **PROJ-218** | V18 / V18.1 | `V18__promotion_target.sql` / `V18.1__seed_promotion_target.sql` |

**규칙**:
- 각 worktree-agent 의 prompt 에 자기 V 번호 명시 (예: PROJ-215 agent prompt 에 "Flyway 신규 마이그레이션 사용 시 V15 / V15.x 만 사용")
- Flyway migrate **실행은 jira-test 단계에서만**, 그것도 **머지 후 메인에서 lead 가 일괄**. worktree 안에서는 H2 (test profile) 또는 standalone schema 로 단위 테스트만.
- 머지 순서에 따라 V 번호가 비어버리면 (예: PROJ-215 가 V15 만 사용, PROJ-216 이 V16 미사용) → **공백 V 번호 OK** (Flyway 는 누락 V 허용)

**충돌 시나리오**:
- 두 worktree 가 같은 V14 를 만들면 머지 시 conflict → § 5-3 prompt 의 할당표 위반 → 사용자 알림 + 재할당

---

## 8. Tier-2 (각 인스턴스 안 Agent Teams) — 변경 없음

`/harness-workflow PROJ-2XX --subtasks` 가 Phase 5 (jira-execute) 진입 시 자동으로 ADR-070 Agent Teams 모드 진입. SKILL.md 본문 + `_subtasks-convention.md` § 3 jira-execute 행 그대로 따른다.

**Tier-1 ↔ Tier-2 이름 충돌 회피**:
- Tier-1 team name: `app-w6-parallel`
- Tier-1 agent name: `workflow-PROJ-<KEY>`
- Tier-2 team name (각 인스턴스가 자동 생성): `PROJ-<KEY>`
- Tier-2 agent name: `slice-PROJ-<SUB-KEY>`

→ 4 namespace 모두 다르므로 안전.

**Tier-2 안에서 SendMessage 의 도착 범위**: teammate 는 자기 팀 (`PROJ-<KEY>`) 안만 본다. Tier-1 orchestrator 와 통신은 Tier-1 agent (workflow-PROJ-<KEY>) 만 가능. teammate → orchestrator 직통 금지.

---

## 9. 사용자 승인 게이트 직렬화

SKILL.md Phase 4 (사용자 승인) 에서 5 인스턴스가 동시에 sprint contract 요약을 던지면 **사용자가 어느 게 어느 건지 못 알아본다**.

**해결책 2 가지** (사용자 선호 1개 택):

| 옵션 | 설명 | 장단 |
|------|------|------|
| **9-A. orchestrator 가 사용자 1:1 응대 (직렬)** | 5 workflow-agent 가 sprint contract 를 메시지로 orchestrator 에 보내고 idle. orchestrator 가 순서대로 "PROJ-214 계획 — 승인?" 1개씩 사용자에게 제시 → 사용자 OK → orchestrator 가 해당 agent 깨움 | 안전, 약간 느림 |
| **9-B. 일괄 승인** | orchestrator 가 5 sprint contract 를 한 화면에 묶어 제시 → 사용자가 "전부 OK" 또는 "PROJ-216 만 수정" | 빠름, 한 묶음 거부 시 처리 복잡 |

권장: **9-A** (사고 방지).

---

## 10. Hook 동시 발화 안전성 검증

| Hook | 위치 | 발화 빈도 | worktree 격리 | 위험 |
|------|------|-----------|---------------|------|
| `UserPromptSubmit` → harness-context-inject.sh | 각 agent 의 turn 시작 | 매 turn | stdout 만, 부수효과 없음 | ✅ 안전 |
| `PostToolUse` (Edit\|Write) → compile-check.sh | Edit/Write 호출마다 | 빈번 | `.claude/runtime/changed-files.txt` 는 `mkdir -p .claude/runtime` (pwd 기준) → worktree 별 격리 | ✅ 안전 |
| `PreToolUse` (Bash git commit*) → review-gate.sh | git commit 호출 시 | 5회 (각 인스턴스 1번) | aggregate-verdict.md read 만 (pwd 기준 worktree 격리) | ✅ 안전 |
| `Stop` → persist-checkpoint.sh | agent turn 종료 시 | 매 turn | checkpoint.md 는 `cd "$REPO_ROOT"` 후 `mkdir -p .claude/runtime` (REPO_ROOT = worktree top) | ✅ 안전 |

**모든 hook 이 pwd / git rev-parse --show-toplevel 기준** → worktree 자동 격리. 5 동시 발화 race 없음.

**단 한 가지 예외**: 만약 사용자가 hooks 를 수정해서 절대경로 (`/d/project/.claude/runtime/...`) 를 hard-code 하면 격리 깨짐 → 본 plan 진입 전 § 0-1 부록 체크리스트로 확인.

---

## 11. 머지 (PR / git merge) — 강제 직렬화

각 worktree-agent 의 `jira-complete` 가 `git push origin feat/PROJ-<KEY>` 까지만 수행. **PR 생성과 머지는 orchestrator** (`merge-ready` 메시지 수신 시).

### 11-1. 머지 순서 (§ 3 결정 사용)

```
1. 214 머지 (격리, 충돌 0 보장)
2. 215 머지 (foundation)
3. 218 머지 (WEAK REF — 215 와 합쳐도 promotion/ 충돌 거의 0)
4. 217 머지 (215 REF — rebase 후 통합 빌드 검증)
5. 216 머지 (215 REF — rebase 후 통합 빌드 검증)
```

### 11-2. 각 머지 사이클 (orchestrator)

```
1. git checkout main && git pull --ff-only
2. git merge --no-ff feat/PROJ-<KEY>   (또는 PR 머지)
3. cd D:\project (메인 worktree)
4. ./gradlew clean build              ← 통합 빌드, GREEN 필수
5. npm run build (FE 변경 있으면)
6. Flyway 적용 (V<N>) — dev MySQL 에 migrate
7. INDEX.md / LOG.md ingest closure update (§ 6-A)
8. STOP — 4~7 중 1개라도 실패하면 다음 머지 중단 + 사용자 알림
```

### 11-3. Conflict 발생 시

- 코드 충돌: 215 머지 후 217/216 의 SettlementCalculator 사용처가 깨지면 → 해당 worktree-agent 에 SendMessage `rebase-fix` → agent 가 자기 worktree 에서 `git fetch origin && git rebase origin/main` → conflict 해결 → 통합 빌드 → push --force-with-lease (자기 브랜치만)
- INDEX.md / LOG.md 충돌: § 6-A 위배 = 5 워크플로 중 하나가 직접 만진 경우. 사용자 알림 + 수동 머지

---

## 12. 실패 / 복구 시나리오

| 시나리오 | 감지 | 복구 |
|---------|------|------|
| **워크플로 중간 세션 종료** | Tier-1 agent idle 알림 + 일정 시간 무응답 | persist-checkpoint hook 이 worktree 별 checkpoint.md 작성 → 새 세션에서 해당 worktree 로 진입 + `/harness-resume` |
| **하나의 worktree 가 ESCALATE (3회 ITERATE 실패)** | 해당 agent 가 `SendMessage("escalate <KEY> reason=...")` | orchestrator 가 다른 4 개를 계속 진행, 사용자에게 ESCALATE 알림 + 재계획 옵션 제시 |
| **Flyway V 번호 충돌** (두 worktree 가 같은 V14 생성) | 머지 시 conflict | orchestrator 가 § 7 표 재할당 → agent 에 rename 지시 |
| **메인 push 권한 거부 / GitLab rate limit** | jira-complete push 실패 | 해당 agent 가 SendMessage 알림 → orchestrator 가 사용자 재시도 결정 |
| **Codex sandbox 1385 동시 호출 deadlock** | review 단계 무응답 | § 6-B 의 review-slot-request 가 사전 방지. 발생 시 orchestrator 가 Codex 호출 직렬화 |
| **사용자가 한 인스턴스 거부 (Phase 4)** | orchestrator 가 § 9-A 으로 1:1 응대 중 reject | 해당 agent 에 SendMessage("re-plan with feedback: ...") → 다른 4는 계속 |
| **dev MySQL down** | jira-test 의 통합 테스트 실패 | 모든 인스턴스가 H2 fallback (Spring profile=test). orchestrator 가 사용자에게 인프라 복구 알림 |
| **worktree 디렉토리 오염 (작업 외 변경)** | git status 가 dirty | 해당 agent 가 SendMessage 알림 → orchestrator 가 사용자 확인 후 `git reset --hard` 또는 stash |

---

## 13. 비용 / 시간 추정

| 메트릭 | 단일 인스턴스 (SKILL.md 기준) | 5 동시 (옵션 A wave) | 5 동시 (옵션 B 풀) |
|--------|------------------------------|----------------------|---------------------|
| Wall time | 6~10h × 5 = 30~50h 순차 | ~18~25h (2-2-1) | ~12~16h |
| Token cost | base | ~3.5× | ~5× (subagent 폭주 시 7×) |
| 사용자 대기 (승인 게이트) | 1×N | 1×N (직렬화) | 1×N (직렬화) |
| 코드 충돌 처리 시간 | 0 | 1~2h (215 머지 후 rebase) | 3~5h |
| **권장** | 보통 작업 | 🟢🟢 **현 5 이슈** | 🟡 시간 압박 + 충돌 감수 |

**Anthropic 공식 문서 기준**: Agent Teams 모드는 "단일 세션 × 3~7" token. 5 부모 × 평균 3 슬라이스 = 약 5×4 = 20 token 단위 → 약 **단일 인스턴스 1개의 12~20×**. 사용자 사전 승인 필수.

---

## 14. 체크리스트 (orchestrator 가 그대로 실행)

### 14-1. Pre-flight (작업 시작 전)

- [ ] § 0 의 10 개 조건 모두 ✅
- [ ] 사용자가 코드 충돌 매트릭스 (§ 3) + 머지 순서 (§ 3-결정) 동의
- [ ] 사용자가 옵션 A / B / C 중 선택
- [ ] 사용자가 token cost 12~20× 인지·승인
- [ ] Flyway V 번호 표 (§ 7) 사용자 검토·승인
- [ ] sprint 정책 위반 (W5 미진입 + W6 동시 진입) 사용자 명시 OK
- [ ] hooks 4개 모두 worktree-aware (§ 10) 검증
- [ ] git status clean + main 최신
- [ ] 5 worktree 생성 + `git worktree list` 확인 (§ 5-1)
- [ ] (옵션 C) interface stub 사전 push

### 14-2. Tier-1 spawn

- [ ] ToolSearch 로 TeamCreate/Task*/SendMessage/Agent schema 로드
- [ ] TeamCreate "app-w6-parallel"
- [ ] TaskCreate 5 개 + DAG 의존성 (옵션 A: 217/216/218 blockedBy 215)
- [ ] Agent spawn 5 개 (working dir 명시 + 프롬프트 § 5-3)
- [ ] TaskUpdate(owner) 5 개

### 14-3. Runtime 모니터링

- [ ] 5 인스턴스의 sprint contract 메시지 수집 (§ 9-A)
- [ ] 사용자 승인 게이트 1:1 직렬화
- [ ] ingest-request / codex-slot-request / review-slot-request 메시지 라우팅
- [ ] merge-ready 메시지 도착 시 § 11 머지 사이클 실행

### 14-4. Post-completion

- [ ] 5 워크플로 모두 jira-complete 완료 확인
- [ ] 머지 5 회 모두 PASS
- [ ] Flyway 통합 적용 (V14~V18)
- [ ] organize-claude-md 1회 통합 실행 (§ 6-C)
- [ ] wiki-lint 1회 (corpus-scoped)
- [ ] `~/.claude/teams/app-w6-parallel/` 삭제 (TeamDelete)
- [ ] `~/.claude/teams/PROJ-214 ~ 218/` 5개 삭제 (각 Tier-2 lead 가 SKILL.md 정리 단계에서 자동)
- [ ] worktree 5 개 삭제: `git worktree remove .claude/worktrees/PROJ-<KEY>` × 5
- [ ] CLAUDE.md `Last Updated:` 갱신 (5 이슈 closure 요약)
- [ ] CHANGELOG.md append (5 이슈 묶음)
- [ ] 사용자에게 머지 요약 + 통합 빌드 결과 + Codex review 종합 보고

---

## 15. 안 되는 것 (명시 금지)

| 시도 | 왜 금지 |
|------|---------|
| 5 worktree 가 같은 main 브랜치 위에서 작업 | 브랜치 1개 동시 체크아웃 불가 → 반드시 각자 feat/PROJ-<KEY> |
| Tier-1 agent 가 INDEX.md / LOG.md / 08-decision-log.md / sprint/weeks/*.md 직접 수정 | § 6-A wiki append race → 데이터 손실 |
| Tier-1 agent 가 메인 working dir (D:\project) 의 파일 수정 | 다른 worktree 와 충돌 |
| 5 worktree 가 동시에 Flyway migrate 호출 | dev MySQL schema 단일 → migration race + 시퀀스 깨짐 |
| 5 워크플로의 jira-complete 가 동시에 main 머지 push | main race + GitLab CI 동시 발화 → 사고 |
| Codex review 5 동시 호출 | Windows sandbox 1385 lock → deadlock |
| harness-review subagent 동시 30 이상 spawn | OOM / API rate limit / context 폭주 |
| Tier-2 teammate 가 다른 부모 (다른 worktree) 의 파일 read | working dir 격리 위반 |
| `isolation: "worktree"` 옵션과 § 5-1 명시 worktree 동시 사용 | claude code 가 임시 worktree 추가 생성 → cleanup 충돌 |
| 사용자 승인 게이트 (Phase 4) 5 인스턴스 동시 sprint contract 던지기 | 사용자가 어느 게 어느 건지 못 알아봄 |
| `jira-complete` 의 organize-claude-md auto-chain 을 5 인스턴스가 동시에 트리거 | CLAUDE.md 5번 덮어씀 |

---

## 16. 부록 — 도구 호출 cheatsheet

### A. Worktree 생성/삭제
```powershell
# 생성 (5개)
foreach ($k in 214,215,216,217,218) {
  git -C D:\project worktree add "D:\project\.claude\worktrees\PROJ-$k" -b "feat/PROJ-$k"
}

# 확인
git -C D:\project worktree list

# 정리 (작업 완료 후)
foreach ($k in 214,215,216,217,218) {
  git -C D:\project worktree remove "D:\project\.claude\worktrees\PROJ-$k"
}
# 머지 후 브랜치 정리
foreach ($k in 214,215,216,217,218) {
  git -C D:\project branch -d "feat/PROJ-$k"
}
```

### B. Agent Teams API (Tier-1)

> ⚠️ **Sub-agent 회귀 안티패턴 차단** — 아래 시퀀스가 진짜 Agent Teams. `Agent({ subagent_type:"general-purpose", isolation:"worktree" })` 단독 호출 (team_name / SendMessage 없음) 은 **sub-agent + 워크트리 격리** 이지 Agent Teams 가 아님. 이름이 비슷해 자주 혼동. 호출 직전 자가검증: "내 시퀀스에 `TeamCreate` + `team_name` 파라미터 + `SendMessage` 가 다 들어있는가?" 셋 중 하나라도 빠지면 sub-agent 모드. 자세한 차이 표는 `jira-execute/SKILL.md § 4A` 의 ⚠️ 박스 참조.

```
ToolSearch({ query: "select:TeamCreate,TeamDelete,TaskCreate,TaskList,TaskUpdate,TaskGet,SendMessage", max_results: 10 })
TeamCreate({ team_name: "app-w6-parallel", agent_type: "orchestrator", description: "..." })
TaskCreate({ subject: "workflow-PROJ-214", description: "...", activeForm: "..." })
Agent({ team_name: "app-w6-parallel", name: "workflow-PROJ-214", subagent_type: "general-purpose", prompt: "...", description: "..." })
TaskUpdate({ taskId: "1", owner: "workflow-PROJ-214" })
SendMessage({ to: "workflow-PROJ-214", message: "merge-ack <sha>", summary: "merge ack" })
TeamDelete({})  # 작업 끝, 모두 idle 후
```

### C. 메시지 프로토콜 (orchestrator ↔ workflow-agent)
```
agent → orchestrator:
  - "sprint-contract-ready <KEY> path=<.claude/runtime/sprint-contract/<KEY>.md>"
  - "ingest-request <KEY> mode=forecast|closure"
  - "codex-slot-request <KEY>"
  - "review-slot-request <KEY>"
  - "merge-ready <KEY> sha=<HEAD>"
  - "escalate <KEY> reason=<...>"
  - "blocker <KEY> reason=<...>"

orchestrator → agent:
  - "approve <KEY>" / "reject <KEY> feedback=<...>"
  - "ingest-ack"
  - "codex-slot-grant" / "codex-slot-deny retry=<sec>"
  - "review-slot-grant"
  - "merge-ack <sha>"
  - "rebase-fix <KEY> base=<sha>"
```

### D. 인스턴스 1개 강제 중단
```
SendMessage({ to: "workflow-PROJ-216", message: {type: "shutdown_request", reason: "user-cancel"}, summary: "cancel PROJ-216" })
# 응답 shutdown_response approve=true 받으면 worktree 삭제 + jira 상태 되돌리기
```

---

## 17. 변경 이력

- **2026-05-18**: 초안 — PROJ-214~218 W5/W6 묶음 5 이슈 동시 실행 시 적용. SKILL.md (단일 부모 + Tier-2 fan-out) 위에 Tier-1 worktree 격리 + orchestrator 직렬화 패턴 추가.

---

**핵심 요약 — 5 가지만 지키면 사고 없음**:

1. **worktree 5 개 명시 생성** (§ 5-1) — 브랜치 1개 동시 체크아웃 금지
2. **INDEX.md / LOG.md / CLAUDE.md 는 orchestrator 만 만진다** (§ 6-A, 6-C) — wiki append race 제거
3. **Flyway V 번호 사전 할당** (§ 7) — V14=214 / V15=215 / V16=216 / V17=217 / V18=218
4. **머지는 215 먼저, 그 후 217/216 rebase** (§ 11) — REF dependency 해소
5. **사용자 승인 게이트 1:1 직렬화** (§ 9-A) — 5 sprint contract 동시 제시 금지
