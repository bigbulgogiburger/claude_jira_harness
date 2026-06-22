# `_wiki-schema.md` — jira-ingest + wiki-lint 공통 SSoT

> **단일 출처 (single source of truth)** — `jira-ingest` 와 `wiki-lint` 두 스킬이 본 문서를 참조한다.
> 본 문서를 수정하면 즉시 두 스킬의 동작이 바뀐다. `_subtasks-convention.md` 와 동일 위상.

## 1. Karpathy LLM Wiki 패턴 — 우리 적용 요약

핵심 통찰: **RAG 처럼 매번 재발견하지 말고, LLM 이 점진적으로 영구 wiki 를 만들고 유지한다.** synthesis 는 query-time 이 아니라 build-time 에 누적.

3-layer 아키텍처:

| Layer | 소유 | 내용 |
|-------|------|------|
| Raw Sources | 사용자 (immutable) | 원문 — Jira 이슈, 외부 문서, 회의록 |
| Wiki | LLM (관리 + write) | `docs/INDEX.md`, `docs/LOG.md`, `docs/<KEY>-dev-guide.md` 본문 |
| Schema | 사용자 (git tracked) | `docs/INDEX-SCHEMA.md` — 카테고리·정책 |

### 우리의 의도적 분기 (Karpathy vs 우리)
- "single source touches 10~15 pages" → 우리는 **1~5 pages bounded** (PR review + git blame 보존 필요)
- ingest 워크플로 자유형 → 우리는 **forecast + closure 2-phase** 강제 (abandon 검출)
- frontmatter 강제 → 신규 dev-guide 만, 기존은 best-effort 파싱

## 2. INDEX-SCHEMA.md — 프로젝트별 schema

프로젝트의 `docs/INDEX-SCHEMA.md` 가 카테고리·정책 정의. **처음 실행 시 부재 가능** — 그 때는 jira-ingest 가 default schema 를 제안.

### Default schema (신규 프로젝트 부트스트랩용)

```yaml
version: 1
project: <auto-detected-from-CLAUDE.md-or-package-name>

categories:
  - id: foundational
    label: 기반 (PRD/DB/Domain)
    match:
      pattern: "^[0-9]{2}-.*\\.md$"
    columns: [num, file, summary, owner, updated]

  - id: decisions
    label: 의사결정 (ADR)
    match:
      explicit: ["08-decision-log.md"]
    columns: [file, adr_count, updated]

  - id: issue_guides
    label: 이슈 가이드
    match:
      pattern: "^<ISSUE_PREFIX>-\\d+(?:[+:](?:STD-)?\\d+)*-dev-guide\\.md$"
    columns: [issue, status, title, week, parent, siblings, adrs, persona, updated]

  - id: sprint
    label: 스프린트
    match:
      pattern: "^sprint/.*\\.md$"

  - id: setup
    label: 셋업/운영
    match:
      pattern: "^(setup|ops|qa|external|data)/.*\\.md$"

cross_refs:
  adr_pattern: "\\bADR-\\d+\\b"
  issue_pattern: "\\b<ISSUE_PREFIX>-\\d+\\b"   # 예: STD- / SURINP- / SCRUM-

closure_signals:
  jira_qa_transition: true
  archive_dir_exists: ".claude/runtime/archive/<ISSUE>"

bounded_writes:
  always:
    - "docs/INDEX.md"
    - "docs/LOG.md"
  conditional:
    - path: "docs/08-decision-log.md"
      write_when:
        - mode: "closure"
        - dev_guide.related_adrs: not_empty
      action: "upsert ingest-managed block per ADR section"
    - path: "docs/sprint/weeks/w*.md"
      write_when:
        - mode: "closure"
        - dev_guide.week: present
        - issue_not_in_file: true
      action: "append closure line to ingest-managed block"
    - path: "docs/sprint/tracks/*.md"
      write_when:
        - mode: "closure"
        - dev_guide.track: present
        - issue_not_in_file: true
      action: "append closure line"
  forbidden:
    - "docs/01-prd*.md"
    - "docs/02-db-schema.md"
    - "CLAUDE.md"
    - "CHANGELOG.md"
    - "**/*.java"
    - "**/*.vue"
    - "**/*.ts"
    - "**/*.js"
    - "**/*.py"

stale_thresholds:
  planned_days: 7
  last_activity_days: 14

claude_md_integration:
  mode: auto-patch          # announce | auto-patch | skip
  target_section: "Planning Docs"
  block_template: |
    | Wiki Index  | 작업 착수 시 관련 이슈·ADR cross-ref 조회 | docs/INDEX.md         |
    | Wiki Log    | ingest 이벤트 로그 (append-only)          | docs/LOG.md           |
    | Wiki Schema | wiki 카테고리·정책 (사용자 편집)          | docs/INDEX-SCHEMA.md  |
```

