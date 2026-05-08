---
name: jira-start
description: "jira-start — Jira 이슈를 조회하고 feature 브랜치를 생성한 뒤 상태를 In Progress로 전환합니다. Jira 이슈 작업을 시작할 때, '이슈 시작해줘', '작업 시작', '브랜치 만들어줘', 'feature 브랜치 생성', 'In Progress로', 'jira start', '티켓 잡아줘' 등의 요청에 이 스킬을 사용하세요. Jira 워크플로우의 첫 단계로, /jira-clarify 또는 /jira-plan 이전에 사용합니다."
---

# jira-start — Jira 이슈 작업 시작

Jira 이슈를 조회하고 feature 브랜치를 생성한 뒤 상태를 In Progress로 전환합니다.
지라에 댓글이나 설명을 작성할 때에는 한글로 작성합니다.

## Usage

```
/jira-start <ISSUE-KEY>
```

- `ISSUE-KEY`: Jira 이슈 키 (예: PROJ-20, SCRUM-42, PROJ-100)

## Procedure

### 1. 스택 감지

작업 디렉토리에서 프로젝트 스택을 자동 감지합니다.

| 감지 파일 | 스택 | 비고 |
|-----------|------|------|
| `pubspec.yaml` | Flutter/Dart | Riverpod, GoRouter 등 |
| `build.gradle` 또는 `pom.xml` | Spring Boot (Java/Kotlin) | Gradle/Maven |
| `package.json` + Vue 의존성 | Vue.js (JavaScript/TypeScript) | vue, @vue/cli 등 |
| `package.json` + React 의존성 | React (JavaScript/TypeScript) | react, next 등 |
| `package.json` + Angular 의존성 | Angular (TypeScript) | @angular/core 등 |
| `go.mod` | Go | — |
| `Cargo.toml` | Rust | — |
| `pyproject.toml` 또는 `requirements.txt` | Python | Django, FastAPI 등 |

감지된 스택 정보를 이후 단계의 컨텍스트로 활용합니다.

### 2. Jira 이슈 조회

MCP Atlassian 도구를 사용하여 이슈 정보를 조회합니다:
- 이슈 상태, 제목, 설명
- 우선순위, 담당자
- 서브태스크 또는 체크리스트 (있는 경우)

### 3. Git 브랜치 생성

```bash
git checkout -b feature/<ISSUE-KEY>
```

- main/master 브랜치에서 분기하는 것을 권장
- 이미 존재하는 브랜치라면 체크아웃만 수행
- 커밋되지 않은 변경사항이 있으면 경고

### 4. 담당자 지정 (Assignee = 현재 개발자)

작업을 시작하는 사람이 이슈의 책임자라는 게 명확해야 추적·리뷰·알림이 정확해집니다. 따라서 이슈 상태를 바꾸기 **전에** 담당자를 현재 개발 중인 유저로 잡습니다.

1. `mcp__atlassian__atlassianUserInfo` 로 현재 인증된 Jira 유저 정보를 조회 → `accountId` 확보
2. 조회된 이슈의 기존 `assignee.accountId` 와 비교:
   - 비어 있거나 다르면 `mcp__atlassian__editJiraIssue` 로 `fields.assignee = { "accountId": "<현재 유저 accountId>" }` 패치
   - 이미 동일하면 스킵 (불필요한 audit log 생성 방지)
3. 다른 사람이 담당이었다가 본인으로 바뀌는 경우엔 출력에 `🔁 담당자: <이전> → <현재 유저 displayName>` 표기
4. `atlassianUserInfo` 호출이 실패하거나 accountId 를 못 얻으면 담당자 지정은 건너뛰고 경고만 출력 (작업 시작 자체는 막지 않음)

> Cloud Jira 는 username 이 아니라 `accountId` 만 받습니다. 절대로 email/username 으로 assignee 를 패치하지 마세요.

### 5. Jira 상태 전환

- 이슈 상태를 **"In Progress"** 로 전환 (`getTransitionsForJiraIssue` → `transitionJiraIssue`)
- 코멘트 추가: `작업 시작: feature/<ISSUE-KEY> 브랜치 생성 (스택: <감지된 스택>, 담당: <현재 유저 displayName>)`

### 6. 작업 컨텍스트 출력

```
✅ <ISSUE-KEY> 작업 시작
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 제목: <이슈 제목>
🎯 우선순위: <우선순위>
📌 상태: <이전 상태> → In Progress
👤 담당자: <현재 유저 displayName> (<accountId 앞 8자>)
🔧 스택: <감지된 스택>

📝 주요 작업 내용:
<이슈 설명 요약>

🌿 브랜치: feature/<ISSUE-KEY>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

다음 단계: 개발 작업 수행 후 /jira-test 실행
```

## Error Handling

- 이슈가 존재하지 않으면 오류 메시지 출력
- 이미 In Progress인 이슈는 경고 후 계속 진행
- 담당자가 다른 사람이었다면 경고가 아니라 **현재 유저로 재지정** 후 변경 사실을 출력 (Step 4 참조). 단, 부모 이슈에 별도 owner 지정 컨벤션이 있는 경우 (예: PM 고정 담당) 사용자가 명시적으로 거부하면 스킵.
- Git 브랜치가 이미 존재하면 체크아웃만 수행

## --subtasks Mode

사용자가 `/jira-start <KEY> --subtasks` 로 호출하고 부모 이슈에 하위 작업이 있으면, 부모 처리 후 **추가로** 다음을 수행:

1. 부모 이슈의 `subtasks` 필드에서 하위 키 목록 추출
2. 각 하위 이슈에 대해:
   - **담당자 = 현재 유저** 로 지정 (Step 4 와 동일 로직 — accountId 비교 후 변경 시에만 patch)
   - **In Progress 전환** (transitionJiraIssue, 부모와 동일 transition ID)
   - **짧은 댓글** 추가 (1~2 줄, 예: "🚀 부모 `<PARENT>` 의 일부로 작업 시작. 같은 feature 브랜치 `feat/<PARENT>` 공유.")
3. 새 브랜치는 부모 키 기준만 생성 (하위별 브랜치 X — touched-files 가 disjoint 하면 한 브랜치 내 동시 수정)
4. 출력에 부모 + 하위별 결과 표 포함

자세한 정책: `~/.claude/skills/_subtasks-convention.md` § 3 (스킬별 액션 매트릭스), § 5 (댓글 템플릿)
