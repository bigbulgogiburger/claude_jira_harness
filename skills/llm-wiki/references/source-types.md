# Source Types — Ingest 절차 (10가지)

> SKILL.md §2.1 의 단계 1 (소스 타입 판별) → 본 문서의 해당 섹션 따라감.
> 모든 절차는 **raw 보존 + source-card 작성 + entity/concept 추출 + cross-link + INDEX/LOG 갱신** 의 공통 형태.

## 0. 공통 사전 단계

```
1. 사용자 입력에서 타입 단서 추출 (URL / 확장자 / 키워드)
2. raw/<subdir>/<slug>.<ext> 경로 결정
3. 기존 source_ref 충돌 검사 (멱등) — 있으면 사용자에게 재합성 의도 확인
4. 타입별 절차 (아래)
5. 공통 후처리: source-card → entity/concept 추출 → INDEX/LOG
```

slug 규약: `YYYY-MM-DD_<short-title-kebab>` (예: `2026-04-30_karpathy-llm-wiki`). 충돌 시 `-2`, `-3` suffix.

---

## 1. Article (Web URL)

**감지**: `http://` / `https://` URL 단일. 도메인이 youtube/podcast/github 아닌 경우.

**raw 저장**:
```
raw/articles/<slug>.html       # 원본 HTML (선택)
raw/articles/<slug>.md         # readability 추출된 main content
raw/articles/<slug>.meta.json  # title, author, publish_date, canonical_url
```

**추출 절차**:
1. `scripts/fetch_web.py <url>` 호출 → readability-lxml 로 본문만 추출
2. 실패 (paywall / JS-rendered) → 사용자에게 알림 + raw text paste 요청
3. meta 추출: `<title>`, `<meta name="author">`, `<meta property="article:published_time">`, JSON-LD
4. 본문이 너무 짧으면 (< 500자) — paywall 의심, 사용자 확인

**source-card 특수 필드**:
```yaml
canonical_url: https://example.com/...
author: <name>
publish_date: YYYY-MM-DD
publisher: <site name>
estimated_read_time: 8 min
```

**함정**:
- `?utm_*` 파라미터는 canonical_url 비교 전 제거 (멱등성)
- 동일 글 다른 URL (mirror, archive.org) 은 사용자 판단
- 너무 긴 글 (> 50KB text) — 사용자에게 부분 흡수 vs 전체 확인

---

## 2. PDF (논문 / 보고서 / 책 챕터)

**감지**: `.pdf` 확장자. 또는 `arxiv.org`, `*.pdf` URL.

**raw 저장**:
```
raw/pdfs/<slug>.pdf            # 원본 (immutable)
raw/pdfs/<slug>.txt            # 추출된 텍스트
raw/pdfs/<slug>.meta.json      # title, authors, abstract, year, pages
```

**추출 절차**:
1. `pdftotext -layout <file> <slug>.txt` (poppler)
   - 폴백: PyPDF2 / pdfplumber
   - 실패 (이미지 PDF) → Tesseract OCR 시도 → 그래도 실패면 사용자 paste
2. 첫 페이지 + abstract 영역 자동 인식 (논문이면)
3. References 섹션 분리 → meta 에 `cited_works: []` 보관 (선택)

**source-card 특수 필드**:
```yaml
authors: [...]
year: 2026
venue: <conference / journal>
pages: 12
arxiv_id: 2604.12345  # 있으면
doi: 10.xxxx/...      # 있으면
abstract: |
  <원문 abstract>
```

**함정**:
- 2단 컬럼 PDF: `-layout` 옵션 + 후처리로 정리
- 수식·표·그림: 텍스트 추출에서 소실 → source-card 에 "수식 / 그림은 원본 참조" 명시
- 100p+ 책 챕터: section 별로 source-card 분할 옵션

---

## 3. Podcast Audio

**감지**: `.mp3` / `.m4a` / `.wav` / `.ogg` 확장자. 또는 podcast platform URL.

**raw 저장**:
```
raw/audio/<slug>.mp3           # 원본 오디오
raw/audio/<slug>.transcript.txt # 트랜스크립트
raw/audio/<slug>.meta.json     # podcast name, episode, host, guests, duration
```

**추출 절차**:
1. `scripts/transcribe.py <audio_file>` 호출
   - 1차: OpenAI Whisper API (OPENAI_API_KEY 있으면)
   - 2차: faster-whisper 로컬 모델
   - 3차: 실패 시 사용자에게 외부 트랜스크립트 paste 요청
2. 트랜스크립트에 timestamp 포함 (`[00:14:23] speaker: ...`)
3. host / guest 화자 분리 (Whisper diarization 옵션) — 안 되면 사용자 입력

**source-card 특수 필드**:
```yaml
podcast: <show name>
episode: <number / title>
host: <name>
guests: [<name>, ...]
duration: 1h 23m
audio_url: <원본 URL>
key_timestamps:
  - "00:14:23 — <topic>"
  - "00:32:10 — <topic>"
```

