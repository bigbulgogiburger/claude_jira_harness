---
name: llm-wiki
description: |
  Karpathy LLM Wiki 패턴 — 임의의 정보 소스(웹 글, PDF, 팟캐스트, 책, 슬랙 스레드, 이미지/OCR, 음성 메모, 영상,
  코드 리포, 구조화 노트)를 build-time 합성하는 개인용 위키. 한 번 흡수하면 영구 자산이 됨.
  jira-ingest / wiki-lint 는 jira 도메인 전용이고, 이 스킬은 그 외 모든 raw input → wiki 변환 흐름을 담당.

  자동 트리거 (사용자가 명시적으로 /llm-wiki 라고 하지 않아도 호출 검토):
  - "이 글/논문/PDF/팟캐스트/영상/책 정리해줘"
  - "이거 위키에 추가" / "노트로 저장" / "지식 베이스에 넣어줘"
  - URL + "요약·기록·메모" 의도
  - "내 위키 / 노트 / 지식 베이스 에서 X 찾아줘 / 알려줘 / 관련된 것"
  - "위키 검토 / 정합성 / lint / stale / 중복"
  - "Obsidian / Logseq / 마크다운 노트 그래프"
  - "이 음성/녹음/트랜스크립트 wiki로"

  모드는 사용자 입력에서 자동 추론 (ingest / query / lint). 명시 플래그는 없음.

triggers:
  - "/llm-wiki"
  - "위키에 넣어줘"
  - "위키에 추가"
  - "지식 베이스"
  - "knowledge base"
  - "노트로 저장"
  - "정리해서 기록"
  - "내 위키"
  - "내 노트"
  - "위키 검토"
  - "wiki lint"
---

# /llm-wiki — Karpathy LLM Wiki (범용)

> **단일 출처(SSoT)**: schema 사양은 `~/.claude/skills/_wiki-schema.md` 와 호환되지만,
> 본 스킬은 jira 도메인을 가정하지 않는 **범용 wiki** 를 다룬다.
> jira/dev-guide 워크플로우는 `jira-ingest` + `wiki-lint` 사용.

## 핵심 아이디어 (Karpathy 2026-04 gist 원형)

```
raw/         <- 원본 소스 (PDF/오디오/HTML/이미지/텍스트 — 절대 손대지 않음)
  ↓ ingest (build-time 합성 — LLM 이 읽고 구조화)
wiki/        <- 정제된 노트 (entities / concepts / sources / questions / syntheses)
  ↑ query (이미 합성된 노트에서 검색·재구성 — build-time 비용 분할상환)
CLAUDE.md / AGENTS.md  <- wiki 메타 (디렉토리 구조, 작성 규약, 명명 룰)
```

핵심 원칙:
1. **Wiki ≠ RAG**: RAG 는 query-time 합성(매번 처음부터), Wiki 는 build-time 합성(한 번만, 영구 자산).
2. **원본 보존**: `raw/` 의 파일은 절대 수정·삭제하지 않는다. 사람이 직접 정리할 때만 (수동 archive).
3. **점진적 합성**: 한 번에 완벽한 위키를 만들지 않는다. 흡수 → 인덱스 → 점진 보강.
4. **그래프 구조**: 노트끼리 wikilink(`[[Other Note]]`) 로 연결. Concept ↔ Source ↔ Question 그래프.
5. **Lint loop**: 주기적 자체 검토 (contradictions / stale / orphans / missing concepts / broken xref / data gaps).

## Usage

```
사용자 입력 예 (자연어 — 모드 자동 추론):

# ingest 모드
"https://example.com/article 위키에 넣어줘"
"이 PDF 정리해줘: ~/Downloads/paper.pdf"
"방금 들은 팟캐스트 받아써서 위키화" (+ 오디오 파일 경로)
"슬랙 #design 스레드 4월 12일자 위키에"

# query 모드
"내 위키에서 'mixture of experts' 찾아줘"
"transformer attention 관련 노트 표로 보여줘"
"이 주제로 슬라이드 만들어줘 — wiki 기반"

# lint 모드
"내 wiki stale 한 거 있는지 봐줘"
"위키 정합성 점검"
"orphan 노트 찾아"
```

