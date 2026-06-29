---
name: jira-execute
description: "jira-execute — docs/<ISSUE-KEY>-dev-guide.md를 읽고 스택 최고 개발자 페르소나로 실제 구현을 진행합니다. 병렬 작업 가이드가 있으면 Agent Teams로 병렬 개발을 수행합니다. 구현 단계에서, '구현해줘', '실행해줘', '코드 작성해줘', 'Phase 진행', 'dev-guide대로 개발', 'jira execute', '개발 시작' 등의 요청에 이 스킬을 사용하세요. /jira-plan 이후, /jira-test 이전에 사용합니다."
---

# jira-execute — 개발 가이드 기반 구현 실행

개발 가이드 MD 파일을 읽고, 스택 최고 개발자 페르소나로 실제 구현을 진행합니다.
MD에 병렬 작업 가이드가 있으면 background teammate(병렬 Agent)를 spawn하여 병렬 개발을 수행합니다.
지라에 댓글이나 설명을 작성할 때에는 한글로 작성합니다.

## Usage

```
/jira-execute <ISSUE-KEY>
```

- `ISSUE-KEY`: Jira 이슈 키 (예: SURINP-156)
- `docs/<ISSUE-KEY>-dev-guide.md` 파일이 존재해야 함 (`/jira-plan`으로 생성)

## Procedure

### 1. 개발 가이드 MD 로드 및 검증

**1-1. MD 파일 읽기**
```
docs/<ISSUE-KEY>-dev-guide.md
```

파일이 없으면:
```
❌ 개발 가이드를 찾을 수 없습니다.
먼저 /jira-plan <ISSUE-KEY> 를 실행하세요.
```

**1-2. 가이드 구조 검증**

필수 섹션 확인:
- `## 1. 요구사항 요약` — 인수조건 존재
- `## 2. 영향 범위 분석` — 수정 대상 파일 목록 존재
- `## 3. 구현 계획` — Phase가 1개 이상

누락된 섹션이 있으면 경고 후 진행 가능한 범위에서 실행.

### 2. 스택 감지 및 페르소나 활성화

작업 디렉토리에서 프로젝트 스택을 자동 감지하고 페르소나를 활성화합니다 — 감지 매핑 + 스택별 페르소나는 `~/.claude/skills/_stack-detection.md` §1 + §2 참조.

### 3. 실행 모드 결정

MD 파일의 `## 5. 병렬 작업 가이드` 섹션 존재 여부로 실행 모드를 결정합니다.

```
IF "## 5. 병렬 작업 가이드" 섹션 존재 AND "Agent Teams 구성" 테이블 존재:
  → 병렬 모드 (§ 4A 진입 → 환경 분기: Agent Teams / § 4A-FB sub-agent / § 4B 순차)
ELSE IF "--subtasks" 플래그 AND 부모 이슈에 하위 작업 존재:
  → 병렬 모드 (§ 4A 진입 → 환경 분기) — slice 마다 1 워커
ELSE:
  → 순차 실행 모드 (Step 4B)
```

> **자동 트리거**: dev-guide § 5 의 "Agent Teams 구성" 표가 있으면 사용자 추가 확인 없이 Step 4A 진입. 진입 시점에 두 줄 출력:
> ```
> 🧑‍🤝‍🧑 Agent Teams 모드 진입 — N teammate spawn 예정
> ⚠️  Token cost ≈ 단일 세션 × 3-7 (공식 문서 기준). 중단하려면 Ctrl+C
> ```

> **`/resume` 제약** (공식 limitation): in-process teammate 는 `/resume` 후 복원 안 됨. 도중 종료 시 lead 가 새 teammate 다시 spawn. `harness-resume` 도 동일.

