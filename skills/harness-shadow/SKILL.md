---
name: harness-shadow
description: "Shadow run 프로토콜 — HARNESS_MODE=off로 baseline Claude만의 리뷰와 Harness full-run을 비교하여 counterfactual lift를 측정합니다. 5개 이슈 중 1개 권장 주기. Harness가 baseline을 능가하는지 경험적 증거 수집. '/harness-shadow', 'harness shadow', 'shadow run', 'counterfactual lift', 'baseline 비교' 요청 시 사용."
---

# /harness-shadow — Counterfactual Lift 측정 프로토콜

> **존재 이유**: "Harness가 baseline Claude 대비 추가 가치를 내는가?" 를 경험적으로 증명.
> Baseline이 이미 80% 잡는다면 Harness는 15~20% lift만 추가 → 비용 정당화 어려움.
> Baseline이 40% 잡는다면 Harness가 90% 잡을 때 큰 가치.
> **이 측정 없이는 Harness ROI 주장이 공허**.

## ⛔ Guard — HARNESS_MODE 확인 (최우선)

> 이 스킬의 모든 단계보다 **먼저** 실행. SSoT: `~/.claude/skills/_harness-guard.md` — `HARNESS_MODE` 가 미설정/빈값/`off` 면 즉시 중단(안내 출력 후 이후 단계 실행 금지), `suggest`/`auto` 면 정상 진행.

---

## 실행 전제

이 스킬은 **정상 `/harness-workflow` 완료 전**에 호출해야 한다. 시나리오:
1. 사용자가 PROJ-999 시작 → 5번째마다 shadow 지정
2. `/harness-shadow PROJ-999` 먼저 실행 → baseline 리뷰 수집
3. 그 후 `/harness-workflow` 또는 `/harness-review` 정상 실행
4. 두 결과를 비교하는 메타 파일 생성

**절대 금지**: baseline과 Harness를 **동일 세션에서** 연달아 돌리는 것. Context contamination. 세션을 분리하거나 `/clear` 후 실행해야 함.

## 절차

### Step 1. 사전 조건 확인

```bash
# 현재 HARNESS_MODE 확인
grep HARNESS_MODE .claude/settings.local.json

# 이미 aggregate-verdict.md가 있는가?
ls .claude/runtime/aggregate-verdict.md 2>/dev/null
```

- 이미 aggregate-verdict.md가 있으면: "⚠️ 이미 Harness 리뷰가 완료됨. Shadow는 Harness 이전에 실행해야 함. 새 이슈를 택하거나 /clear 후 재시도."
- 없으면: Step 2로

### Step 2. HARNESS_MODE 임시 override

이 스킬 내에서는 environment 변수를 세션에 전달하지 않고, **메인 세션이 harness 스킬을 절대 호출하지 않는 것**으로 시뮬레이트한다.

사용자에게 명시 안내:
```
════════════════════════════════════════
  Shadow Run Mode Active

  다음 단계에서는 /harness-plan, /harness-review를
  절대 호출하지 마세요. Baseline Claude만으로 리뷰합니다.

  사용 가능: /jira-plan, /jira-execute, 그리고 baseline 방식의 테스트·커밋 직접 수행
            (구 /jira-test·/jira-commit 은 2026-07-20 폐기 — harness-workflow gate 단계로 흡수)
  금지: /harness-plan, /harness-review, /harness-gate
════════════════════════════════════════
```

### Step 3. Baseline 리뷰 수집

메인 세션이 `git diff`와 dev-guide.md만 보고 자체적으로 리뷰 수행 (에이전트 위임 없이):

1. Goal 파악 (dev-guide의 Acceptance Criteria 기반)
2. `git diff` 확인
3. Blocker / Advisory 후보를 메인 세션이 직접 판단 (에이전트 호출 금지)
4. 판단 이유는 dev-guide와 CLAUDE.md의 Key Rules만 기반으로

### Step 4. Baseline Verdict 작성

`.claude/runtime/baseline-verdict.md`로 저장 (**aggregate-verdict.md와 동일 스키마**):

