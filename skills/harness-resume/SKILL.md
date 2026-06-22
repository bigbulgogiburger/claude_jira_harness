---
name: harness-resume
description: "이전 세션의 체크포인트를 복원하여 작업을 이어갑니다. workflow-state.json과 checkpoint.md를 읽어 중단된 단계부터 재개합니다."
triggers:
  - "/harness-resume"
  - "harness resume"
  - "이어서 작업"
  - "이전 작업 복원"
---

# /harness-resume — 체크포인트 복원

> **직교 원칙**: Jira 이슈 상태는 건드리지 않는다. Harness 워크플로 상태만 복원.
> **참조**: ~/.claude/docs/HARNESS-JIRA-ORTHOGONAL-ARCHITECTURE.md

## ⛔ Guard — HARNESS_MODE 확인 (최우선)

> 이 스킬의 모든 단계보다 **먼저** 실행. SSoT: `~/.claude/skills/_harness-guard.md` — `HARNESS_MODE` 가 미설정/빈값/`off` 면 즉시 중단(안내 출력 후 이후 단계 실행 금지), `suggest`/`auto` 면 정상 진행.

---

## 절차

### Step 1. 체크포인트 파일 탐색

다음 순서로 복원 정보를 찾는다:

1. `.claude/runtime/workflow-state.json` (Shared State)
2. `.claude/runtime/checkpoint.md` (Stop Hook 산출물)
3. 사용자가 이슈 키를 인자로 전달하면 해당 이슈의 아티팩트 탐색

### Step 2. 상태 파싱 + 요약 출력

workflow-state.json에서 읽을 항목:
```json
{
  "issue_key": "SURINP-200",
  "stage": "implementing-phase-2",
  "current_phase": 2,
  "total_phases": 3,
  "iteration": 1,
  "aggregate_verdict": "PASS",
  "dev_guide_path": "docs/SURINP-200-dev-guide.md",
  "sprint_contract_path": ".claude/runtime/sprint-contract/SURINP-200.md"
}
```

사용자에게 요약:
```
══════════════════════════════════
  Harness Resume — SURINP-200
  
  현재 단계: Phase 2 구현 중
  전체 Phase: 3
  마지막 리뷰: Phase 1 PASS ✅
  
  → /jira-execute SURINP-200로 Phase 2 계속
  → /harness-review로 리뷰 진행
══════════════════════════════════
```

### Step 3. 관련 문서 자동 로드

복원 시 다음 파일을 Read:
1. dev-guide (경로가 state에 있으면)
2. Sprint Contract (경로가 state에 있으면)
3. 마지막 Aggregate verdict (있으면)

### Step 4. 단계별 재개 안내

| 복원된 stage | 안내 |
|-------------|------|
| `planning` | "/jira-plan이 완료된 상태. /harness-plan으로 Contract 보충" |
| `plan-supplement` | "Sprint Contract 완료. /jira-execute로 구현 시작" |
| `implementing-phase-N` | "/jira-execute로 Phase N 계속" |
| `reviewing-phase-N` | "/harness-review로 리뷰 진행" |
| `committing` | "/harness-gate → /jira-commit 순서로 진행" |

---

## 주의사항

- 체크포인트가 없으면 "복원할 상태가 없습니다" 출력 후 종료
- Jira 이슈 상태(In Progress 등)는 건드리지 않음 — 이미 jira-start가 처리함
- 오래된 체크포인트(7일 이상)는 경고 출력 후 사용 여부 확인