ISSUE_PREFIX 는 첫 호출 시 프로젝트의 Jira 이슈 키 prefix 로부터 추론 (예: `STD`, `SURINP`, `SCRUM`).

## 3. dev-guide YAML frontmatter 표준

신규 dev-guide 는 다음 frontmatter 권장 (jira-plan 이 자동 삽입):

```yaml
---
issue: STD-247
title: W5 QA 라우트 가드 권한 침투 spec
type: single                # single | composite | slice
status: planned             # planned | closed | abandoned
week: W5
track: QA
parent: STD-206             # null if single
siblings: [STD-245, STD-246]
related_adrs: [ADR-021, ADR-058, ADR-060]
persona: Vue.js Specialist
created: 2026-05-14
closed: null
---
```

기존 dev-guide 는 비공식 quoted header (`> 부모:`, `> 자매:`, ...) 도 best-effort 파싱.

## 4. dev-guide 파싱 — 6단계 fallback chain

각 단계 순차 시도, 누락 항목은 null:

```
1. YAML frontmatter      ^---\n...\n---\n         → 전체 메타 (있으면 끝)
2. Quoted header lines   ^> 키: 값                → created/stack/persona/parent/siblings/mode
   - r"^> 생성일: (\d{4}-\d{2}-\d{2})"
   - r"^> 스택: (.+)"
   - r"^> 페르소나: \*\*(.+?)\*\*"
   - r"^> 부모: (<ISSUE>-\d+)"
   - r"^> 자매: ((?:<ISSUE>-\d+(?:, )?)+)"
3. Title line            ^# \[(<ISSUE>-\d+(?:-<ISSUE>-\d+)?)\] \[(W\d+)\]\[(\w+)\] (.+?) —
                         → issue, week, track, title
4. Body scan             \bADR-\d+\b → related_adrs (uniq)
                         \b<ISSUE>-\d+\b → mentioned_issues (uniq, parent/siblings 제외)
5. File name             <ISSUE>-(\d+)(?:-<ISSUE>-(\d+))?-dev-guide\.md
                         → issue_key (1~4 모두 실패 시)
6. Git log 보완          git log --diff-filter=A --reverse --format=%cI -- <file> → created
                         git log -1 --format=%cI -- <file> → last_activity
```

## 5. Unique Key — 3 종 dev-guide 구분

| Type | 패턴 | Key 형식 | 예 |
|------|------|---------|-----|
| single | `STD-247-dev-guide.md` | `STD-247` | 단일 이슈 |
| composite | `STD-10-STD-81-dev-guide.md` | `STD-10+STD-81` | 통합 (cross-track) |
| slice | `STD-194-68-dev-guide.md` | `STD-194::STD-68` | 부모 + 슬라이스 (--subtasks) |

**Bootstrap 휴리스틱** (frontmatter 부재 시):
1. `STD-<N>-dev-guide.md` 가 같은 디렉토리에 존재 → 두 번째 숫자는 slice
2. 둘 다 단독 dev-guide 존재 → composite
3. 그 외 → composite 가정 + bootstrap 결과 표에 ⚠️ 표시 → 사용자 confirm

신규 dev-guide 는 frontmatter `type:` 필드 강제 — bootstrap 한 번만 휴리스틱 의존.

## 6. LOG.md 형식 — grep-first

```
[YYYY-MM-DD HH:MM KST  <MODE>     <KEY>          <phase>] key=value key=value...
[2026-05-14 14:32 KST  INGEST     STD-247        forecast] guide=docs/STD-247-dev-guide.md parent=STD-206 adrs=ADR-021,058,060
[2026-05-14 18:45 KST  CLOSURE    STD-247        ] verdict=PASS commit=6c0072b touched=3 qa=2026-05-14
[2026-05-14 18:45 KST  INGEST     STD-247        closure] index_row=updated touched=[INDEX.md,LOG.md,sprint/weeks/w5-w8.md]
[2026-05-13 17:20 KST  INGEST     STD-246        forecast] guide=docs/STD-246-dev-guide.md parent=STD-200 adrs=ADR-029
[2026-05-12 09:00 KST  BOOTSTRAP  -              ] parsed=94 categories=5 warnings=2
[2026-05-15 10:00 KST  LINT       -              ] mode=summary score=92 errors=2 warnings=7
```

