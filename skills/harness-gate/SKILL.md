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

> 이 스킬의 모든 단계보다 **먼저** 실행. SSoT: `~/.claude/skills/_harness-guard.md` — `HARNESS_MODE` 가 미설정/빈값/`off` 면 즉시 중단(안내 출력 후 이후 단계 실행 금지), `suggest`/`auto` 면 정상 진행.

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

### Step 2. 빌드 검증 (cwd 우선 + 스택 fallback)

cwd가 알려진 프로젝트와 매칭되면 그 명령을 우선 사용하고, 매칭되지 않으면 스택을 감지하여 기본 명령을 실행한다. 이 분기는 새 프로젝트(Flutter, 다른 백엔드 등)에서도 게이트가 의미 있게 동작하도록 만들기 위함이다.

**알려진 프로젝트 (우선)**

| 프로젝트 | 명령어 |
|---------|--------|
| **app-ha-back** | `./gradlew compileJava -q` |
| **cs-back** | `./gradlew.bat compileJava -q` |
| **cs-front** | `npx vue-tsc --noEmit` (타입 체크만, 빌드 아님) |

**Stack-based Fallback (cwd가 위에 매칭 안 되거나 알 수 없을 때)**

CLAUDE.md에 빌드/타입체크 명령이 명시되어 있으면 그것을 우선 사용한다. 없으면 다음 기본:

| 스택 | 기본 명령 | 비고 |
|------|----------|------|
| Spring Boot (Gradle) | `./gradlew.bat compileJava -q` (Windows) 또는 `./gradlew compileJava -q` | gradlew 존재 우선 |
| Spring Boot (Maven) | `mvn -q compile` | |
| Vue/React/Angular | `npx tsc --noEmit` 또는 `npm run typecheck` | package.json scripts 우선 |
| Flutter | `flutter analyze --no-pub` | |
| Go | `go build ./...` | |
| Rust | `cargo check` | |
| Python | `mypy .` 또는 `python -m py_compile **/*.py` | mypy 설정 있을 때 우선 |
| unknown | (스킵 + 경고) | "스택 감지 실패 — 빌드 검증 생략" 표시 |

빌드 실패 시 차단 + 에러 메시지 출력.

### Step 3. Sprint Contract DoD 체크

Sprint Contract (`.claude/runtime/sprint-contract/SURINP-XXX.md`)가 있으면:
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
  - app-ha-back: `haback-build-resolver`
  - cs-back: (build-resolver 에이전트 없음 — 수동 해결)
  - cs-front: (build-resolver 에이전트 없음 — 수동 해결)
- `HARNESS_MODE=off`일 때는 이 스킬을 제안하지 않음
