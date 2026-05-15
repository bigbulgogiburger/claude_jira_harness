# Lint Rules — Karpathy 6 Categories

> SKILL.md §4 (Lint 모드) 의 6가지 규칙 세부.
> `wiki-lint` 스킬 (jira 도메인 14 rules) 과는 직교 — 본 스킬의 lint 는 자신의 wiki 만.

## 0. 공통 사양

- **scope**: `<WIKI_ROOT>/wiki/**/*.md` + `INDEX.md` + `LOG.md`
- **read-only 기본**: finding 리스트만. 수정은 사용자 승인 후 (`--fix` 의도 시).
- **severity**:
  - **high** — 사실 충돌 / 깨진 링크 / 데이터 신뢰도 위협
  - **medium** — stale / orphan / missing concept
  - **low** — 형식·메타데이터 누락
- **finding 출력**: 표 형태 + 옵션 JSON

## 0.1 JSON 출력 스키마 (`--json` 의도 시)

```json
{
  "version": 1,
  "generated_at": "2026-05-14T15:30:00+09:00",
  "wiki_root": "/Users/me/wiki",
  "stats": {
    "notes_total": 247,
    "findings_total": 14,
    "by_severity": {"high": 2, "medium": 5, "low": 7}
  },
  "findings": [
    {
      "id": "L1-001",
      "rule": "contradictions",
      "severity": "high",
      "notes": ["wiki/concepts/attention.md", "wiki/concepts/self-attention.md"],
      "lines": [14, 23],
      "summary": "...",
      "suggestion": "..."
    }
  ]
}
```

---

## L1. Contradictions (사실 충돌) — high

같은 entity/concept 노트끼리 진술이 충돌하는 경우.

**감지 휴리스틱**:
1. 같은 슬러그 entity/concept 가 별도 노트로 흩어진 경우 (예: `attention.md` vs `self-attention.md` 동일 정의)
2. 노트 본문에 "정의 / 즉 / 의미하는 것 / is defined as" 패턴 추출 → 비교
3. 숫자·날짜·인물 사실 (정량 / 정명) 추출 → 충돌 검사

**limitation**: LLM 추론 기반 — false positive 발생 가능. 결과는 "후보" 로 표시.

**Suggestion 패턴**:
```
[[Concept A]] 와 [[Concept B]] 가 같은 정의를 가짐.
  → 머지 후보 (synthesis 노트로) — 사용자 승인 후 자동 머지 가능.

[[Concept X]] 날짜 충돌:
  - wiki/concepts/x.md:14 — "발표 2024년"
  - wiki/sources/x-paper.md:8 — "발표 2025년"
  → source-card 의 publish_date 가 권위. concept 노트 갱신 권장.
```

**자동 수정 가능**:
- 단순 머지 (양 노트 동일 정의 + 사용자 승인)
- source-card 권위 사실로 concept 노트 정렬

---

## L2. Stale (신선도) — medium

`updated` 가 schema 의 `lint.stale_days` (default 180) 초과 + `status` 가 `stable` 이 아닌 경우.

**감지**:
- frontmatter `updated` 필드 파싱 → 오늘과 차이 > stale_days
- `status: draft` 또는 status 누락 + 오래됨 → stale 후보

**예외**:
- `status: stable` 노트는 stale 검사 면제 (의도적 stable 표시)
- entity 노트 (특히 역사 인물·고정 사실) — `status: stable` 권장

**Suggestion**:
```
wiki/concepts/old-tech.md updated 2024-10-12 (583일 전, status: draft)
  → 옵션:
     a) status=stale 마킹 (앞으로 lint 면제)
     b) status=stable 마킹 (확정)
     c) 갱신 (최근 ingest 한 source 와 cross-check)
     d) 삭제 후보 (사용자만 결정)
```

**자동 수정 가능**:
- (a) `status: stale` 마킹 (사용자 승인 후)

---

## L3. Orphan (고립 노트) — medium

inbound link + outbound link 둘 다 0 인 노트.

**감지**:
1. 모든 `.md` 파일의 wikilink `[[Title]]` + markdown link `[Title](path)` 수집
2. 각 노트의 inbound count (다른 노트가 자기 가리키는 횟수) 계산
3. 각 노트의 outbound count (자기가 다른 노트 가리키는 횟수) 계산
4. 둘 다 0 → orphan

**예외**:
- `wiki/syntheses/` 의 일부 노트는 의도적 isolated (예: journal 엔트리)
- `status: draft` orphan 은 정상 (작성 중)

**Suggestion**:
```
wiki/concepts/lonely.md — inbound 0 / outbound 0
  → 옵션:
     a) 적당한 synthesis 노트에 backlink 추가 (제안: [[Topic Synthesis]])
     b) 비슷한 concept 노트와 머지 (제안: [[Similar Concept]])
     c) `status: archived` 마킹 (보존하되 lint 면제)
     d) 삭제 후보
```

**자동 수정 가능**:
- 사용자 선택한 synthesis 노트에 ingest-managed sentinel 안에 link 추가

---

## L4. Missing Concepts (개념 부재) — medium

