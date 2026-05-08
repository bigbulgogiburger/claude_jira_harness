---
name: imagegen
description: Raster/bitmap 이미지 생성·편집 전용 스킬. OpenAI Codex CLI 의 `$imagegen` 을 메인 Claude 세션에서 직접 오케스트레이션합니다 — 사용자와 2~3개 질문으로 brief 를 구체화하고, `codex exec` 를 백그라운드로 호출하면서 Monitor 로 폴링합니다. **Use PROACTIVELY** whenever the user asks to generate/create/draw/design/edit a raster asset — photo, illustration, logo, icon, banner, thumbnail, avatar, character, sprite, texture, mockup, background, transparent cutout, 또는 기존 이미지 재가공. 한국어 자동 트리거 예시 — "이미지 만들어줘", "이미지 생성", "로고 디자인", "아이콘 만들어", "배너 생성", "썸네일", "일러스트", "목업", "캐릭터 그려줘", "포스터 제작", "사진 만들어", "배경 이미지". 결과 파일은 호출 프로젝트 루트 하위 `codex-image/` 폴더에 저장됩니다. **기본 경로는 Codex built-in image tool (ChatGPT Plus 한도 내 무료, API 키 불필요)** — OPENAI_API_KEY 기반 유료 CLI fallback 은 사용자가 먼저 명시적으로 요청했을 때만. SVG/벡터/아이콘 시스템 확장·코드 생성·버그 조사·리뷰·리팩토링에는 **절대 사용 금지** — 그건 일반 Claude 세션 또는 codex-rescue 담당입니다.
---

# Imagegen — Codex CLI 기반 raster 이미지 생성

## 이 스킬의 철학

이 스킬은 **thin orchestrator** 입니다. 메인 Claude 세션이 직접 사용자와 대화하며 brief 를 합의한 뒤, OpenAI Codex CLI 의 `$imagegen` 스킬을 백그라운드로 호출합니다. 스킬 자체가 "이미지를 그리는 AI" 가 아니라, 그림 그리는 AI(Codex built-in `image_gen` tool) 를 잘 쓰도록 돕는 얇은 프로토콜입니다.

**이전 구현 (서브에이전트) 대비 차이점:**
- Clarify 단계가 메인 세션에서 일어나므로 사용자 답이 지연 없이 바로 반영됨
- 폴링/에러 복구/한도 소진 감지가 같은 세션에서 이뤄져 진단이 빠름
- 사용자가 언제든 끼어들어 방향을 바꿀 수 있음 (서브에이전트는 격리)

## Scope (반드시 지킬 것)

**포함:**
- Raster/bitmap 생성 — 사진, 일러스트, 텍스처, 스프라이트, 캐릭터, 목업, 로고(raster), 아이콘, 배너, 썸네일, 배경, 투명 배경 컷아웃
- 기존 이미지 기반 편집·재가공 (참조 이미지 경로 제공 시 `-i` 플래그)

**제외 (즉시 반려):**
- SVG·벡터·아이콘 시스템 확장 → `$imagegen` 스코프 밖. 사용자에게 "벡터 툴(Figma/Illustrator)로 작업하시거나 별도 요청 주세요" 안내
- 코드·문서·텍스트 생성 → 일반 Claude 세션 또는 codex-rescue
- 버그 조사·리뷰·리팩토링·테스트 수정 → codex-rescue

## 실행 경로 매트릭스

Codex v0.122.x ~ v0.123.x 실증 결과 — **Primary 만 기본값**이며, 나머지는 사용자 명시 또는 실패 시에만 진입.

| 경로 | 트리거 | imagegen 경로 | 비용 | 우선순위 |
|---|---|---|---|---|
| `codex exec` + **built-in 강제 프롬프트** | 기본 | built-in `image_gen` tool | **무료** (ChatGPT 한도) | **Primary** |
| Interactive `codex` TUI | Primary 실패 시 handoff | built-in `image_gen` tool | **무료** | Hand-off |
| `codex exec` + 일반 프롬프트 | 사용자 명시 요청 + 재확인 | CLI fallback (`scripts/image_gen.py`) | **유료** | 최후 수단 |

