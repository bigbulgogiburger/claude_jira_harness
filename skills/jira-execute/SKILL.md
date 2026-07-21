---
name: jira-execute
description: "jira-execute — docs/<ISSUE-KEY>-dev-guide.md를 읽고 스택 최고 개발자 페르소나로 실제 구현을 진행합니다. 병렬 작업은 dynamic Workflow 레인(모델 티어링)으로 수행합니다. 구현 단계에서, '구현해줘', '실행해줘', '코드 작성해줘', 'Phase 진행', 'dev-guide대로 개발', 'jira execute', '개발 시작' 등의 요청에 이 스킬을 사용하세요. /jira-plan 이후, harness-workflow gate 단계 이전에 사용합니다."
---

# jira-execute — 개발 가이드 기반 구현 실행

개발 가이드 MD 파일을 읽고, 스택 최고 개발자 페르소나로 실제 구현을 진행합니다.
병렬 작업이 필요하면 **dynamic Workflow 레인**으로 수행합니다 (Agent Teams 신규 사용 금지 — 2026-07-20 확정, 실측 결함 4건).
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

작업 디렉토리에서 프로젝트 스택을 자동 감지하고 페르소나를 활성화합니다 — 감지 매핑 + 스택별 페르소나는 `~/.claude/skills/_stack-detection.md` §1 + §2 참조.

### 3. 실행 모드 결정

```
IF dev-guide 에 "## 5. 병렬 작업 가이드" 존재 (BE/FE 2레인, disjoint slice 등):
  → § 4A 병렬 모드 (dynamic Workflow 레인)
ELSE:
  → § 4B 순차 실행 모드
```

> **구 Agent Teams / `--subtasks` slice fan-out / sub-agent 낱개 fan-out 은 전부 supersede** (2026-07-20, harness v2 설계 §7 — 시퀀스 해석 결함·worker hang·모델 오버라이드 미적용 전원-fable 상속 실측 4건). dev-guide 에 "Agent Teams 구성" 표가 남아 있으면 각 행을 Workflow 레인 1개로 읽는다.

### 4A. 병렬 실행 모드 (dynamic Workflow) — 표준

병렬 모드 SSoT: `~/.claude/skills/harness-workflow/references/parallel-modes.md` (단일이슈 2레인 / 다중부모 fan-out + 모델 티어링). 핵심 절차:

1. **Phase 0 scaffold** — 공통 계약(DTO/interface/migration)은 레인 spawn 전에 **메인이 직접** 완료 (레인끼리 합의 불가).
2. **Workflow 스크립트 구성** — 레인별 `agent()` 호출. **모든 호출에 `opts.model` 명시** (BE 복잡 도메인=opus, FE·기계적 변환=sonnet — 미지정 = 메인 모델 상속 함정). `meta.phases[].model` 표기.
3. **모델 스모크 프로브 1회** — 첫 agent 에게 자기 모델 식별을 보고시켜 오버라이드 실적용 확인 후 본 fan-out.
4. 레인 프롬프트: dev-guide 경로 + 담당 파일(타 레인 파일 read-only) + 단위 테스트 GREEN + "통합 빌드/Codex 는 메인 책임 — 시도 금지" + 최종 메시지로 수정 파일 목록·테스트 결과 반환.
5. 동시 쓰기 충돌 우려 시 `isolation:'worktree'` (머지 부담 발생 — disjoint 확실하면 단일 워킹트리).
6. **크로스레인 seam(계약 정합)은 메인이 직접 대조·해소** — 레인에 재위임 금지.
7. 통합 빌드는 § 7 에서 메인이 1회.

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

각 Phase(또는 레인) 완료 시:
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

**Step 6-0. 프로젝트 표준 래퍼 우선** — 프로젝트에 `scripts/codex-review.sh` 가 있으면 **반드시 래퍼 경유** (stdin 봉인·출력 파일화·이중 타임박스·호출 계측 — hang 원천 차단):

```bash
bash scripts/codex-review.sh <prompt-file>   # exit 0: 출력 파일 경로 반환 / exit 42: 폴백
```

- exit 42 → **Claude adversarial workflow(opus skeptic 레인)로 자동 대체** + verdict 에 `codex=fallback(<사유>)` 기록. 파이프라인은 Codex 가용성과 분리.
- 래퍼가 없으면 Step 6-1 로.

**Step 6-1. 설치 감지**:

```bash
CODEX_SCRIPT=$(printf '%s\n' "$HOME"/.claude/plugins/cache/openai-codex/codex/*/scripts/codex-companion.mjs 2>/dev/null | sort -V | tail -1)
```

> `ls` 대신 `printf` 글로브를 쓰는 이유: 일부 환경의 `ls` 는 실행 파일에 `*` suffix 를 붙여 후속 `[ -f ]` 검증을 깨뜨립니다.

