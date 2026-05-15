---
name: jira-execute
description: "jira-execute — docs/<ISSUE-KEY>-dev-guide.md를 읽고 스택 최고 개발자 페르소나로 실제 구현을 진행합니다. 병렬 작업 가이드가 있으면 Agent Teams로 병렬 개발을 수행합니다. 구현 단계에서, '구현해줘', '실행해줘', '코드 작성해줘', 'Phase 진행', 'dev-guide대로 개발', 'jira execute', '개발 시작' 등의 요청에 이 스킬을 사용하세요. /jira-plan 이후, /jira-test 이전에 사용합니다."
---

# jira-execute — 개발 가이드 기반 구현 실행

개발 가이드 MD 파일을 읽고, 스택 최고 개발자 페르소나로 실제 구현을 진행합니다.
MD에 병렬 작업 가이드가 있으면 Agent Teams를 생성하여 병렬 개발을 수행합니다.
지라에 댓글이나 설명을 작성할 때에는 한글로 작성합니다.

## Usage

```
/jira-execute <ISSUE-KEY>
```

- `ISSUE-KEY`: Jira 이슈 키 (예: PROJ-156)
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

작업 디렉토리에서 프로젝트 스택을 자동 감지하고 페르소나를 활성화합니다.

| 감지 파일 | 스택 | 페르소나 |
|-----------|------|----------|
| `build.gradle` / `pom.xml` | Spring Boot | **Spring Boot Master** — JPA/QueryDSL, CQRS, 트랜잭션 설계, 성능 최적화에 정통한 10년차 백엔드 아키텍트. N+1 방지, Read/Write 서비스 분리, 소프트 삭제 패턴을 자연스럽게 적용함 |
| `pubspec.yaml` | Flutter/Dart | **Flutter Architect** — Riverpod/BLoC, GoRouter, 플랫폼 채널, 위젯 성능 최적화 전문. Widget rebuild 최소화, 상태 격리, 테스트 가능한 아키텍처를 우선시함 |
| `package.json` + Vue | Vue.js | **Vue.js Specialist** — Composition API, Pinia, Vite, SSR/SSG 전문. 반응형 시스템 이해 기반의 composable 설계, 컴포넌트 재사용성 극대화 |
| `package.json` + React | React | **React Expert** — Hooks, Server Components, Next.js, Zustand/Jotai 전문. 렌더링 최적화, 데이터 페칭 패턴, 관심사 분리 |
| `package.json` + Angular | Angular | **Angular Master** — RxJS, Signal, Standalone Components, Change Detection 전문. 엔터프라이즈 수준의 모듈 설계 |
| `go.mod` | Go | **Go Expert** — goroutine, interface 설계, stdlib 활용 전문. 단순함과 명시성 최우선 |
| `Cargo.toml` | Rust | **Rust Master** — ownership/lifetime, async runtime, trait 설계 전문. 안전성과 성능의 균형 |
| `pyproject.toml` / `requirements.txt` | Python | **Python Expert** — FastAPI/Django, type hints, async 전문. Pythonic 코드와 실용적 설계 |

### 3. 실행 모드 결정

MD 파일의 `## 5. 병렬 작업 가이드` 섹션 존재 여부로 실행 모드를 결정합니다.

```
IF "## 5. 병렬 작업 가이드" 섹션 존재 AND "Agent Teams 구성" 테이블 존재:
  → 병렬 실행 모드 (Step 4A) — Agent Teams 자동 진입
ELSE IF "--subtasks" 플래그 AND 부모 이슈에 하위 작업 존재:
  → 병렬 실행 모드 (Step 4A) — slice 마다 1 teammate 자동 spawn
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

> 이 절은 자연어 묘사가 아니라 **구체적 도구 호출 시퀀스**입니다. 모든 step 을 순서대로 그대로 실행하세요. "팀 생성 프롬프트를 구성한다" 같은 추상 표현으로 대체 금지.

**4A-0. Deferred tool 스키마 로드 (스킵 금지)**

Agent Teams 도구들은 deferred — 기본 도구 목록에 스키마가 없습니다. 호출 전에 한 번만 ToolSearch 로 로드:

```
ToolSearch({ query: "select:TeamCreate,TaskCreate,TaskList,TaskUpdate,TaskGet,SendMessage", max_results: 10 })
```

> Agent tool 의 `team_name` / `name` 파라미터는 default 로드돼 있어 별도 fetch 불필요.

**4A-1. 팀 생성**

```
TeamCreate({
  team_name: "PROJ-<KEY>",          // 예: "PROJ-49"
  agent_type: "lead",
  description: "<이슈 제목> — N slice 병렬 구현 (jira-execute)"
})
```

생성 시 `~/.claude/teams/PROJ-<KEY>/config.json` + `~/.claude/tasks/PROJ-<KEY>/` 가 만들어집니다.

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
      `docs/PROJ-<KEY>-dev-guide.md` § 3 Phase <N> + § 5 작업 의존성

      ## 완료 기준
      - 단위 테스트 GREEN
      - 자기 소유 파일만 수정 (git diff 확인)
      - 빌드는 lead 가 통합 단계에서 1회 수행 — teammate 는 compile 만 보장
    """,
    activeForm: "<역할명> 작업 중"
  })
```

