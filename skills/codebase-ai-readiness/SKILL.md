---
name: codebase-ai-readiness
description: |
  임의의 git 레포지토리가 AI 코딩 에이전트(Claude Code, Cursor, Copilot, Aider 등)와
  얼마나 잘 협업할 수 있는지 100점 7-카테고리 루브릭으로 감사하고 JSON 점수표,
  한국어 HTML 대시보드, ROI 우선순위 액션 리스트를 산출합니다. 프레임워크 무관 —
  Python, JS/TS, Java, Go, Rust, Ruby 등 어떤 언어든 동작.

  Use this skill PROACTIVELY whenever the user asks about:
  - "AI-ready", "AI 준비도", "에이전트 준비도", "agent readiness", "codebase audit"
  - "이 코드베이스 점수 매겨줘", "AI 협업 가능한지 평가해줘", "코드베이스 감사"
  - "AGENTS.md 있는지 확인", "CLAUDE.md 점검", "에이전트 친화적인지"
  - "이 레포가 AI랑 얼마나 잘 맞는지", "Claude Code 쓰기 좋은 구조인지"
  - "리팩토링 우선순위", "ROI 기반 개선 항목", "어디부터 손대야 하나"
  - 새 레포에 합류했을 때 / 외부 OSS 평가 / 도입 가능성 검토
  - 시니어 엔지니어가 팀 코드베이스 진단을 의뢰하는 모든 상황

  Also trigger when the user mentions any of: Factory.ai Agent Readiness,
  AGENTS.md spec, agentic coding setup, dev environment scoring, repo health check,
  codebase quality benchmark.
---

# Codebase AI-Readiness Audit

## What this skill does

이 스킬은 git 레포지토리를 7개 카테고리·100점 루브릭으로 감사해 다음 3개 산출물을 생성합니다:

1. **`<repo>/.ai-readiness/report.json`** — 모든 점수와 근거의 구조화 데이터
2. **`<repo>/.ai-readiness/dashboard.html`** — 한국어 단일파일 대시보드 (오프라인 가능)
3. **`<repo>/.ai-readiness/actions.md`** — ROI 순으로 정렬된 개선 액션 리스트

루브릭은 Factory.ai의 8 Agent Readiness pillars, AGENTS.md 명세(GitHub 2,500개 레포 분석),
Anthropic Claude Code 베스트 프랙티스를 종합한 산업 표준 기반입니다.

### 7개 카테고리 (총 100점)

| ID | 카테고리 | 배점 | 핵심 측정 |
|---|---|---:|---|
| `discoverability` | 발견 가능성 & 컨텍스트 | 15 | README, AGENTS.md/CLAUDE.md, ADR, 다이어그램 |
| `structure` | 구조 & 모듈성 | 15 | 파일/함수 크기, god-file, 디렉토리 구조 |
| `static_analysis` | 정적 분석 & 스타일 | 15 | 린터, 포매터, 타입체커, pre-commit |
| `testing` | 테스트 & 검증 | 15 | 테스트 존재/비율/단일명령/CI/커버리지 |
| `build` | 빌드 & 재현성 | 15 | 매니페스트, 락 파일, 부트스트랩, 컨테이너 |
| `security` | 보안 & 의존성 | 10 | 시크릿, .gitignore, LICENSE, 취약점 스캔 |
| `operability` | 운영성 & 관찰성 | 15 | 구조화 로깅, 에러 처리, env 설정, 헬스체크 |

## 어떻게 호출하는가

### 기본 사용 (현재 디렉토리)

```bash
python "C:/Users/DBInc/.claude/skills/codebase-ai-readiness/audit.py"
```

### 다른 레포 감사

```bash
python "C:/Users/DBInc/.claude/skills/codebase-ai-readiness/audit.py" --path D:/path/to/repo
```

### 출력 디렉토리 지정

```bash
python ".../audit.py" --path . --out ./my-report
```

### 특정 포맷만

```bash
python ".../audit.py" --format json     # JSON만
python ".../audit.py" --format html     # 대시보드만
python ".../audit.py" --format md       # 액션 마크다운만
```

## 사용 흐름

사용자가 "이 코드베이스 AI-ready 점수 좀 매겨줘" 같은 요청을 하면:

1. **감사 실행**: 위 명령으로 `audit.py` 실행. 보통 수초~수십초 소요.
2. **요약 보고**: stderr에 출력된 점수표를 사용자에게 한국어로 전달.
3. **상위 ROI 액션 강조**: 액션 1~3위는 보통 1~2시간이면 처리 가능한 큰 점수원.
   사용자가 즉시 처리하길 원하면 그 자리에서 수정 PR을 만들 수 있음.
4. **HTML 대시보드 안내**: `<repo>/.ai-readiness/dashboard.html`을 브라우저로 열라고 안내.

## 점수 밴드 해석

| 점수 | 라벨 | 의미 |
|---|---|---|
| 90~100 | **AI-Native** | 에이전트가 거의 마찰 없이 작업 가능. 모범 사례. |
| 75~89 | **AI-Ready** | 에이전트 작업이 빠르고 안전. 작은 개선으로 최상 도달. |
| 60~74 | **AI-Compatible** | 에이전트 협업 가능하지만 시행착오 발생. 보강 필요. |
| 40~59 | **AI-Cautious** | 인간 감독 필수. 구조와 검증 인프라 부족. |
| 0~39 | **AI-Hostile** | 에이전트가 의미 있는 작업 어려움. 기반 작업 다수 필요. |

## ROI 계산 방식

각 미만점 항목에 대해:

- **Points lost** = `max_points - current_score` (얻을 수 있는 점수)
- **Effort** = 1(수분) ~ 5(수일~수주) — 루브릭에 항목별 사전 정의됨
- **ROI** = `points_lost / effort`

ROI 높은 순으로 정렬해 출력. 보통 상위 3~5개는 30분~2시간 작업으로 5~10점 향상 가능.

## 프레임워크 무관성 보장

스크립트는 다음 기법으로 프레임워크 편향을 회피:

- **언어 감지**: 확장자 + 매니페스트 파일 (`pom.xml`, `package.json`, `Cargo.toml`, `go.mod` 등)
- **휴리스틱 매트릭스**: 각 검사가 언어별 시그니처 사전(`LINTER_CONFIGS`, `LOCK_FILES` 등) 사용
- **N/A 처리**: 정적 타입 언어는 `A3 타입체커`에서 자동 만점 (컴파일러가 처리)
- **library/CLI 감지**: 웹 시그니처(express, spring-boot-starter-web 등) 없으면 헬스체크 N/A

따라서 Spring Boot, Next.js, Rust CLI, Python ML 라이브러리 등 어떤 형태든 공정 비교 가능.

## 구성 파일

- **`rubric.json`** — 루브릭 단일 진실 소스. 카테고리/항목/배점/효과/이유/해결법.
  팀 컨벤션에 맞게 수정 후 `--rubric custom.json` 으로 사용 가능.
- **`audit.py`** — 메인 스크립트. stdlib만 사용 (외부 의존성 없음).

## 한계와 보완

휴리스틱 기반이므로 **정확도가 100%는 아님**. 대표 한계:

- **시크릿 스캔**: 패턴 매칭만 — gitleaks 같은 전문 도구 대체 아님
- **테스트 비율**: 파일 수 기반 — 실제 단언 수와 다를 수 있음
- **타입 체커 점수**: Python의 경우 100개 표본 — 대형 모노레포는 보강 필요
- **god-file 탐지**: LOC 기반 — 정당하게 큰 파일(생성 코드 등) 오탐 가능

루브릭이 평가하는 것은 "에이전트가 협업하기 좋은 구조 신호의 존재 여부"이며,
실제 코드 품질 자체는 인간 리뷰와 정밀 도구로 보완해야 합니다.

## 결과를 가지고 무엇을 할 것인가

대시보드를 본 후 권장 후속 작업:

1. **상위 3개 ROI 액션을 즉시 처리** — 보통 README/AGENTS.md 보강, .editorconfig 추가,
   pre-commit 도입 등 1시간 이내 항목
2. **카테고리 점수 50% 미만인 곳을 다음 분기 OKR로** — 보통 testing 또는 operability
3. **재감사**: 변경 후 다시 실행해 점수 변화 추적. 90점+ 도달이 합리적 목표.