**핵심 통찰**: 로컬 `~/.codex/skills/imagegen/SKILL.md` 구버전이 CLI fallback 을 기본값으로 씀. 프롬프트에 `[STRICT INSTRUCTION: Use the built-in image_gen tool only]` 를 **명시적으로** 박아야 무료 built-in 경로로 감.

---

## Phase 1 — Clarify (QnA, 대부분 필수)

사용자 요청을 받자마자 **차원 체크리스트**를 훑어 명시되지 않은 차원 2~3개만 골라 QnA. 이 단계를 건너뛰면 generic 이미지가 나와 사용자 의도와 어긋납니다.

### 필수 차원 체크리스트

| # | 차원 | 질문 예시 | 기본값 전략 |
|---|------|-----------|-----------|
| 1 | 용도 (where) | 앱 어느 화면·위치? 헤더/배너/아이콘/썸네일/배경/일러스트 | 사용자 맥락 충분하면 생략 |
| 2 | 크기/비율 | 해상도·비율 | 기존 asset 교체면 원본 매치 |
| 3 | 스타일 | photo / flat illustration / 3D / 수채화 / 픽셀아트 | 프로젝트 기존 자산 톤 참고 |
| 4 | 주제·피사체 | 무엇을 담나 | **반드시 묻기** (추측 금지) |
| 5 | 팔레트 | 브랜드 컬러·자유·기존 유지 | 기존 asset 분석 가능하면 자동 |
| 6 | 배경 | 투명 / 단색 / 그라데이션 / 장면 | 교체 asset 이면 원본 스펙 상속 |
| 7 | 금지 요소 | 텍스트·로고·워터마크·특정 스타일 | 기본값: 텍스트·로고·워터마크 금지 |
| 8 | 참조 이미지 | 로컬 파일 경로 있음? | 선택 사항 |

### QnA 포맷 (그대로 사용)

부족한 차원 **2~3개 이내** 만. 질문 폭탄 금지. 각 질문에 **A/B/C 선택지 + 추천안** 제시:

```
이미지 생성 전에 <N>가지 확인드릴게요.

Q1. <질문 문장>
  A) <옵션 1>
  B) <옵션 2>
  C) <옵션 3>
  D) 자유 입력 또는 "알아서"
  → 추천: <추천안> (<짧은 이유>)

Q2. <질문 문장>
  A) ...
  B) ...
  → 추천: ...

답변 주시면 합의된 내용으로 Codex 에 넘깁니다.
"그대로", "ㄱㄱ", "추천대로" 하시면 바로 진행합니다.
```

### Skip 조건 (Clarify 건너뛰고 바로 Phase 2)

다음 중 하나라도 충족하면 Clarify 없이 진행:

- 사용자 첫 요청에 **4개 차원 이상** 명시 (예: "1024×1024 투명 PNG, 플랫 스타일 주황 토끼, 텍스트 없음")
- 기존 asset 교체 요청이고 원본 스펙(크기·배경 타입·팔레트)이 파일 분석으로 확정됨
- 사용자가 명시적으로 "알아서 해" / "기본값" / "그냥 만들어" / "추천대로"
- 직전 대화에서 이미 clarify 된 내용을 재활용

**중요**: 메인 세션의 Claude 가 스스로 모든 차원을 "알아서" 채워넣고 Codex 에 넘기는 것을 경계할 것. 그건 이전 서브에이전트 구현이 실패한 패턴이다 — 사용자가 Clarify 를 받아보길 원했는데 brief 가 너무 상세히 작성돼 skip 당함. 애매하면 **묻는 쪽으로 편향**.

### Brief Compilation

QnA 답변이 오면 구조화된 brief 로 정리:

```
[합의된 Brief]
- 용도: <답변>
- 크기/비율: <답변>
- 스타일: <사용자 정서 키워드 + 답변>   # "과하지 않은", "자연스럽게" 등 원문 그대로 유지
- 주제·피사체: <답변>
- 팔레트: <답변>
- 배경: <답변>
- 금지: <답변>
- 참조 이미지: <경로 또는 없음>
```

사용자의 정서 키워드는 **원문 그대로 보존**. 팩트성 사양만 Context 대괄호로 정리. 창의적 해석은 Codex 몫.

---

## Phase 2 — Pre-flight (단일 Bash)