작업 의존성이 있으면 (§ 5 작업 의존성 다이어그램 참조) `TaskUpdate({ taskId, addBlockedBy: [...] })` 로 DAG 구성.

**4A-3. Teammate spawn + pre-assign**

각 슬라이스마다 (a) Agent spawn → (b) lead 가 즉시 TaskUpdate 로 owner 지정 (self-claim race 방지):

```
FOR each row in "Agent Teams 구성":
  # (a) teammate spawn
  Agent({
    description: "<역할명> teammate",
    subagent_type: "<§ 5 에 명시된 agent>",     // 예: app-back-cqrs-refactorer. 없으면 "general-purpose"
    team_name: "PROJ-<KEY>",
    name: "<slug-역할명>",                        // 예: "slice-PROJ-163". 이 name 이 TaskUpdate(owner) 값
    prompt: """
      당신은 팀 `PROJ-<KEY>` 의 `<slug-역할명>` 입니다.

      ## 역할
      <스택 페르소나> — <역할 한줄 요약>

      ## 자기 task
      `TaskList` 호출 → owner 가 `<slug-역할명>` 인 task 1건 → `TaskGet` 으로 상세 확인 → `TaskUpdate({ taskId, status: "in_progress" })` 로 시작.

      ## 작업 규칙
      - 자기 task description 의 "담당 파일" 만 수정. 다른 teammate 파일은 read-only.
      - 다른 teammate 와 contract (interface/method signature) 합의가 필요하면 SendMessage 로 직접 협의 — lead 우회 X.
      - 단위 테스트 작성 + GREEN 확인.
      - 완료 시 `TaskUpdate({ taskId, status: "completed" })` + idle. 통합 빌드/Codex review 는 lead 책임이므로 시도 X.

      ## 프로젝트 컨텍스트
      - CLAUDE.md 자동 로드됨 (working dir 기준)
      - dev-guide: `docs/PROJ-<KEY>-dev-guide.md`
      - slice dev-guide (있으면): `docs/PROJ-<KEY>-<SUB>-dev-guide.md`
    """,
    mode: "default"   // dev-guide § 5 에 "plan approval 필수" 명시 시 "plan"
  })

  # (b) 즉시 task assign — self-claim race 방지
  TaskUpdate({ taskId: "<해당 slice 의 task id>", owner: "<slug-역할명>" })
```

> **왜 self-claim 대신 pre-assign**: 공식 문서가 둘 다 허용하지만, lead 가 spawn 직후 `TaskUpdate(owner)` 로 명시 assign 하면 (i) teammate 가 자기 task 를 찾을 때 owner 매칭으로 결정론적, (ii) DAG 의 blocked task 가 잘못 claim 되는 일 없음, (iii) 디버깅 시 lead 시점에서 누가 무엇을 받았는지 명확.

> `mode: "plan"` 사용 시 teammate 가 plan 제출 → lead 가 검토 후 approve/reject. lead 의 approve 기준은 dev-guide § 5 의 "파일 충돌 방지" + "완료 기준" 충족 여부.

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
2. 빌드 통과 시 → 각 teammate 종료:
   FOR each teammate:
     SendMessage({ to: "<name>", message: { type: "shutdown_request" } })
   teammate 가 reject 하면 (드물게 발생) — 사용자에게 reject 사유 보고 후 진행 여부 확인
3. 모든 teammate idle/종료 확인 후 사용자에게 cleanup 안내:
   "팀 정리하려면 lead 채팅에 'clean up the team' 이라고 입력하세요"
