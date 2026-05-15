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
/jira-complete <ISSUE-KEY>                            # 기본
/jira-complete <ISSUE-KEY> --no-organize              # CLAUDE.md 위생 자동 organize 호출 스킵
/jira-complete <ISSUE-KEY> --subtasks                 # 부모 + 하위 일괄 QA 전이 (ADR-070)
/jira-complete <ISSUE-KEY> --subtasks --no-organize   # 두 플래그 동시 사용 가능
```

- `ISSUE-KEY`: Jira 이슈 키 (예: PROJ-20)
- `--no-organize`: §4.6 위생 체크는 수행하되 임계점 도달 시 organize-claude-md 자동 호출은 스킵하고 권고 메시지만 출력. 나중에 별도로 organize 를 돌리고 싶을 때.
- `--subtasks`: 부모 + 모든 하위 이슈 일괄 QA 전이. 자세한 정책은 `~/.claude/skills/_subtasks-convention.md`.

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

### 4.4. Wiki Ingest 자동 Chain (closure 단계) — **MANDATORY**

> ⛔ **이 단계는 선택 사항 아님.** QA 전환이 막 끝났고 사용자가 명시적으로 `<ISSUE-KEY>` 를 전달했으므로, **wiki INDEX 의 해당 이슈 row 를 closed 로 전환할 유일한 정상 시점**이다. archive (§4.5) 보다 먼저 수행하는 이유: archive 가 runtime 산출물을 이동시키기 전에 INDEX/LOG 가 archive 경로를 참조할 수 있도록.
>
> 본 chain 누락 시 wiki 가 drift 한다: INDEX row 가 영구히 `planned` 또는 미존재 → wiki-lint L14 (Jira/INDEX 불일치) 가 다음 호출마다 위반 보고. 사용자에게 "ingest 할까요?" 라고 물어보지 않는다 (조용한 누락 방지 — 명시적 `--no-ingest` 플래그만 인정).

**왜 이 시점인가**: Jira QA 전환은 closure 의 정식 단언. archive 가 일어나기 전에 INDEX status 를 `planned → closed` 로 전환해야 wiki-lint L14 (Jira/INDEX 불일치) 가 다음 호출에서 정상 PASS.

**자기 점검 (skill 종료 직전 last-mile check)**:
1. `docs/INDEX-SCHEMA.md` 존재? → 존재하면 본 §4.4 chain 호출 흔적이 conversation 에 있어야 함
2. 호출 흔적 없으면 → **지금 즉시 호출** + 사용자에게 "§4.4 chain 누락 감지 → 사후 호출함" 1줄 보고
3. 그래도 호출 못 한 사유 (skill 부재 등) 가 있으면 사용자에게 명시 경고 (조용한 skip 금지)

> 💡 **harness-workflow 또는 직접 호출 무관** — `/jira-complete` 가 호출되는 모든 경로에서 본 chain 은 반드시 발화. harness-workflow Phase 7 이 jira-complete skill 호출 없이 직접 transition/push 만 수행하면 본 chain 이 통째로 누락된다 (2026-05-14 PROJ-208 사고). harness-workflow 도 반드시 `Skill('jira-complete', ...)` 로 진입해야 §4.4 + §4.7 둘 다 발화 보장.

#### 조건

```
실행 조건: docs/INDEX-SCHEMA.md 존재 AND 사용자가 --no-ingest 플래그 전달 안 함
```

조건 미충족 시 전체 §4.4 skip (wiki 미설정 프로젝트).

#### 절차

Skill tool 로 jira-ingest 호출:
```
Skill('jira-ingest', '<ISSUE-KEY> closure 모드로 ingest — Jira QA 전환 완료, INDEX status 갱신 + cross-ref 보강')
```

`--subtasks` 모드면 flag 자동 전파:
```
Skill('jira-ingest', '<ISSUE-KEY> closure --subtasks')
```

jira-ingest 가 수행:
- INDEX.md 의 row 갱신 (status=closed, closed=<today>)
- LOG.md append (CLOSURE + INGEST closure 2줄)
- `08-decision-log.md` 관련 ADR 의 ingest-managed 블록 갱신 (Referenced by 추가)
- sprint/weeks/w*.md 의 ingest-managed 블록 갱신 (closure 라인)
- sprint/tracks/*.md 동일

#### 멱등성 + 안전

- 같은 이슈로 jira-complete 재호출 시 (In Review 추가 commit 후) → 같은 closure 다시 호출해도 INDEX/LOG 동일 결과 (jira-ingest 멱등성)
- ingest 실패 시 경고만 출력하고 §4.5 archive 로 계속 진행 (jira-complete 의 다른 단계 막지 않음)
- **forbidden 파일은 절대 touch X** — `_wiki-schema.md` § 10 bounded_writes 정책

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

### 4.6. CLAUDE.md 위생 체크 + 자동 organize 호출

이슈 closure 가 commit 메시지 + Jira 댓글에 반영되었고, 사용자가 CLAUDE.md "오늘 closure / Last Updated" 라인을 갱신했을 가능성이 높은 시점이다. push + QA 전환이 이미 끝났으므로 흐름 단절 위험 없이 위생 체크 + 임계점 도달 시 organize 를 자동 진입할 수 있다.

**원칙 — 임계점 도달 시 자동 호출, 미달 시 no-op**:
- 줄 수 + closure 카운트는 jira-complete 안에서 lightweight 하게 계산한다 (수십 ms, 컨텍스트 부담 없음).
- **임계점 도달 → Skill tool 로 `/organize-claude-md` 자동 호출**. organize 자체가 Phase 6 (실행 전 사용자 확인) 단계를 가지고 있어 데이터 안전성이 보장된다 — 사용자가 변경 계획을 보고 승인해야 실제 재구성이 일어난다. 즉 "자동 진입 + 사용자 승인" 의 2단 구조.
- **임계점 미달 → 한 줄 로그만 출력**. organize 호출 안 함 (Phase 1-5 무거운 분석 회피).
- 이 단계가 실패해도 jira-complete 의 다른 단계를 막지 않는다 (push/QA 전환은 이미 완료). organize 호출 실패 시 경고만 출력.

**왜 이 시점인가**: organize-claude-md 의 트리거 임계점 ("Last Updated 3K 토큰 또는 5회 closure 누적") 평가는 **새 closure 가 CLAUDE.md 에 반영된 직후** 가장 정확하다. jira-commit 직후도 후보지만 commit 책임 (DoD + Jira 댓글) 과 분리하는 게 깔끔하고, jira-complete 은 "이슈 마감 = 정리 시점" 의 의미가 자연스럽다.

#### 절차

1. **점검 대상 CLAUDE.md 수집**
   - 현재 작업 디렉토리 + sub-project 디렉토리 모두 스캔
   - 단일 프로젝트: `./CLAUDE.md` 1개
   - Monorepo (root `CLAUDE.md` 에 `Sub-Projects` 표 또는 sub 디렉토리에 별도 `CLAUDE.md` 존재): root + 각 sub 의 `CLAUDE.md` 모두
   - 파일 부재 시 그 항목만 스킵 (경고 없음)

2. **임계점 평가** (각 CLAUDE.md 별, 모두 OR 조건)

   | 지표 | 임계점 |
   |------|--------|
   | 줄 수 | 단일 프로젝트 120 초과 / monorepo root 150 초과 / sub 120 초과 |
   | 누적 closure 라인 수 | 5개 이상 (`Last Updated:` 라인부터 EOF 영역에서 `^- (PROJ-|PROJ-|[A-Z]+-)\d+` 패턴 또는 `**오늘 closure` 헤더 개수) |
   | "Last Updated" 섹션 크기 | 약 3K 토큰 이상 (대략 12,000 자 — 1 token ≈ 4 chars 기준) |

   - Monorepo 판단 기준: root CLAUDE.md 에 `## Sub-Projects` / `## Sub Projects` 표가 있거나, sub 디렉토리에 자체 CLAUDE.md 가 존재. 둘 다 아니면 단일 프로젝트 (120 임계점 적용).
   - 최소 1개 파일이라도 임계점 초과 → 임계점 도달로 판정.

