# claude_jira_harness

Jira 워크플로우 + Harness Engineering Claude Code 스킬 셋.

Jira 이슈 한 줄짜리 요구사항을 받아서 → 등록 → 시작 → 구체화 → 계획 → 구현 → 테스트 → 커밋 → 완료까지의 전 사이클을 슬래시 명령으로 묶고, 그 위에 다중 에이전트 리뷰(Harness)와 사후 채점/Shadow 비교까지 얹은 사용자 스코프 스킬 모음. 부가적으로 raster 이미지 생성(`imagegen`) 과 CLAUDE.md 자동 정리(`/organize-claude-md`) 도 포함.

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

### `--subtasks` 모드 (공통 컨벤션)

부모 Jira 이슈 1개 + 하위 작업 N개를 한 묶음의 fan-out 단위로 처리하는 모드. 모든 `jira-*` / `harness-workflow` 스킬이 공유하는 단일 컨벤션 문서로 동작 — [`skills/_subtasks-convention.md`](skills/_subtasks-convention.md) 가 single source of truth.

- 진입: `/jira-start PROJ-7 --subtasks` 또는 `/harness-workflow PROJ-7 --subtasks`
- 원칙: 산출물(dev-guide, sprint-contract, verdict, commit) 은 **부모에 귀속**, 하위는 **트래킹 미러** (PM/QA 가시성 위한 상태 동기화 + 1~3줄 댓글)
- `harness-workflow --subtasks` 가 자식 스킬 전부에 flag 자동 전파
- 부모 이슈에 `subtasks` 가 없으면 일반 모드로 자동 폴백
- 사후 보정 절차도 문서 §8 에 포함 (구버전으로 작업해서 하위가 To Do 로 남은 케이스)

### 부가 스킬·명령어

| 항목 | 종류 | 역할 |
| ---- | ---- | ---- |
| `imagegen` | skill | OpenAI Codex CLI 의 built-in `image_gen` 을 메인 Claude 세션이 직접 오케스트레이션하는 thin orchestrator. 2~3개 질문으로 brief 합의 후 `codex exec` 백그라운드 호출 + Monitor 폴링. 결과는 호출 프로젝트의 `codex-image/` 폴더에 저장. **raster 전용** — SVG/벡터·코드 생성에는 사용 금지. |
| `/organize-claude-md` | command | CLAUDE.md를 **Lazy Loading 참조 구조 + 프레임워크 특화 템플릿 + Mermaid 아키텍처**로 재구성. `(빈 값)` git diff 기반 증분 / `full` 전체 재구성 / `main` / `references` / `module:<name>` / `scan` / `diff` / `gap` / `<경로>` 인자 지원. |

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

또는 심볼릭 링크로:

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
- `imagegen` 사용 시: OpenAI Codex CLI 설치 + ChatGPT Plus 로그인 (built-in `image_gen` 무료 한도 사용). 유료 fallback 은 `OPENAI_API_KEY` 명시 요청 시에만.

## 권장 사용 흐름

```
/jira-create                       (요구사항/문서 → 이슈 등록)
  → /jira-start PROJ-123
    → /jira-clarify PROJ-123       (요구사항 흐릿하면)
      → /jira-plan PROJ-123
        → /jira-execute PROJ-123
          → /jira-test PROJ-123
            → /jira-commit PROJ-123
              → /jira-complete PROJ-123
```

전 과정을 한 번에 가고 싶으면:

```
/harness-workflow PROJ-123
```

부모 + 하위 이슈를 한 번에 가려면:

```
/harness-workflow PROJ-7 --subtasks
```

## 라이선스

MIT — `LICENSE` 참조.

## 비고

원본은 사내 사용 목적으로 작성됐고, 공개 배포를 위해 모든 사내 식별자(프로젝트 키, 마이크로서비스 명, 도메인 클래스/필드, 커스텀 어노테이션)를 중립적인 e-commerce 예시로 치환했다. 본인 환경에 맞게 `PROJ-`, `order-service`, `catalog-service`, `order-admin` 등의 placeholder를 자유롭게 바꿔 사용하면 된다.
