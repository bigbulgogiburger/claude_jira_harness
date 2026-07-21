---
name: harness-workflow
description: "Jira 이슈 풀사이클 유일 진입점 — start(브랜치+In Progress)→grill(요구 명확화)→plan(dev-guide)→contract→[compile]→execute(dynamic Workflow 레인 / unattended 러너)→review(fan-out+Codex)→gate(테스트+DoD+커밋)→complete(QA 전이+closure ingest)를 자동 시퀀싱. '/harness-workflow', 'harness workflow', '전체 워크플로우', '이슈 전체 진행', '풀사이클', '이슈 시작해줘', '작업 시작', '브랜치 만들어줘', '티켓 잡아줘', '테스트 돌려줘', '커밋해줘', 'DoD 체크', '이어서 작업', '이전 작업 복원' 요청 시 사용 (구 /jira-start·/jira-clarify·/jira-test·/jira-commit·/harness-resume 는 2026-07-20 폐기 — 전부 이 워크플로의 내부 단계)."
---

# /harness-workflow — 통합 오케스트레이터 (유일 진입점)

> **직교 원칙**: 유지되는 Jira/Harness 스킬은 수정하지 않고 `Skill()` 로 호출. 상세 절차는 단계 진입 시에만 `references/<단계>.md` 를 Read (lazy-load 를 단계 레벨까지 연장).
> **폐기된 단독 명령** (2026-07-20, harness v2 설계 §3·ADR-106): `/jira-start` `/jira-clarify` `/jira-test` `/jira-commit` `/harness-resume` — 사용자가 이 이름으로 요청하면 해당 **단계만** 이 워크플로 절차로 수행하면 된다 (풀사이클 강제 아님).

## Usage

```
/harness-workflow <KEY>                # 단일 이슈 (BE+FE 걸치면 자동 2레인)
/harness-workflow <KEY1> <KEY2> ...    # 다중부모 fan-out (worktree 격리 — references/parallel-modes.md)
```

## ⛔ Guard — HARNESS_MODE (최우선)

`HARNESS_MODE` 확인: `suggest`/`auto` 면 진행, 미설정/빈값/`off` 면 안내 후 중단. 정책 SSoT: `~/.claude/skills/_harness-guard.md` (**`Skill()` 호출 금지** — Read 또는 env 직접 확인).

## 단계 결정표

| # | 단계 | 하는 일 | 상세/호출 | 산출물 | 게이트 |
|---|------|---------|-----------|--------|--------|
| ① | start | 이슈 조회·브랜치·assignee·In Progress | `references/start.md` | `feat/<KEY>` 브랜치 | — |
| ② | grill | 요구·결정사항 확정 (모호할 때만, 한 번에 한 질문) | `Skill('grilling')` + `references/clarify.md` (사전 크롤링) | 확정 결정 목록 | 이슈가 이미 구체적이면 skip |
| ③ | plan | recon → dev-guide 생성 (+ ingest forecast 자동 chain) | `Skill('jira-plan', <KEY>)` **필수 — 우회 금지** (§6 forecast 발화) | `docs/<KEY>-dev-guide.md` | INDEX.md cross-ref 선조회 (ALWAYS) |
| ④ | contract | DoD·Verify Targets·인간게이트 명시 | `Skill('harness-plan', <KEY>)` | `.claude/runtime/sprint-contract/<KEY>.md` | — |
| — | **승인** | dev-guide+contract 요약 제시 | — | — | **사용자 승인 필수** (수정 요청 시 ③ 복귀) |
| ⑤ | compile | (opt-in) dev-guide → step 컴파일 | `Skill('jira-compile', <KEY>)` — 대형 이슈·무인 실행 시에만 | `phases/<KEY>/index.json` + `step*.md` | 소형 이슈는 skip (러너는 opt-in) |
| ⑥ | execute | 구현 | attended: dynamic Workflow 레인 (`references/parallel-modes.md` — 모든 `agent()` 에 `opts.model`, 스모크 프로브) / unattended: `harness-execute.py` 러너 | 코드 + step summary | blocked/error 시 인간 개입 |
| ⑦ | review | fan-out 전문 리뷰 + Codex adversarial (`scripts/codex-review.sh` 래퍼) | `Skill('harness-review')` | `.claude/runtime/aggregate-verdict.md` | PASS→⑧ / ITERATE(≤3)→수정 후 재리뷰 / ESCALATE→재계획 |
| ⑧ | gate | 테스트+빌드 GREEN → DoD → 커밋 → Jira 댓글 | `references/gate.md` + `Skill('harness-gate')` | commit SHA | **review-gate hook 이 verdict≠PASS commit 물리 차단** (JSON deny) |
| ⑨ | complete | QA 전이 + push + closure ingest + wiki-lint | `Skill('jira-complete', <KEY>)` **필수 — 우회 금지** (§4.4/4.6/4.7 chain 발화) | INDEX row closed·LOG append | — |

