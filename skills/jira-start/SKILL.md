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

### 4. Jira 상태 전환

- 이슈 상태를 **"In Progress"** 로 전환 (`getTransitionsForJiraIssue` → `transitionJiraIssue`)
- 코멘트 추가: `작업 시작: feature/<ISSUE-KEY> 브랜치 생성 (스택: <감지된 스택>)`

### 5. 작업 컨텍스트 출력

```
✅ <ISSUE-KEY> 작업 시작
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 제목: <이슈 제목>
🎯 우선순위: <우선순위>
📌 상태: <이전 상태> → In Progress
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
- 담당자가 다른 사람이면 경고 메시지 출력
- Git 브랜치가 이미 존재하면 체크아웃만 수행
