---
name: harness-score
description: "Post-merge VALID/INVALID 채점 — 머지 후 7일 이상 경과한 이슈의 aggregate-verdict.md에 사후 평가를 기록합니다. Harness의 catch rate/false positive rate 측정에 사용. 자기 채점 편향 방지를 위해 별도 세션에서 외부 증거와 함께 수행."
triggers:
  - "/harness-score"
  - "harness score"
  - "사후 평가"
  - "post-merge scoring"
  - "catch rate 측정"
---

# /harness-score — Post-merge VALID/INVALID 채점 에이전트

> **존재 이유**: Harness가 실제로 유효한 catch를 내고 있는지 검증.
> n≥5 쌓이면 Catch rate / False positive rate 계산 → 살림/축소/폐기 결정 가능.
> **원칙**: 외부 증거 없는 VALID 금지. 작업 직후 채점 금지. 별 세션에서만.

## ⛔ Guard — HARNESS_MODE 확인 (최우선)

> 이 스킬의 모든 단계보다 **먼저** 실행. SSoT: `~/.claude/skills/_harness-guard.md` — `HARNESS_MODE` 가 미설정/빈값/`off` 면 즉시 중단(안내 출력 후 이후 단계 실행 금지), `suggest`/`auto` 면 정상 진행.

---

## 절차

### Step 1. 대상 이슈 확인

사용자가 인자로 이슈 키 전달 (예: `/harness-score PROJ-190`). 없으면 `.claude/runtime/archive/` 디렉토리에서 가장 최근 아카이브 이슈 제시.

### Step 2. 머지 시점 확인 (7일 게이팅)

```bash
git log --all --pretty=format:"%H %ci %s" | grep -i "PROJ-XXX\|feature/PROJ-XXX" | head -5
```

머지 커밋의 committer date 추출. 현재 시각과 비교:
- **경과일 < 7일**: "⏰ 머지 후 7일 미만. {N}일 더 기다린 후 채점하세요. (현재: M일 경과)"
  → 중단
- **경과일 ≥ 7일**: Step 3으로 진행

### Step 3. aggregate-verdict.md 로드

경로 탐색 순서:
1. `.claude/runtime/archive/PROJ-XXX/aggregate-verdict.md` (머지된 이슈는 보통 여기)
2. `.claude/runtime/aggregate-verdict.md` (archive 전)

파일의 Metadata + Blockers + Advisories 추출.

### Step 4. Blocker 별 VALID/INVALID 채점

사용자에게 각 Blocker마다 다음 질문:

```
[ID: REV-001] cs-reviewer — getRepairRequestsForCustomer 고객 경로 침범
   요지: ...

이 blocker는 실제로 유효했습니까?
  1) VALID — 머지되지 않았다면 실제 영향 있었을 것 (+ 외부 증거)
  2) INVALID — false positive, 불필요한 수정이었음
  3) UNCERTAIN — 판단 불가 (피해야 함, 노력 필요)

외부 증거 (필수, VALID 선택 시):
  - Prod 로그 URL / grep 결과:
  - 관련 Jira 버그 티켓:
  - 수정 commit SHA:
  - 기타 증거 파일 경로:
```

**게임 방지 규칙**:
- UNCERTAIN은 "상한 20%" — 5개 중 1개 이상 UNCERTAIN이면 재고 요청
- VALID 선택 시 외부 증거 경로 필수 (빈 필드 금지)
- 작업자 본인이 아닌 다른 팀원이 채점하는 것이 이상적 (1인 개발 시에는 시간 격리 7일이 mitigation)

### Step 5. Advisory 별 Actioned/Ignored 채점

```
[ID: REV-A1] cs-reviewer — excel-download 엔드포인트 @Parameter 누락

이 advisory는:
  1) ACTIONED — 후속 commit/PR에서 실제로 수정
  2) IGNORED — 의도적으로 무시 (합리적 이유 있음)
  3) FORGOTTEN — 보지 못해서 놓침 (→ advisory가 불명확하거나 우선순위 낮음)

증거 (ACTIONED 시):
  - 수정 commit SHA:
```

