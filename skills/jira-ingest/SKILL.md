---
name: jira-ingest
description: "jira-ingest — Karpathy LLM Wiki 패턴으로 docs/ 디렉토리에 영구 지식 wiki 를 구축·갱신합니다. dev-guide 가 생성/완료될 때마다 docs/INDEX.md (전체 카탈로그) + docs/LOG.md (이벤트 로그) + ADR/sprint cross-reference 를 점진적으로 자동 갱신합니다. 사용자가 'wiki 등록', 'INDEX 갱신', 'docs 인덱스', 'wiki 만들어줘', 'wiki 처음 설정', '이슈 카탈로그화', 'dev-guide ingest', '문서 인덱싱', 'docs/INDEX.md 갱신', 'cross-reference 보강', '문서 정합성 동기화' 등을 요청하거나, /jira-plan / /jira-complete 가 자동 chain 으로 호출할 때 트리거됩니다. 또한 사용자가 새 프로젝트에 합류해서 'wiki 시작하자', 'Karpathy 패턴 적용', 'LLM 위키 셋업' 같은 의도를 보이면 첫 실행 onboarding 모드로 진입합니다. 이 스킬은 어느 프로젝트에서나 작동 (user-scope) — docs/INDEX-SCHEMA.md 가 프로젝트별 정책을 보유합니다."
---

# jira-ingest — Wiki Index/Log/Cross-ref 점진 갱신

> **Karpathy LLM Wiki 패턴** — synthesis 를 query-time 이 아니라 build-time 에 누적.
> dev-guide 가 생성/완료될 때마다 INDEX·LOG·cross-ref 를 멱등하게 점진 갱신.
> SSoT: `~/.claude/skills/_wiki-schema.md` (정책·schema·규칙 전부 그곳).

## Usage

```
/jira-ingest <ISSUE-KEY>                 # 기본 (의도는 자연어로 전달 또는 컨텍스트 추론)
/jira-ingest <ISSUE-KEY> --subtasks      # 부모 + 슬라이스 일괄 (유일한 명시 플래그)
/jira-ingest                             # 인자 없이 — corpus 수준 의도 (bootstrap / backfill 등) 자연어로
```

**호출 모드는 사용자 자연어에서 추론**한다. 플래그 explosion 회피.
유일한 예외: `--subtasks` — `_subtasks-convention.md` 와 mechanical 일관성 필요.

## ⛔ Guard — Wiki 자산 존재 확인 (최우선)

스킬 시작 직후 다음 3 항목 점검. 결과에 따라 분기:

| 점검 | 부재 시 행동 |
|------|-------------|
| `docs/` 디렉토리 | 사용자에게 "docs/ 디렉토리 만들까요? 다른 경로 (예: `documentation/`) 사용하시나요?" 확인 |
| `docs/INDEX-SCHEMA.md` | **First-run onboarding flow** (§ 1) 진입 |
| `docs/INDEX.md` | **Bootstrap flow** (§ 2) 진입 (schema 는 있음 = onboarding 끝남) |

세 가지 모두 정상이면 → § 3 (정상 ingest) 로.

---

## § 1. First-run Onboarding — 새 프로젝트에서 처음 호출됐을 때

`docs/INDEX-SCHEMA.md` 가 없으면 wiki 자체가 미설정 상태. 사용자에게 안내 후 schema 부트스트랩.

### 1-1. ISSUE_PREFIX 추론

프로젝트 Jira 키 prefix 자동 감지 (예: `STD`, `PROJ`, `SCRUM`):

1. `CLAUDE.md` / `README.md` 에서 `\b[A-Z]+-\d+\b` 패턴 가장 빈도 높은 prefix
2. 추론 실패 시 `mcp__atlassian__getVisibleJiraProjects` → 사용자에게 어느 프로젝트인지 확인
3. 위 둘 다 실패 시 사용자에게 직접 질문 ("Jira 이슈 키 prefix 는? 예: STD")

### 1-2. 사용자 확인 + Schema 작성

`_wiki-schema.md` § 2 의 default schema 를 보여주고 (ISSUE_PREFIX 만 치환), 다음 확인:

```
🆕 첫 실행 감지 — 이 프로젝트는 아직 wiki 가 설정되지 않았습니다.

다음 자산을 생성합니다:
  📁 docs/INDEX-SCHEMA.md   (프로젝트 schema, git tracked)
  📁 docs/INDEX.md          (LLM-maintained 카탈로그)
  📁 docs/LOG.md            (이벤트 로그, append-only)

추론된 설정:
  ISSUE_PREFIX = <STD>
  카테고리     = foundational / decisions / issue_guides / sprint / setup (5종)
  bounded_writes.forbidden = PRD / DB schema / 코드 파일 일체

진행할까요? (yes / 카테고리 조정 / 취소)
```