**인용 시 timestamp 보존**: `> "..." — [00:14:23]`

**함정**:
- 긴 팟캐스트 (2h+) — chunk 분할 후 합치기 (Whisper API 25MB 제한)
- 배경음악 / 광고 구간 — 트랜스크립트 후처리 단계 제안만, 자동 삭제 X
- 다국어 — 언어 명시 후 ingest

---

## 4. Book (EPUB / Plain Text)

**감지**: `.epub` / `.txt` 큰 단일 파일. 또는 사용자가 "이 책" 언급.

**raw 저장**:
```
raw/books/<slug>.epub          # 원본
raw/books/<slug>/              # chapter split (선택)
  ├── chapter-01.md
  ├── chapter-02.md
  └── meta.json
```

**추출 절차**:
1. EPUB → `ebook-convert <file> <slug>.txt` (calibre) 또는 epub2md
2. Chapter 자동 분할 (toc.ncx 기반)
3. 각 chapter 가 한 source-card → `wiki/sources/<slug>-chapter-N.md`
4. 책 전체 1장 synthesis 노트 → `wiki/syntheses/book-<slug>.md`

**source-card 특수 필드**:
```yaml
book_title: <전체 제목>
book_author: <author>
isbn: <ISBN>
chapter: <N or title>
year: <publish year>
edition: <edition>
```

**함정**:
- 픽션 vs 논픽션 처리 다름 — 픽션은 entity 추출 시 등장인물 위주, 논픽션은 concept 위주
- 사용자가 "이 책 전체" vs "이 챕터만" 의도 명확화 (긴 작업이므로)

---

## 5. Slack Thread / Forum / Email

**감지**: "스레드 / thread / 토론 / 채널 / 메일" 키워드 + paste 텍스트. 또는 export 파일.

**raw 저장**:
```
raw/threads/<slug>.json        # 구조화 dump (사용자 paste 또는 export)
raw/threads/<slug>.md          # 사람이 읽기 좋게 정리
raw/threads/<slug>.meta.json   # channel, date, participants
```

**추출 절차**:
1. 사용자가 raw text / json paste — 자동 구조 인식 시도
2. 시간순 + 화자 분리 표시
3. 첨부 파일 / 이미지 링크는 raw/threads/<slug>-attachments/ 로 보관
4. 핵심 결정·인용·decision 추출

**source-card 특수 필드**:
```yaml
channel: "#design-system"
platform: slack / discord / email / forum
date_range: 2026-04-10 ~ 2026-04-12
participants: [<name>, ...]
message_count: 47
key_decisions:
  - <decision 1>
  - <decision 2>
```

**함정**:
- PII / 민감 정보 — paste 전 사용자가 redact 했는지 확인
- 긴 스레드 — 핵심 빌트만 추출, 전체는 raw 에만 보관

---

## 6. Image (OCR / Screenshot)

**감지**: `.png` / `.jpg` / `.heic` / `.webp` 확장자.

**raw 저장**:
```
raw/images/<slug>.<ext>        # 원본 이미지
raw/images/<slug>.ocr.txt      # OCR 결과 (있으면)
raw/images/<slug>.alt.md       # 사람이 작성한 alt text (선택)
```

**추출 절차**:
1. 텍스트 위주 이미지 (스크린샷 / 슬라이드 / 칠판 / 책 페이지):
   - Tesseract OCR → `<slug>.ocr.txt`
   - 또는 사용자가 Claude vision 으로 직접 읽고 alt.md 작성
2. 다이어그램 / 차트:
   - Claude vision 으로 구조 추출 → markdown / mermaid 변환 후 source-card 본문에 inline
3. 사진 (인물·풍경) — alt 설명만, 본문 추출 X

**source-card 특수 필드**:
```yaml
image_type: screenshot / diagram / photo / handwritten
source_app: <앱 / 사이트> (스크린샷일 때)
ocr_confidence: high / medium / low / none
```

**함정**:
- 손글씨 / 칠판 — OCR 정확도 낮음, 사용자 검수 필수
- 다이어그램 — 자동 mermaid 변환은 단순 케이스만, 복잡하면 사용자 정리 요청

---

## 7. Voice Memo (자기 음성 노트)

**감지**: 짧은 `.m4a` / `.mp3` / `.wav` (보통 < 10분) + "음성 메모 / 녹음 / 보이스" 키워드.

**raw 저장**:
```
raw/voice_memos/<slug>.m4a     # 원본
raw/voice_memos/<slug>.txt     # 트랜스크립트
raw/voice_memos/<slug>.meta.json
```

**추출 절차**:
1. `scripts/transcribe.py` (팟캐스트와 동일)
2. 트랜스크립트가 **나의 생각** 일 가능성 높음 → entity 추출보다 concept / question 추출에 무게
3. source-card 보다 → 곧장 `wiki/questions/` 또는 `wiki/syntheses/` 로 변환하기도 함 (사용자 의도 추론)

