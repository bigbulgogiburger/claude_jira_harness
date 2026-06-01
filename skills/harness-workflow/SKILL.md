---
name: harness-workflow
description: "Jira 스킬과 Harness를 자동 시퀀싱하는 통합 오케스트레이터. /jira-start부터 /jira-complete까지 + 중간 Sprint Contract + 리뷰 Inner Loop를 한 번에 실행합니다."
triggers:
  - "/harness-workflow"
  - "harness workflow"
  - "전체 워크플로우"
  - "이슈 전체 진행"
---

# /harness-workflow — 통합 오케스트레이터 (Level 4)

> **직교 원칙**: Jira 스킬을 수정하지 않고 **Skill tool로 순차 호출**하여 감싼다.
> **핵심 가치**: 사용자는 이슈 키 하나만 입력. 나머지는 자동 시퀀싱.
> **참조**: ~/.claude/docs/HARNESS-JIRA-ORTHOGONAL-ARCHITECTURE.md

## Usage

```
/harness-workflow <KEY>                          # 1 부모 일반
/harness-workflow <KEY> --subtasks               # 1 부모 + 하위 fan-out (Tier-2, ADR-070)
/harness-workflow <KEY1> <KEY2> ... [--subtasks] # ⚡ 다중 부모 병렬 (Tier-1 + Tier-2)
```

### 모드 결정 트리 (입력 시 무조건 확인)

1. **입력에 부모 키가 2개 이상인가?** (공백 / 슬래시 / 쉼표로 구분된 별개 부모 — 같은 epic 의 형제 작업 포함)
   → **YES → 즉시 `parallel-fanout.md` 로 분기**. 본 SKILL.md 의 단일-인스턴스 시퀀스는 적용 금지.
   - `Read('~/.claude/skills/harness-workflow/parallel-fanout.md')` 먼저 호출 + §0 사전조건 10개 검증 + §3 충돌 매트릭스 + §4 옵션 A/B/C/D 사용자 승인 → §5 worktree 생성 + Tier-1 TeamCreate + Agent spawn × N
   - 일반적인 misconception: "fan-out = `--subtasks` 만" ❌ — fan-out 은 **2-tier**. Tier-1 (다중 부모 worktree) + Tier-2 (단일 부모 하위 Agent Teams). `parallel-fanout.md` 가 SSoT.

2. **입력에 부모 키가 1개 + `--subtasks` 플래그?**
   → 본 SKILL.md 의 단일-인스턴스 시퀀스 + 자식 스킬 호출마다 `--subtasks` 자동 전파 (`_subtasks-convention.md` § 7).
   - 진입 조건: 부모 이슈의 `subtasks` 필드에 하위 키 1개 이상 존재 (자동 검증). 미충족 시 일반 모드 폴백.

3. **입력에 부모 키가 1개 + 플래그 없음?**
   → 본 SKILL.md 의 단일-인스턴스 시퀀스, 부모만 처리.

⚠️ **회귀 사례** (2026-05-22): 사용자가 `PROJ-233 / PROJ-234 --subtasks` 입력 시 "두 별개 부모는 한 워크플로로 못 묶는다" 며 순차 진행 제안 → `parallel-fanout.md` 존재 자체를 놓침. **결정 트리 1번 분기를 반드시 먼저 평가**.

## ⛔ Guard — HARNESS_MODE 확인 (최우선)

이 스킬의 모든 단계보다 **먼저** 실행한다. `HARNESS_MODE` 환경변수를 확인:

| HARNESS_MODE 값 | 동작 |
|-----------------|------|
| 미설정 / 빈값 / `off` | **즉시 중단**. 사용자에게 알림: "⛔ 이 프로젝트는 Harness가 설정되지 않았습니다 (HARNESS_MODE=$HARNESS_MODE). `/jira-*` 워크플로우를 사용하세요." 출력 후 **이후 단계를 절대 실행하지 않는다.** |
| `suggest` / `auto` | 정상 진행 |

---

## Shared State 초기화

워크플로 시작 시 `.claude/runtime/workflow-state.json` 생성:

```json
{
  "issue_key": "PROJ-XXX",
  "stage": "start",
  "current_phase": 0,
  "total_phases": 0,
  "iteration": 0,
  "dev_guide_path": null,
  "sprint_contract_path": null,
  "aggregate_verdict": null,
  "changed_files": [],
  "agent_outputs": {},
  "history": [],
  "subtasks_mode": false,
  "subtasks": [],
  "slice_status": {}
}
```