명시적 플래그는 **하나도 없다** — 모든 동작은 입력 의도 추론. (※ jira-ingest 의 `--subtasks` 와 다름.)

## ⛔ Guard — 첫 실행 / 위치 결정 (최우선)

이 스킬의 어떤 단계보다 **먼저** 실행한다.

### 1단계: WIKI_ROOT 결정

**입력에 명시 경로가 있으면** (`~/wiki/`, `/Volumes/Notes/`, `D:/Obsidian/Vault/` 등):
- 그 경로를 사용. 없으면 생성 확인.

**없으면 후보 자동 탐색** (우선순위):
1. 현재 작업 디렉토리의 `wiki/`, `notes/`, `vault/`
2. `~/wiki/`, `~/notes/`, `~/Documents/wiki/`, `~/Obsidian/`
3. 환경변수 `WIKI_ROOT` / `OBSIDIAN_VAULT`

발견되면 사용자에게 확인:
```
🔍 위키 후보 발견: ~/wiki/ (이전 생성 흔적 — CLAUDE.md + raw/ 존재)
이 위치 사용? [Y/n] / 다른 경로 입력
```

**아무것도 없으면 → 첫 실행 (§1 Onboarding)**.

### 2단계: 의도 분류 (intent inference)

사용자 입력 + 컨텍스트 (전달된 파일 / URL / 키워드) 보고 분류:

| 입력 단서 | 모드 |
|----------|------|
| URL / 파일 경로 / "넣어줘 / 정리 / 저장 / 추가" | **ingest** |
| "찾아줘 / 알려줘 / 어디 / 표로 / 슬라이드 / 차트" | **query** |
| "점검 / 정합성 / lint / stale / orphan / 중복" | **lint** |
| 애매하면 → 사용자에게 1줄 확인 | (default ingest) |

---

## §1. 첫 실행 / Onboarding

WIKI_ROOT 가 비어있거나 `CLAUDE.md` + `raw/` 구조가 없으면 진입.

### 1.1 위치 합의

```
📓 LLM Wiki 첫 셋업이군요.

추천 경로:
  A. ~/wiki/          (가장 간단)
  B. ~/Documents/wiki/ (다른 문서와 함께)
  C. ~/Obsidian/MyVault/ (Obsidian 호환 — 그래프뷰/플러그인 사용)
  D. <사용자 지정>

어디로 할까요?
```

### 1.2 기본 디렉토리 생성

```
<WIKI_ROOT>/
├── CLAUDE.md           # wiki 자체 메타 (이 파일)
├── raw/                # 원본 소스 (immutable)
│   ├── articles/
│   ├── pdfs/
│   ├── audio/
│   ├── images/
│   ├── threads/        # 슬랙/이메일/포럼 dump
│   └── notes/          # 직접 작성한 raw notes
├── wiki/               # 합성된 노트
│   ├── entities/       # 인물 / 조직 / 제품 (고유명사)
│   ├── concepts/       # 추상 개념 / 기법 / 패턴
│   ├── sources/        # 원본 1:1 매칭 source-card
│   ├── questions/      # 미해결 질문 / open loop
│   └── syntheses/      # 여러 노트를 묶는 longer-form 정리
├── INDEX.md            # grep-first 평탄 인덱스 (전체 노트 1줄/개)
├── LOG.md              # append-only 활동 로그
└── .wiki-schema.yaml   # 스키마 / 규약
```

### 1.3 `.wiki-schema.yaml` 기본값

```yaml
version: 1
layout: karpathy-3layer  # raw + wiki + meta
obsidian_compat: false   # true 시 wikilinks + Dataview 호환
note_format:
  frontmatter: required
  fields:
    - id           # slug (snake-kebab, 영문/숫자/하이픈만)
    - title        # 자연어 제목
    - type         # entity / concept / source / question / synthesis
    - source_refs  # raw/ 또는 외부 URL refs (배열)
    - tags         # 자유 태그
    - created      # YYYY-MM-DD
    - updated      # YYYY-MM-DD
    - status       # draft / stable / stale
linking:
  style: wikilink         # [[Note Title]] (obsidian_compat=true 일 때만)
  fallback: markdown_link # [Note Title](path/to/note.md)
log_format: "[YYYY-MM-DD HH:MM TZ MODE id] key=value"
lint:
  rules: [contradictions, stale, orphan, missing_concepts, broken_xref, data_gaps]
  stale_days: 180
ingest:
  default_mode: review    # interactive / batch / review
  source_types: [article, pdf, audio, video, book, thread, image, voice_memo, code_repo, structured_notes]
```