**source-card 특수 필드**:
```yaml
recorded_at: 2026-05-14 14:32
duration: 4m 12s
location: <옵션 — GPS / 장소>
mood_tag: <옵션 — brainstorm / debrief / journal>
```

**함정**:
- 자동 PII 검사 — 이름·전화번호 언급 시 사용자 확인 (보관 의도?)
- 짧으면 source-card 생략하고 entity/concept 노트에 직접 인용

---

## 8. Video URL (YouTube / Vimeo)

**감지**: `youtube.com/watch` / `youtu.be/` / `vimeo.com/` URL.

**raw 저장**:
```
raw/videos/<slug>.transcript.txt  # 트랜스크립트
raw/videos/<slug>.meta.json       # title, channel, duration, published
raw/videos/<slug>.thumbnail.jpg   # 옵션
```

원본 영상은 보관 X (URL 만). 사용자가 명시적으로 "다운로드 보관" 요청 시만 `yt-dlp` 사용.

**추출 절차**:
1. YouTube 자동 자막 (`youtube-transcript-api`) — 1차
2. 없으면 `yt-dlp --extract-audio` → `scripts/transcribe.py`
3. 채널 / 업로더 메타 추출

**source-card 특수 필드**:
```yaml
video_url: https://youtube.com/watch?v=...
channel: <channel name>
duration: 14m 32s
published: YYYY-MM-DD
key_timestamps: [...]
```

**함정**:
- 라이브 / 스트림 — 자막 신뢰도 낮음
- 너무 긴 영상 (1h+) — 사용자에게 부분 흡수 확인

---

## 9. Code Repo (GitHub / GitLab)

**감지**: `github.com/<owner>/<repo>` / `gitlab.com/...` URL. 또는 로컬 git repo 경로.

**raw 저장**:
```
raw/code_repos/<owner>__<repo>.meta.json  # stars, lang, last_commit, readme
raw/code_repos/<owner>__<repo>.README.md  # README 사본
```

코드 자체는 보관 X (clone 은 사용자가 명시 요청 시만).

**추출 절차**:
1. README + 주요 docs (`docs/`, `ARCHITECTURE.md`) 만 흡수
2. 메타: stars, language, license, latest release
3. source-card 는 "프로젝트 카드" 성격 — 진입점·핵심 아이디어·관련 concept

**source-card 특수 필드**:
```yaml
repo_url: https://github.com/owner/repo
language: Python
stars: 12345
license: MIT
latest_release: v2.3.1
related_concepts: [[Concept A]], [[Concept B]]
```

**함정**:
- 큰 monorepo — README 만으로는 표면적, 사용자가 "디렉토리 N 자세히" 요청 시 단계 추가
- private repo — paste 우회

---

## 10. Structured Notes (Notion / Markdown bulk / Obsidian export)

**감지**: 디렉토리 단위 markdown / Notion export zip / `.md` 다수.

**raw 저장**:
```
raw/structured_notes/<bundle-slug>/
  ├── original/             # 원본 통째로 (immutable)
  └── meta.json
```

**추출 절차**:
1. 디렉토리 트리 파악 — 페이지·하위페이지 관계
2. 각 페이지를 source-card 1장으로 — 1:1 매칭
3. 페이지 간 링크 (`[[]]` 또는 `[](./page.md)`) 보존
4. tag / property 가 있으면 frontmatter 로 흡수
5. 사용자에게 "bulk 흡수 vs 선택 흡수" 확인 (큰 dump 일 수 있음)

**source-card 특수 필드**:
```yaml
bundle: <export name>
origin: notion / obsidian / dendron / logseq
original_path: <원본 페이지 경로>
backlinks_count: 5  # 흡수 후 자동 산출
```

**함정**:
- Notion → 마크다운 변환 깨짐 (toggle, callout, embed) — 1차 변환 후 사용자 검수
- 중복 흡수 방지 — 이미 ingest 한 bundle 재흡수 시 diff only 모드

---

## 디스패치 테이블 (요약)

| 단서 | 타입 | 섹션 |
|------|------|------|
| URL (일반 도메인) | article | §1 |
| `.pdf` | pdf | §2 |
| `.mp3`/`.m4a`/`.wav` (장시간) | podcast | §3 |
| `.epub`, "이 책" | book | §4 |
| "스레드 / 채널 / 메일" + paste | thread | §5 |
| `.png`/`.jpg`/스크린샷 | image | §6 |
| 짧은 audio + "메모 / 녹음" | voice_memo | §7 |
| youtube.com / vimeo | video | §8 |
| github.com / gitlab | code_repo | §9 |
| 디렉토리 / .zip + 다수 .md | structured_notes | §10 |
| 애매 | 사용자에게 1줄 확인 | — |

---

**See also**:
- `output-formats.md` — query 모드의 5가지 출력 포맷
- `lint-rules.md` — 6가지 lint 규칙 세부
- `obsidian-compat.md` — Obsidian / Logseq 호환 모드