`--subtasks` 모드 시:
- `subtasks_mode: true`
- `subtasks: [<sub-key>, ...]` (부모 이슈 조회 결과)
- `slice_status: {<sub-key>: "pending"}` (구현/리뷰/완료 단계마다 갱신)

## 시퀀스

> **`--subtasks` flag 자동 전파 규칙** — 사용자가 `/harness-workflow <KEY> --subtasks` 로 호출했으면, 아래 모든 자식 Skill 호출 인자에 `--subtasks` 자동 부착. 단 통합 검증 단계 (jira-test, harness-gate) 는 flag 불필요. 자세히는 `~/.claude/skills/_subtasks-convention.md` § 7.

### Phase 0: 모드 확인 (`--subtasks` 시)

```
0. 사용자 입력에 --subtasks 가 있으면:
   - mcp__atlassian__getJiraIssue 로 부모 이슈 조회
   - subtasks 필드에 1개 이상 있으면 subtasks_mode 진입
   - 비어있으면 일반 모드 폴백 + 사용자에게 안내
   - state.subtasks_mode = true, state.subtasks = [...]
```

### Phase 1: 착수

```
1. Skill tool로 /jira-start <ISSUE-KEY> [--subtasks] 호출
   → 부모 In Progress 전환 + 브랜치
   → (--subtasks) 모든 하위 In Progress 전환 + 짧은 댓글
   → state.stage = "start"
```

### Phase 2: 요구 명확화 (조건부)

```
2. 사용자에게 확인: "요구사항이 명확합니까? /jira-clarify가 필요합니까?"
   → 필요하면: Skill tool로 /jira-clarify <ISSUE-KEY> [--subtasks] 호출
   → 불필요하면: 스킵
```

### Phase 3: 계획

```
3. Skill tool로 /jira-plan <ISSUE-KEY> [--subtasks] 호출
   → 부모 dev-guide.md 생성
   → (--subtasks) slice dev-guide N장 추가 + 각 하위에 댓글
   → (자동 chain) jira-plan §6 — docs/INDEX-SCHEMA.md 있으면 jira-ingest forecast 자동 호출
                   INDEX.md row 추가 (status=planned) + LOG append
                   wiki 미설정 프로젝트는 skip
   → state.dev_guide_path = <생성된 경로>
   → state.stage = "planning"

4. Skill tool로 /harness-plan <ISSUE-KEY> [--subtasks] 호출
   → Sprint Contract 생성 (slice 별 DoD 인라인)
   → state.sprint_contract_path = <생성된 경로>
   → state.stage = "plan-supplement"
   → state.total_phases = <Sprint Contract의 Phase 수>
```

### Phase 4: 사용자 승인

```
5. Sprint Contract의 핵심을 요약하여 사용자에게 제시
   → "이 계획으로 진행하시겠습니까?"
   → 승인: Phase 5로
   → 수정 요청: Phase 3으로 돌아가 재계획
```

### Phase 5: 구현 + 리뷰 Inner Loop

```
현재 Phase = state.current_phase + 1

OUTER LOOP (Phase 단위):
  while current_phase <= total_phases:
  
    6. Skill tool로 /jira-execute <ISSUE-KEY> [--subtasks] 호출
       → Phase N 구현
       → (--subtasks) slice 별 구현 완료 시 해당 하위에 짧은 댓글
       → state.stage = "implementing-phase-N"
    
    INNER LOOP (리뷰-수정 반복):
      state.iteration = 0
      
      7. Skill tool로 /harness-review [--subtasks] 호출
         → Fan-out 리뷰 + Aggregate verdict
         → (--subtasks) slice 별 verdict 가 있으면 부모 verdict 에 롤업
         → state.stage = "reviewing-phase-N"
         → state.iteration += 1
      
      8. Verdict 분기:
         PASS → Inner Loop 탈출, 다음 Phase
         ITERATE (iteration < 3) → 수정 후 7번으로
         ESCALATE → 사용자에게 재계획 제안
           → 수락 시: /harness-plan 재호출 (v2), Phase 3으로
           → 거부 시: 현재 상태로 강제 진행
    
    state.current_phase += 1
```

### Phase 6: 최종 검증 + 커밋