### 1.4 CLAUDE.md / AGENTS.md 시드

위키 자체 메타. **사용자 디렉토리 구조 + 규약** 을 LLM 이 다음 호출에 자동 흡수하도록.

```markdown
# LLM Wiki

> Karpathy 3-layer (raw / wiki / meta) — 자세히는 `.wiki-schema.yaml`

## 디렉토리
- `raw/` — 원본 (immutable). 절대 수정·삭제 금지
- `wiki/` — 합성된 노트
  - `entities/` 인물/조직/제품
  - `concepts/` 추상 개념
  - `sources/` 원본 1:1 매칭
  - `questions/` open loop
  - `syntheses/` longer-form
- `INDEX.md` — 전체 노트 인덱스 (grep first)
- `LOG.md` — append-only

## 작성 규약
- 모든 노트는 frontmatter (id/title/type/source_refs/tags/created/updated/status)
- 링크: `[Title](relative/path.md)` (Obsidian 호환 모드면 `[[Title]]`)
- source_refs 는 raw/ 의 파일 경로 또는 외부 URL
```

### 1.5 첫 ingest 즉시 실행

Onboarding 완료 후, 사용자가 원래 주려던 입력(URL/파일/주제) 으로 ingest 흐름 진입.

---

## §2. Ingest 모드

새 raw 소스를 흡수해서 `wiki/` 에 정제된 노트를 만든다.

### 2.1 절차 개요

```
1. 소스 타입 판별 (URL / 파일 확장자 / 키워드)
   → references/source-types.md 의 해당 타입 절차 따라감
2. raw/ 로 원본 보존 (텍스트 변환된 사본 + 메타)
3. LLM 합성:
   a) source-card 1장 작성 (wiki/sources/<slug>.md) — 1:1 매칭
   b) 등장 entity/concept 추출 → 기존 노트 있으면 갱신, 없으면 신규
   c) cross-link (wikilink / markdown link)
   d) open question 발견 → wiki/questions/ 에 stub
4. INDEX.md 에 새 노트 row 추가 / 기존 노트 updated 갱신
5. LOG.md append (mode=ingest, source=..., notes_added=N, notes_updated=M)
```

### 2.2 Supervision 모드 (사용자 입력으로 추론)

| 단서 | Supervision |
|------|-------------|
| "내가 검토할게 / 보여주고 / 확인할게" | **interactive** — 각 노트 작성 직전 사용자 확인 |
| "한꺼번에 / 알아서 / 빨리 / 일괄" | **batch** — 끝까지 진행 후 diff 보고 |
| (default) | **review** — 전체 끝 후 변경 요약만 출력, diff 는 요청 시 |

기본값은 schema 의 `ingest.default_mode` 따름.

### 2.3 Source-Card 템플릿

```markdown
---
id: source-<slug>
title: <원제목>
type: source
source_refs:
  - raw/<subdir>/<file>
  - <원본 URL 또는 식별자>
tags: [<자동 추출>]
created: 2026-05-14
updated: 2026-05-14
status: draft
---

# {{title}}

**저자/출처**: {{author / publisher}}
**날짜**: {{publish date}}
**유형**: {{article / pdf / podcast / ...}}

## 핵심 요약 (TL;DR)
- {{3-5 bullet}}

## 등장 인물·조직 (entities)
- [[Person A]] — {{relation}}
- [[Org B]] — {{relation}}

## 핵심 개념 (concepts)
- [[Concept X]] — {{why mentioned}}

## 인용 / 발췌
> "{{notable quote}}" — p.{{N}} / {{timestamp}}

## 내 메모 (commentary)
- {{user's own takes — optional}}

## Open questions
- [[Q: <질문>]]

## 관련 노트
- [[Related Synthesis]]
```

10가지 소스 타입별 세부 절차는 `references/source-types.md`.

