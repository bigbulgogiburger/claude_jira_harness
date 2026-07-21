# gate — 통합 검증 + 커밋 (구 /jira-test + /jira-commit 흡수, 2026-07-20 명령 표면 축소)

> harness-workflow ⑦ gate 단계의 상세 절차. 단독 슬래시 명령은 폐기됨.
> 순서: **테스트 → /harness-gate 스킬(verdict 확인 포함) → DoD → commit → Jira 댓글**.

## 1. 스택별 통합 테스트

CLAUDE.md 에 프로젝트별 명령이 정의돼 있으면 **그것이 우선** (예: BE `./gradlew build` — 데몬 ON, `--no-daemon` 은 Mockito 계열 깨짐 / FE `npm run test -- --run` + `npm run build`). 스택별 기본 패턴은 `test-stacks/*.md`.

| 카테고리 | 기준 |
|----------|------|
| Lint/Analyze | 오류 0 |
| Test | 실패 0 |
| Build | 성공 |

- 10분+ 장기 빌드는 **메인 세션 background Bash** 로 완주 (workflow 에이전트에 위임하면 미완 RED — 운영 실측). BE bootRun(DevTools) 가동 중 gradle test 는 클래스 삭제 레이스로 BE 를 죽인다 — 사전 TaskStop 또는 사후 health 확인 (운영 실측).
- 파이프로 exit code 를 마스킹하지 말 것 (가짜 GREEN — 운영 실측).
- 실패 시 커밋 금지. 원인 수정 후 재실행.

## 2. /harness-gate 호출

`Skill('harness-gate')` — aggregate-verdict PASS 확인 + 프로젝트 빌드/타입체크/린트 종합. GATE PASS 필수.

## 3. DoD 검증 (commit 직전)

공통: 하드코딩 시크릿 0 / 디버그 출력(console.log·System.out.println) 0 / .env·credentials 미포함 / 스테이징 파일이 전부 이슈 범위 내. 스택별 상세는 `dod/dod-*.md`.

## 4. Commit

```
<type>(<KEY>): <description>       # feat|fix|refactor|docs|test|chore|perf|ci
```

- 관련 파일만 선택적 staging (`git add .` 지양). 프로젝트 커밋 규칙(CLAUDE.md·rules/git-workflow.md)이 우선.
- **review-gate hook 이 물리 차단** (PreToolUse JSON deny): verdict ≠ PASS 면 commit 자체가 거부된다 (2026-07-20 수정 — 구 exit 1 은 비차단이었음). 차단되면 review 단계로 복귀.

## 5. Jira 진행 댓글

`addCommentToJiraIssue` 한글 댓글: 커밋 SHA·변경 파일 수·핵심 요약. 리터럴 `\n` 금지 (실제 개행). 다중부모/레인 병렬이었으면 각 이슈에 해당 레인 결과만 요약.