```markdown
# Baseline Verdict — PROJ-XXX Phase N (Shadow Run)

<!-- Metadata -->
- **Issue**: PROJ-XXX
- **Phase**: N
- **Mode**: baseline (HARNESS_MODE=off emulated)
- **Ran At**: YYYY-MM-DDTHH:MM:SSZ
- **Duration**: Xm Ys
- **Tokens (approx)**: ~Xk (baseline은 보통 Harness 대비 30~50% 토큰)
- **Reviewer**: main session (no project agents)
- **Shadow Pair**: aggregate-verdict-shadow.md (대응 Harness run)

<!-- Body: Blockers/Advisories (baseline이 찾은 것) -->
## Blockers
| ID | 위치 | 요지 |
|---|---|---|
| B-BL1 | ... | ... |

## Advisories
| ID | 요지 |
|---|---|
| B-A1 | ... |
```

### Step 5. 사용자 안내: Harness run 실행

```
════════════════════════════════════════
  Baseline 완료. 이제 Harness full-run을 실행:

  권장: 새 세션에서 /harness-workflow PROJ-XXX
  (같은 세션에서 돌리면 baseline에서 본 내용이 Harness 추론을 오염시킴)

  두 verdict가 모두 준비되면:
    → /harness-shadow compare PROJ-XXX
════════════════════════════════════════
```

### Step 6. Compare 모드 (두 verdict 준비 후)

`/harness-shadow compare PROJ-XXX` 호출 시:

1. baseline-verdict.md 읽기
2. aggregate-verdict.md 읽기 (archive에서라도)
3. Blocker/Advisory를 diff하여 분류:
   - **Both**: 둘 다 찾음 (Harness 필요 없음 영역)
   - **Harness only**: Harness만 찾음 (positive lift)
   - **Baseline only**: Baseline만 찾음 (Harness의 miss)
4. 비교 파일 `.claude/runtime/shadow-comparison-PROJ-XXX.md` 작성:

```markdown
# Shadow Comparison — PROJ-XXX

## Participants
- Baseline: .claude/runtime/baseline-verdict.md (tokens ~30k, duration 2m)
- Harness: .claude/runtime/archive/PROJ-XXX/aggregate-verdict.md (tokens ~85k, duration 6m)

## Overlap Matrix

| Category | Count | IDs |
|---|---|---|
| Both (same finding) | 2 | REV-001≈B-BL1, JQA-1≈B-BL2 |
| Harness only (lift) | 1 | DTS-1 (domain trap — baseline 놓침) |
| Baseline only (miss) | 0 | — |

## Lift Score
- **Harness-only findings**: 1 / 3 total = **33% lift**
- **Harness-only Blockers**: 1 → 만약 post-merge에서 VALID 판정 시 실질 lift 확정

## Cost Ratio
- Harness tokens: ~85k
- Baseline tokens: ~30k
- Ratio: 2.8× cost → 1 추가 catch 당 cost: ~55k tokens
- **평가**: 단일 Blocker catch 당 $X 값어치인가? 팀 기준으로 판단.

## Next
→ 머지 7일 후 /harness-score 실행
→ Both 항목은 "Harness 불필요" 카운트에 들어감
→ Harness-only VALID 카운트가 실질 lift
```

### Step 7. Metrics 통합

비교 결과를 `.claude/runtime/harness-metrics/scorecard.md`에 shadow 섹션으로 append.

---

## 운영 빈도

- **초기 (첫 4주)**: 5 이슈 중 1개 (20%)
- **안정화 후**: 분기당 3~5회 (약 5~10%)
- **모델 변경 시**: 즉시 1회 (Opus → Sonnet 교체 등)

## 절대 금지

- 같은 세션에서 baseline + Harness 연달아 실행 (contamination)
- Harness가 이미 완료된 이슈에 대해 "retroactive baseline" 만들기 (자기기만)
- Baseline 리뷰에 프로젝트 도메인 에이전트 호출 금지. 구체적으로는 `.claude/agents/` 안에 등록된 모든 프로젝트 에이전트(예: `haback-*`, `cs-*`, `csfront-*`, `app-*`, 또는 임의의 `{prefix}-*` 접두사) 및 글로벌 reviewer/auditor/sentinel 계열 에이전트 호출이 금지된다. baseline은 **메인 세션의 추론 + git diff + dev-guide + CLAUDE.md만**으로 작성해야 lift 측정의 의미가 살아난다. 새 프로젝트에서 어떤 prefix를 쓰든 이 룰은 동일하게 적용된다.

## 출력 상한

요약 반환 500 토큰 이하. 상세 비교는 파일로만.