### 2.4 Entity / Concept 노트 갱신 룰

**이미 존재하는 노트 갱신 시**:
- frontmatter `updated` 만 갱신
- 본문은 ingest-managed 영역에 새 source-ref 추가 (사용자 작성 영역은 보존)
- ingest-managed sentinel: `<!-- llm-wiki:auto-section name="source-references" -->...<!-- /llm-wiki:auto-section -->`

**신규 노트**:
- type 결정 (entity/concept) → 해당 디렉토리 + slug 파일명
- 최소 frontmatter + 한 줄 정의 + 소스 1개 link

### 2.5 cross-link 정책

- source-card 는 등장하는 모든 entity/concept 로 outbound link.
- entity/concept 노트는 inbound source 들로 backlink (ingest-managed 영역).
- Obsidian 호환 모드면 `[[Title]]` (Obsidian 가 자동으로 양방향 해결).
- 기본 모드는 `[Title](../concepts/title.md)` 명시 경로.

---

## §3. Query 모드

이미 합성된 위키에서 정보를 꺼낸다. **RAG 가 아니라 grep + 노트 탐색** 이 기본.

### 3.1 절차

```
1. 사용자 키워드 / 주제 추출
2. 1차 탐색:
   - INDEX.md grep (title + tags)
   - wiki/**/*.md frontmatter grep (id / tags)
3. 2차 보강:
   - 발견된 노트의 outbound link 1-hop traversal
   - related synthesis 노트 확인
4. 출력 포맷 결정 (사용자 입력 추론):
   - "표로" → table
   - "슬라이드 / 발표" → Marp / reveal markdown
   - "차트 / 다이어그램" → mermaid
   - "캔버스 / 시각화" → Obsidian Canvas json (호환 모드)
   - 기본 → markdown 답변
5. 답변 작성. 모든 주장은 [[Note]] 또는 (note.md:line) 출처 포함.
```

### 3.2 출력 포맷 세부

`references/output-formats.md` — 5가지 포맷 템플릿 + 변환 룰.

### 3.3 모름·미정 처리

- 위키에 없으면 **거짓말하지 않는다**. "위키에 없음" 명시 + 외부 검색/ingest 제안.
- 모순되는 노트 2개 발견 시 → 둘 다 인용 + lint 에 contradiction 후보 등록.

---

## §4. Lint 모드

위키 자체 정합성·신선도 점검. **read-only 기본, 수정은 사용자 승인 후**.

### 4.1 6가지 규칙 (Karpathy 원본)

| 규칙 | 검사 내용 |
|------|----------|
| **L1 contradictions** | 같은 entity/concept 노트끼리 진술 충돌 |
| **L2 stale** | `updated` 가 schema.lint.stale_days 초과 + status≠stable |
| **L3 orphan** | inbound link 0, outbound link 0 (고립) |
| **L4 missing_concepts** | source-card 가 언급한 concept 의 노트 부재 |
| **L5 broken_xref** | wikilink / markdown link 대상 부재 |
| **L6 data_gaps** | TODO / `[?]` / "TBD" / 빈 섹션 다수 |

세부 룰 + JSON 출력 스키마는 `references/lint-rules.md`.

### 4.2 동작

```
1. 6가지 규칙 일괄 실행 → finding 리스트
2. severity = high / medium / low
3. 기본은 read-only — finding 표 출력
4. 사용자가 "고쳐줘 / 자동 수정 / --fix" 의도면 → 항목별 제안 + 승인 받고 적용
   - L5 broken_xref: 대상 노트 stub 자동 생성 (사용자 승인 필수)
   - L3 orphan: 적당한 synthesis 후보 제안
   - L2 stale: status=stale 마킹 + LOG 기록
```

---

## §5. Idempotency / 충돌

**3-layer 멱등 보장**:

1. **source-ref 중복 방지**: 이미 source_refs 에 있는 URL/파일은 재 ingest 시 noop + updated 만 갱신 (사용자가 "다시 / 재합성" 의도 명시하면 강제 재작성).
2. **ingest-managed sentinel**: entity/concept 노트의 source-references 섹션은 sentinel 사이만 수정. 사용자 free-form 영역은 절대 손대지 않음.
3. **LOG append-only**: 같은 source 라도 ingest 시도마다 LOG 1줄 (mode / 시각 / 결과).