사용자 승인 시:
- `docs/INDEX-SCHEMA.md` 작성 (default schema, ISSUE_PREFIX 치환)
- `docs/INDEX.md` 빈 골격 작성 (헤더 + ingest-managed 마커)
- `docs/LOG.md` 헤더 1줄 + BOOTSTRAP 라인

이어서 § 1-3 (CLAUDE.md 보강 안내) → § 2 bootstrap 으로 자동 진행.

### 1-3. CLAUDE.md 보강 안내 — wiki 자산 가시화

`_wiki-schema.md` § 15 의 `claude_md_integration` 정책 적용 (default `auto-patch`).

**왜 필요한가**: 미래 LLM 세션은 CLAUDE.md 만 자동 로드 → 이 안내가 없으면 INDEX.md / LOG.md 의 존재를 모르고 dev-guide 작업 중 wiki 활용 안 함.

**탐지**:
```
CLAUDE.md grep "docs/INDEX.md"
  매칭 있음 → 이미 안내됨, 생략
  매칭 없음 → 보강 진행
```

**announce 모드 (CLAUDE.md 무수정 — schema 에서 명시적으로 선택 시)**:

```
📌 권장: CLAUDE.md 에 wiki 자산 안내를 추가하세요
   (jira-ingest 는 CLAUDE.md 를 자동 수정하지 않습니다 — 사용자가 직접 commit)

"Planning Docs" 또는 "Reference Docs" 표 끝에 다음 3 row:

| Wiki Index  | dev-guide 카탈로그·상태 조회        | docs/INDEX.md         |
| Wiki Log    | ingest 이벤트 로그 (append-only)    | docs/LOG.md           |
| Wiki Schema | 카테고리·정책 (사용자 편집)         | docs/INDEX-SCHEMA.md  |

또는 "Key Rules" 에 1줄 추가:
- **ALWAYS** 새 dev-guide 작성 후 자동으로 INDEX/LOG 갱신
  (jira-plan / jira-complete chain. 누락 시 `/jira-ingest <KEY>` 수동 호출)
```

**auto-patch 모드 (default)**:
- "Planning Docs 표 끝에 3 row 를 자동 추가할까요? [y/n]" 1회 confirm
- y → Edit 툴로 target_section 헤더 직후 표 끝 anchor 찾아 append
- 표 헤더 매칭 실패 시 → announce 폴백

**skip 모드**: 안내 자체 생략 (실험적 셋업 또는 wiki 가 일시적).

---

## § 2. Bootstrap — 기존 dev-guide 일제 카탈로그화

`docs/INDEX-SCHEMA.md` 는 있는데 `docs/INDEX.md` 가 없거나 비어있으면, 또는 사용자가 "bootstrap" / "처음 카탈로그화" 의도를 보이면.

### 2-1. 5+1 Pass 알고리즘

**Pass 1: Inventory** (glob 만, ~1분)
```
glob: docs/**/*.md, sprint/**, setup/**, ops/**, qa/**, external/**, data/**
match → INDEX-SCHEMA.categories
read 안 함 — 카테고리 분류만
```

**Pass 2: Metadata extraction** (batch, ~10분)
파일 read + `_wiki-schema.md` § 4 의 6단계 fallback chain 적용.
100+ 파일은 10개씩 batch (context window 보호).

**Pass 3: Cross-ref graph 구축**
- parent / siblings / related_adrs 그래프 양방향 검증
- 비대칭 검출 시 LOG 에 warning, 자동 수정 X (wiki-lint L07 영역)

**Pass 4: Render INDEX.md**
- 카테고리별 표 생성
- 정렬: week 역순 + key 내림차순 (이슈 가이드)
- 빈 cell = `-`
- ingest-managed 마커 전체 둘러쌈

**Pass 5: LOG.md 백필**
- entry 별 `git log --diff-filter=A --reverse --format=%cI -- <file>` → created
- `git log -1 --format=%cI -- <file>` → last_activity
- status 추론: archive 디렉토리 / closed_date / Jira 상태 (선택)
- 시간순 INGEST 라인 append

**Pass 6 (옵션): Type 휴리스틱 confirm**
multi-issue 파일명 (`PROJ-10-PROJ-81-dev-guide.md`) 처리. `_wiki-schema.md` § 5 휴리스틱 적용 후 ⚠️ 표시된 항목을 사용자에게 일괄 confirm:

```
⚠️ 다음 dev-guide 의 type 판정이 모호합니다 — 검토해주세요:

  PROJ-10-PROJ-81-dev-guide.md   → composite 추정 (PROJ-10/PROJ-81 둘 다 단독 guide 존재)
  PROJ-194-68-dev-guide.md      → slice 추정 (부모 PROJ-194 단독 존재, sub PROJ-68 단독 없음)
  PROJ-24-PROJ-107-dev-guide.md  → composite 추정

수정할 항목이 있으면 알려주세요. 없으면 'OK' 로 진행.
```