- `$CODEX_SCRIPT` 가 비어있으면 미설치 → "⚠️ Codex 미설치 — adversarial review 스킵" 명시 출력 후 진행
- 있으면 Step 6-2 진행

**Step 6-2. 실행 전 working-tree 정리 (EISDIR / ENOENT 회피)**

Codex companion 은 `git status` 의 `??`(untracked) 라인을 파일로 간주해 read 합니다. untracked **디렉토리**, 또는 `.gitignore` 슬래시 mismatch 로 파일이 untracked 로 남으면 EISDIR/ENOENT 로 죽습니다. 호출 직전 `git status --short | grep '^??'` 점검 → 디렉토리는 `git add` 로 파일 단위 staging 후 호출. (메모리: `codex-working-tree-eisdir`)

**Step 6-3. 실행** (스킵 금지):

```bash
node "$CODEX_SCRIPT" adversarial-review --wait --scope working-tree
```

| 실패 증상 | fix |
|------|------|
| `EISDIR ... read` | untracked 디렉토리 → `git add <dir>` 또는 `.gitignore` 정리 (Step 6-2 재점검) |
| `ENOENT ... stat` | 모노레포 sub-repo 안에서 호출 → root 에서 재호출 |
| hang(무출력 3분+) | kill 후 opus skeptic workflow 폴백 — `codex=fallback(hang)` 기록 |

#### 리뷰 결과 처리

1. 피드백 중 **타당한 지적만 선별** 반영 (전문적 판단으로 필터링 — 무비판 수용 금지)
2. 수정 발생 시 해당 파일만 재수정 후 Step 7(빌드 검증)에서 함께 확인
3. 요약 출력: `🔍 Codex 코드 리뷰 완료 — 피드백 <N>건 중 <M>건 반영`

### 7. 전체 완료 검증

모든 Phase/레인 완료 후:

**7-1. 빌드 검증** (CLAUDE.md 프로젝트 명령 우선)
```bash
./gradlew.bat build -x test   # Spring Boot
npm run build                  # Vue/React/Angular
flutter analyze                # Flutter
```

**7-2. 인수조건 체크** — MD의 "인수조건"을 하나씩 확인 (수동 확인 필요 항목은 ⚠️ 로 명시).

**7-3. 변경사항 요약** — `git diff --stat`

### 8. Jira 코멘트 및 결과 출력

#### Jira 코멘트
```
🔨 구현 완료 (<ISSUE-KEY>)

📊 변경사항: 수정 <N>·신규 <M>개 / +XXX / -XXX
✅ 인수조건 충족: <X>/<Total>
✅ 빌드: 성공
🔍 Codex 리뷰: <수행 — N건 반영 / fallback(<사유>) / 미설치 스킵>
실행 모드: <순차 / 병렬 (Workflow N레인)>
```

#### 터미널 출력 — 위 코멘트와 동일 정보 + 스택·페르소나. 다음 단계: `/harness-review` → harness-workflow **gate** 단계 (테스트+DoD+커밋 — 구 /jira-test·/jira-commit 은 폐기, `~/.claude/skills/harness-workflow/references/gate.md`).

## Error Handling

- MD 파일 미존재 → `/jira-plan` 실행 안내
- MD 구조 불완전 → 누락 섹션 경고 후 가능한 범위에서 진행
- 빌드 실패 → 해당 Phase에서 중단, 에러 내용 출력, 수정 시도
- 레인 간 파일 충돌 → 즉시 중단, 사용자에게 알림 (worktree 격리 재구성 검토)
- Phase 검증 실패 → 해당 Phase에서 중단, 원인 분석 출력
- MD에 없는 파일 수정 필요 발생 → 사용자에게 확인 후 진행

## Notes

- `/jira-plan`에서 생성된 MD를 소비하도록 설계됨. MD 직접 수정 후 실행도 정상 동작
- 사이드 이펙트 방지가 핵심 원칙 — 가이드에 없는 변경은 하지 않음
- CLAUDE.md에 프로젝트별 빌드/린트 명령이 있으면 우선 사용
- **Codex adversarial review (Step 6)는 Codex 설치 시 필수** — 어떤 모드에서도 스킵 금지. 단 hang/실패 시 opus skeptic 폴백은 정식 경로 (skip 이 아님)
- **Agent Teams 신규 사용 금지 (2026-07-20)** — 구 § 4A(teammate 협업)·4A-FB(sub-agent 낱개 fan-out)·`--subtasks` slice fan-out 서술은 전부 dynamic Workflow 레인으로 supersede. Jira 하위이슈 댓글/전이는 부모와 함께 처리하되, 병렬 실행 단위는 § 4A 기준으로만 판단