---

## §6. 에러 / 폴백

| 상황 | 처리 |
|------|------|
| URL fetch 실패 | `scripts/fetch_web.py` 재시도 → 그래도 실패 시 사용자에게 raw 텍스트 paste 요청 |
| PDF 텍스트 추출 실패 (이미지 PDF) | OCR (Tesseract / 외부) — 없으면 사용자에게 알림 |
| 오디오 트랜스크립션 | `scripts/transcribe.py` (Whisper API → 키 없으면 faster-whisper 로컬) |
| Obsidian 호환 모드인데 vault 가 아님 | 자동 mismatch 알림 + 폴백 markdown link |
| wiki/ 가 너무 커서 grep 느림 | INDEX.md 인덱스만 먼저 grep, 2차 보강만 노트 read |
| 사용자 schema 가 손상 | 백업 + 기본값으로 복원 + 사용자 알림 |

---

## §7. Output 포맷

각 모드 종료 시 1줄 요약 + 표.

**ingest 결과**:
```
📚 ingest 완료 — source: <slug>
  - 신규 노트: 3 (concept:[[X]], entity:[[Y]], question:[[Q: ...]])
  - 갱신 노트: 2 (source-ref 추가)
  - INDEX.md row: +1
  - LOG.md: append 1줄
다음 제안: lint 점검? 관련 노트 그래프 시각화?
```

**query 결과**:
```
🔍 'X' 검색 — 6 노트 매칭
[표 또는 답변 본문]
출처: [[Note A]], [[Note B]], [[Source: ...]]
```

**lint 결과**:
```
🔎 lint 완료 — 14 findings (high 2 / medium 5 / low 7)
high:
  L1 [[A]] vs [[B]] 진술 충돌 (line 14 vs line 23)
  L5 [[Missing X]] broken xref (referenced in 3 notes)
medium: ...
low: ...
자동 수정 진행? (high 만 / 전체 / 안 함)
```

---

## §8. 도구 의존성

| 기능 | 도구 |
|------|------|
| URL fetch | `scripts/fetch_web.py` (requests + readability-lxml) |
| 음성 → 텍스트 | `scripts/transcribe.py` (OpenAI Whisper / faster-whisper) |
| PDF → 텍스트 | `pdftotext` (poppler) 또는 PyPDF2 — 없으면 사용자 paste |
| 그래프 시각화 | `scripts/build_graph.py` (D3.js static html) |
| 이미지 OCR | Tesseract (선택) — 없으면 사용자 paste |

모든 스크립트는 **실패해도 위키 자체는 동작** — 사용자 raw paste 폴백 항상 존재.

---

## §9. Obsidian / Logseq 호환

`obsidian_compat: true` 활성화 시:
- wikilink `[[Title]]` 사용 (Obsidian 자동 해석)
- frontmatter 에 Dataview 친화 필드 추가 (`type::`, `tags::` inline 도 옵션)
- Canvas json 출력 가능
- 자세히는 `references/obsidian-compat.md`

기본은 **plain markdown** — 어떤 마크다운 뷰어에서도 동작.

---

## §10. 다른 스킬과의 관계

| 스킬 | 도메인 | 본 스킬과 |
|------|--------|----------|
| `jira-ingest` | jira issue + dev-guide | 직교. 본 스킬은 jira 도메인 아닌 모든 것 |
| `wiki-lint` | jira wiki (docs/INDEX.md, LOG.md) | 직교. 본 스킬의 lint 는 자신의 wiki 만 |
| `graphify` | 임의 입력 → 지식 그래프 (one-shot) | 본 스킬은 영구 자산화 (graphify 는 ephemeral) |
| `learned` | 학습 메모 1줄 추가 | 본 스킬은 longer-form + 그래프 구조 |

겹쳐 보이면 본 스킬은 "build-time 합성 + 영구 자산" 이라는 점이 핵심.

---

**Last Updated**: 2026-05-14 (M1 초안 — Karpathy 2026-04 gist 패턴 적용. references/ + scripts/ 묶음)