### 2-2. Bootstrap 출력

```
📋 Wiki Bootstrap 완료
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ INDEX.md         : 94개 entry (foundational 15 / decisions 1 / issue_guides 74 / sprint 4)
✓ LOG.md           : 102 lines (git log 백필 포함)
⚠ Parse warnings   : 3개 (frontmatter 없는 신규 dev-guide — L08 lint 권고)
⚠ Type 휴리스틱    : 5개 항목 사용자 확인 완료

다음 단계:
  wiki-lint --full   # baseline health score 측정 (자동 chain 권장)
```

Bootstrap 종료 후 자동 chain:
1. **§ 1-3 CLAUDE.md 보강 안내** — wiki 자산 row 가 CLAUDE.md 에 없으면 출력 (announce/auto-patch/skip 정책에 따라)
2. **wiki-lint 자동 호출** — baseline health score 측정 (사용자 명시 거부 없으면)

---

## § 3. 정상 Ingest — forecast / closure / refresh

호출자 의도를 자연어 컨텍스트에서 추론.

### 3-1. 의도 추론 우선순위

| 시그널 | 추론 |
|--------|------|
| harness-workflow / jira-plan 가 직접 호출 + 인자에 "forecast" | forecast |
| harness-workflow / jira-complete 가 직접 호출 + "closure" | closure |
| 사용자가 `<KEY>` 만 주고 dev-guide 존재 + Jira 상태 = Open/In Progress | forecast |
| 사용자가 `<KEY>` 만 주고 Jira 상태 = QA/Done | closure |
| 사용자가 "다시 갱신" / "refresh" 의도 표명 | refresh (특정 이슈만 재계산) |
| 사용자가 "누락 채워줘" / "backfill" 의도 | backfill (INDEX 만 보충, LOG 변경 X) |
| 사용자가 "cross-ref 다시" 의도 | rebuild-cross-refs (그래프 재구축) |

추론이 모호하면 사용자에게 1회 확인.

### 3-2. Forecast 모드

`/jira-plan` 직후 호출됨. dev-guide 가 막 생성된 상태.

절차:
1. `docs/<KEY>-dev-guide.md` 존재 확인 (없으면 오류)
2. `_wiki-schema.md` § 4 fallback chain 으로 메타 파싱
3. `INDEX.md` 의 issue_guides 표에서 같은 key 검색
   - 존재 → row 교체 (status 는 기존 유지, 다른 필드 갱신)
   - 없음 → 표 끝에 row 추가 (status=planned)
4. `LOG.md` append:
   ```
   [<timestamp> KST INGEST <KEY> forecast] guide=<path> parent=<parent or '-'> adrs=<csv> siblings=<csv>
   ```
5. dev-guide 에 YAML frontmatter 없으면 best-effort 추가 제안 (사용자 확인)
6. **forecast 모드는 ADR / sprint cross-ref 갱신 안 함** — dev-guide 가 확정 전이라 위험

### 3-3. Closure 모드

`/jira-complete` 가 호출. 검증 무시 + 신뢰 (책임은 호출자).

절차:
1. `INDEX.md` row 찾아서 status=`closed`, closed=`<today>`, related_adrs/siblings 갱신
2. `LOG.md` append:
   ```
   [<timestamp> KST INGEST <KEY> closure] index_row=updated touched=<csv>
   ```
3. **Conditional writes** 실행 (`_wiki-schema.md` § 10 bounded_writes):
   - `08-decision-log.md` 의 각 related_adr 섹션에 `ingest-managed` 블록 upsert (referenced-by entry 추가)
   - dev-guide.week 있으면 `sprint/weeks/<w>.md` 의 ingest-managed 블록에 closure 라인 append
   - dev-guide.track 있으면 `sprint/tracks/<n>-<track>.md` 의 ingest-managed 블록에 closure 라인 append
4. `forbidden` 파일은 **절대 touch X** — `_wiki-schema.md` § 10
5. 각 conditional write 는 dry-run 가능 (사용자가 "preview" 요청 시)

### 3-4. Refresh 모드 (특정 이슈)

사용자가 dev-guide 를 손으로 수정한 후 INDEX 갱신 원할 때.

절차:
1. 해당 key 의 `INDEX.md` row 만 재계산
2. `LOG.md` append: `REFRESH <KEY>`
3. cross-ref 갱신 안 함 (해당 dev-guide 의 ADR/siblings 변경됐어도 closure 처럼 다루지 않음)

### 3-5. Backfill 모드 (INDEX 보충)