source-card 가 언급한 entity/concept 의 노트가 없는 경우.

**감지**:
1. 모든 source-card 의 본문에서 wikilink `[[X]]` 추출
2. 대상 노트가 `wiki/entities/<x>.md` 또는 `wiki/concepts/<x>.md` 에 존재하는지 확인
3. 부재 시 missing_concept finding

**Suggestion**:
```
wiki/sources/karpathy-llm-wiki.md 가 [[Memex]] 언급, 노트 없음
  → 자동 stub 생성 가능 — type=concept, 최소 frontmatter + "(작성 필요)" 본문
    또는 사용자가 직접 작성
```

**자동 수정 가능**:
- stub 자동 생성 (사용자 승인 필수) — 본문은 "(작성 필요)" 1줄
- stub 생성 시 backlink 자동 추가

---

## L5. Broken Cross-Reference (깨진 링크) — high

wikilink 또는 markdown link 의 대상이 부재하거나 잘못된 경로.

**감지**:
1. 모든 노트의 link 추출
2. `[[Title]]` → 위키 전체에서 title 매칭 검색 (frontmatter title 또는 파일명)
3. `[Title](path.md)` → 상대 경로 resolve 후 파일 존재 확인
4. 부재 / 잘못된 경로 → broken_xref

**L4 와 차이**: L4 는 "개념 노트가 아예 없음" (의미적 미흡), L5 는 "링크가 실제로 깨짐" (구문 / 경로 오류).

**Suggestion**:
```
wiki/concepts/a.md:14 — link [Old Note](old-note.md) 대상 부재
  → 옵션:
     a) 대상 노트가 rename 되었는지 검색 (fuzzy match)
     b) 대상 노트 stub 생성
     c) 링크 제거 (사용자 승인)
```

**자동 수정 가능**:
- fuzzy match 가 95%+ 유사도면 자동 정정 제안 (사용자 승인 후 적용)

---

## L6. Data Gaps (정보 공백) — low~medium

노트에 TODO / `[?]` / "TBD" / 빈 섹션이 많은 경우.

**감지**:
1. 본문에서 다음 패턴 카운트:
   - `TODO`, `TBD`, `[?]`, `???`, `FIXME`
   - 빈 섹션 (`## Heading` 다음에 본문 없는 경우)
   - "작성 필요", "확인 필요", "추가 조사"
2. 카운트 ≥ 3 → data_gap

**severity 결정**:
- type=source 노트의 핵심 요약이 비어있음 → **medium**
- type=concept 의 정의가 비어있음 → **medium**
- 부수 섹션 (관련 노트 / commentary) 만 비어있음 → **low**

**Suggestion**:
```
wiki/sources/x-paper.md — 5 TODO / 2 빈 섹션
  → "TL;DR" 섹션이 비어있음. ingest 다시 (raw 재읽기) 또는 사용자 직접 작성
  → "내 메모" 섹션은 비어있어도 정상 (선택)
```

**자동 수정 가능**:
- 없음 (사용자 작성 / 재 ingest 필요)

---

## 7. Lint 실행 순서

```
1. L5 broken_xref 우선 (구조 깨짐 — 다른 lint 결과 신뢰도에 영향)
2. L4 missing_concepts (구조 보강 후)
3. L1 contradictions (의미 충돌 — LLM 추론 비용 큼, 마지막)
4. L2 stale (메타데이터만)
5. L3 orphan (그래프 분석 — L5 fix 후 결과 변동)
6. L6 data_gaps (휘발성 — 마지막)
```

각 단계는 독립 finding 출력 — 한 규칙 실패해도 다음 규칙 계속.

---

## 8. 결과 표 템플릿

```markdown
🔎 lint 완료 — 14 findings (high 2 / medium 5 / low 7)

## High (2)
| ID | Rule | Notes | Summary | Suggestion |
|----|------|-------|---------|-----------|
| L1-001 | contradictions | [[A]], [[B]] | 동일 정의 / 별도 노트 | 머지 후보 |
| L5-003 | broken_xref | [[X]] | 대상 노트 부재 (line 14) | stub 생성 또는 삭제 |

## Medium (5)
...

## Low (7)
...

자동 수정 진행? (high 만 / 전체 / 안 함)
```

---

## 9. 자주 묻는 케이스

| 케이스 | 해결 |
|--------|------|
| Orphan 노트가 많다 (수십 개) | 자동 머지 의심 — schema 의 link style (wikilink vs markdown) 일관성 확인 |
| Broken xref 가 갑자기 폭증 | 노트 rename 후 backlink 미갱신 — `--fix` 로 fuzzy match 일괄 정정 |
| L1 contradictions false positive | LLM 추론 한계. severity 를 medium 으로 강등 옵션 schema 추가 |
| Stale 이 100+ | stale_days 가 너무 짧음 (default 180 — 1년 / 2년으로 늘리기) |

---

**See also**:
- `source-types.md` — ingest 10 source types
- `output-formats.md` — query 5 formats
- `obsidian-compat.md` — Obsidian 호환 시 link resolve 차이