MODE 종류: `INGEST` / `CLOSURE` / `BOOTSTRAP` / `LINT` / `REFRESH` / `REBUILD-XREFS`.

`grep STD-247 docs/LOG.md` → 단일 이슈의 전체 타임라인. append-only, 절대 read 하지 않음 (lint 만 스캔).

## 7. INDEX.md 형식

전체 표가 ingest-managed 블록 안에 위치. 사람이 손대지 않음.

```markdown
# <Project> — 문서 인덱스 (LLM-maintained)

> 자동 갱신: `jira-ingest` 호출 시. 마지막 갱신: 2026-05-14 14:32 KST.
> 카테고리/정책: `INDEX-SCHEMA.md`. lint 보고서: `wiki-lint` 호출.

<!-- ingest-managed:begin file=INDEX.md -->

## 기반 (PRD/DB/Domain)

| # | 파일 | 한줄 요약 | 갱신 |
|---|------|----------|------|
| 00 | `00-baseline.md` | 최종 기준선 | 2026-04-29 |
| 01 | `01-prd.md` | PRD v1.2 단일 본문 | 2026-05-04 |

## 의사결정 (ADR)
| 파일 | ADR 수 | 갱신 |
|------|--------|------|
| `08-decision-log.md` | 70 | 2026-05-13 |

## 이슈 가이드
| Issue | Status | Title | Week | Parent | ADRs | Siblings | Updated |
|-------|--------|-------|------|--------|------|----------|---------|
| STD-247 | closed | W5 QA 라우트 가드 권한 침투 spec | W5 | STD-206 | ADR-021,058,060 | STD-245,246 | 2026-05-14 |
| STD-246 | closed | W5.1+ 사이드바 collapse persistence | W5 | STD-200 | ADR-029 | STD-247 | 2026-05-13 |

<!-- ingest-managed:end file=INDEX.md -->
```

정렬: 카테고리별 — 이슈 가이드는 week 역순 + issue key 내림차순. 빈 cell = `-`.

## 8. ingest-managed Block Sentinel

자동 갱신과 사용자 수정의 충돌을 마커로 격리. ADR 본문 / sprint week / INDEX 모두 동일 패턴.

```markdown
## ADR-070 — Agent Teams 슬라이스 fan-out
... 본문 (절대 jira-ingest 가 손대지 않음) ...

<!-- ingest-managed:begin adr=ADR-070 -->
### Referenced by (auto-maintained by jira-ingest)
- [STD-247](../STD-247-dev-guide.md) — W5 QA 라우트 가드 (2026-05-14 closed)
- [STD-246](../STD-246-dev-guide.md) — W5.1+ 사이드바 (2026-05-13 closed)
<!-- ingest-managed:end adr=ADR-070 -->
```

**규칙**:
- jira-ingest 는 `<!-- ingest-managed:begin ... -->` ~ `:end` **사이만** rewrite
- 마커 부재 시 섹션 끝에 자동 추가
- 사용자가 마커 안 수정해도 다음 ingest 가 덮어씀 (의도)
- **본문 100% safe** — git blame 보존

## 9. 상태 머신 — 3-state (단순화)

```
INDEX.status ∈ {planned, closed, abandoned}
```

| 전이 | 트리거 |
|------|--------|
| `(none) → planned` | jira-ingest forecast (jira-plan 직후) |
| `planned → closed` | jira-ingest closure (jira-complete 직전) |
| `* → abandoned` | 사용자 수동 / wiki-lint --fix L03 권고 수락 시 |

> **implementing 상태는 의도적으로 없음**. 구현 중 활동은 LOG 의 `last_activity` 로 추적. wiki-lint stale 검사가 `last_activity > 7d AND status=planned` 기반 → 자연스럽게 stale 회피.

## 10. Bounded Writes 정책

bounded_writes 는 INDEX-SCHEMA.md 의 `bounded_writes` 섹션 (§ 2 default 참조). 3 카테고리:

- **always**: INDEX.md, LOG.md — ingest 호출 시 항상 갱신
- **conditional**: ADR / sprint week·track — 조건 만족 시만 (mode + dev_guide 필드 + 중복 검사)
- **forbidden**: PRD / DB schema / 코드 파일 — **자동 갱신 절대 금지**. wiki-lint L13 (v2) 이 위반 검출 예정

PR diff 가 항상 5 파일 이내 보장.

## 11. Wiki Lint Rules — 14 종 (L13 은 v2 로 미룸)

| ID | 카테고리 | 검사 | Severity | Auto-fix |
|----|---------|------|----------|----------|
| L01 | Orphan | dev-guide 파일 있는데 INDEX 에 없음 | high | ✅ |
| L02 | Orphan | INDEX 에 있는데 dev-guide 파일 부재 | high | ⚠️ (수동) |
| L03 | Stale | `status=planned` + `last_activity > 7d` | medium | × |
| L04 | Stale | (안 씀 — L03 으로 통합, implementing 상태 제거 영향) | — | — |
| L05 | Xref | dev-guide 의 ADR-N 이 08-decision-log.md 에 없음 | high | × (Levenshtein 후보 제안) |
| L06 | Xref | dev-guide 의 STD-M 가 INDEX 에 없음 | medium | × |
| L07 | Xref | parent/siblings 양방향 비대칭 | medium | ✅ |
| L08 | Frontmatter | 신규 dev-guide (생성일 ≥ schema.frontmatter_required_since) 에 YAML frontmatter 없음 | low | ✅ (best-effort 변환) |
| L09 | Conflict | 같은 ADR-N 을 두 dev-guide 가 모순되게 인용 (heuristic) | high | × |
| L10 | Memory drift | MEMORY.md 인용 파일/클래스 부재 | high | × |
| L11 | INDEX integrity | 표 정렬 깨짐 / 중복 row / 빈 cell / 마커 손상 | low | ✅ |
| L12 | LOG integrity | LOG 라인 형식 일탈 | low | × |
| L13 | Policy | forbidden 파일이 ingest 호출 PR 에서 수정 (git log) | high | × | (**v2 — 첫 릴리스 제외**) |
| L14 | Closure | Jira 상태 = QA/Done 인데 INDEX status = planned | medium | ✅ (Jira 진실로) |
| L15 | Coverage | sprint week 가 그 week 의 closed issue 인용 안 함 | low | ✅ |

`--fix` 는 ✅ 표시된 것만. 나머지는 보고 + 권고.

## 12. 첫 실행 (First-run) 시나리오

스킬이 호출됐는데 wiki 자산이 없는 경우 — 단계적 onboarding:

| 상태 | 행동 |
|------|------|
| `docs/` 디렉토리 부재 | 사용자에게 "docs/ 디렉토리 만들까요?" 확인. 거부 시 종료 (다른 경로 안내) |
| `docs/INDEX-SCHEMA.md` 부재 | § 2 default schema 를 보여주고 "이걸로 `docs/INDEX-SCHEMA.md` 생성할까요?" 확인. 프로젝트 ISSUE_PREFIX 추론 (CLAUDE.md / Jira API 시도) |
| `docs/INDEX.md` 부재 | bootstrap 권고 — "기존 dev-guide N개 발견. 카탈로그화할까요?" 확인 후 5+1 Pass |
| `docs/LOG.md` 부재 | bootstrap 시 자동 생성 (git log 백필) |
| `CLAUDE.md` 에 wiki 자산 row 부재 | § 15 의 `claude_md_integration` 정책 적용 (default `auto-patch`, 첫 1회 승인) — bootstrap / onboarding 종료 직후 1회만 |
| 정상 (모두 존재) | 호출자 의도 추론 후 진행 |

## 13. 호출자 의도 추론 — 자연어 우선, `--subtasks` 만 명시

플래그 explosion 회피. 사용자가 자연어로 의도 전달하면 LLM 이 추론:

| 사용자 입력 | 추론 모드 |
|------------|----------|
| "STD-247 등록해줘" + dev-guide 존재 + Jira Open | forecast |
| "STD-247 closure 처리" / "마감처리" | closure |
| "wiki 처음 설정" / "INDEX 만들어줘" + INDEX 부재 | bootstrap |
| "STD-247 다시 갱신" / "refresh" | refresh (특정 issue 재계산) |
| "INDEX 누락분 채워줘" | backfill |
| "cross-ref 다시 만들어줘" | rebuild-cross-refs |

