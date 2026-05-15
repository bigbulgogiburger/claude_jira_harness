# Obsidian / Logseq 호환 모드

> SKILL.md §9 (Obsidian / Logseq 호환).
> `obsidian_compat: true` 활성화 시 동작 차이 + 추가 기능.

## 0. 활성화 / 비활성화

`.wiki-schema.yaml`:
```yaml
obsidian_compat: true   # 기본 false
```

활성화하면:
- 링크 스타일: `[[Title]]` (wikilink) 기본
- frontmatter 외에 inline metadata 지원 (Dataview)
- Canvas (`.canvas`) 출력 가능
- 그래프뷰 호환 메타 자동 추가

---

## §1. Link 스타일 차이

### 1.1 plain markdown (default — `obsidian_compat: false`)

```markdown
[Concept A](../concepts/concept-a.md)
```

- 경로 명시. GitHub / VSCode / 일반 마크다운 뷰어 어디서나 클릭 가능.
- 단점: 파일 rename 시 모든 backlink 수동 갱신.

### 1.2 wikilink (`obsidian_compat: true`)

```markdown
[[Concept A]]
```

- 파일명/title 매칭 자동. rename 시 Obsidian 이 backlink 자동 갱신.
- 단점: Obsidian / Logseq 외 뷰어에선 일반 텍스트.

### 1.3 혼합 (호환 모드 + 외부 공유)

- 본 스킬이 작성하는 노트는 호환 모드면 `[[Title]]` 사용
- 외부 공유용 변환 필요 시 `--export markdown` 의도로 wikilink → markdown link 일괄 변환

---

## §2. Dataview 친화 frontmatter

Obsidian 의 **Dataview** 플러그인은 frontmatter + inline `key:: value` 둘 다 인식.

본 스킬의 frontmatter 는 Dataview 호환:
```yaml
---
id: concept-attention
title: Attention
type: concept
tags: [transformer, dl-2017]
status: stable
source_refs:
  - raw/pdfs/attention-is-all-you-need.pdf
created: 2026-05-10
updated: 2026-05-14
---
```

→ Dataview 쿼리 예:
~~~markdown
```dataview
TABLE title, updated, status
FROM "wiki/concepts"
WHERE type = "concept" AND status = "stable"
SORT updated DESC
```
~~~

호환 모드에서 본문 inline metadata 도 옵션:
```markdown
type:: concept
related:: [[Self-Attention]], [[Transformer]]
```

기본은 frontmatter only (덜 어수선).

---

## §3. 그래프뷰 호환 메타

Obsidian 그래프뷰는 wikilink + tag 로 자동 그래프 구성. 본 스킬은 추가 메타 없이 호환.

옵션 보강:
- 노트 타입별 색상 — Obsidian Settings → Graph view → Groups
  - `wiki/entities/` → 파랑
  - `wiki/concepts/` → 초록
  - `wiki/sources/` → 노랑
  - `wiki/questions/` → 빨강
  - `wiki/syntheses/` → 보라

이 설정은 본 스킬이 작성하지 않음 — vault 별 사용자 설정.

---

## §4. Canvas (`.canvas`)

Obsidian Canvas — 무한 캔버스에 노트를 자유 배치 + 화살표 연결.

본 스킬은 query 모드에서 Canvas 출력 가능 (`output-formats.md §5`).

**파일 위치**:
```
<WIKI_ROOT>/query-output/<topic-slug>.canvas
```

Obsidian vault 안에 두면 자동 인식.

**호환성**:
- Obsidian 1.1+ Canvas 필수
- JsonCanvas 1.0 spec (공식) — 다른 도구도 지원 가능 (Anytype 등)

---

## §5. Logseq 차이점

Logseq 도 wikilink 사용하지만 주요 차이:

| 기능 | Obsidian | Logseq |
|------|---------|--------|
| 파일 단위 | 1 파일 = 1 노트 | 1 파일 = 1 page, 본문은 outline (bullet 위주) |
| frontmatter | YAML | `--- key: value ---` 비슷 또는 `key:: value` inline |
| 백링크 | 자동 | 자동 |
| 블록 참조 | 일부 | core 기능 (블록 단위 참조) |
| Canvas | 있음 | "Whiteboard" (베타) |

본 스킬은 **Obsidian 우선** — Logseq 호환은 best-effort.

Logseq 사용자가 본 스킬 흡수 결과를 import 하려면:
1. `obsidian_compat: true` 로 ingest
2. Logseq 의 "Import" → Obsidian vault 선택
3. outline 변환은 사용자가 수동

---

## §6. 호환 모드 lint 차이

`obsidian_compat: true` 일 때 lint 추가 검사:
- **wikilink ambiguity**: `[[X]]` 가 여러 노트와 매칭되는 경우 (Obsidian 도 헷갈림)
- **Canvas orphan**: `.canvas` 파일이 참조하는 노트 부재
- **Dataview query 실패**: inline query 가 결과 0 (사용자 의도 미스매치 가능)

`L5 broken_xref` 의 변형으로 흡수 — 별도 severity 없음.

---

## §7. 마이그레이션

### 7.1 plain → Obsidian compat 전환

```
1. .wiki-schema.yaml — obsidian_compat: true 로 변경
2. 전체 노트의 [Title](path.md) → [[Title]] 일괄 변환
   - 단순 정규식 + frontmatter title 매칭
   - 본 스킬에 "마이그레이션 모드" 의도 (사용자 입력) 시 자동
3. lint 1회 실행 — wikilink ambiguity 후처리
```

### 7.2 Obsidian → plain 전환

```
1. obsidian_compat: false 로 변경
2. [[Title]] → [Title](relative/path.md) 일괄 변환
   - title 검색 → 첫 매칭 노트 경로 사용
   - 매칭 안 되면 finding 으로 출력
```

---

## §8. 주의

- **vault 위치**: Obsidian vault 가 `<WIKI_ROOT>` 자체이면 자동 인식. 별도 디렉토리면 사용자가 Obsidian 에 vault 등록 필요.
- **숨김 파일**: Obsidian 은 `.obsidian/` 디렉토리에 설정 저장. 본 스킬은 건드리지 않음.
- **plugins**: 본 스킬은 Obsidian plugin 설치 / 활성화 요청 안 함. Dataview 등 사용자가 직접.

---

**See also**:
- `source-types.md` — Notion / Obsidian export 흡수 (§10)
- `output-formats.md §5` — Canvas 출력
- `lint-rules.md §0` — wikilink ambiguity 처리
