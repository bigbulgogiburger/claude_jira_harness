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
  "history": []
}
```

## 시퀀스

### Phase 1: 착수

```
1. Skill tool로 /jira-start <ISSUE-KEY> 호출
   → 브랜치 생성, In Progress 전환
   → state.stage = "start"
```

### Phase 2: 요구 명확화 (조건부)

```
2. 사용자에게 확인: "요구사항이 명확합니까? /jira-clarify가 필요합니까?"
   → 필요하면: Skill tool로 /jira-clarify 호출
   → 불필요하면: 스킵
```

### Phase 3: 계획

```
3. Skill tool로 /jira-plan <ISSUE-KEY> 호출
   → dev-guide.md 생성
   → state.dev_guide_path = <생성된 경로>
   → state.stage = "planning"

4. Skill tool로 /harness-plan <ISSUE-KEY> 호출
   → Sprint Contract 생성
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
  
    6. Skill tool로 /jira-execute <ISSUE-KEY> 호출
       → Phase N 구현
       → state.stage = "implementing-phase-N"
    
    INNER LOOP (리뷰-수정 반복):
      state.iteration = 0
      
      7. Skill tool로 /harness-review 호출
         → Fan-out 리뷰 + Aggregate verdict
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
9. Skill tool로 /jira-test 호출
   → 프로젝트별 테스트 실행

10. Skill tool로 /harness-gate 호출
    → 최종 품질 게이트
    → GATE PASS 필수

11. Skill tool로 /jira-commit <ISSUE-KEY> 호출
    → 커밋 + Jira 상태 업데이트
```

### Phase 7: 완료

```
12. Skill tool로 /jira-complete <ISSUE-KEY> 호출
    → 최종 검증 + 푸시
    → state cleanup (workflow-state.json 삭제 또는 아카이브)
```

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
