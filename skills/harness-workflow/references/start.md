# start — 이슈 착수 (구 /jira-start 흡수, 2026-07-20 명령 표면 축소)

> harness-workflow ① start 단계의 상세 절차. 단독 슬래시 명령은 폐기됨 — 이 문서는 workflow 진입 시에만 Read.

## 절차

1. **스택 감지** — `~/.claude/skills/_stack-detection.md` §1 매핑으로 프로젝트 스택 파악.
2. **Jira 이슈 조회** — `mcp__atlassian__getJiraIssue`: 상태·제목·설명·우선순위·subtasks.
3. **브랜치 생성** — `git checkout -b feat/<KEY>` (프로젝트 컨벤션 우선 — 예: `feat/PROJ-N`).
   - 이미 존재하면 체크아웃만. 미커밋 변경 있으면 경고.
   - 다중부모 fan-out 이면 브랜치 전략은 `parallel-modes.md` 참조 (worktree 별 브랜치).
4. **담당자 지정** — `mcp__atlassian__atlassianUserInfo` 로 현재 유저 `accountId` 확보 → 기존 assignee 와 다르면 `editJiraIssue` 로 패치 (Cloud Jira 는 accountId 만 유효, email/username 금지). 실패 시 경고만 하고 진행.
5. **In Progress 전환** — `getTransitionsForJiraIssue` → `transitionJiraIssue` + 한글 댓글 1줄: `작업 시작: feat/<KEY> 브랜치 (스택: <스택>, 담당: <displayName>)`.
6. 병렬 이슈(부모 N개)면 각 이슈에 대해 2~5 반복.

## 에러 처리

- 이슈 미존재 → 중단 보고. 이미 In Progress → 경고 후 계속. 브랜치 존재 → 체크아웃만.
- Jira 쓰기 실패(ratelimit) → deferred queue 메모 후 작업 자체는 진행 (운영 실측).