> **사전 조건 (필수)**: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` 가 settings.json 또는 환경변수에 있어야 함. 없으면 § 4A 실행 자체가 실패하므로, Step 4A 진입 직전 1회 확인:
> ```bash
> grep -q "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS" ~/.claude/settings.json "$CLAUDE_PROJECT_DIR/.claude/settings.local.json" 2>/dev/null \
>   || echo "❌ Agent Teams 비활성 — settings.json 에 CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 추가 필요"
> ```
> 미설정 시 § 4B 순차 모드로 폴백.

### 4A. 병렬 실행 모드 (Agent Teams) — **operational**

> **🧭 환경 분기 (진입 시 최우선) — § 4A / § 4A-FB / § 4B**:
> Agent Teams(teammate self-claim + SendMessage 협업)는 **interactive `claude` 터미널(TUI) 전용**이다. SDK/통합앱/CI/비대화형 환경에서는 미지원 — 직접 `Agent()` 가 항상 sub-agent 로 떨어진다(Task 도구 없음, 실측 확인).
> - **§ 4A (Agent Teams)**: interactive TUI + 협업(contract 합의·적대 검토)이 필요할 때.
> - **§ 4A-FB (sub-agent fan-out)**: Agent Teams 미지원 환경(SDK/통합앱/CI) + disjoint files 병렬. lead 가 결과 회수.
> - **§ 4B (순차)**: 의존성 많거나 단순.
>
> **확신이 없으면 § 4A-FB 로 가라**: sub-agent fan-out 은 interactive·SDK 어느 환경에서나 동작한다(협업만 불가). 협업(contract 합의·적대 검토)이 **꼭** 필요할 때만 사용자에게 "interactive `claude` 터미널인가" 확인 후 § 4A. (§ 3 의 `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` 확인과 중복 판별하지 않는다.)

> **spawn 은 자연어, 관리는 도구.** v2.1.178+ 에서 teammate 는 lead 가 **자연어로 spawn 요청**하면 런타임이 팀 컨텍스트로 띄웁니다(사용자 승인 경유). lead 가 `Agent({...})` 를 **직접 도구 호출하면 sub-agent 로 떨어져** Task self-claim·팀 메일박스가 동작하지 않습니다(아래 ⚠️ 박스 + 실측 확인됨). 반면 task 관리(`TaskCreate`/`TaskUpdate`)와 메일박스(`SendMessage`)는 lead 의 명시 도구 호출입니다.

> ## ⚠️ Sub-agent 회귀 안티패턴 차단 (모델 자가 점검 필수)
>
> **v2.1.178 부터 `TeamCreate`/`TeamDelete` 도구는 제거됐고, 팀은 첫 teammate spawn 시 세션에서 자동 형성됩니다** (`team_name` 은 무시됨). 하지만 teammate 와 sub-agent 는 **여전히 다른 메커니즘**입니다 — 이름이 비슷해 자주 혼동되니 주의. teammate 는 공유 Task list 에 참여(self-claim)하고 SendMessage 로 양방향 통신하지만, sub-agent 는 결과만 단방향으로 lead 에 회수합니다(Task 도구 없음 — 실측 확인). 회귀란 **협업 teammate 가 필요한데 lead 가 `Agent({...})` 를 직접 도구 호출해 sub-agent 로 결과만 받는 것**입니다.
>
> **⚠️ 적용 범위**: 이 박스는 **§ 4A(협업 teammate)를 의도할 때만** 적용된다. § 4A-FB(Agent Teams 미지원 환경의 **의도적** sub-agent fan-out)·§ 4B 는 정상 경로이며 아래 STOP 신호가 적용되지 않는다 — 거기선 `Agent()` 직접 호출·`isolation:"worktree"` 가 올바른 동작이다.
>
> **회귀 신호 (§ 4A 를 의도할 때) — 1개라도 보이면 STOP**:
> 1. teammate 가 필요한데 `Agent({...})` 를 **직접 도구 호출**해서 결과만 회수 (자연어 spawn 경로 미사용 → sub-agent)
> 2. spawn 된 워커가 `TaskList`/`TaskUpdate` 로 self-claim 을 못 함 (= sub-agent. teammate 는 Task 도구 보유)
> 3. 팀원 간 `SendMessage` 협의 없이 lead 가 모든 걸 중개 (= sub-agent 단방향)
> 4. `isolation: "worktree"` 로 워커 격리 → 단일 워킹트리 disjoint-files 협업 불가 (sub-agent 성격)
> 5. 공유 Task list (lead 의 `TaskCreate`/`TaskUpdate(owner)`) 가 아예 없음
>
> **강제 자가검증** (spawn 직전 자문): "나는 teammate 를 **자연어로 spawn 요청**(사용자 승인 경유)하고, 그 teammate 가 공유 Task 를 self-claim + SendMessage 협업하는가? `Agent({...})` 를 직접 호출해 결과만 회수하면 sub-agent 회귀 — § 4B 순차 폴백 또는 사용자에게 '진짜 협업이 필요한가, disjoint fan-out 이면 순차로 충분한가' 재확인."
>
> **둘 차이**:
>
> | | sub-agent (단방향 워커) | 협업 teammate (이 § 4A) |
> |---|---|---|
> | spawn 방법 | `Agent({...})` 직접 도구 호출 | lead 에게 **자연어로 spawn 요청** (사용자 승인) |
> | Task 도구 | 없음 (결과만 회수) | `TaskList`/`TaskUpdate` self-claim 보유 |
> | 컨텍스트 | 자체 컨텍스트, lead 가 결과 회수 (단방향) | 자체 컨텍스트 + 메일박스 + 공유 task list |
> | 팀원 간 통신 | 불가 (lead 거쳐야) | `SendMessage({to:"이름"})` 직접 메시지 |
> | 적합 작업 | disjoint fan-out, dev-guide 4 파일 작성, 단순 조사 (토큰↓) | 협업·적대 토론·공유 contract 합의 (토큰↑↑) |
> | 활성화 | 기본 도구 | `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` + `teammateMode` (v2.1.178+: TeamCreate 없이 자동 형성) |
>
> **언제 sub-agent 가 정답인가**: disjoint fan-out (팀원 간 합의 불요, 결과만 모으면 됨)·단순 조사. 협업(contract 합의·적대 검토)이 필요하면 teammate.

**4A-0. Deferred tool 스키마 로드 (lead 용, 스킵 금지)**

lead 가 쓸 팀 관리 도구(`Task*` / `SendMessage`)는 deferred — 기본 도구 목록에 스키마가 없습니다. 호출 전에 한 번만 ToolSearch 로 로드:

```
ToolSearch({ query: "select:TaskCreate,TaskList,TaskUpdate,TaskGet,SendMessage", max_results: 10 })
```

> teammate spawn 은 자연어이므로 lead 가 `Agent` 도구를 직접 호출하지 않습니다 (직접 호출 = sub-agent 회귀). teammate 자신은 spawn 시 Task·SendMessage 가 자동 제공됩니다. (`TeamCreate`/`TeamDelete` 는 v2.1.178 에서 제거됐습니다.)

**4A-1. 팀 컨텍스트 (자동 — 별도 생성 호출 없음)**

> v2.1.178 부터 `TeamCreate`/`TeamDelete` 도구는 제거됐습니다. 팀은 **현재 세션에서 자동 파생**되며, 첫 background teammate 를 spawn 하는 순간 lead(= 메인 세션) 중심으로 구성됩니다. 별도 생성 호출이 필요 없습니다 (`team_name` 파라미터는 Agent tool 에 남아있으나 accepted-but-ignored — 전달해도 무시됩니다).

lead 는 현재 메인 세션입니다. 공유 task list(`TaskCreate`/`TaskUpdate`)와 메일박스(`SendMessage`)가 팀 통신 채널입니다.

**4A-2. Task list 작성**

dev-guide § 5 "Agent Teams 구성" 표의 각 행(또는 `--subtasks` 모드에서는 각 slice dev-guide)을 1 task 로 변환:

```
FOR each row in "Agent Teams 구성":
  TaskCreate({
    subject: "<역할명> — <담당 범위 요약 (1줄)>",
    description: """
      ## 담당 파일 (자기 owned, 다른 teammate 의 owned 파일은 수정 금지)
      - <파일1>
      - <파일2>

      ## dev-guide 참조
      `docs/STD-<KEY>-dev-guide.md` § 3 Phase <N> + § 5 작업 의존성

      ## 완료 기준
      - 단위 테스트 GREEN
      - 자기 소유 파일만 수정 (git diff 확인)
      - 빌드는 lead 가 통합 단계에서 1회 수행 — teammate 는 compile 만 보장
    """,
    activeForm: "<역할명> 작업 중"
  })