```

> **왜 lead 자동 cleanup 안 하나**: 공식 문서 — "Always use the lead to clean up. Teammates should not run cleanup". cleanup 호출자는 lead 가 맞지만 **트리거는 사용자 명시 입력**. 자동 cleanup 은 active teammate 잔존 시 resource 불일치 위험.

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

Codex companion 은 `git status` 의 `??` (untracked) 라인을 그대로 파일로 간주해 `fs.readFile()` 를 시도합니다. 항목이 디렉토리이거나 `.gitignore` 에 디렉토리 패턴(`foo/`)만 있어 파일 (`foo`) 이 untracked 로 남으면 EISDIR / ENOENT 로 즉시 죽습니다. 모노레포 (sub-repo `.git` 없는 통합 repo) 에서 특히 잘 터집니다.

**필수 사전 점검 (Codex 호출 직전 1회)**:

```bash
# 1) untracked 디렉토리 / 슬래시 mismatch 가 있는 ignore 패턴 확인
git status --short | grep -E '^\?\?' | awk '{print $2}'
```

위 출력에 다음 중 하나라도 있으면 **반드시 처리 후** Codex 호출:

| 패턴 | 처리 |
|------|------|
| `path/to/dir/` (슬래시 끝, 디렉토리) | (a) `.gitignore` 에 추가하거나 (b) `git add path/to/dir/` 로 staging — 파일 단위로 펼침 |
| `.graphify_python` (파일인데 `.gitignore` 엔 `.graphify_python/` 만 있음) | `.gitignore` 패턴에서 슬래시 제거 → 파일/디렉토리 둘 다 매칭 |
| 새 도메인 디렉토리 (`controller/`, `dto/` 등) | `git add` 로 staging — 파일 단위 펼침 |

**Step 6-3. 실행** (설치된 경우 — 스킵 금지):

```bash
node "$CODEX_SCRIPT" adversarial-review --wait --scope working-tree
```

- `--wait`: 포그라운드 실행 (결과 즉시 수신)
- `--scope working-tree`: 워킹 트리 변경사항 리뷰

이 호출은 **건너뛰지 않습니다**. 루프 모드, `--subtasks` 모드, 단일 이슈 — 어떤 컨텍스트에서도. 시간이 부족하다고 판단되더라도 실행합니다 (사용자의 명시적 정책).

**Step 6-3-b. EISDIR / ENOENT 진단 매트릭스** (실행 실패 시):

| 증상 | 원인 | 빠른 fix |
|------|------|---------|
| `EISDIR: illegal operation on a directory, read` | untracked 빈/내용 디렉토리를 파일처럼 read | `.gitignore` 추가 또는 `git add <dir>` 로 펼침 |
| `ENOENT: no such file or directory, stat 'D:\<root>\src\...'` | 모노레포 sub-repo (예: `app-back/`) 안에서 호출했는데 git 이 root 기준 경로를 반환 | 모노레포 **root 에서 호출** (sub-repo 안에서 호출 X) |
| `EISDIR` 가 cwd=root 에서도 재현 | untracked dir 여전히 존재 | 위 Step 6-2 의 점검 다시 |

재시도 후에도 동일하게 실패하면 사용자에게 알리고 진행 여부 확인.

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
- **Agent Teams 진입은 자연어 묘사가 아닌 도구 시퀀스**: § 4A-0 ToolSearch → 4A-1 TeamCreate → 4A-2 TaskCreate × N → 4A-3 Agent(team_name,name) × N → 4A-4 모니터링 → 4A-5 SendMessage(shutdown_request). "팀 만들어줘" 식 자연어로 위임 금지 — Lead 가 직접 호출
- **`--subtasks` 모드의 worktree 분기 제거 (2026-05-13)**: ADR-070 의 manual worktree 패턴 → Agent Teams 의 disjoint-files 패턴으로 대체. 자세히는 § "--subtasks Mode" 의 supersession 노트

## --subtasks Mode (Agent Teams 통합)

사용자가 `/jira-execute <KEY> --subtasks` 로 호출 시 — slice fan-out 은 **Agent Teams 로 처리** (worktree 분기 X, 단일 working tree + disjoint files):

1. **Phase 0 (scaffold)** — 부모 dev-guide § 3 Phase 0 (DTO/interface/migration) 를 lead 가 직접 수행. teammate spawn 전에 끝내야 slice 들이 공통 contract 위에서 동작.
2. **Phase 1 (slice fan-out)** — § 4A 절차 그대로:
   - `TeamCreate({ team_name: "PROJ-<PARENT>", agent_type: "lead" })`
   - 각 slice (`PROJ-<SUB>`) 마다 `TaskCreate` + `Agent({ team_name, name: "slice-PROJ-<SUB>", ... })`
   - 각 teammate prompt 에 slice dev-guide 경로 명시: `docs/PROJ-<PARENT>-PROJ-<SUB>-dev-guide.md`
3. **slice 별 댓글** — teammate 가 자기 task 를 `completed` 로 마킹할 때, lead 가 하위 이슈에 1~3 줄 댓글 추가 (Jira tool 호출은 lead 가):
   ```
   🔨 구현 완료. 단위 테스트 N PASS.
   통합 검증 + harness verdict 은 부모 `<PARENT-KEY>` 댓글 참조.
   ```
4. **Phase 2 (통합 빌드)** — 모든 slice teammate `completed` 이후 lead 가 단일 빌드 1회. 하위 댓글에 재인용 X.
5. **Teardown** — § 4A-5 절차 (SendMessage shutdown_request → 사용자에게 "clean up the team" 안내).

> **Worktree 미사용 — ADR-070 supersession**: 종전 ADR-070 은 `git worktree add` + `Agent({ cwd: <worktree path> })` 패턴이었으나, Agent Teams 도입 후 **단일 working tree + disjoint files + shared task list** 패턴으로 대체. 이유:
> - Teammate 끼리 SendMessage 직접 통신 가능 → contract 합의가 lead 우회 가능 (worktree 격리 모델에서는 불가)
> - manual worktree create/remove cleanup 부담 제거
> - Phase 0 scaffold 가 모든 teammate 에 자동 visible (worktree base branch fork 이슈 #50850 회피)
>
> 단점 (감수): 두 teammate 가 동일 파일 수정 시 마지막 write win. § 4A-2 의 "담당 파일" 정의 + § 4A-4 의 `git diff --name-only` 모니터링으로 방지.

자세한 정책: `~/.claude/skills/_subtasks-convention.md` § 3, § 5
