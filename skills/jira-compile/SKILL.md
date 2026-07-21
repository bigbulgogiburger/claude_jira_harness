---
name: jira-compile
description: "jira-compile — dev-guide + sprint-contract 를 러너 실행 가능한 step 시퀀스로 컴파일합니다 (phases/<KEY>/index.json + step*.md). harness-workflow ⑤ compile 단계 — 대형 이슈·무인(unattended) 실행 opt-in 시에만. '/jira-compile', 'step 컴파일', '러너 준비', 'phases 생성' 요청 시 사용. /harness-plan 이후, harness-execute.py 러너 실행 이전."
---

# /jira-compile — dev-guide → step 컴파일 (harness v2 §4.1)

> 산출물은 `harness-execute.py` 러너(§4.2)가 소비한다. **러너는 모델 자기보고를 믿지 않는다** — 이 컴파일이 만드는 `ac`/`probe` 가 completed 판정의 전부이므로, 실행 가능하고 결정론적으로 작성하는 것이 이 스킬의 존재 이유다.
> **opt-in**: 소형 이슈는 attended(현행 레인)가 정량적으로 유리 (§10.2-b) — 대형 이슈·야간 무인만 컴파일.

## 입력

- `docs/<KEY>-dev-guide.md` (필수 — 없으면 /jira-plan 먼저)
- `.claude/runtime/sprint-contract/<KEY>.md` (필수 — DoD·인간게이트 목록)
- `docs/INDEX.md` 의 해당 이슈 행 cross-ref (ADR-\d+·STD-\d+ 패턴, INDEX-SCHEMA `cross_refs`)

## 출력

```
phases/<KEY>/
├── index.json          # 상태머신 SSoT (러너 재개점 — 첫 pending 부터)
├── step0-<slug>.md     # 자기완결 step 지시서
└── ...
```

## 절차

1. **dev-guide Phase → step 분해**: Phase 1개 = step 1~N개. 각 step 은 **fresh 세션이 이것만 읽고 완결 가능**해야 한다 — 목표·수정 파일·구현 상세·검증 방법을 step*.md 에 자기완결로 기술 (dev-guide "참조" 금지, 내용을 복사).
2. **context_refs 산출 (선별 가드레일 — 전량 주입 금지)**: INDEX.md 에서 이슈 행의 cross-ref 추출 → 관련 ADR 은 `docs/08-decision-log.md#ADR-NNN` (W1 정규화 헤더 앵커), sibling dev-guide 는 관련 섹션만. step 당 주입 상한 ≈ 60~90KB.
3. **ac 작성 (실행 커맨드만)**: Git Bash 문법, exit 0 = 통과. 예: `cd backend && JAVA_HOME=<JDK 경로> ./gradlew compileJava -q`. 서술형 금지.
4. **probe 작성 (anti-gaming)**: loop.yaml probe 문법 미러 — `{kind: db|http|grep|shell, cmd: <bash 커맨드>, expect: <정규식>}`. 정적 컴파일 GREEN 만으로 completed 가 되지 않도록 실환경 신호(DB 컬럼 실재·200+실데이터·grep 코드신호) 최소 1개.
5. **touched_files 선언**: step 이 수정할 파일 glob 목록 — 러너가 범위 밖 변경을 error 처리한다. 좁게 선언.
6. **model 티어링** (§7.2): step 난이도 판정 → `"model"` 필드. 원장/동시성/상태머신급=사유 명시 후 fable 상한 1개, BE 복잡 도메인=opus, FE·기계적=sonnet.
7. **인간 게이트 → blocked 선언**: sprint-contract 의 인간 게이트(Flyway QA·W13 외부 API·prod)가 걸리는 step 은 컴파일 시점에 `"status": "blocked"` + `error_message` 에 사유 — 러너가 실행하지 않게.
8. **index.json 조립**: `forbid` 는 프로젝트 safety 설정(있으면 — 예: `.loop/loop.yaml` forbid 목록, 없으면 러너 DEFAULT_FORBID)을 복사. `always_context: ["phases/_always.md"]`. `branch` = 현재 feature 브랜치.

## index.json 스키마

`scripts/harness-execute.py` 모듈 docstring 이 SSoT — 필드: issue/branch/contract/always_context/forbid/steps[{step,name,status,model,max_turns,timeout,prompt_file,ac,probe,context_refs,touched_files,summary,error_message,cost_usd,attempts}].

## 검증 (컴파일 직후 필수)

1. `python scripts/harness-execute.py phases/<KEY> --dry-run --step 0` — 프롬프트 조립 확인 (앵커 미발견/파일 없음 경고 0).
2. 각 step 의 `ac`/`probe` 커맨드를 1회씩 직접 실행해 **현재(변경 전) 상태에서 실패**함을 확인 — 변경 전부터 통과하는 AC 는 게이트가 아니다 (단 컴파일/빌드형 AC 는 예외).
3. 사용자에게 step 목록 + 모델 배정 + blocked 선언 요약 제시.
