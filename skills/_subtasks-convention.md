# `--subtasks` 모드 — Jira/Harness 스킬 공통 컨벤션

> **단일 출처(single source of truth)** — 모든 jira-* / harness-* 스킬이 본 문서를 참조.
> 본 문서를 수정하면 즉시 모든 스킬의 동작이 바뀐다.

## 1. `--subtasks` 모드란?

부모 Jira 이슈 1개 + 그 산하 하위 작업(sub-task) N개를 **한 묶음의 fan-out 단위**로 처리하는 모드.

진입 조건:
- 사용자가 명시적으로 `--subtasks` 플래그 전달 (예: `/jira-start STD-7 --subtasks`)
- 부모 이슈의 `subtasks` 필드에 하위 키 1개 이상 존재

진입 조건 미충족 시: 일반(부모만) 모드로 폴백. `--subtasks` 가 무의미한 단계도 일반 모드로 동작.

## 2. 핵심 원칙

1. **부모 = primary work item** — 모든 산출물(dev-guide, sprint-contract, verdict, commit) 은 부모 이슈에 귀속
2. **하위 = 트래킹 미러** — Jira 보드에서 하위 카드도 부모와 동일한 상태/진척을 반영해야 함 (PM/QA 가시성)
3. **하위 댓글은 짧게** — 1~3 줄, "부모 STD-N 의 일부로 X" 패턴. 산출물 본문은 부모에만 (노이즈 방지)
4. **transition 일관성** — 부모와 하위가 같은 상태로 동기화 (To Do → In Progress → QA → Done)
5. **실패 격리** — 하위 작업 중 1건이 실패해도 다른 하위 + 부모 작업은 계속. 실패는 출력 단계에서 사용자에게 보고

## 3. 스킬별 액션 매트릭스

| Skill | Parent action | Subtask action (`--subtasks` 시 추가) |
|-------|--------------|---------------------------------------|
| **jira-start** | In Progress 전환 + 댓글 + feature 브랜치 | **모든 하위** In Progress 전환 + 1줄 댓글 ("부모 `<KEY>` 일부로 시작 — 같은 브랜치 `feat/<KEY>` 공유") |
| **jira-clarify** | description 갱신 + Q&A | (선택) 각 하위 description 에 slice 컨텍스트 1~2 문단 추가 — Q&A 결과가 slice 별로 구분되는 경우만 |
| **jira-plan** | `docs/<KEY>-dev-guide.md` 작성 | slice dev-guide `docs/<KEY>-<sub>-dev-guide.md` 추가 작성 + 각 하위에 댓글 ("dev-guide: `<경로>`") |
| **jira-ingest** (forecast) | `INDEX.md` 에 부모 row 추가 (key=`<KEY>`, status=planned) + `LOG.md` forecast 1줄 | 각 slice 의 INDEX row 추가 (key=`<KEY>::<sub>`, parent=`<KEY>`) + LOG slice forecast 1줄/슬라이스. **하위 Jira 댓글 없음** (wiki 자산은 로컬 파일이라 Jira 노이즈 회피) |
| **jira-ingest** (closure) | INDEX row 갱신 (status=closed) + LOG closure + conditional cross-ref (ADR/sprint) | 각 slice INDEX row closed 갱신 + LOG slice closure. Conditional cross-ref 는 부모 한 번만 (slice 별 ADR ref 가 같으면 중복 회피) |
| **harness-plan** | `sprint-contract/<KEY>.md` | (산출물은 부모 contract 에 slice 별 DoD 인라인 — 하위 댓글 불필요. 단 verdict 미반영 시 사용자 알림) |
| **jira-execute** | Phase 0 scaffold + Agent Teams lead + 통합 빌드 + Phase 댓글 | **Agent Teams 모드** (worktree 미사용 — ADR-070 supersession). `TeamCreate({team_name:"STD-<PARENT>"})` + slice 마다 `TaskCreate` + `Agent({team_name, name:"slice-STD-<SUB>", ...})` spawn. teammate 가 자기 task `completed` 시 lead 가 하위에 1~3 줄 댓글 ("구현 완료 — 단위 테스트 N PASS, 자세히는 부모 `<KEY>`"). ⚠️ `Agent({isolation:"worktree"})` 단독 호출 = sub-agent 회귀 (TeamCreate/team_name/SendMessage 셋 다 누락) — 자세한 안티패턴은 `jira-execute/SKILL.md § 4A` ⚠️ 박스 참조. |
| **harness-review** | aggregate-verdict | slice 별 verdict 가 있으면 `aggregate-verdict/<KEY>-<sub>.md` 추가, 부모 verdict 에서 롤업 |
| **jira-test** | 통합 빌드/테스트 + 댓글 | (생략 OK — 통합 검증은 부모 산출물. 단 slice 별 단위 테스트 결과를 부모 댓글에 인용) |
| **jira-commit** | git commit + 댓글 | **모든 하위**에 commit SHA + 1줄 ("commit `<sha>` 에 통합 — 부모 `<KEY>` 댓글 참조") |
| **jira-complete** | QA 전이 + push + archive | **모든 하위** QA 전이 + 1줄 댓글 ("부모 `<KEY>` 와 동시 QA 전이. 통합 결과 + harness verdict 는 부모 댓글") |
| **wiki-lint** | corpus-scoped (전체 wiki 점검) | **N/A** — 본 스킬은 issue-scope 가 아니라 wiki 전체 검사. `--subtasks` 받아도 무시 + 1줄 경고 ("wiki-lint 는 corpus-scoped — `--subtasks` 무관") |

