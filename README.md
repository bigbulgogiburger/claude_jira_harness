# claude_jira_harness

> Made by **dhpyun** ([@bigbulgogiburger](https://github.com/bigbulgogiburger)) — Jira × Harness × LLM Wiki 스킬 셋의 설계·구현·운영 SSoT 모두 본인이 작성.

Jira 워크플로우 + Harness Engineering + LLM Wiki Claude Code 스킬 셋.

Jira 이슈 한 줄짜리 요구사항을 받아서 → 등록 → 시작 → 구체화 → 계획 → 구현 → 테스트 → 커밋 → 완료까지의 전 사이클을 슬래시 명령으로 묶고, 그 위에 다중 에이전트 리뷰(Harness)와 사후 채점/Shadow 비교, 그리고 산출물을 **영구 지식 자산(LLM Wiki)** 으로 누적하는 사용자 스코프 스킬 모음. 부가적으로 코드베이스 AI 준비도 감사, knowledge graph 추출, Spring Boot 리팩토링, raster 이미지 생성, CLAUDE.md 자동 정리까지 포함.

## 구성

### Jira 워크플로우 (8개)

| 스킬 | 역할 | 호출 시점 |
| ---- | ---- | --------- |
| `/jira-create` | 자연어 한 줄 또는 문서(주차 계획/RFC 등) 기반으로 단일 이슈 또는 에픽→이슈→하위이슈 계층 일괄 등록 | 워크플로우 시작점 |
| `/jira-start <KEY>` | 이슈 조회 + feature 브랜치 생성 + In Progress 전환 | 작업 시작 |
| `/jira-clarify <KEY>` | Q&A로 요구사항 구체화, 멀티 프로젝트면 하위 이슈 자동 생성 | start 직후 |
| `/jira-plan <KEY>` | dev-guide MD 생성 (스택 페르소나 적용) | clarify 직후 |
| `/jira-execute <KEY>` | dev-guide 기반 실제 구현 (병렬 가능) | plan 직후 |
| `/jira-test <KEY>` | 스택별 unit/lint/build/all 테스트 자동 실행 | execute 직후 |
| `/jira-commit <KEY>` | DoD 체크 + 커밋 + Jira 한글 댓글 업데이트 | test 통과 후 |
| `/jira-complete <KEY>` | 최종 검증 + QA 상태 전환 | commit 직후 |

### Harness Engineering (8개)

| 스킬 | 역할 |
| ---- | ---- |
| `/harness-setup` | 프로젝트 스택 감지 후 에이전트/훅/메트릭 인프라 자동 프로비저닝 (멱등) |
| `/harness-workflow <KEY>` | Jira 스킬 + Sprint Contract + 리뷰 Inner Loop 통합 오케스트레이터 |
| `/harness-plan <KEY>` | dev-guide 기반 Sprint Contract(DoD/Verify Targets/Out of Scope) 생성 |
| `/harness-review` | 코드 변경에 프로젝트별 전문 에이전트 fan-out 후 aggregate verdict |
| `/harness-gate` | 커밋 전 최종 품질 게이트 (aggregate-verdict + 빌드/타입체크/린트) |
| `/harness-shadow <KEY>` | `HARNESS_MODE=off` baseline vs full-run 비교로 counterfactual lift 측정 |
| `/harness-score <KEY>` | post-merge VALID/INVALID 채점 (catch rate / FP rate 측정) |
| `/harness-resume` | 체크포인트 복원으로 중단된 단계부터 재개 |

### LLM Wiki — 영구 지식 자산화 (3개 + 1 SSoT)

Karpathy LLM Wiki 패턴 기반. dev-guide, ADR, 외부 문서 등 모든 산출물을 build-time 합성해 **한 번 흡수하면 영구 자산**이 되는 지식 베이스를 구축한다. `/jira-plan`·`/jira-complete` 가 자동으로 ingest/lint를 chain 호출하므로 별도 호출 없이도 wiki가 누적된다.

| 스킬 | 역할 | 호출 시점 |
| ---- | ---- | --------- |
| `/jira-ingest` | dev-guide 생성/완료마다 `docs/INDEX.md` + `docs/LOG.md` + ADR/sprint cross-reference 증분 갱신 (Jira 도메인 전용) | `/jira-plan`·`/jira-complete` 자동 chain, 또는 명시 호출 |
| `/llm-wiki` | 임의 raw input(웹 글, PDF, 팟캐스트, 책, 이미지/OCR, 음성, 영상, 코드 리포) → wiki 합성. Jira 외 모든 정보 소스 담당 | "이 글 정리해줘", "위키에 추가" 등 자연어 트리거 |
| `/wiki-lint` | 14가지 정합성 체크 (orphan / stale / broken xref / parent-sibling 비대칭 / Jira 상태 불일치 / memory drift / INDEX integrity) → 자동수정 가능/수동 검토 분리 보고 | `/jira-complete` 자동 chain (high severity, non-blocking) 또는 명시 호출 |
| [`_wiki-schema.md`](skills/_wiki-schema.md) | jira-ingest ↔ wiki-lint 가 공유하는 single source of truth | — |

### 코드베이스 분석·리팩토링 (3개)

| 스킬 | 역할 |
| ---- | ---- |
| `/codebase-ai-readiness` | 임의 git 레포를 7-카테고리 100점 루브릭으로 감사 → JSON 점수표 + 한국어 HTML 대시보드 + ROI 우선순위 액션 리스트 산출. Factory.ai Agent Readiness pillars + AGENTS.md 명세 + Anthropic best practice 종합 기반. 프레임워크 무관. |
| `/graphify` | 임의 input(코드, docs, 논문, 이미지) → knowledge graph → community detection → HTML + JSON + audit report. god node / BFS·DFS 쿼리 도구 포함. post-commit hook 으로 graph 증분 갱신 가능. |
| `/spring-boot-refactor` | Spring Boot 프로젝트의 DDD 패턴 강화, CQRS 적용, Service 계층 분리(Read/Write), 테스트 커버리지 개선, N+1 해결 자동 분석·제안. |

### `--subtasks` 모드 (공통 컨벤션)

부모 Jira 이슈 1개 + 하위 작업 N개를 한 묶음의 fan-out 단위로 처리하는 모드. 모든 `jira-*` / `harness-workflow` 스킬이 공유하는 단일 컨벤션 문서로 동작 — [`skills/_subtasks-convention.md`](skills/_subtasks-convention.md) 가 single source of truth.

- 진입: `/jira-start PROJ-7 --subtasks` 또는 `/harness-workflow PROJ-7 --subtasks`
- 원칙: 산출물(dev-guide, sprint-contract, verdict, commit) 은 **부모에 귀속**, 하위는 **트래킹 미러** (PM/QA 가시성 위한 상태 동기화 + 1~3줄 댓글)
- `harness-workflow --subtasks` 가 자식 스킬 전부에 flag 자동 전파
- 부모 이슈에 `subtasks` 가 없으면 일반 모드로 자동 폴백
- 사후 보정 절차도 문서 §8 에 포함 (구버전으로 작업해서 하위가 To Do 로 남은 케이스)

### Parallel Fan-out — 다중 부모 이슈 동시 실행 (2-tier)

`/harness-workflow <KEY1> <KEY2> …` 형식으로 **여러 부모 이슈를 동시에** 진행할 때의 격리·직렬화·머지·복구 규칙. SKILL.md 의 단일 인스턴스 가정을 넘어서는 운영 모드. SSoT 는 [`skills/harness-workflow/parallel-fanout.md`](skills/harness-workflow/parallel-fanout.md) — 단일 인스턴스만 돌리면 본 문서 불필요.

**2-Tier 구조**:
- **Tier-1 (Outer)**: 메인 세션이 orchestrator. 각 부모 이슈마다 **git worktree 격리** + `Agent("workflow-PROJ-XXX")` 로 `/harness-workflow KEY --subtasks` 동시 fan-out
- **Tier-2 (Inner)**: 각 worktree 안에서 ADR-070 패턴 — `TeamCreate` + 하위태스크 슬라이스별 teammate (평균 3~4 슬라이스)
- 총 동시 에이전트 ≈ 부모 N × (1 워크플로 + ~3.2 teammate) — 5 부모 시 ~21 인스턴스

**진입 게이트 (10 조건 全 충족 시에만)**:
1. 부모 이슈 ≥ 2개 동시 진행 의도
2. 부모 이슈 간 **코드 영역 충돌 매트릭스** 사전 분석 (PRIMARY 패키지 + import dependency)
3. `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` 활성
4. `HARNESS_MODE=auto` 또는 `suggest`
5. **Flyway V 번호 사전 할당표** (worktree 마다 DDL 충돌 방지)
6. 공유 파일 (예: `application.yml`, `package.json`) lock/직렬화 전략 합의
7. token cost 1.5–2× 인지·승인 (단일×N 대비)
8. working tree clean + 모든 부모 이슈가 같은 main 베이스에서 분기 가능
9. (권장) Codex 설치 + sandbox 1385 우회 정착

**핵심 직렬화 포인트**:
- **머지 순서**: REF (import) 등급이 있는 경우, 의존 대상이 먼저 main 머지되어야 의존 측 통합 빌드 통과
- **사용자 승인 게이트**: 5 인스턴스가 동시에 "이대로 진행할까요?" 묻지 않도록 orchestrator 가 메인에 직렬화 큐
- **Hook 동시 발화**: post-commit / Flyway scan 등 글로벌 hook 의 race 방어
- **PR / git merge 직렬화**: PR 동시 머지 = merge conflict 폭발 → orchestrator 가 큐로 처리

**명시 금지**:
- worktree 미사용 동시 실행 (= 동일 working tree 5 instance 침범)
- Flyway V 번호 자동 할당 위임 (= 동일 V 번호 중복 발급)
- 충돌 매트릭스 미작성 진입
- 충돌 등급 REF 인 부모 동시 머지

처음 시도라면 **3 인스턴스부터 시작** → OOM / rate-limit / hook race 관찰 후 5로 증분 권장. 실패 시 단일 인스턴스 순차 모드로 폴백.

### 부가 스킬·명령어 (2개)

| 항목 | 종류 | 역할 |
| ---- | ---- | ---- |
| `imagegen` | skill | OpenAI Codex CLI 의 built-in `image_gen` 을 메인 Claude 세션이 직접 오케스트레이션하는 thin orchestrator. 2~3개 질문으로 brief 합의 후 `codex exec` 백그라운드 호출 + Monitor 폴링. 결과는 호출 프로젝트의 `codex-image/` 폴더에 저장. **raster 전용** — SVG/벡터·코드 생성에는 사용 금지. |
| `/organize-claude-md` | skill + command | CLAUDE.md를 **Lazy Loading 참조 구조 + 프레임워크 특화 템플릿 + Mermaid 아키텍처**로 재구성. Monorepo 분기 + CHANGELOG 분리 + ADR 자동 생성 안내. `(빈 값)` git diff 기반 증분 / `full` 전체 재구성 / `main` / `references` / `module:<name>` / `scan` / `diff` / `gap` / `<경로>` 인자 지원. Spring Boot / Vue / Nuxt / React / Next.js / Flutter / NestJS / FastAPI / Django / Go 특화 스캔. |

## 설치

스킬은 `~/.claude/skills/<skill-name>/`, 슬래시 명령어는 `~/.claude/commands/<name>.md` 하위에 위치해야 Claude Code가 인식한다.

```bash
git clone https://github.com/bigbulgogiburger/claude_jira_harness.git
cd claude_jira_harness

# 스킬
mkdir -p ~/.claude/skills
cp -R skills/* ~/.claude/skills/

# 슬래시 명령어
mkdir -p ~/.claude/commands
cp -R commands/* ~/.claude/commands/
```

또는 심볼릭 링크로 (이후 `git pull` 만으로 즉시 반영):

```bash
for d in skills/*/; do
  ln -s "$(pwd)/$d" "$HOME/.claude/skills/$(basename "$d")"
done
for f in commands/*.md; do
  ln -s "$(pwd)/$f" "$HOME/.claude/commands/$(basename "$f")"
done
```

## 요구사항

- Claude Code (CLI 또는 데스크톱 앱)
- Jira 사용 시: MCP Atlassian 서버가 활성화되어 있어야 함 (`mcp__atlassian__*` 도구 사용)
- Harness 채점/리뷰는 프로젝트 루트에 `.claude/runtime/` 쓰기 권한 필요
- LLM Wiki (`/jira-ingest`, `/llm-wiki`, `/wiki-lint`) 사용 시: 프로젝트 루트에 `docs/` 디렉토리 쓰기 권한
- `imagegen` 사용 시: OpenAI Codex CLI 설치 + ChatGPT Plus 로그인 (built-in `image_gen` 무료 한도 사용). 유료 fallback 은 `OPENAI_API_KEY` 명시 요청 시에만.
- `/codebase-ai-readiness` 사용 시: 감사 대상 레포 루트에 `.ai-readiness/` 쓰기 권한
- `/graphify` 사용 시: Python 환경 (`graphify-out/` 산출물 생성)

## 권장 사용 흐름

기본 Jira 사이클:

```
/jira-create                       (요구사항/문서 → 이슈 등록)
  → /jira-start PROJ-123
    → /jira-clarify PROJ-123       (요구사항 흐릿하면)
      → /jira-plan PROJ-123        ─┐  자동 chain
                                    ├─ /jira-ingest (docs/INDEX.md 갱신)
        → /jira-execute PROJ-123
          → /jira-test PROJ-123
            → /jira-commit PROJ-123
              → /jira-complete PROJ-123 ─┐  자동 chain
                                         ├─ /jira-ingest (최종 상태 반영)
                                         └─ /wiki-lint (high severity health check)
```

전 과정을 한 번에 가고 싶으면:

```
/harness-workflow PROJ-123
```

부모 + 하위 이슈를 한 번에 가려면:

```
/harness-workflow PROJ-7 --subtasks
```

여러 부모 이슈를 worktree 격리로 **동시에** 가려면 (진입 게이트 10조건 충족 필수):

```
/harness-workflow PROJ-214 PROJ-215 PROJ-216 --subtasks
  # → orchestrator 가 3개 git worktree 격리 + Agent fan-out
  # → 충돌 매트릭스 + Flyway V 번호 할당표 사전 확정 필수
  # → 자세한 안전 가이드: skills/harness-workflow/parallel-fanout.md
```

새 프로젝트 합류 시 진단부터:

```
/codebase-ai-readiness      → 100점 루브릭 감사 + ROI 액션 리스트
/organize-claude-md         → CLAUDE.md 재구성 (또는 부재 시 신규 생성)
/harness-setup              → 에이전트/훅/메트릭 인프라 프로비저닝
```

Jira 외부 정보 자산화:

```
/llm-wiki <URL 또는 파일 경로>   → docs/wiki/ 에 영구 노트 추가
/wiki-lint                       → 정기 health check
```

## 라이선스

MIT — `LICENSE` 참조.

## Author

**dhpyun** — [@bigbulgogiburger](https://github.com/bigbulgogiburger)

본 스킬 셋의 설계·구현·SSoT 문서·운영 패턴 (jira-*, harness-*, llm-wiki / wiki-lint, parallel-fanout, organize-claude-md, _subtasks-convention) 일체가 본인 작품이다. 실제 사내 Spring Boot 3.3.8 / Vue 3 / Java 21 풀스택 프로젝트 운영 중 W1~W7 sprint 사이클에서 검증·정착됐다.

## 비고

원본은 사내 사용 목적으로 작성됐고, 공개 배포를 위해 모든 사내 식별자(프로젝트 키, 마이크로서비스 명, 도메인 클래스/필드, 커스텀 어노테이션)를 중립적인 e-commerce 예시로 치환했다. 본인 환경에 맞게 `PROJ-`, `order-service`, `catalog-service`, `order-admin` 등의 placeholder를 자유롭게 바꿔 사용하면 된다.