```

작업 의존성이 있으면 (§ 5 작업 의존성 다이어그램 참조) `TaskUpdate({ taskId, addBlockedBy: [...] })` 로 DAG 구성.

**4A-3. Teammate spawn (자연어 — 직접 Agent 도구 호출 금지)**

lead 는 `Agent({...})` 를 직접 호출하지 않습니다. § 4A-2 에서 만든 task 들을 바탕으로, 각 slice 를 1 teammate 로 **자연어 spawn 지시**로 일괄 요청합니다 (런타임이 팀 컨텍스트로 띄우고 사용자 승인을 거침). 예:

```
"<이슈 제목> 을 N 개 slice 로 병렬 구현하기 위해 teammate N 명을 spawn한다.
 각 teammate 는 자기 task 를 TaskList 로 찾아 self-claim(in_progress → 완료 시 completed)하고,
 다른 teammate 와의 contract(interface/method signature) 합의는 SendMessage 로 직접 한다 (lead 우회 X).

 - <slug-역할1> (<§5 subagent-type 또는 일반>): 담당 <파일/모듈>.
     prompt: '당신은 <slug-역할1>, <스택 페르소나>. 담당 파일 <...> 만 수정(다른 teammate 파일 read-only).
              dev-guide: docs/STD-<KEY>-dev-guide.md § 3 Phase <N> (+ slice dev-guide docs/STD-<KEY>-<SUB>-dev-guide.md).
              단위 테스트 GREEN 확인. 통합 빌드/Codex 는 lead 책임이라 시도 X.'
 - <slug-역할2> (...): ...

 plan approval 이 필요한 slice 는 plan 모드로 spawn (lead 가 approve/reject)."
