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
  → 병렬 실행 모드 (Step 4A)
ELSE:
  → 순차 실행 모드 (Step 4B)
```

### 4A. 병렬 실행 모드 (Agent Teams)

MD의 병렬 작업 가이드에 정의된 구성으로 Agent Teams를 생성합니다.

**4A-1. 팀 생성 프롬프트 구성**

MD에서 추출한 정보로 팀을 구성합니다:

```
다음 작업을 병렬로 진행할 Agent Team을 만들어줘.

[MD의 "Agent Teams 구성" 테이블을 기반으로 각 teammate 역할 설명]

각 teammate에게 다음 컨텍스트를 전달:
- 프로젝트 스택: <스택>
- CLAUDE.md의 핵심 규칙
- 담당 파일 목록과 구체적 변경 내용
- 파일 충돌 방지 규칙: 자기 담당 파일만 수정

모든 teammate는 plan approval을 받은 후 실행해줘.
```

**4A-2. teammate별 프롬프트**

각 teammate에게 다음을 포함한 구체적 프롬프트를 전달:

```
당신은 <페르소나명>입니다.

## 담당 작업
<MD Phase에서 해당 teammate 작업 내용>

## 수정 가능 파일 (이 파일들만 수정)
- path/to/file1.java
- path/to/file2.java

## 수정 금지 파일
<다른 teammate가 소유한 파일 목록>

## 코딩 규칙
<CLAUDE.md에서 추출한 핵심 규칙>

## 완료 기준
<해당 작업의 인수조건>
```

**4A-3. 팀 실행 및 모니터링**

- Lead가 각 teammate의 plan을 승인
- 파일 충돌 발생 시 즉시 중단하고 사용자에게 알림
- 모든 teammate 완료 후 통합 빌드 검증

**4A-4. 통합 후 Step 5로 이동**

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

**Step 6-2. 실행** (설치된 경우 — 스킵 금지):

```bash
node "$CODEX_SCRIPT" adversarial-review --wait --scope working-tree
```

- `--wait`: 포그라운드 실행 (결과 즉시 수신)
- `--scope working-tree`: 워킹 트리 변경사항 리뷰

이 호출은 **건너뛰지 않습니다**. 루프 모드, `--subtasks` 모드, 단일 이슈 — 어떤 컨텍스트에서도. 시간이 부족하다고 판단되더라도 실행합니다 (사용자의 명시적 정책).

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

## --subtasks Mode

사용자가 `/jira-execute <KEY> --subtasks` 로 호출 시:

1. 부모 dev-guide 의 Phase 0 (scaffold) → Phase 1 (slice fan-out) → Phase 2 (통합) 순서로 진행
2. **slice 별 구현 완료 시점**에 해당 하위 이슈에 1~3 줄 댓글 추가:
   ```
   🔨 구현 완료. 단위 테스트 N PASS.
   통합 검증 + harness verdict 은 부모 `<KEY>` 댓글 참조.
   ```
3. Phase 1 fan-out 은 worktree 4개 (slice 마다) 또는 sequential — touched-files disjoint 검증 후 결정
4. 통합 빌드 (Phase 2) 는 부모에서 1회만 수행 — 하위 댓글에 다시 인용 X

자세한 정책: `~/.claude/skills/_subtasks-convention.md` § 3, § 5