`harness-workflow` 가 chain 호출할 때는 자연어로 forecast/closure 명시 (예: `Skill("jira-ingest", "STD-247 forecast 모드로 ingest")`).

**유일한 명시 플래그**: `--subtasks` — `_subtasks-convention.md` 와 일관성. 자연어로는 부모/슬라이스 mechanical 처리 모호.

## 14. 책임 분리

| 책임 | 담당 |
|------|------|
| Wiki write (INDEX/LOG/cross-ref) | jira-ingest |
| Wiki verify (orphan/stale/drift) | wiki-lint |
| Closure 단언 신뢰 | jira-complete 가 호출 = 신뢰. 검증은 wiki-lint L14 가 사후 |
| Schema 관리 | 사용자 (git tracked) |
| Skill SSoT | 본 문서 (`_wiki-schema.md`) |

jira-ingest 와 wiki-lint 는 본 문서의 정책만 따른다 → 한 곳 수정으로 두 스킬 행동 동시 변경.

## 15. CLAUDE.md Integration — wiki 자산 가시화

bootstrap / onboarding 직후 CLAUDE.md 에 wiki 자산 안내가 없으면 **미래 LLM 세션이 INDEX.md / LOG.md 의 존재를 모름** — dev-guide 작업 중에도 wiki 활용 안 함. INDEX-SCHEMA.md 의 `claude_md_integration.mode` 로 격리:

| mode | 동작 |
|------|------|
| `auto-patch` (default) | 사용자 승인 후 Edit 툴로 CLAUDE.md 의 `target_section` 표 끝에 row 추가. |
| `announce` | 보강 블록 templated text 만 출력. 사용자가 수동 복붙. **CLAUDE.md 무수정**. |
| `skip` | 안내 자체 생략. |

**왜 default 가 `auto-patch` 인가?**
- 핵심 목적: wiki 를 build-time 에 쌓아도 **CLAUDE.md 가 가리키지 않으면 미래 LLM 세션이 안 읽음**. 활성화 직후 자동 가시화가 wiki 의 존재 이유.
- auto-patch 는 무단 수정이 아님 — **첫 패치 1회 사용자 승인** 후 Edit. 승인 게이트가 PR 노이즈 / git blame 오염 우려를 통제.
- announce 의 trade-off (사람 친화 문서, 수동 commit 으로 author 명확) 는 여전히 유효 → 자동 갱신을 원치 않는 프로젝트는 schema 에서 `announce` / `skip` 으로 격리.

**호출 타이밍** (3 회만):
- § 1 First-run Onboarding 종료 직후
- § 2 Bootstrap 종료 직후
- 사용자가 명시적으로 "CLAUDE.md 에 wiki 안내 추가해줘" 요청 시

**일반 ingest (forecast / closure) 에서는 절대 호출 안 함** — 의도된 침묵.

**탐지 휴리스틱** (보강 필요 여부):
```
CLAUDE.md grep "docs/INDEX.md"
  매칭 있음 → 이미 안내됨, 생략
  매칭 없음 → 보강 블록 출력 / auto-patch
```

**block_template** 은 schema 의 `claude_md_integration.block_template` 사용. 프로젝트별로 컬럼 형식 조정 가능 (헤더 추가, 영문/한글 등).

---

**Last Updated**: 2026-05-27 (§ 15 default `announce` → `auto-patch` 전환 + block_template 참조시점 칸을 행동 의도 ("작업 착수 시 관련 이슈·ADR 조회") 로 개선. 이유: 사용자 피드백 — announce 는 수동 복붙 단계가 실제로 실행 안 돼 wiki 가 CLAUDE.md 에 가시화 안 됨 → 미래 세션이 자산 미활용. auto-patch (첫 1회 승인) 가 가시화를 보장)
**Previous**: 2026-05-14 (§ 15 추가 — CLAUDE.md Integration 정책 + § 2 schema 에 claude_md_integration 키 + § 12 표 row 추가. 이유: 사용자 피드백 — 부트스트랩 후 CLAUDE.md 에 wiki 안내 없으면 미래 LLM 세션이 자산 활용 못 함)
**Previous**: 2026-05-14 (신설 — Karpathy LLM Wiki 패턴 도입 + jira-ingest/wiki-lint 두 스킬 SSoT)
