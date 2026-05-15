---
name: wiki-lint
description: "wiki-lint — Karpathy LLM Wiki 패턴의 정기 health check. docs/INDEX.md + LOG.md + dev-guide + ADR + memory 전반의 정합성을 14가지 체크 (orphan / stale / broken cross-reference / parent-sibling 비대칭 / Jira 상태 불일치 / memory drift / INDEX integrity 등) 로 검증합니다. 사용자가 'wiki 점검', 'docs 정합성 확인', 'INDEX 검사', 'orphan dev-guide', 'stale 확인', 'ADR drift', 'cross-reference 깨짐', 'wiki lint', 'docs lint', 'health check', 'memory drift', '문서 health score', '문서 위반 사항' 등을 요청하거나, /jira-complete 가 끝나면서 자동 chain 으로 호출 (high severity 만, non-blocking) 하거나, /jira-ingest --bootstrap 직후 baseline 측정을 위해 자동 호출될 때 트리거됩니다. jira-ingest 와 _wiki-schema.md SSoT 공유. 어느 프로젝트에서나 작동 (user-scope). 자동수정 가능 항목 (--fix 의도) 과 수동 검토 필요 항목을 분리해서 보고합니다."
---

# wiki-lint — Wiki 정기 health check (14 rules)

> **Karpathy LLM Wiki 패턴의 lint 단계** — periodic health-checks for contradictions, stale claims, orphan pages, missing concepts, broken cross-references.
> jira-ingest 와 `~/.claude/skills/_wiki-schema.md` SSoT 공유.
> **Read-only by default** — `--fix` 의도가 명시될 때만 write 수행 (각 fix 전 사용자 승인).

## Usage

```
/wiki-lint                       # 기본 — 의도는 자연어로 추론
/wiki-lint --subtasks            # 의미 없음 (corpus-scoped). 부모/슬라이스 구분 무관 — 무시 + 경고
```

자연어 입력에서 추론하는 호출 의도 (플래그 없음):

| 사용자 의도 | 추론 모드 |
|------------|----------|
| "점검해줘" / "health check" | summary (high+medium 만, 상위 5건 미리보기) |
| "전체 점검" / "full lint" | full (모든 위반 + 권고) |
| "고쳐줘" / "auto-fix" / "자동 수정" | fix (✅ 표시된 것만 수정, 각 변경 사용자 승인) |
| "orphan 검출" / "L05 만" / "ADR 깨진 거 찾아줘" | specific rule (해당 ID 만) |
| "high 만" / "심각한 거" | severity 필터 (high 이상) |
| "최근 N일" / "이번 주" | since 인크리멘탈 (해당 기간 변경 파일만) |
| "PROJ-247 만" / "이 이슈 점검" | issue scope (해당 이슈 관련 체크만) |
| "JSON 으로" / "머신 출력" | JSON 모드 (CI 통합용) |

## ⛔ Guard — Wiki 자산 존재 확인

스킬 시작 직후 점검:

| 점검 | 부재 시 행동 |
|------|-------------|
| `docs/INDEX-SCHEMA.md` | "Wiki 가 설정되지 않았습니다. `/jira-ingest` 로 먼저 wiki 셋업 진행해주세요" 안내 후 종료 |
| `docs/INDEX.md` | "INDEX.md 가 비어있거나 부재 — `/jira-ingest bootstrap` 권고" 안내 후 종료 |
| `docs/LOG.md` | (선택) — 없어도 lint 는 INDEX 기반 가능. 단 L03 (stale) 은 정확도 떨어짐 경고 |

세 가지 모두 정상이면 lint 진행.

## § 1. 정상 lint 절차

### 1-1. Schema 로딩

```
~/.claude/skills/_wiki-schema.md       # SSoT 정책
docs/INDEX-SCHEMA.md                   # 프로젝트 schema
```

### 1-2. Inventory 수집

- `docs/INDEX.md` 표 파싱 → issue_key → metadata 매핑
- `docs/LOG.md` 라인 파싱 → 시간순 이벤트
- glob `docs/**/*.md` → 실제 파일 inventory
- `docs/08-decision-log.md` (있으면) → ADR-N 목록 추출
- `memory/MEMORY.md` + memory entries (있으면) → 인용 파일/클래스 목록
- (옵션) `mcp__atlassian__getJiraIssue` × N — L14 closure mismatch 시만

### 1-3. 14 Rule 실행

`_wiki-schema.md` § 11 의 매트릭스 기반. 각 rule 독립 try-catch — 한 rule 실패해도 다른 rule 계속.