### Step 6. 규제 질문

```
Q1. 머지 이후 이 이슈와 관련된 Regression 버그가 발생했습니까? (Y/N)
    관련 티켓:
Q2. 머지 이후 Production 장애/인시던트가 있었습니까? (Y/N)
    관련 포스트모템:
```

### Step 7. aggregate-verdict.md 업데이트 (Post-merge Scoring 섹션)

`## Post-merge Scoring` 섹션을 **Edit으로 교체**:

```markdown
## Post-merge Scoring
- **Scored At**: YYYY-MM-DDTHH:MM:SSZ
- **Scored By**: (사용자명 or 'self-scored with 7-day gating')
- **Days After Merge**: N일
- **Blocker Results**:
  | ID | Status | Evidence |
  |---|---|---|
  | REV-001 | VALID | commit abc1234 (fix), Jira BUG-XXX |
  | REV-002 | INVALID | 실제로는 기존 패턴과 동등, false positive |

- **Advisory Results**:
  | ID | Actioned? | Evidence |
  |---|---|---|
  | REV-A1 | ACTIONED | commit def5678 |
  | REV-A2 | IGNORED | 의도: 이번 스코프 외 (기획 결정) |
  | REV-A3 | FORGOTTEN | (개선 필요) |

- **Regression filed?**: N
- **Production incident linked?**: N
- **Catch rate (this issue)**: 50% (1 VALID / 2 Blockers)
- **FP rate (this issue)**: 50% (1 INVALID / 2 Blockers)
- **Advisory uptake**: 33% (1 ACTIONED / 3 Advisories)
```

### Step 7.5. INDEX.md Merge 메타 Backfill

`.claude/runtime/archive/INDEX.md`에서 채점 대상 이슈의 행을 찾는다. `Merged` 컬럼이 `(pending)` 또는 비어있으면 git log로 backfill한다:

```bash
# 머지 commit + committer date 추출
git log --all --pretty=format:"%H %ci" --grep="Merge branch 'feature/<ISSUE-KEY>'" | head -1
```

추출 결과로 INDEX.md의 해당 행 `Merged` 컬럼을 `YYYY-MM-DD (<short-sha>)` 형식으로 Edit. 머지 commit이 없으면(아직 미머지) 그대로 두고 경고만 출력.

**왜 여기서 하나**: jira-complete은 머지 전이라 SHA/date를 모르고, harness-score는 정확히 7일 후 채점 시점에 호출되므로 git log에 머지 commit이 확실히 있다. 이 단계로 archive lifecycle의 머지 메타 빈칸이 자연스럽게 채워진다.

### Step 8. Scorecard 집계 트리거

Write 후 `.claude/runtime/harness-metrics/scorecard.md`가 있으면 "새 데이터 추가됨" 알림. 수동 집계 스크립트:
```bash
bash .claude/runtime/harness-metrics/aggregate.sh
```
(있는 경우에만 실행 권장)

### Step 9. 사용자 요약 출력

```
════════════════════════════════════════════
  Post-merge Scoring Complete — PROJ-190

  Blockers:   1 VALID / 1 INVALID (n=2)
  Advisories: 1 ACTIONED / 2 not actioned (n=3)
  Regression: N
  Incident:   N

  → aggregate-verdict.md 갱신 완료
  → 누적 scorecard 업데이트 필요 시 aggregate.sh 실행
════════════════════════════════════════════
```

---

## 절대 금지

- 작업 직후(머지 후 7일 미만) 채점 금지 — 편향 위험
- 외부 증거 경로 없이 VALID 마킹 금지
- aggregate-verdict.md의 Metadata/Blockers/Advisories 섹션 **수정 금지** (Post-merge Scoring 섹션만 Edit)
- 이 스킬 실행 중 원본 코드 수정 금지 (Read-only + scorecard Write만)

## 출력 상한

요약 반환은 500 토큰 이하. 상세는 aggregate-verdict.md에 기록.