```
9. Skill tool로 /jira-test 호출        # flag 불필요 (통합 검증)
   → 프로젝트별 테스트 실행

10. Skill tool로 /harness-gate 호출    # flag 불필요 (통합 게이트)
    → 최종 품질 게이트
    → GATE PASS 필수

11. Skill tool로 /jira-commit <ISSUE-KEY> [--subtasks] 호출
    → 부모 commit + 댓글
    → (--subtasks) 모든 하위에 commit SHA 인용 댓글
```

### Phase 7: 완료

> ⛔ **Phase 7 은 반드시 `Skill('jira-complete', ...)` 로 진입할 것.** harness-workflow 가 직접 `mcp__atlassian__transitionJiraIssue` + `git push` + comment 만 호출하고 jira-complete skill 자체를 우회하면 §4.4 (ingest closure) + §4.6 (organize CLAUDE.md) + §4.7 (wiki-lint summary) chain 이 통째로 발화 안 한다 (2026-05-14 PROJ-208 사고). transition/push 를 본 skill 안에서 미리 한 경우라도 §4.4/§4.6/§4.7 발화를 위해 jira-complete skill 을 후속 호출해야 한다.
>
> 또한 Phase 3 도 동일 — 반드시 `Skill('jira-plan', ...)` 로 진입해야 §6 (ingest forecast) chain 이 발화. harness-workflow 가 직접 dev-guide 만 작성하고 jira-plan skill 우회하면 forecast 단계 누락 → closure 단계에서 row 가 갑자기 튀어나오는 비대칭.

```
12. Skill tool로 /jira-complete <ISSUE-KEY> [--subtasks] 호출
    → 부모 QA 전이 + 푸시 + archive
    → (--subtasks) 모든 하위 QA 전이 + 짧은 댓글
    → (자동 chain) jira-complete §4.4 — wiki 설정된 프로젝트면 jira-ingest closure 자동 호출
                   INDEX status=closed + cross-ref (ADR/sprint week·track) 갱신
    → CLAUDE.md 위생 체크 자동 포함 (jira-complete §4.6) — 임계점 도달 시
      organize-claude-md 자동 호출 + Phase 6 사용자 승인 대기.
    → (자동 chain) jira-complete §4.7 — wiki 설정된 프로젝트면 wiki-lint summary 자동 호출
                   high severity 만, non-blocking. 위반 보고만 출력.
    → state cleanup (workflow-state.json 삭제 또는 아카이브)
```

**자기 점검 (harness-workflow 종료 직전 last-mile check)**:
- `docs/INDEX-SCHEMA.md` 존재? → 본 워크플로 동안 jira-ingest forecast (Phase 3) + closure (Phase 7) 호출 흔적이 conversation 에 모두 있어야 함
- wiki-lint summary (Phase 7) 호출 흔적도 있어야 함
- 누락 감지 시 → **지금 즉시 일괄 호출** + 사용자에게 "Phase X chain 누락 감지 → 사후 호출함" 보고

## 중단 + 재개 지원

워크플로 중간에 세션이 종료되면:
- Stop Hook이 자동으로 checkpoint 저장
- 새 세션에서 `/harness-resume`로 마지막 단계부터 재개

## 에러 핸들링

| 에러 | 처리 |
|------|------|
| jira-start 실패 (브랜치 충돌) | 사용자에게 알림, 수동 해결 후 재시도 |
| jira-plan 실패 | 사용자에게 직접 dev-guide 작성 또는 재시도 제안 |
| 빌드 실패 (Phase 중) | 프로젝트 build-resolver 에이전트 자동 제안 |
| harness-review 에이전트 미존재 | 해당 축 스킵, 경고 출력 |
| 3회 ITERATE 후 동일 Blocker | ESCALATE → 재계획 제안 |

## HARNESS_MODE 동작

| 모드 | /harness-workflow 동작 |
|------|----------------------|
| `auto` | 전체 시퀀스 자동 진행, Phase 승인만 수동 |
| `suggest` | 각 Harness 단계(plan/review/gate)마다 사용자 확인 |
| `off` | `/harness-workflow` 자체를 호출하면 동작하지만, Hook은 비활성 |

---

## 주의사항

- **Jira 스킬은 Skill tool로 호출** — 내부적으로 스킬의 SKILL.md를 변경하지 않음
- 스킬 호출 실패 시 스킬이 없다면 해당 단계 스킵 가능 여부를 사용자에게 확인
- Inner Loop는 **같은 Phase 안에서만** 동작 — Phase 간 Blocker는 ESCALATE
- 전체 워크플로 중 어디서든 사용자가 중단 가능 — state 자동 저장