#### L01 — Orphan (high, auto-fix ✅)
INDEX-SCHEMA 의 issue_guides pattern 매칭 파일이 INDEX 에 없는 경우.
```
for f in glob('docs/<ISSUE_PREFIX>-*-dev-guide.md'):
  key = parse_key(f)
  if key not in INDEX:
    violations.append(L01, file=f, key=key)
auto_fix: jira-ingest 의 backfill 모드를 자연어로 chain ('PROJ-247 INDEX 에 누락 — 추가해줘')
```

#### L02 — Orphan reverse (high, manual)
INDEX 에 있는데 파일 부재. 자동 삭제 위험 → 사용자 결정.

#### L03 — Stale (medium, no-fix)
```
status=planned AND last_activity_in_LOG > 7d
```
last_activity 는 LOG.md 의 해당 KEY 가장 최근 라인 timestamp.

#### L05 — Xref ADR broken (high, no-fix, Levenshtein 제안)
```
for guide in INDEX.issue_guides:
  for adr in guide.related_adrs:
    if adr not in ADR_list:
      candidates = top3_levenshtein(adr, ADR_list)
      violations.append(L05, guide, adr, candidates)
```

#### L06 — Xref issue broken (medium, no-fix)
dev-guide 본문의 `<ISSUE>-N` 가 INDEX 에 없음 (삭제된 이슈 또는 오타).

#### L07 — Parent/sibling asymmetry (medium, auto-fix ✅)
```
for guide in INDEX:
  if guide.parent:
    parent = INDEX[guide.parent]
    if guide.key not in parent.children:
      violations.append(L07, type='missing_child', parent=parent.key, child=guide.key)
  for sib in guide.siblings:
    if sib in INDEX and guide.key not in INDEX[sib].siblings:
      violations.append(L07, type='asymmetric_sibling', ...)
auto_fix: INDEX 표의 양방향 동기화 (jira-ingest rebuild-cross-refs 자연어 chain)
```

#### L08 — Frontmatter missing (low, auto-fix ✅)
신규 dev-guide (created ≥ 2026-05-14) 에 YAML frontmatter 없음.
auto_fix: 비공식 헤더 → frontmatter 변환 (사용자 확인 후).

#### L09 — Conflict (high, manual)
같은 ADR-N 을 두 dev-guide 가 다른 결정으로 인용. heuristic:
- 같은 ADR 을 인용한 dev-guide 쌍 추출
- 본문에서 "ADR-N 적용" vs "ADR-N 폐기" 같은 상반 키워드 동시 검출 시 경고
- false positive 많음 — 수동 검토만

#### L10 — Memory drift (high, manual)
`memory/*.md` 의 인용 파일/클래스가 실 코드에 없음:
- memory 본문에서 파일 경로 추출 (정규식: `[A-Za-z0-9/_\-.]+\.(java|vue|ts|js|py)`)
- 클래스명 추출 (CamelCase 휴리스틱)
- glob/grep 으로 실재 확인
- 부재 시 violation (사용자가 update / forget 결정)

#### L11 — INDEX integrity (low, auto-fix ✅)
- 표 정렬 깨짐 (key 내림차순 아님)
- 중복 row (같은 key 2회)
- ingest-managed 마커 begin/end 짝 안 맞음
- 빈 cell 가 `-` 가 아닌 다른 값
- auto_fix: jira-ingest rebuild 자연어 chain

#### L12 — LOG integrity (low, manual)
LOG 라인 형식 일탈. 드물고 위험 → 자동 수정 X.

#### L14 — Closure mismatch (medium, auto-fix ✅)
```
for guide in INDEX.issue_guides:
  if guide.status == 'planned':
    jira_status = atlassian.getJiraIssue(guide.key).status
    if jira_status in ['QA', 'Done']:
      violations.append(L14, guide, jira_status)
auto_fix: jira-ingest closure 자연어 chain ('PROJ-247 closure 처리')
```
Jira API 실패 시 해당 체크만 skip + 경고.

#### L15 — Coverage (low, auto-fix ✅)
sprint week 파일이 그 week 의 closed issue 를 ingest-managed 블록에 포함하는지.
auto_fix: 누락된 라인 append.

### 1-4. 결과 집계 + 출력