```

- **subagent 정의 재사용**: role 을 `stdback-cqrs-refactorer` 같은 subagent-type 으로 지정하려면 이름으로 언급("stdback-cqrs-refactorer agent type 으로 spawn"). 그 정의의 `tools`/`model` 을 따르되 **Task·SendMessage 는 항상 사용 가능**(공식). § 5 에 없으면 일반 teammate.
- **task 배정**: lead 는 § 4A-2 의 task 에 `TaskUpdate({ taskId, owner: "<slug-역할명>" })` 로 명시 assign 하거나 teammate self-claim 에 맡깁니다. pre-assign 이 DAG·디버깅에 결정론적이라 권장 — spawn 승인 직후 owner 지정.
- **사용자 승인**: teammate spawn 은 사용자 승인을 거칩니다(공식: "Claude won't spawn teammates without your approval"). 승인 후 팀 형성 + 각자 self-claim 시작.

> **왜 자연어 spawn**: v2.1.178+ 공식 메커니즘이 자연어다. lead 가 `Agent({ name, run_in_background })` 를 직접 호출하면 **sub-agent 로 떨어져** Task self-claim·팀 메일박스가 동작하지 않는다(⚠️ 박스 + 실측 확인). teammate 의 역할 지시는 자연어 spawn 안의 prompt 텍스트로 담는다.

> `plan` 모드 spawn 시 teammate 가 plan 제출 → lead 가 검토 후 approve/reject. approve 기준은 dev-guide § 5 의 "파일 충돌 방지" + "완료 기준" 충족 여부.

**4A-4. 진행 모니터링 (lead 의 의무)**

- Teammate idle 알림은 자동 메시지로 도착 — polling 금지.
- 5 분 이상 응답 없는 task: `SendMessage({ to: "<name>", message: "<상태 확인 1줄>" })`.
- File conflict 의심 (예: 두 teammate 가 동일 import 추가): `git diff --name-only` 로 owned 파일 매트릭스 검증. 위반 시 즉시 해당 teammate 에 `SendMessage` 로 중단 지시 + 사용자 알림.
- DAG 상 blocked 였던 task 는 선행 완료 시 자동 unblock. lead 가 새 task 추가가 필요하면 `TaskCreate` 후 `SendMessage` 로 idle teammate 깨움.

**4A-5. 통합 진입 조건만 확인 (빌드는 Step 7 에서 1회)**

모든 task 가 `completed` 가 되면:

```
1. TaskList 로 status=pending|in_progress 인 task 가 0개임을 확인
2. teammate 는 idle 상태 유지 (아직 종료 X) — Codex review/빌드 실패 시 fix 위해 깨울 수 있음
3. → Step 5 (출력) → Step 6 (Codex) → Step 7 (빌드 검증) 정상 흐름 진입
```

> **빌드 중복 금지**: 4A 안에서 빌드를 돌리지 않습니다. 통합 빌드는 Step 7 에서 1회. teammate 마다 자기 영역 compile 만 보장 (단위 테스트 GREEN).

**4A-6. Teammate completion 단위 출력 (Step 5 대체)**

순차 모드의 Phase 출력 대신, teammate 단위로:
```
✅ <slug-역할명> 완료: <task subject>
  수정: <파일 N개>
  단위 테스트: GREEN / N건
```

**4A-7. Teardown — Step 7 빌드 검증 통과 직후**

Step 7 빌드 통과 + Step 8 Jira 코멘트 직전에:

```
1. 빌드 실패 시 (Step 7) → 책임 teammate 식별 → SendMessage({ to: "<name>", message: "<수정 지시>" })
   teammate idle 상태에서 메시지 받으면 깨어남 → fix → 완료 → 다시 Step 7 빌드