3. **결과 출력 + 분기**

   **(A) 임계점 도달** — 결과 표시 후 organize 자동 진입:
   ```
   📋 CLAUDE.md 위생 체크 — 임계점 도달
     ⚠️  <경로>: <N>줄 (한계 <limit>) / closure <M>회 / Last Updated ~<K>K chars
     ✅ <다른 경로>: 정상 (<N>줄 / closure <M>회)

   → /organize-claude-md 자동 호출 (Phase 6 에서 변경 계획 확인 후 승인 필요)
   ```

   이어서 **Skill tool 로 `organize-claude-md` 를 호출**한다.
   - 인자 없이 호출 (= git diff 기반 증분 모드, organize SKILL.md `(빈 값)` 인자). CLAUDE.md `Last Updated` 라인 기준으로 변경된 파일만 감지하여 영향받는 reference 만 선택적 갱신 → 가장 효율적.
   - Monorepo 의 경우 organize 가 자체적으로 monorepo 감지 (Phase 1-2) + root/sub 모두 처리하므로 단일 호출로 충분.
   - organize Phase 6 에서 사용자가 변경 계획을 보고 승인/거부 — 거부 시 organize 자체가 종료되고 jira-complete 의 §5 결과 출력 단계로 자연 진행.

   **(B) 임계점 미달** — 한 줄 로그만:
   ```
   📋 CLAUDE.md 위생: 정상 (재구성 불필요)
   ```

   **(C) 점검 대상 없음** (Harness 미사용 + CLAUDE.md 없는 프로젝트):
   ```
   📋 CLAUDE.md 위생: 점검 대상 없음 (CLAUDE.md 부재)
   ```

#### 안전 규칙

