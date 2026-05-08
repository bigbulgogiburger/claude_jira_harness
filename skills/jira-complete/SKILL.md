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
  - "In Review", "Review", "QA", "Done" 등 적절한 전환 선택
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

### 4.5. Harness Runtime 산출물 Archive (Harness 사용 프로젝트만)

`.claude/runtime/aggregate-verdict.md` 또는 `.claude/runtime/workflow-state.json`이 존재할 때만 실행한다. 둘 다 없으면 이 단계 전체 스킵 (Harness 미사용 프로젝트).

**왜 이 시점인가**: jira-complete은 사용자가 명시적으로 `<ISSUE-KEY>`를 전달해서 호출하므로, 어떤 이슈의 산출물을 archive할지 모호성이 없다. 다음 jira-start이 호출되어 runtime을 새 이슈로 덮어쓰기 전에 보존해야 verdict가 휘발되지 않는다. PR 머지는 이 시점 이후 외부에서 일어나므로 머지 SHA/date는 알 수 없지만, archive 후 `harness-score`가 git log로 backfill하므로 무방하다.

**원칙**: 멱등하게 동작한다. 같은 이슈로 두 번 호출되면 archive 디렉토리를 덮어쓴다 (In Review에서 추가 commit 발생 후 jira-complete 재호출 시 verdict 갱신 가능).

#### 절차

1. **archive 디렉토리 준비**
   ```bash
   mkdir -p .claude/runtime/archive/<ISSUE-KEY>
   ```

2. **runtime 산출물 이동/복사** (존재하는 것만)

   | 원본 | 대상 | 동작 |
   |------|------|------|
   | `.claude/runtime/aggregate-verdict.md` | `archive/<ISSUE-KEY>/aggregate-verdict.md` | 이동 |
   | `.claude/runtime/workflow-state.json` | `archive/<ISSUE-KEY>/workflow-state.json` | 이동 |
   | `.claude/runtime/checkpoint.md` | `archive/<ISSUE-KEY>/checkpoint.md` | 이동 (있으면) |
   | `.claude/runtime/changed-files.txt` | `archive/<ISSUE-KEY>/changed-files.txt` | 이동 (있으면) |
   | `.claude/runtime/sprint-contract/<ISSUE-KEY>.md` | `archive/<ISSUE-KEY>/<ISSUE-KEY>.md` | **복사** (sprint-contract는 다음 이슈에서도 참조 가능하므로 원본 유지) |

3. **INDEX.md 등재** (`archive/INDEX.md`)

   기존 표에 행 추가. 멱등성을 위해 같은 이슈 키 행이 이미 있으면 교체, 없으면 추가:
   ```markdown
   | <ISSUE-KEY> | feature/<ISSUE-KEY> | <Verdict> | <Iter>/3 | (pending) | <YYYY-MM-DD> | jira-complete으로 archive (머지 SHA는 harness-score가 backfill) |
   ```

   - **Verdict/Iter**: 방금 이동한 `archive/<ISSUE-KEY>/aggregate-verdict.md`의 Metadata 섹션에서 추출
   - **Merged 컬럼**: jira-complete 시점에는 미머지이므로 `(pending)` 기록. `harness-score`가 7일 후 채점할 때 git log에서 머지 SHA + 날짜를 backfill
   - **Archived**: 오늘 날짜 (KST)
   - INDEX.md가 없으면 헤더부터 새로 만들지 말고 경고만 출력 (이는 Harness 미설치 표시)

4. **사용자에게 알림**
   ```
   📦 Harness archive
     archive/<ISSUE-KEY>/ 에 verdict + state 보존
     INDEX.md 등재 (Merged: pending — 7일 후 /harness-score로 backfill)
   ```

#### 멱등성 + 안전 규칙

- 이미 `archive/<ISSUE-KEY>/`가 있으면 **덮어쓰기**한다 (재호출 시 최신 verdict 반영). 단, 기존 파일 중 `aggregate-verdict.md`에 `## Post-merge Scoring` 섹션이 비어있지 않으면 (이미 채점됨) 덮어쓰기 전 사용자 확인을 받는다.
- runtime 원본 파일이 없으면 그 파일만 스킵하고 나머지는 정상 진행한다.
- 이 단계가 실패해도 jira-complete의 다른 단계를 막지 않는다 (push/Jira 상태 전환은 이미 완료된 상태). 실패 시 경고만 출력.

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
📦 Harness archive: <archive 경로> (Harness 사용 시)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

다음 단계: Pull Request 생성
  - 머지 후 7일이 지나면 /harness-score <ISSUE-KEY>로 사후 채점 가능
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

## --subtasks Mode

사용자가 `/jira-complete <KEY> --subtasks` 로 호출 시:

1. 부모 처리 (검증 + push + QA 전이 + archive + 댓글) 그대로 수행
2. **모든 하위 이슈** QA(또는 동등) 상태로 일괄 transition + 짧은 댓글:
   ```
   ✅ 부모 `<KEY>` 와 동시 QA 전이.
   통합 결과 + harness verdict + archive 경로는 부모 댓글 참조.
   ```
3. 하위 이슈가 현재 To Do 상태라면 "To Do → In Progress → QA" 다단계 transition 자동 적용 (사후 보정 케이스 대응)
4. transition 권한 부족 / 실패 시 누적 → 출력에 ❌ 표시 + 사유. 부모 작업은 계속.
5. 출력에 부모 + 하위별 transition 결과 표 포함

자세한 정책: `~/.claude/skills/_subtasks-convention.md` § 3, § 5, § 8 (사후 보정)