2. 빌드 통과 시 → teammate 는 자기 task `completed` 후 idle. 명시 종료는 선택사항:
   - 제거된 건 `TeamDelete` 뿐 — in-process 팀의 shared 디렉토리는 세션 종료 시 자동 정리되므로 teardown 단계가 불필요하다.
   - `shutdown_request` 는 **유효**하다: 사용자가 "teammate 종료해줘"라고 요청하면 lead 가 이름으로 shutdown 을 보내고 teammate 가 approve/reject 한다(공식 "Shut down teammates"). 굳이 안 보내도 세션 종료 시 정리된다.
3. 별도 cleanup 입력을 사용자에게 요구하지 않습니다 — 자동 정리에 의존.
```

> **종료 모델 (v2.1.178+)**: in-process teammate 는 task `completed` → idle. shared 디렉토리는 세션 종료 시 자동 정리(제거된 도구는 `TeamDelete` 뿐 — `shutdown_request` 는 유효). `/resume`·`/rewind` 는 in-process teammate 를 복원하지 못하므로(공식 limitation), 중단 후 재개 시 lead 가 새로 spawn 한다. 빌드 실패 fix 는 세션 내 `SendMessage` 로 idle teammate 를 깨워 처리한다.

### 4A-FB. Sub-agent fan-out (Agent Teams 미지원 환경 폴백)

> § 4A 진입 가드에서 환경이 Agent Teams 미지원(SDK/통합앱/CI/비대화형)으로 판명됐는데 병렬이 필요하면 이 모드. sub-agent 는 Task self-claim·팀 메일박스가 없으므로:
> - **disjoint files 전제**: 각 slice 가 서로 다른 파일만 수정 (겹치면 마지막 write 가 이김 → 충돌)
> - **contract 합의가 필요하면 이 모드 금지** → § 4B 순차 (sub-agent 끼리 협의 불가)

절차:

1. **Phase 0 scaffold** (공통 DTO/interface/migration) 를 lead 가 먼저 완료 — sub-agent 끼리 합의 못 하므로 공통 계약을 미리 박아둔다.
2. **disjoint slice fan-out** — 한 메시지에서 sub-agent 를 동시 호출(병렬):

```
FOR each disjoint slice:
  Agent({
    description: "<역할명> slice 구현",
    subagent_type: "<§ 5 agent 또는 general-purpose>",
    prompt: """
      <slice dev-guide 경로>. 담당 파일 <...> 만 수정 (다른 파일 read-only).
      구현 + 단위 테스트 GREEN 확인. 통합 빌드/Codex 는 lead 책임.
      완료 시 '수정 파일 목록 + 테스트 결과' 를 최종 메시지로 반환.
    """
  })
  # run_in_background 미사용 — lead 가 각 sub-agent 의 최종 결과를 직접 회수 (단방향)
```

3. lead 가 모든 sub-agent 결과를 취합 → Step 7 통합 빌드 1회 → Step 6 Codex.

> **동시 쓰기 충돌이 우려되면** 각 sub-agent 에 `isolation: "worktree"` 를 줘서 격리하고, lead 가 각 worktree 변경을 메인 워킹트리에 머지한다(머지 부담 발생). disjoint files 가 확실하면 단일 워킹트리로 충분.
> **§ 4A 와 차이**: sub-agent 는 결과만 단방향 회수 — self-claim/SendMessage 협업 없음. 그래서 contract 합의가 필요한 작업엔 부적합(→ § 4B).

### 4B. 순차 실행 모드

MD의 Phase를 순서대로 실행합니다.

**각 Phase 실행 프로세스:**

```
FOR each Phase in 구현 계획:
  1. Phase 목표 확인
  2. 수정 대상 파일 읽기 (반드시 Read 먼저)
  3. 변경 적용 (Edit/Write)
  4. Phase 검증 (MD에 명시된 검증 방법 실행)
END FOR