## 4. 표준 절차 (모든 스킬 공통)

```
IF "--subtasks" in args AND issue.subtasks 존재:
  1. parent 이슈 처리 (스킬 본래 절차)
  2. parent 이슈의 subtasks[] 추출 → [sub-key, ...]
  3. FOR each sub-key:
     - 위 매트릭스의 "Subtask action" 수행
     - 실패 시 누적 (하나 실패해도 다음 진행)
  4. 결과 출력에 parent + 하위별 결과 표 포함
ELSE:
  - 일반 모드 (parent 만 처리)
```

## 5. 댓글 템플릿

각 단계의 표준 하위 댓글 (한글, 2~3 줄):

**jira-start (하위)**:
```
🚀 부모 [PARENT-KEY] 의 일부로 작업 시작.
같은 feature 브랜치 `feat/<PARENT-KEY>` 공유, slice dev-guide 는 plan 단계 후 생성.
```

**jira-plan (하위)**:
```
📝 dev-guide 작성 완료: `docs/<PARENT-KEY>-<SUB-KEY>-dev-guide.md`
부모 `<PARENT-KEY>` 의 통합 가이드 (`docs/<PARENT-KEY>-dev-guide.md`) 와 함께 참고.
```

**jira-execute (하위, slice 완료 시점)**:
```
🔨 구현 완료. 단위 테스트 N PASS.
통합 검증 + harness verdict 은 부모 `<PARENT-KEY>` 댓글 참조.
```

**jira-commit (하위)**:
```
✅ commit `<SHA>` 에 통합 (부모 `<PARENT-KEY>` 와 동일 commit, 5 slice 묶음).
변경 파일 + 검증 결과는 부모 댓글 참조.
```

**jira-complete (하위)**:
```
✅ 부모 `<PARENT-KEY>` 와 동시 QA 전이.
통합 결과 + harness verdict + archive 경로는 부모 댓글 참조.
```

## 6. 실패 처리

- **부모 처리 실패** → 즉시 중단 (하위는 손대지 않음)
- **하위 1건 실패** → 다음 하위 계속, 출력 단계에서 사용자에게 ❌ 표시 + 사유 명시
- **transition 권한 부족** → 댓글만 추가하고 계속 (하위 transition 실패 → 부모 ✅)
- **subtasks 필드가 비어있음** → 일반 모드로 폴백 + 안내 메시지

## 7. harness-workflow 의 flag 전파

`harness-workflow <KEY> --subtasks` 호출 시:

```
모든 자식 Skill 호출에 --subtasks 자동 부착:
  Skill(jira-start, "<KEY> --subtasks")
  Skill(jira-clarify, "<KEY> --subtasks")
  Skill(jira-plan, "<KEY> --subtasks")
  Skill(harness-plan, "<KEY> --subtasks")
  Skill(jira-execute, "<KEY> --subtasks")
  Skill(harness-review, "<KEY> --subtasks")
  Skill(jira-test, "<KEY>")          # 통합 검증 — flag 불필요
  Skill(harness-gate, "<KEY>")       # 통합 게이트 — flag 불필요
  Skill(jira-commit, "<KEY> --subtasks")
  Skill(jira-complete, "<KEY> --subtasks")
```

`workflow-state.json` 에 `subtasks_mode: true` + `subtasks: [...]` 기록 → 중간 재개 시에도 모드 보존.

**Wiki chain 자동 전파** (jira-ingest / wiki-lint 는 harness-workflow 가 직접 호출하지 않음 — 부모 스킬 안의 자동 chain):
- `jira-plan` §6 → `jira-ingest` forecast 호출 시 `--subtasks` 자동 전파
- `jira-complete` §4.4 → `jira-ingest` closure 호출 시 `--subtasks` 자동 전파
- `jira-complete` §4.7 → `wiki-lint` 호출 — `--subtasks` 무관 (corpus-scoped)

## 8. 사후 보정 (이미 누락된 경우)

부모 이슈가 이미 QA 인데 하위가 To Do 그대로 남은 상황 (구버전 스킬로 작업) — 다음 단계로 보정:

```
1. 부모 이슈의 subtasks 조회
2. 각 하위:
   - 현재 상태 확인 (To Do / In Progress / QA)
   - 부모 상태에 맞춰 transition 일괄 적용 (To Do → In Progress → QA 등 다단계)
   - 짧은 보정 댓글 추가 ("사후 보정 — 부모 <KEY> 와 동기화")
3. 사용자에게 보정 결과 표 출력
```

---

**Last Updated**: 2026-05-14 (jira-ingest forecast/closure 행 + wiki-lint 행 추가 — Karpathy LLM Wiki 패턴 도입. wiki-lint 는 corpus-scoped 라 `--subtasks` N/A. § 7 에 wiki chain 자동 전파 규칙 추가)

**Previous**: 2026-05-13 (jira-execute § "--subtasks Mode" 를 Agent Teams 기반으로 재작성 — worktree 4분기 패턴 supersede)
**Previous**: 2026-05-07 (STD-7 작업 후 신설 — 8 jira-* + harness-workflow 의 `--subtasks` 일관 처리 위해)