OS · Codex CLI · 출력 디렉토리 확인. `OPENAI_API_KEY` 는 정보성 로그일 뿐 분기 근거로 삼지 않음.

```bash
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*) os=windows; sandbox_flag=--dangerously-bypass-approvals-and-sandbox ;;
  Darwin) os=macos; sandbox_flag=--full-auto ;;
  Linux) os=linux; sandbox_flag=--full-auto ;;
  *) os=unknown; sandbox_flag=--dangerously-bypass-approvals-and-sandbox ;;
esac
command -v codex >/dev/null 2>&1 && codex_ok=1 || codex_ok=0
[ -n "$OPENAI_API_KEY" ] && key_info=present || key_info=absent
project_root=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
out_dir="$project_root/codex-image"
mkdir -p "$out_dir"
printf 'OS=%s\nSANDBOX_FLAG=%s\nCODEX_OK=%s\nKEY_INFO=%s\nOUT_DIR=%s\n' \
  "$os" "$sandbox_flag" "$codex_ok" "$key_info" "$out_dir"
```

**분기:**
- `CODEX_OK=0` → 즉시 중단, `npm install -g @openai/codex` 안내
- `CODEX_OK=1` → Phase 3 Primary 실행 (key_info 값 무시)

---

## Phase 3 — Primary 실행 (built-in tool 강제)

**반드시 `run_in_background: true` + Monitor 조합 사용.** Codex 이미지 생성은 수 초~수 분 걸리고, foreground 로 돌리면 세션이 블로킹되거나 timeout 걸림.

### 실행 템플릿

**반드시 stdin heredoc 로 prompt 전달.** `codex exec [flags] "prompt"` 포지셔널 인자 방식은 뒤에 `-i` 가 붙으면 multi-value 옵션이 prompt 를 흡수해버린다 (실증: 2026-04-23). stdin heredoc(`<<'EOF'`, quoted) 로 넘기면 `$imagegen` 변수 확장도 안 되고 참조 이미지도 깔끔하게 결합됨.

#### 참조 이미지 없을 때

```bash
ts=$(date +%Y%m%d_%H%M%S)
cd "$out_dir" && cat <<'EOF' | codex exec \
  --dangerously-bypass-approvals-and-sandbox \
  --skip-git-repo-check \
  > /tmp/imagegen_${ts}.log 2>&1
$imagegen [STRICT INSTRUCTION: You MUST use the built-in image_gen tool. You MUST NOT use scripts/image_gen.py even if OPENAI_API_KEY is missing. If the built-in tool is unavailable, fail explicitly and do not fall back.]

<Phase 1 합의된 Brief — 정서 키워드 보존>

[Copy the final generated PNG into the current working directory as imagegen_<TS-리터럴>.png.]
EOF
```

**주의**: `<<'EOF'`(quoted heredoc) 은 `$imagegen`·`${ts}` 등 변수 확장을 하지 않는다. 따라서 파일명 리터럴(예: `imagegen_20260423_175514.png`) 은 Bash 에서 TS 를 먼저 계산해 **heredoc 본문에 직접 박아 넣어야** 한다 — TS 변수를 한 Bash 호출로 `echo` 받은 뒤 다음 호출에 리터럴로 삽입하는 2단계 패턴이 안전.

#### 참조 이미지가 있을 때 (`-i <FILE>...`)

`-i` 는 multi-value 옵션이므로 **prompt 는 반드시 stdin 으로** 넘길 것.

```bash
ts=$(date +%Y%m%d_%H%M%S)
cd "$out_dir" && cat <<'EOF' | codex exec \
  --dangerously-bypass-approvals-and-sandbox \
  --skip-git-repo-check \
  -i "<참조 1 절대 경로>" \
  -i "<참조 2 절대 경로>" \
  > /tmp/imagegen_${ts}.log 2>&1
$imagegen [STRICT INSTRUCTION: Use built-in image_gen tool only; do not fall back to scripts/image_gen.py.]

<Phase 1 Brief>

[Copy final PNG to cwd as imagegen_<TS-리터럴>.png.]
EOF
```

❌ 이 형태는 **작동하지 않음** — `-i <path>` 가 뒤의 `"prompt"` 를 두 번째 `<FILE>` 값으로 흡수해 `No prompt provided via stdin` 에러:

```bash
codex exec --skip-git-repo-check -i "<file>" "$imagegen ..."   # 깨짐
```

Bash 툴에 `run_in_background: true` 로 전달.

### 폴링 전략 (Monitor 툴 사용)

Bash 로그를 `tail -F` + `grep --line-buffered` 로 감시. Primary 호출 바로 다음에 같은 턴에서 Monitor 를 걸어둘 것.

**주의 — grep 패턴 오탐 방지.** `tail -F` 는 열자마자 파일 마지막 10줄 정도를 덤프하는데, 이때 **우리가 보낸 prompt 본문(STRICT INSTRUCTION, 출력 파일명 리터럴 등) 이 grep 에 걸려 false-positive** 로 "성공했다" 오판할 수 있다 (실증: 2026-04-23). 패턴에는 **Codex 출력 고유 문자열만** 넣고 prompt 본문과 겹치는 키워드(`imagegen_.*\.png`, `image saved`, `PNG copied`) 는 피하거나, `tail -n 0 -F` 로 초기 덤프를 건너뛸 것.

```
Monitor 호출 (권장 패턴):
  command: tail -n 0 -F /tmp/imagegen_<ts>.log 2>&1 | grep -E --line-buffered "^ERROR|Reconnecting\.\.\. [2-5]/5|Exception|Traceback|Failed|fatal|usage limit|rate.?limit|quota|saved to .+\.png|wrote .+\.png|session id"
  description: "imagegen — 완료/에러 감지"
  timeout_ms: 300000 (5분, 대용량 작업은 600000)
  persistent: false
```

성공 확정은 Monitor 시그널만 믿지 말고 **파일 존재 확인**으로 검증:

```bash
ls "<out_dir>/imagegen_<ts>.png"  # 실제 파일 있는지
```

없으면 `~/.codex/generated_images/<session-id>/ig_*.png` → cwd 수동 복사.

### 실패 감지 패턴

Codex stdout/stderr 에 다음이 나오면 각각 대응:

| 감지 패턴 | 의미 | 다음 단계 |
|----------|------|----------|
| `ERROR: Reconnecting... 5/5` | **ChatGPT Codex 한도 소진 또는 서버 장애 확정** (실증됨) | Phase 3 실패 → 한도 확인 안내 |
| `ERROR: Reconnecting... [2-4]/5` 후 60초+ 추가 로그 없음 | **한도 소진 hang** — 5/5 까지 안 가도 실질 실패 (실증: 2026-04-23, 4/5 에서 7분 멈춤) | Phase 3 실패 → 한도 확인 안내 + codex 프로세스 kill |
| `No prompt provided via stdin` | **`-i` 플래그가 prompt 를 흡수함** — positional 방식 호출 버그 | 실행 템플릿의 stdin heredoc 패턴으로 재시도 |
| `OPENAI_API_KEY is not set` / `required local secret` | built-in 강제 지시가 먹히지 않음 | 프롬프트에 `[STRICT ...]` 포함됐는지 확인, 그래도 실패면 Phase 4 Hand-off |
| `scripts/image_gen.py` 실행 흔적 | 동상 | 동상 |
| 생성 파일이 cwd 에 없음 + codex 종료됨 | agent 복사 단계 누락 | `cp ~/.codex/generated_images/*/ig_*.png "$out_dir/imagegen_<ts>.png"` 수동 복사 |
| `login required` | codex 인증 만료 | `codex login` 안내 |
| `windows sandbox: CreateProcessWithLogonW failed: 1385` | Windows + `--full-auto` | `sandbox_flag` 가 bypass 인지 확인 |

### Reconnecting = 한도 소진일 가능성 높음

`Reconnecting... 2/5` → `5/5` 까지 찍히고 멈추거나, **중간 단계(2~4/5) 에서 60초 이상 추가 로그 없이 hang** 되는 현상은 Codex CLI의 알려진 이슈로, 원인 대부분이 **ChatGPT Plus Codex 5시간/주간 한도 소진**이다. image_gen tool 은 일반 한도를 3~5배 빠르게 소진한다(공식 Help Center 명시). 실증 케이스(2026-04-23)에서 **4/5 에서 7분간 5/5 로 진행조차 못 한 hang** 도 확인됨 — 5/5 를 기다리지 말고 4/5 에서 60초+ 멈추면 실패 처리.

