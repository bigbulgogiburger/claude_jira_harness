---
name: harness-gate
description: "커밋 전 최종 품질 게이트. aggregate-verdict 확인 + 프로젝트별 빌드/타입체크/린트를 종합 검증합니다."
triggers:
  - "/harness-gate"
  - "harness gate"
  - "품질 게이트"
  - "커밋 전 검증"
---

# /harness-gate — Pre-commit 품질 게이트

> **직교 원칙**: /jira-commit의 DoD 검증과 독립. 더 엄격한 Harness 품질 기준 적용.
> **참조**: ~/.claude/docs/HARNESS-JIRA-ORTHOGONAL-ARCHITECTURE.md

## ⛔ Guard — HARNESS_MODE 확인 (최우선)

이 스킬의 모든 단계보다 **먼저** 실행한다. `HARNESS_MODE` 환경변수를 확인:

| HARNESS_MODE 값 | 동작 |
|-----------------|------|
| 미설정 / 빈값 / `off` | **즉시 중단**. 사용자에게 알림: "⛔ 이 프로젝트는 Harness가 설정되지 않았습니다 (HARNESS_MODE=$HARNESS_MODE). `/jira-*` 워크플로우를 사용하세요." 출력 후 **이후 단계를 절대 실행하지 않는다.** |
| `suggest` / `auto` | 정상 진행 |

---

## 절차

### Step 1. Aggregate Verdict 확인

`.claude/runtime/aggregate-verdict.md`를 읽는다.

| 상태 | 동작 |
|------|------|
| 파일 없음 | "⚠️ /harness-review를 먼저 실행하세요" 경고 후 Step 2로 진행 |
| verdict = PASS | Step 2로 진행 |
| verdict = ITERATE | "🔴 Blocker 미해결. 커밋 불가." 차단 |
| verdict = ESCALATE | "🔴 재계획 필요. /harness-plan 재실행." 차단 |

### Step 2. 프로젝트별 빌드 검증

| 프로젝트 | 명령어 |
|---------|--------|
| **catalog-service** | `./gradlew compileJava -q` |
| **order-service** | `./gradlew.bat compileJava -q` |
| **order-admin** | `npx vue-tsc --noEmit` (타입 체크만, 빌드 아님) |

빌드 실패 시 차단 + 에러 메시지 출력.

### Step 3. Sprint Contract DoD 체크

Sprint Contract (`.claude/runtime/sprint-contract/PROJ-XXX.md`)가 있으면:
- "Definition of Done" 섹션의 체크박스 상태 확인
- 미완료 항목이 있으면 경고 (차단은 아님)

### Step 4. 최종 판정

| 조건 | 결과 |
|------|------|
| Aggregate PASS + 빌드 성공 | ✅ **GATE PASS** — 커밋 진행 가능 |
| Aggregate PASS + 빌드 실패 | 🔴 빌드 수정 후 재시도 |
| Aggregate 없음 + 빌드 성공 | ⚠️ 리뷰 없이 커밋 가능 (경고만) |
| Aggregate ITERATE/ESCALATE | 🔴 차단 |

### Step 5. Shared State 갱신 (Read-Merge-Write 필수)

판정 완료 직후 반드시 실행:

1. **Read**: `.claude/runtime/workflow-state.json`을 Read.
2. **Merge**: 기존 필드 보존하며 다음 갱신:
   ```json
   {
     "stage": "<gate-passed|gate-blocked>",
     "gate_verdict": "<PASS|BLOCKED>",
     "gate_reason": "<빌드 성공/실패, verdict 상태 요약>",
     "gated_at": "YYYY-MM-DDTHH:MM:SS"
   }
   ```
3. **Write**: 병합한 JSON을 Write로 저장.

### Step 6. 출력

```
══════════════════════════════════
  Harness Quality Gate
  
  Aggregate: PASS ✅
  Build:     PASS ✅
  DoD:       3/4 completed ⚠️
  
  → 커밋 진행 가능합니다.
══════════════════════════════════
```

---

## 주의사항

- /jira-commit의 기존 DoD 검증과 **독립** — 이중 체크가 되어도 충돌 없음
- 빌드 실패 시 프로젝트 에이전트 제안 (있는 경우):
  - catalog-service: `catalog-build-resolver`
  - order-service: (build-resolver 에이전트 없음 — 수동 해결)
  - order-admin: (build-resolver 에이전트 없음 — 수동 해결)
- `HARNESS_MODE=off`일 때는 이 스킬을 제안하지 않음