```
📋 Wiki Lint Report (<timestamp> KST)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ <N> checks passed
⚠️  <M> warnings  / ❌ <K> errors

━━━ ❌ ERRORS ━━━

❌ L05 (Xref, high) — Broken ADR reference [3건]
  • docs/PROJ-247-dev-guide.md:52 → ADR-099 (decision-log 에 없음)
    Levenshtein 후보: ADR-029, ADR-060
  • ...

━━━ ⚠️ WARNINGS ━━━

⚠️ L03 (Stale, medium) — 'planned' 상태 7일 초과 [4건]
  PROJ-201 (10d), PROJ-198 (12d), PROJ-196 (15d), PROJ-195 (21d)
  → 진행 중이면 status=implementing 갱신, 폐기면 status=abandoned

━━━ 📊 SUMMARY ━━━

Health Score:        92 / 100
Total checks:        97
Auto-fixable:        4건 — '자동 수정해줘'
Manual review:       5건

권장 다음 단계:
  1. 자동 수정 4건 처리
  2. PROJ-201/198/196/195 status 결정
  3. memory drift 검토
```

### 1-5. Auto-fix 모드 (사용자 의도 명시 시만)

사용자가 "고쳐줘" / "auto-fix" / "자동 수정" 의도 표명 시:

1. ✅ 표시된 위반만 candidate
2. 각 fix 별로 변경 plan 미리보기 (organize-claude-md Phase 6 패턴 차용)
3. 사용자 승인 후 적용
4. fix 결과를 LOG.md 에 `[<ts> LINT-FIX <KEY>] rule=L07 action=symmetry-restored` append

Auto-fix 가 다른 스킬을 chain 호출하는 경우 (대부분 jira-ingest):
- L01: `jira-ingest <KEY>` (backfill 의도 자연어)
- L07: `jira-ingest --rebuild-cross-refs 의도 자연어`
- L08: `jira-ingest <KEY>` (refresh frontmatter)
- L11: `jira-ingest rebuild 의도 자연어`
- L14: `jira-ingest <KEY> closure` (Jira QA 신뢰)
- L15: 직접 sprint week 파일 ingest-managed 블록에 append (간단)

## § 2. 자동 트리거 — 2가지 chain 진입

본 스킬은 두 곳에서 **자동 호출**된다 (둘 다 high+medium 만, non-blocking):

### 2-1. `/jira-complete` §4.7 자동 chain

`/jira-complete` 의 §4.6 (CLAUDE.md 위생 체크) 직후 §4.7 으로 chain:
```
Skill('wiki-lint', '요약 점검해줘 — high 와 medium 만, non-blocking')
```
실패해도 jira-complete 자체 진행은 막지 않음.

### 2-2. `/jira-ingest --bootstrap` 끝 자동 chain

bootstrap 종료 직후 baseline health score 측정:
```
Skill('wiki-lint', '전체 점검 — baseline 확보')
```
첫 lint 결과를 LOG.md 에 `[<ts> LINT baseline] score=92 errors=2 warnings=7` append.

## § 3. Error Handling

- 각 rule 독립 try-catch — 일부 실패해도 다른 rule 계속
- Jira API 실패 (L14) → 해당 체크만 skip + 경고
- INDEX.md / LOG.md 파싱 실패 → 사용자에게 손상 안내 + bootstrap 권고
- memory/ 디렉토리 부재 (L10) → 해당 체크 skip (정상)

## § 4. Context Cost

- 인크리멘탈 (`--since 7d` 의도) 기본 권장 — 변경된 파일만 read
- full mode 는 100+ 파일 전체 read = ~500K char → batch 처리 (10 파일씩)
- LOG.md 전체 스캔 비용은 lint 단계에서만 (jira-ingest 는 LOG read 안 함)

## § 5. Notes

- **이 스킬은 read-only by default**. write 는 사용자 명시 `--fix` 의도 + 각 변경 승인 후만.
- HARNESS_MODE 무관 (직교)
- `--subtasks` 받지 않음 (corpus-scoped). 호출 시 무시 + 경고.
- 정책은 모두 `_wiki-schema.md` SSoT 에서 관리

## § 6. JSON 출력 모드 (CI 통합용)

사용자가 "JSON" / "머신 출력" 의도 표명 시:

```json
{
  "timestamp": "2026-05-14T14:32:00+09:00",
  "health_score": 92,
  "total_checks": 97,
  "violations": [
    {
      "rule_id": "L05",
      "severity": "high",
      "category": "xref",
      "auto_fixable": false,
      "file": "docs/PROJ-247-dev-guide.md",
      "line": 52,
      "evidence": "ADR-099 not in decision-log",
      "suggestions": ["ADR-029", "ADR-060"]
    }
  ],
  "summary": {
    "errors": 2,
    "warnings": 7,
    "auto_fixable_count": 4
  }
}
```