이 패턴 감지 시 **먼저 codex.exe 프로세스를 kill** 한 뒤 사용자에게 안내:

```
⚠️ Codex image_gen 호출이 Reconnecting 5/5 에서 실패했어요.
원인 후보 (가능성 순):
1. ChatGPT Codex 한도 소진 — 웹 대시보드에서 확인 가능
   → https://chatgpt.com/codex/settings/usage
2. OpenAI image_gen 엔드포인트 일시 장애 (10~30분 후 재시도)
3. Codex 로그인 세션 만료 (`codex login`)

한도면 5시간 윈도우 리셋 후 재시도하거나, 웹 서비스(ChatGPT 웹 / Gemini / Recraft 등)로 우회 가능합니다.
```

---

## Phase 4 — Hand-off to Interactive TUI (무료 fallback)

Phase 3 Primary 가 실패하고 한도 소진도 아닌 경우, 사용자에게 interactive session 용 포장 프롬프트를 출력:

```
⚠️ 자동 실행에서 built-in image tool 경로가 막혔습니다.
Interactive Codex TUI 로 직접 실행하면 ChatGPT 구독 한도 내에서 무료로 생성됩니다.

1) 새 터미널:
   cd "<out_dir>"
   codex

2) TUI 에 붙여넣고 Enter:
────────────────────────────────────────────
$imagegen <Phase 1 합의된 Brief — 정서 키워드 보존>
[Save the final PNG to the current workspace as imagegen_<timestamp>.png.]
────────────────────────────────────────────

3) 생성된 PNG 는 ~/.codex/generated_images/<session-id>/ig_*.png 에 저장되며,
   TUI agent 가 cwd 로 복사합니다.

완료 후 <out_dir>/ 내 PNG 를 확인해 주세요.
```

---

## Phase 5 — Paid CLI Fallback (🚫 자발적 제안 금지, 최후 수단)

**기본적으로 사용하지 않음.** 다음 **모두** 충족 시에만:

1. Phase 3 Primary 실패 (built-in 강제도 안 먹힘)
2. Phase 4 Hand-off 불가 (사용자가 TUI 접근 불가, ChatGPT 미구독 등)
3. 사용자가 **먼저** "API 로 해도 돼" / "유료로라도 해줘" / "--use-api" 등을 **반복적으로** 명시
4. 비용 고지 후 사용자 재확인 ("응, 유료로 진행해")

**중요 — 자발적 제안 금지:** 사용자가 먼저 꺼내지 않았다면 이 옵션을 언급조차 하지 말 것. Phase 3/4 설명 시 Paid 경로 언급 자체를 회피. Default 는 언제나 "무료 경로만" 제시.

허용 후 호출:

```bash
ts=$(date +%Y%m%d_%H%M%S)
cd "$out_dir" && codex exec \
  "$sandbox_flag" \
  --skip-git-repo-check \
  "\$imagegen <Phase 1 Brief 원문> [Save as imagegen_${ts}.png in cwd using scripts/image_gen.py]" \
  > /tmp/imagegen_${ts}.log 2>&1
```

비용 고지 (반드시 재확인 후 실행):

```
⚠️ Paid CLI fallback 경로입니다. 이미지당 실 비용이 발생합니다.
 - gpt-image-1 1024×1024 medium: $0.042/image
 - gpt-image-1 1024×1024 high  : $0.167/image
 - OPENAI_API_KEY 환경변수 필수

무료 경로(Interactive TUI Hand-off)가 아직 가능하다면 그쪽을 권장드립니다.
정말 유료로 진행하시겠습니까? (y/N)
```

---

## 🔒 Critical Rules

1. **`\$imagegen` 이스케이프 필수.** Bash 에서 `$imagegen` 은 빈 변수로 확장돼 skill 호출 실패. 반드시 `\$imagegen` 로 literal `$imagegen` 이 Codex 에 도달해야 함.

2. **built-in 강제 지시 절대 누락 금지.** 모든 `codex exec` 프롬프트에 `[STRICT INSTRUCTION: Use the built-in image_gen tool only; do not fall back to scripts/image_gen.py.]` 포함. 이게 없으면 agent 가 구버전 SKILL.md 따라 CLI fallback(유료)으로 감.