# 모든 Phase 완료 후 1회만 수행:
- npm run lint (전체 lint)
- npm run build (전체 빌드)
```

> **빌드/린트 정책**: Phase 단위로 lint/build를 매번 돌리지 않는다. 매 변경마다 검증하면
> 시간 낭비가 크고 컨텍스트가 무거워진다. 모든 Phase 구현이 끝난 후 단계 7에서 **1회만**
> 전체 검증을 수행한다. Phase 검증은 MD가 명시한 정적 확인(파일 존재, 라우트 등록 등)으로 충분.

**사이드 이펙트 방지 규칙:**

이 규칙들은 가이드에 없는 변경이 코드에 스며드는 것을 막기 위해 존재합니다. 가이드 외 변경이 쌓이면 리뷰 범위가 넓어지고, 의도하지 않은 동작 변경을 일으킬 수 있습니다.

1. **MD에 명시된 파일만 수정** — 영향 범위 분석에 없는 파일은 수정하지 않음
2. **MD에 명시된 변경만 적용** — 추가 리팩토링, 코드 정리, 주석 추가 금지
3. **기존 코드 스타일 유지** — 수정 대상 파일의 기존 포맷팅/네이밍 따르기
4. **import 정리 외 포맷팅 변경 금지** — 새 import 추가는 허용, 기존 코드 재정렬 금지
5. **빌드 깨뜨리지 않기** — Phase 단위 빌드는 생략. 모든 Phase 완료 후 단계 7(전체 완료 검증)에서 1회만 수행. 단, 명백히 빌드를 깰 변경(존재하지 않는 import, 신택스 에러)은 즉시 발견·수정.

**예외**: 빌드 에러나 컴파일 에러가 발생하면 해결에 필요한 최소 범위의 추가 수정은 허용. 이 경우 사용자에게 알림.

### 5. Phase별 진행 상황 출력

각 Phase 완료 시:
```
✅ Phase <N>/<Total> 완료: <Phase명>
  수정: <파일 목록>
  검증: <통과/실패>
