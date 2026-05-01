---
name: jira-complete
description: "jira-complete — Jira 티켓 작업을 완료하고 최종 검증(빌드/테스트/Lint/DoD)을 수행한 뒤 QA 상태로 전환합니다. 모든 커밋이 끝나고 작업 마무리가 필요할 때, '작업 완료', '마무리해줘', 'QA로 넘겨줘', '최종 검증', '티켓 완료 처리', 'jira complete', '이슈 마감' 등의 요청에 이 스킬을 사용하세요. Jira 워크플로우의 마지막 단계로, /jira-commit 이후에 사용합니다."
---

# jira-complete — 작업 완료 및 최종 검증

Jira 티켓 작업을 완료하고 최종 검증을 수행한 뒤 QA 상태로 전환합니다.
지라에 댓글이나 설명을 작성할 때에는 한글로 작성합니다.
Jira API에 보내는 텍스트에 리터럴 `\n` 문자열을 넣지 마라 — Jira가 줄바꿈으로 해석 못하고 텍스트가 깨진다. 실제 개행문자를 사용할 것.

## Usage

```
/jira-complete <ISSUE-KEY>
```

- `ISSUE-KEY`: Jira 이슈 키 (예: PROJ-20)

## Procedure

### 1. 스택 감지

작업 디렉토리에서 프로젝트 스택을 자동 감지합니다.

### 2. 최종 검증 체크리스트

스택에 맞는 품질 검증을 수행합니다:

#### 코드 품질 (스택별 자동 실행)

| 스택 | Lint | Test | Build |
|------|------|------|-------|
| Flutter | `flutter analyze` | `flutter test` | `flutter build` |
| Spring Boot | built-in | `./gradlew test` (Windows: `gradlew.bat test`) | `./gradlew build -x test` |
| Vue.js | `npm run lint` | `npm test` | `npm run build` |
| React | `npm run lint` | `npm test` | `npm run build` |
| Go | `go vet ./...` | `go test ./...` | `go build ./...` |
| Python | `ruff check .` 또는 `flake8` | `pytest` | — |

**CLAUDE.md에 커스텀 명령이 정의되어 있으면 해당 명령을 우선 사용합니다.**

#### Git 상태
- ✅ 모든 변경사항이 커밋됨
- ✅ 브랜치가 최신 main/master과 충돌 없음

### 3. Git Push

```bash
git push -u origin feature/<ISSUE-KEY>
```

### 4. Jira 상태 전환

- 이슈 상태를 **"In Review"** 또는 **QA 가능한 다음 상태**로 전환
  - `getTransitionsForJiraIssue`로 가용 전환 목록 조회
  - 우선순위: "In Review" → "Review" → "QA" → 그 외 중간 상태
  - **위 상태가 모두 없으면 "완료" / "Done" 으로 전환** (단순 워크플로 보드 fallback)
  - 사용자 확인 없이 자동 전환 가능 — 단, "완료" 전환 시 잔여 작업이 있으면 코멘트에 명시
- 최종 코멘트 추가:

```
✅ 작업 완료

📊 작업 요약:
- 총 커밋 수: X개
- 변경된 파일: XX개
- 추가: +XXX줄
- 삭제: -XXX줄

✅ 검증 완료:
- Lint: 통과
- Test: 통과
- Build: 성공

🌿 브랜치: feature/<ISSUE-KEY>
🔧 스택: <감지된 스택>
```

### 5. 결과 출력

```
🔍 최종 검증 완료
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ 코드 품질 검증
  ✅ Lint: 통과
  ✅ Test: 통과
  ✅ Build: 성공

✅ Git 상태 검증
  ✅ 미커밋 변경사항: 없음

📊 작업 요약:
  총 커밋 수: X개
  변경된 파일: XX개

✅ Git Push 완료
✅ Jira 상태 업데이트: <새 상태>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

다음 단계: Pull Request 생성
```

## Error Handling

### 검증 실패 시
```
❌ 최종 검증 실패

다음 항목을 해결해주세요:
  ❌ <실패 항목>

완료 처리를 계속하려면 위 문제를 해결해주세요.
```

- 검증 실패 시 push/상태 전환을 수행하지 않음
- Jira 업데이트 실패 시 경고 (push는 유지)

## Notes

- 완료 처리는 신중하게 수행
- QA 전환 상태명은 Jira 프로젝트 워크플로에 따라 다를 수 있음 — 가용 전환 목록에서 자동 선택