3. **자동 유료 경로 금지.** `OPENAI_API_KEY` 가 환경에 있어도 자동 CLI fallback 금지. Phase 3 실패 시 Phase 4 Hand-off 로 이동. Phase 5(Paid)는 사용자가 명시적·반복적 요구 시에만 비용 고지 후 진입.

4. **Paid 경로 자발적 제안 금지.** Phase 3/4 설명 시 Paid 옵션 언급 자체 회피. 사용자가 먼저 꺼내야 테이블에 올라옴.

5. **Clarify 건너뛰기 편향 주의.** 사용자 첫 발화가 모호하면 (차원 4개 미만 명시) **반드시 Phase 1 QnA**. 메인 Claude 가 brief 를 "알아서" 채워 skip 조건을 가짜로 충족시키지 말 것. 애매하면 묻는 쪽.

6. **Brief 의도·뉘앙스 보존.** 사용자의 정서 키워드("과하지 않은", "자연스럽게", "귀엽게", "프리미엄")는 **원문 그대로** Codex 프롬프트에 포함. 팩트성 사양(크기·RGBA·팔레트)만 Context 대괄호로 정리. 프롬프트 "개선" 금지 — 그건 Codex 책임.

7. **출력 경로 강제.** 항상 `<project_root>/codex-image/imagegen_<timestamp>.png`. 사용자가 다른 경로 명시했다면 그 경로로 `cd` 후 호출.

8. **Windows 샌드박스 금지.** Windows 에서는 `--full-auto`(= workspace-write) 가 `CreateProcessWithLogonW failed: 1385` 로 무조건 실패. 반드시 `--dangerously-bypass-approvals-and-sandbox`.

9. **API 키 요구 금지.** Built-in tool 경로는 키 불필요. Phase 5 가 정말 필요할 때만 키 설정법 안내.

10. **폴링 방식 — 반드시 Monitor.** `sleep 30` 류 long leading sleep 은 Claude 런타임에서 차단됨. 폴링은 `run_in_background: true` + `Monitor` 툴 또는 `until <check>; do sleep 2; done` 패턴.

11. **세션 재사용 금지.** 매번 fresh `codex exec`. `--resume-last` 금지.

---

## 출력 템플릿

**성공 (Phase 3 Primary):**
```
✅ 이미지 생성 완료 (Codex built-in image_gen tool)
- <절대 경로>

출력 위치 : <project_root>/codex-image/
비용      : 무료 (ChatGPT 구독 한도 내)
실행 경로 : codex exec + built-in image_gen tool
소요 시간 : <초>
```

**Hand-off (Phase 4):** 위 Phase 4 블록 그대로 출력 후 종료.

**Paid 성공 (Phase 5, 사용자 동의 후):**
```
✅ 이미지 생성 완료 (OpenAI Image API 유료 호출)
- <절대 경로>
비용      : gpt-image-1 1024×1024 <quality> ~$<amount>
실행 경로 : codex exec + scripts/image_gen.py (CLI fallback)
```

**한도 소진 추정 실패:** 위 "Reconnecting 5/5 = 한도 소진일 가능성 높음" 블록 그대로 출력.

**일반 실패:**
```
❌ Codex 실행 실패 (exit <code>)
원인: <매트릭스 항목명>
<stdout/stderr 핵심부 5줄 이내>
권장 조치: <1줄>
```

---

## 부가 사항

- **응답 언어**: 사용자에게 돌려주는 메시지는 한국어. Codex 프롬프트는 사용자 원문 언어 그대로.
- **토큰 절약**: Phase 2 Bash 1회 + Codex 호출 1회 + Monitor + 경로 보고. 중간 추론 출력 최소화.
- **비용 정책 요약**: Primary(built-in) = 무료 / Hand-off(TUI) = 무료 / Paid(CLI) = 사용자 명시 동의 후 유료. **기본값은 절대 유료 아님**.
- **세션 복구**: 한도 소진은 5시간 윈도우 기준으로 리셋됨. 주간 한도 병존. `/status` 슬래시 커맨드(Codex TUI 내) 또는 `https://chatgpt.com/codex/settings/usage` 에서 확인.