```

### 6. Codex 코드 리뷰 (필수 — Codex 설치 시)

구현이 완료되면 Codex adversarial review 로 git diff 기반 코드 리뷰를 **반드시** 수행합니다.
이 단계는 빌드 검증 전에 실행하여, 리뷰 피드백 반영과 빌드 검증을 한 사이클로 끝냅니다.

**왜 필수인가**: Codex 는 다른 모델 시각으로 working-tree diff 를 검토합니다. 같은 모델이 자기 코드를 리뷰하면 동일한 사각지대를 공유하지만, 외부 리뷰어는 페르소나가 놓친 패턴 (race condition, 누락된 edge case, 잘못된 가정)을 잡아냅니다. "선택" 으로 두면 루프 모드/시간 압박 시 가장 먼저 스킵되는데, 그게 정확히 외부 시각이 가장 필요한 시점입니다. 그래서 **설치돼 있으면 무조건 실행**.

#### 실행 방법

`codex:adversarial-review` 는 `disable-model-invocation: true` 라서 Skill 도구로 호출 못 합니다.
Bash 로 codex-companion 스크립트를 직접 실행합니다.

**Step 6-1. 설치 감지** (먼저 실행):

```bash
CODEX_SCRIPT=$(printf '%s\n' "$HOME"/.claude/plugins/cache/openai-codex/codex/*/scripts/codex-companion.mjs 2>/dev/null | sort -V | tail -1)
```

> `ls` 대신 `printf` 글로브를 쓰는 이유: 일부 환경의 `ls` 는 실행 파일에 `*` suffix 를 붙여 (`/path/codex-companion.mjs*`) 후속 `[ -f "$CODEX_SCRIPT" ]` 검증을 깨뜨립니다. `printf '%s\n' <glob>` 은 매치 결과를 그대로 출력하므로 안전합니다.

- glob 으로 버전 디렉토리를 탐색 → 최신 버전 자동 선택 (plugin 자동 업데이트 대응. `1.0.0` hardcoding 금지)
- `$CODEX_SCRIPT` 가 비어있으면 미설치 → Step 6-3 으로 분기
- 비어있지 않으면 Step 6-2 진행

**Step 6-2. 실행 전 working-tree 정리 (EISDIR / ENOENT 회피)**

Codex companion 은 `git status` 의 `??`(untracked) 라인을 파일로 간주해 read 합니다. untracked **디렉토리**, 또는 `.gitignore` 에 `foo/` 만 있어 파일 `foo` 가 untracked 로 남으면 EISDIR/ENOENT 로 죽습니다(모노레포에서 빈발). 호출 직전 점검:

```bash
git status --short | grep -E '^\?\?' | awk '{print $2}'   # untracked 항목 확인
```

출력에 untracked **디렉토리**(`path/dir/`)나 슬래시 mismatch ignore 패턴이 있으면 → `git add <항목>` 으로 staging(파일 단위로 펼침) 하거나 `.gitignore` 패턴에서 슬래시 제거 후 Codex 호출. (메모리: `codex-working-tree-eisdir`)

**Step 6-3. 실행** (설치된 경우 — 스킵 금지):

```bash
node "$CODEX_SCRIPT" adversarial-review --wait --scope working-tree
```

- `--wait`: 포그라운드 실행 (결과 즉시 수신)
- `--scope working-tree`: 워킹 트리 변경사항 리뷰

이 호출은 **건너뛰지 않습니다**. 루프 모드, `--subtasks` 모드, 단일 이슈 — 어떤 컨텍스트에서도. 시간이 부족하다고 판단되더라도 실행합니다 (사용자의 명시적 정책).

**Step 6-3-b. 실행 실패 시 진단**:

| 증상 | fix |
|------|------|
| `EISDIR ... read` | untracked 디렉토리를 파일처럼 read → `git add <dir>` 또는 `.gitignore` (Step 6-2 재점검) |
| `ENOENT ... stat '<root>\src\...'` | 모노레포 sub-repo 안에서 호출 → 모노레포 **root 에서 재호출** |

재시도 후에도 실패하면 사용자에게 알리고 진행 여부 확인.

**Step 6-3. 미설치 시 (스킵 허용 — 단, 명시 출력)**:

`$CODEX_SCRIPT` 가 비어있을 때만 다음 출력 후 진행:
```
⚠️ Codex 미설치 — adversarial review 스킵 (skill 정책상 설치돼 있으면 필수)
```

설치돼 있는데 실행 자체가 실패한 경우 (네트워크/권한/타임아웃) → 사용자에게 알리고 **재시도 또는 수동 검토 후 진행 여부 확인**. 자동 스킵 금지.

#### 리뷰 결과 처리

Codex 가 반환한 리뷰 출력을 읽고:

1. 피드백 중 **타당한 지적만 선별** 반영 (페르소나의 전문적 판단으로 필터링 — 모든 피드백을 무비판 수용하지 않음)
2. 수정 발생 시 해당 파일만 재수정 후 Step 7(빌드 검증)에서 함께 확인
3. 터미널에 요약 출력:
   ```
   🔍 Codex 코드 리뷰 완료 — 피드백 <N>건 중 <M>건 반영
   ```

### 7. 전체 완료 검증

모든 Phase 완료 후:

**6-1. 빌드 검증**
```bash
# 스택별 빌드 명령 (CLAUDE.md 우선)
./gradlew.bat build -x test   # Spring Boot
flutter analyze                # Flutter
npm run build                  # Vue/React/Angular
go build ./...                 # Go
cargo build                    # Rust
```

**6-2. 인수조건 체크**

MD의 "인수조건"을 하나씩 확인:
```
✅ 인수조건 검증
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ AC1: <내용>
✅ AC2: <내용>
⚠️ AC3: <수동 확인 필요 — 이유>
```

**6-3. 변경사항 요약**
```bash
git diff --stat
```

### 8. Jira 코멘트 및 결과 출력

#### Jira 코멘트
```
🔨 구현 완료 (<ISSUE-KEY>)

📊 변경사항:
- 수정 파일: <N>개
- 신규 파일: <M>개
- 추가: +XXX줄 / 삭제: -XXX줄

✅ 인수조건 충족: <X>/<Total>
✅ 빌드: 성공
🔍 Codex 리뷰: <수행됨 — 피드백 N건 반영 / 스킵>

실행 모드: <순차/병렬 (Agent Teams: N명)>
```

#### 터미널 출력
```
🔨 구현 완료
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 이슈: <ISSUE-KEY> — <이슈 제목>
🔧 스택: <감지된 스택>
👤 페르소나: <페르소나명>

📊 실행 결과:
  Phase 완료: <N>/<Total>
  수정 파일: <X>개
  신규 파일: <Y>개
  빌드: ✅ 성공
  🔍 Codex 리뷰: <수행됨 — 피드백 N건 반영 / 스킵>

✅ 인수조건: <충족 수>/<전체> 확인
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

다음 단계: /jira-test → /jira-commit <ISSUE-KEY>
```

## Error Handling

- MD 파일 미존재 → `/jira-plan` 실행 안내
- MD 구조 불완전 → 누락 섹션 경고 후 가능한 범위에서 진행
- 빌드 실패 → 해당 Phase에서 중단, 에러 내용 출력, 수정 시도
- 파일 충돌 (Agent Teams) → 즉시 중단, 사용자에게 알림
- Phase 검증 실패 → 해당 Phase에서 중단, 원인 분석 출력
- MD에 없는 파일 수정 필요 발생 → 사용자에게 확인 후 진행

## Notes

- `/jira-plan`에서 생성된 MD를 소비하도록 설계됨
- MD 파일을 직접 수정한 후 실행해도 정상 동작 (사용자가 가이드를 편집 가능)
- Agent Teams 모드에서 각 teammate는 CLAUDE.md를 자동으로 로드함
- 사이드 이펙트 방지가 핵심 원칙 — 가이드에 없는 변경은 하지 않음
- CLAUDE.md에 프로젝트별 빌드/린트 명령이 있으면 우선 사용
- **Codex adversarial review (Step 6)는 Codex 설치 시 필수** — 루프/병렬/단일 모드 무관, 시간 압박 시에도 스킵 금지. 미설치 시에만 명시 출력 후 진행
- **Agent Teams 트리거 (§ 4A)**: dev-guide 의 `## 5. 병렬 작업 가이드` + "Agent Teams 구성" 표 자동 감지. 사용자 추가 확인 X. 미설정 (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` 부재) 시 § 4B 순차 모드로 폴백
- **Agent Teams 진입(v2.1.178+)**: lead 가 **구체적 자연어로 teammate spawn 요청**(역할·담당파일·prompt 명시, 사용자 승인) → 팀 자동 형성 → teammate 가 공유 Task self-claim + SendMessage 협업. lead 가 `Agent({...})` 를 직접 도구 호출해 결과만 회수하면 sub-agent 회귀(§ 4A ⚠️ 박스). 단계: 4A-0 ToolSearch(Task*/SendMessage, lead) → 4A-2 TaskCreate × N → 4A-3 자연어 spawn × N + TaskUpdate(owner) → 4A-4 모니터링(SendMessage) → 4A-7 자연 종료(자동 정리). "팀 만들어줘" 식 **막연한** 위임은 금지 — slice·담당·prompt 를 명시
- **`--subtasks` 모드의 worktree 분기 제거 (2026-05-13)**: ADR-070 의 manual worktree 패턴 → Agent Teams 의 disjoint-files 패턴으로 대체. 자세히는 § "--subtasks Mode" 의 supersession 노트