**Phase 반복**: contract 의 Phase 수만큼 ⑥→⑦ 을 Phase 단위로 반복 (Inner Loop 는 같은 Phase 안에서만 — Phase 간 blocker 는 ESCALATE).

## 병렬 모드 (fan-out 표준 = dynamic Workflow)

- **모드 결정**: 부모 키 2개 이상 → 다중부모 fan-out / 단일 이슈 BE+FE → 2레인. 두 모드 모두 `references/parallel-modes.md` 가 SSoT.
- **Agent Teams 신규 사용 금지** (실측 결함 4건 — LOG 228·632, CHANGELOG 116·235). 구 `--subtasks` 정식 모드(ADR-070)는 표면 제거 — Jira 하위이슈가 있으면 댓글/전이만 부모와 함께 처리하고, 병렬 실행 단위는 위 2모드로 판단.
- 모델 티어링(메인=fable): fable=orchestration·verify·크로스레인 seam / opus=난이도 상 / sonnet=중·하. 규칙 3개(전 `agent()` model 명시·스모크 프로브·fable 레인 사유 필수)는 `references/parallel-modes.md`.

## 재개 (구 /harness-resume 폐기)

중단된 작업 재개 = 상태 파일 읽고 이어가기 한 줄:
1. `phases/<KEY>/index.json` 있으면 첫 `pending` step 부터 (러너/컴파일 이슈).
2. 없으면 `.claude/runtime/workflow-state.json`(이슈별 임시 산출물) + `sprint-contract/<KEY>.md` + 최신 `aggregate-verdict.md` 를 Read 후 결정표의 해당 단계부터 재개.
3. Jira 상태는 건드리지 않는다 (이미 ① 이 처리).

## 에러 핸들링

| 에러 | 처리 |
|------|------|
| 브랜치 충돌 | 사용자 알림, 수동 해결 후 재시도 |
| 빌드 실패 | 프로젝트 build-resolver 에이전트 제안 |
| 리뷰 에이전트 미존재 | 해당 축 스킵 + 경고 |
| Codex 래퍼 exit 42 | opus skeptic workflow 자동 폴백, verdict 에 `codex=fallback(<사유>)` |
| 3회 ITERATE 동일 blocker | ESCALATE → 재계획 제안 |

## HARNESS_MODE 동작

| 모드 | 동작 |
|------|------|
| `auto` | 전체 자동 진행, 승인 게이트만 수동. review-gate 가 commit 물리 차단 |
| `suggest` | plan/review/gate 단계마다 사용자 확인. review-gate 는 경고만 |
| `off` | 워크플로 호출은 동작하나 hook 비활성 |

## 자기 점검 (종료 직전)

`docs/INDEX-SCHEMA.md` 존재 시 — ③ ingest forecast + ⑨ closure ingest + wiki-lint summary 호출 흔적이 대화에 모두 있어야 함. 누락 감지 → 즉시 일괄 호출 + 사용자 보고.
