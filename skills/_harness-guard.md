# _harness-guard.md — HARNESS_MODE 진입 가드 (SSoT)

> harness-* 스킬 7종이 공유하는 진입 가드의 단일 출처(SSoT).
> 각 스킬은 본문 Guard 섹션에 **1줄 참조**만 두고, 정책은 여기서 관리한다.
> `_subtasks-convention.md` / `_wiki-schema.md` 와 동일한 위상의 공통 규약 파일.

## 가드 규칙

harness-* 스킬은 **모든 단계보다 먼저** `HARNESS_MODE` 환경변수를 확인한다:

| HARNESS_MODE 값 | 동작 |
|-----------------|------|
| 미설정 / 빈값 / `off` | **즉시 중단**. 사용자에게 알림: "⛔ 이 프로젝트는 Harness가 설정되지 않았습니다 (HARNESS_MODE=$HARNESS_MODE). `/jira-*` 워크플로우를 사용하세요." 출력 후 **이후 단계를 절대 실행하지 않는다.** |
| `suggest` / `auto` | 정상 진행 |

## 적용 범위

| 스킬 | 가드 |
|------|------|
| harness-plan / harness-gate / harness-review / harness-resume / harness-score / harness-shadow / harness-workflow | ✅ 적용 |
| **harness-setup** | ❌ 미적용 — Harness 를 **설정하는** 스킬이라 `off`/미설정 상태에서 진입하는 게 정상 |
| jira-* / wiki-lint / jira-ingest | ❌ 미적용 — Harness 와 직교(orthogonal). HARNESS_MODE 무관하게 동작 |

## 참조 방법

각 harness-* 스킬은 Guard 섹션에 다음 1줄만 둔다:

```markdown
## ⛔ Guard — HARNESS_MODE 확인 (최우선)

> 이 스킬의 모든 단계보다 **먼저** 실행. SSoT: `~/.claude/skills/_harness-guard.md` — `HARNESS_MODE` 가 미설정/빈값/`off` 면 즉시 중단(안내 출력 후 이후 단계 실행 금지), `suggest`/`auto` 면 정상 진행.
```

정책을 바꿀 때는 **본 파일만 수정**하면 7개 스킬에 일괄 반영된다 (과거엔 7곳을 글자 단위로 복붙·동기화해야 했음 — SSoT 위반).

## 변경 이력

- **2026-06-09**: 신설. 7개 harness-* 스킬에 복붙돼 있던 동일 9줄 Guard 블록을 단일 SSoT 로 추출 + 각 스킬을 1줄 참조로 교체.