## --subtasks Mode (Agent Teams 통합)

사용자가 `/jira-execute <KEY> --subtasks` 로 호출 시 — slice fan-out 은 **Agent Teams 로 처리** (worktree 분기 X, 단일 working tree + disjoint files):

1. **Phase 0 (scaffold)** — 부모 dev-guide § 3 Phase 0 (DTO/interface/migration) 를 lead 가 직접 수행. teammate spawn 전에 끝내야 slice 들이 공통 contract 위에서 동작.
2. **Phase 1 (slice fan-out)** — § 4A 절차 그대로:
   - 각 slice (`STD-<SUB>`) 마다 lead 가 `TaskCreate` → **자연어로 teammate spawn 요청**(사용자 승인) → `TaskUpdate({ owner })`. lead 가 `Agent()` 를 직접 호출하지 않음 (= sub-agent 회귀, § 4A)
   - 별도 팀 생성 호출 없음 — 팀은 첫 spawn 시 세션 자동 파생 (v2.1.178 에서 `TeamCreate` 제거)
   - 각 teammate spawn prompt 에 slice dev-guide 경로 명시: `docs/STD-<PARENT>-STD-<SUB>-dev-guide.md`
3. **slice 별 댓글** — teammate 가 자기 task 를 `completed` 로 마킹할 때, lead 가 하위 이슈에 1~3 줄 댓글 추가 (Jira tool 호출은 lead 가):
   ```
   🔨 구현 완료. 단위 테스트 N PASS.
   통합 검증 + harness verdict 은 부모 `<PARENT-KEY>` 댓글 참조.
   ```
4. **Phase 2 (통합 빌드)** — 모든 slice teammate `completed` 이후 lead 가 단일 빌드 1회. 하위 댓글에 재인용 X.
5. **Teardown** — § 4A-7 절차 (teammate 자연 종료 + 세션 종료 시 자동 정리. 명시적 shutdown/cleanup 호출 불필요).

> **Worktree 미사용 — ADR-070 supersession**: 종전 ADR-070 은 `git worktree add` + `Agent({ cwd: <worktree path> })` 패턴이었으나, Agent Teams 도입 후 **단일 working tree + disjoint files + shared task list** 패턴으로 대체. 이유:
> - Teammate 끼리 SendMessage 직접 통신 가능 → contract 합의가 lead 우회 가능 (worktree 격리 모델에서는 불가)
> - manual worktree create/remove cleanup 부담 제거
> - Phase 0 scaffold 가 모든 teammate 에 자동 visible (worktree base branch fork 이슈 #50850 회피)
>
> 단점 (감수): 두 teammate 가 동일 파일 수정 시 마지막 write win. § 4A-2 의 "담당 파일" 정의 + § 4A-4 의 `git diff --name-only` 모니터링으로 방지.

자세한 정책: `~/.claude/skills/_subtasks-convention.md` § 3, § 5