- 위생 체크 단계 자체는 read-only. CLAUDE.md 수정은 오직 자동 호출된 organize-claude-md 가 Phase 6 사용자 승인 후에만 수행한다.
- 파일 읽기 실패 / 권한 오류 등은 경고만 출력하고 다른 파일 점검은 계속한다.
- organize 자동 호출이 실패하면 (Skill tool 부재, organize 내부 오류 등) 경고만 출력하고 §5 결과 출력 단계로 계속 진행한다. jira-complete 의 핵심 책임 (push/QA 전환/archive) 은 이미 완료된 상태라 막지 않는다.
- **회피 옵션**: 사용자가 `/jira-complete <KEY> --no-organize` 로 호출하면 §4.6 의 임계점 평가 후 자동 호출을 스킵하고 권고 메시지만 출력. organize 를 나중에 별도로 돌리고 싶을 때 사용.
- **재호출 시 멱등성**: 이미 동일 이슈로 jira-complete 을 재호출한 경우 (In Review 추가 commit 후 재호출) organize 가 다시 임계점 체크 → 이전 organize 가 이미 정리했으면 미달로 빠지므로 자동 호출 안 함. organize 가 idempotent 한 것에 의존.

### 4.7. Wiki Lint 자동 Chain (high severity 만, non-blocking) — **MANDATORY (조건부)**

> ⛔ **이 단계는 선택 사항 아님.** §4.4 ingest closure 가 끝났고 §4.6 organize 도 끝났다 — 이제 wiki 전체 정합성 빠르게 점검할 **유일한 정상 시점**. **high severity 위반만 노출** + non-blocking → cycle 안에서 알람 피로 zero.
>
> 본 chain 누락 시: 방금 ingest 가 만든 broken xref / parent-sibling 비대칭이 다음 jira-plan 까지 잠복 → 그 때는 누가 그 위반을 만들었는지 추적 비용 증가. 본 cycle 안에서 발견하는 게 가장 저렴.
>
> 사용자에게 "lint 할까요?" 라고 물어보지 않는다 — 명시적 `--no-lint` 플래그만 인정.

**왜 이 시점인가**: 방금 이슈가 closed 됐고 ADR/sprint cross-ref 가 갱신됐다. 만약 갱신 과정에서 broken xref / parent-sibling 비대칭 등이 생겼으면 즉시 발견하는 게 가장 저렴. 사용자는 cycle 직후라 컨텍스트 신선 — 5건 이내 위반은 즉시 확인 가능.

**자기 점검 (skill 종료 직전 last-mile check)**:
1. `docs/INDEX-SCHEMA.md` + `docs/INDEX.md` 존재 AND `--no-lint` 부재? → 본 §4.7 chain 호출 흔적이 conversation 에 있어야 함
2. 호출 흔적 없으면 → **지금 즉시 호출** + 사용자에게 "§4.7 chain 누락 감지 → 사후 호출함" 1줄 보고
3. 그래도 호출 못 한 사유가 있으면 사용자에게 명시 경고 (조용한 skip 금지)

#### 조건

```
실행 조건: docs/INDEX-SCHEMA.md 존재 AND docs/INDEX.md 존재 AND --no-lint 플래그 없음
```

조건 미충족 시 전체 §4.7 skip.

#### 절차

```
Skill('wiki-lint', '요약 점검해줘 — high severity 만, non-blocking. cycle 직후라 신선한 상태에서 위반 빠르게 확인')
```

wiki-lint 가 수행:
- §1.3 의 14 rule 중 severity=high 인 것만 (L01, L02, L05, L09, L10) 우선 실행
- summary 모드 출력 (상위 5건 미리보기)
- write 안 함 (read-only). `--fix` 의도 없음.

#### 안전 규칙

- lint 실패해도 §5 결과 출력 진행 (jira-complete 의 책임 단계 — push/QA/archive — 는 이미 완료)
- wiki-lint 도 실패 격리 (각 rule 독립 try-catch)
- lint 가 위반 N건 보고했어도 jira-complete 자체는 PASS 로 종료. 사용자가 별도로 `/wiki-lint --fix` 또는 자동수정 의도 표명 시 다음 행동.

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
📋 CLAUDE.md 위생: <정상 | 임계점 도달 — /organize-claude-md 자동 호출됨 | 사용자 거부됨 | --no-organize 스킵>
📚 Wiki ingest: <closure 등록 완료 — INDEX.md row 갱신, cross-ref N건 보강 | skip (wiki 미설정) | --no-ingest 스킵>
🔍 Wiki lint: <PASS — high 위반 0건 | high 위반 N건 — '/wiki-lint --full' 권고 | skip (wiki 미설정) | --no-lint 스킵>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

다음 단계: Pull Request 생성
  - 머지 후 7일이 지나면 /harness-score <ISSUE-KEY>로 사후 채점 가능
  - CLAUDE.md 위생 임계점 도달 시 /organize-claude-md 가 자동 호출되어 Phase 6 사용자 승인 후 재구성됨 (--no-organize 로 스킵 가능)
  - Wiki lint 가 high 위반 보고했으면 '/wiki-lint --full' 로 상세 확인 또는 '자동 수정해줘' 의도로 fixable 항목 일괄 처리 가능
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