새 카테고리 추가 / wiki-lint 가 orphan 검출 후.

절차:
1. glob docs/**/*.md → INDEX 에 없는 항목 식별
2. 각 항목 메타 파싱 + INDEX 에 row 추가 (기존 row 보존)
3. LOG 변경 안 함 (bulk operation 이라 noise)

### 3-6. Rebuild-cross-refs 모드

schema 의 cross_refs 패턴 변경 후 그래프 재구축.

절차:
1. 모든 dev-guide 의 ADR/issue ref 재추출
2. INDEX 의 related_adrs/siblings 컬럼 일괄 재계산
3. `08-decision-log.md` 의 모든 ingest-managed 블록 재생성
4. dev-guide 본문은 손대지 않음

---

## § 4. ingest-managed Block — 안전 갱신 메커니즘

`_wiki-schema.md` § 8 참조. 핵심 규칙:

- HTML 주석 마커 `<!-- ingest-managed:begin <attr=val> -->` ~ `:end` 사이만 rewrite
- 마커 부재 시 적절한 위치에 자동 삽입
- 본문 절대 touch X — git blame 보존
- 마커 attribute 로 식별 (`adr=ADR-070`, `file=INDEX.md`, `week=w5`, `track=qa`)

ADR 본문에 마커 첫 삽입 시 위치:
- ADR 섹션의 모든 본문 뒤
- 다음 ADR 섹션 직전
- `\n\n<!-- ingest-managed:begin adr=ADR-N -->\n### Referenced by ...\n<!-- ingest-managed:end adr=ADR-N -->\n` 삽입

## § 5. 멱등성 보장

같은 이슈를 두 번 ingest 해도 동일 결과:

| Layer | Mechanism |
|-------|-----------|
| Row | issue_key (composite/slice 포함) 가 unique → upsert |
| File | ingest-managed 블록 전체 rewrite (부분 갱신 X) |
| LOG | append-only, timestamp millisecond 정밀 |

충돌 대응:
- 표 row 사이 빈 줄 1개 → diff 가 row 단위로 잘림 → merge 자연 해결
- INDEX.md 손상 감지 시 `.bak` 자동 백업 후 사용자에게 bootstrap 권고

## § 6. Error Handling

- 각 단계 try-catch — 한 단계 실패해도 다음 단계 계속 (jira-complete §4.5 archive 패턴)
- conditional write 실패 시 경고만, ingest 자체 PASS
- `forbidden` 파일 접근 시도 검출되면 즉시 abort + 사용자에게 보고
- Jira API 실패 → status 추론은 archive 디렉토리 / 사용자 확인으로 fallback

## § 7. 출력 포맷

### Forecast / Closure / Refresh 공통

```
📋 Ingest 완료 — <KEY> (<mode>)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ INDEX.md         : row <upserted | created | refreshed>
✓ LOG.md           : append 1 line
✓ Conditional      : <ADR-X 3개, sprint/weeks/w5.md 1줄 | none>
✗ Forbidden        : <0 — clean | 위반 N건>
💡 CLAUDE.md       : <bootstrap/onboarding 직후 1회 보강 안내 | 일반 ingest = 생략>

Wiki status:
  total entries  : 95
  planned        : 8 (stale ≥7d: 2 — L03)
  closed         : 87

다음 단계 권장:
  wiki-lint --summary --severity high  # high 위반 빠른 점검
```

### Bootstrap (위 § 2-2)

### First-run (위 § 1-2)

## § 8. Notes

- **README.md 손대지 않음** — 사람용 changelog 보존. INDEX.md 가 LLM-maintained 카탈로그.
- Skill 호출당 context cost: forecast ~10K token / closure ~25K token (LOG 는 read 안 함, append 만)
- 모든 정책은 `_wiki-schema.md` SSoT 에서 관리 — 본 SKILL.md 가 SSoT 의 절차적 진입점
- harness-workflow 가 Phase 3, 7 에서 자연어 chain 으로 호출 — 본 스킬이 그 호출에 응답

## § 9. --subtasks Mode

사용자가 `/jira-ingest <KEY> --subtasks` 로 호출하고 부모 이슈에 하위 작업이 있으면:

1. 부모 처리 (forecast 또는 closure)
2. 각 슬라이스 dev-guide (`docs/<KEY>-<sub>-dev-guide.md`) 별로 INDEX entry 추가 (key 형식 `<PARENT>::<SUB>`)
3. LOG 에 슬라이스마다 별도 라인 (`INGEST <PARENT>::<SUB> forecast/closure`)
4. 슬라이스도 부모와 같은 conditional write (closure 모드)
5. 출력에 부모 + 슬라이스별 결과 표 포함

자세한 정책: `~/.claude/skills/_subtasks-convention.md` § 3 매트릭스 (jira-ingest 행).
