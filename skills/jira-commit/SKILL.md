---
name: jira-commit
description: "jira-commit — 스택별 DoD(Definition of Done)를 검증한 뒤 변경사항을 커밋하고 Jira 이슈에 진행 상황을 한글 댓글로 업데이트합니다. 테스트 통과 후 커밋이 필요할 때, '커밋해줘', '커밋 메시지 작성', 'Jira에 진행 상황 남겨줘', 'DoD 체크', 'jira commit', '이슈 업데이트해줘' 등의 요청에 이 스킬을 사용하세요. /jira-test 이후, /jira-complete 이전에 사용합니다."
---

# jira-commit — 커밋 및 Jira 진행 상황 업데이트

스택별 DoD(Definition of Done)를 검증한 뒤 변경사항을 커밋하고 Jira 이슈에 진행 상황을 업데이트합니다.
지라에 댓글이나 설명을 작성할 때에는 한글로 작성합니다.
Jira API에 보내는 텍스트에 리터럴 `\n` 문자열을 넣지 마라 — Jira가 줄바꿈으로 해석 못하고 텍스트가 깨진다. 실제 개행문자를 사용할 것.

## Usage

```
/jira-commit <ISSUE-KEY> [commit-message]
```

- `ISSUE-KEY`: Jira 이슈 키 (예: SURINP-20)
- `commit-message` (선택): 커밋 메시지. 미입력 시 변경사항 분석 후 자동 생성

## Commit Message Format

```
<type>(<ISSUE-KEY>): <description>

[optional body]
```

**Types:** feat, fix, refactor, docs, test, chore, perf, ci

## Procedure

### 1. 스택 감지

작업 디렉토리에서 프로젝트 스택을 자동 감지합니다.

### 2. DoD 검증

감지된 스택에 맞는 DoD 체크리스트를 검증합니다.
각 스택의 상세 DoD는 `references/` 디렉토리를 참조합니다.

#### 공통 DoD

모든 스택에서 검증하는 항목:
- [ ] 하드코딩된 시크릿 없음 (API 키, 비밀번호 등)
- [ ] console.log / print / System.out.println 등 디버그 출력 없음
- [ ] 커밋되지 않은 변경사항 확인
- [ ] 불필요한 파일 (.env, credentials 등) 미포함

### 3. 변경사항 확인

```bash
git status
git diff --stat
```

### 4. Git 커밋

```bash
git add <relevant-files>
git commit -m "<type>(<ISSUE-KEY>): <description>"
```

- 관련 파일만 선택적으로 staging (`git add .` 지양)
- Conventional Commits 형식 준수

### 5. Jira 이슈 코멘트

MCP Atlassian 도구로 코멘트를 추가합니다:

```
✅ 진행 상황 업데이트

📝 커밋: <commit-message>
📊 변경사항:
- 파일 수: X개
- 추가: +XXX줄
- 삭제: -XXX줄

🔗 커밋 SHA: <short-sha>
```

### 6. 결과 출력

```
📝 커밋 완료
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 변경사항:
  <file-stats>

🔒 커밋: <type>(<ISSUE-KEY>): <description>
✅ Jira 업데이트: <ISSUE-KEY>에 코멘트 추가
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

다음 단계:
  - 더 작업할 내용이 있으면 계속 개발
  - 완료되었으면 /jira-complete <ISSUE-KEY> 실행
```

## Error Handling

- 변경사항이 없으면 오류 메시지
- DoD 검증 실패 시 실패 항목 표시 후 수정 안내
- Jira 업데이트 실패 시 경고 (커밋은 유지)

## Notes

- 작은 단위로 자주 커밋하는 것을 권장
- CLAUDE.md에 프로젝트별 커밋 규칙이 있으면 해당 규칙 우선 적용

## --subtasks Mode

사용자가 `/jira-commit <KEY> --subtasks` 로 호출 시:

1. 부모 commit + 댓글 (기존 절차) — 1개 commit 에 N slice 변경 모두 포함
2. **모든 하위 이슈에 짧은 댓글** 추가 (commit SHA 인용):
   ```
   ✅ commit `<SHA>` 에 통합 (부모 `<KEY>` 와 동일 commit, N slice 묶음).
   변경 파일 + 검증 결과 + harness verdict 은 부모 댓글 참조.
   ```
3. 하위 이슈는 별도 transition 안 함 (commit 단계는 status 변경 없음 — 부모와 동일)
4. 출력에 부모 + 하위별 댓글 추가 결과 표 포함

자세한 정책: `~/.claude/skills/_subtasks-convention.md` § 3, § 5
