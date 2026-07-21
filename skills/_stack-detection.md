# _stack-detection.md — 스택 감지 + 페르소나 (SSoT)

> jira-* / harness-* 스킬이 공유하는 **스택 감지 매핑**의 단일 출처(SSoT).
> 각 스킬은 본문에 표를 복붙하지 않고 본 파일을 참조 + 자기 용도 컬럼만 인라인한다.
> `_subtasks-convention.md` / `_wiki-schema.md` / `_harness-guard.md` 와 동일 위상의 공통 규약 파일.
>
> **설계 원칙**: 모든 사용처가 "감지 파일 → 스택" 매핑은 동일하고, **용도별 컬럼(페르소나 / 라벨 / 빌드)** 만 다르다. 그래서 감지 매핑은 §1 하나로 고정하고, 용도 컬럼은 §2~§4 로 분리.

---

## §1. 감지 파일 → 스택 매핑 (공통)

| 감지 파일 | 스택 |
|-----------|------|
| `build.gradle` / `build.gradle.kts` / `pom.xml` | **Spring Boot** (Java/Kotlin) |
| `pubspec.yaml` | **Flutter** (Dart) |
| `package.json` + `vue` 의존성 | **Vue.js** (JS/TS) |
| `package.json` + `react`/`next` 의존성 | **React/Next.js** (JS/TS) |
| `package.json` + `@angular/core` 의존성 | **Angular** (TS) |
| `go.mod` | **Go** |
| `Cargo.toml` | **Rust** |
| `pyproject.toml` / `requirements.txt` | **Python** |
| (감지 불가) | 사용자에게 스택 확인 요청 |

> Gradle/Maven 동시 존재 시 `build.gradle` 우선. `package.json` 은 의존성으로 Vue/React/Angular 구분.

---

## §2. 스택별 페르소나 (jira-plan / jira-execute 용)

스택 감지 후 해당 **시니어 전문가 페르소나**를 활성화한다. 페르소나는 "조언자" 가 아니라 "실무자" — 추상적 조언이 아닌 구체적 파일 경로·코드 변경을 제시한다.

| 스택 | 페르소나 |
|------|----------|
| Spring Boot | **Spring Boot Master** — JPA/QueryDSL, CQRS, 트랜잭션 설계, 성능 최적화에 정통한 10년차 백엔드 아키텍트. N+1 을 먼저 고려하고 서비스 분리는 항상 Read/Write 로 시작, 소프트 삭제 패턴을 자연스럽게 적용 |
| Flutter | **Flutter Architect** — Riverpod/BLoC, GoRouter, 플랫폼 채널, 위젯 성능 최적화 전문. Widget rebuild 최소화·상태 격리·테스트 가능한 아키텍처 우선 |
| Vue.js | **Vue.js Specialist** — Composition API, Pinia, Vite, SSR/SSG 전문. 반응형 시스템 내부 이해 기반 composable 설계·컴포넌트 재사용성 극대화 |
| React/Next.js | **React Expert** — Hooks, Server Components, Next.js, Zustand/Jotai 전문. 렌더링 최적화·데이터 페칭 패턴·관심사 분리 |
| Angular | **Angular Master** — RxJS, Signal, Standalone Components, Change Detection 전문. 엔터프라이즈 모듈 설계 |
| Go | **Go Expert** — goroutine, interface 설계, stdlib 활용 전문. 단순함·명시성 최우선 |
| Rust | **Rust Master** — ownership/lifetime, async runtime, trait 설계 전문. 안전성·성능 균형 |
| Python | **Python Expert** — FastAPI/Django, type hints, async 전문. Pythonic 코드·실용적 설계 |

---

## §3. 스택별 라벨 후보 (jira-create 용)

이슈 생성 시 라벨 자동 부여 + issueType 추정에 사용 (라벨은 kebab-case).

| 스택 | 라벨 후보 |
|------|----------|
| Spring Boot | `spring-boot`, `backend` |
| Flutter | `flutter`, `mobile` |
| Vue.js | `vue`, `frontend` |
| React/Next.js | `react`, `frontend` |
| Angular | `angular`, `frontend` |
| Go | `go`, `backend` |
| Rust | `rust` |
| Python | `python` |

---

## §4. 스택별 검증 명령 (harness-workflow gate 단계 / jira-complete / harness-gate 용 — 구 jira-test·jira-commit 은 2026-07-20 gate 단계로 흡수)

**CLAUDE.md 에 커스텀 명령이 있으면 그것을 우선**한다. 없을 때의 기본:

| 스택 | Lint / 타입체크 | Test | Build |
|------|----------------|------|-------|
| Spring Boot (Gradle) | built-in | `./gradlew test` (Win: `gradlew.bat test`) | `./gradlew build -x test` / 게이트는 `compileJava -q` |
| Spring Boot (Maven) | built-in | `mvn test` | `mvn -q compile` |
| Flutter | `flutter analyze` | `flutter test` | `flutter build` |
| Vue/React/Angular | `npm run lint` / `npx tsc --noEmit` | `npm test` | `npm run build` |
| Go | `go vet ./...` | `go test ./...` | `go build ./...` |
| Rust | `cargo check` | `cargo test` | `cargo build` |
| Python | `ruff check .` / `flake8` / `mypy .` | `pytest` | — |

---

## 적용 스킬 + 참조 방법

| 스킬 | 참조하는 절 |
|------|------------|
| harness-workflow start 단계 (구 jira-start) | §1 (감지 → 스택) |
| jira-create | §1 + §3 (라벨) |
| jira-plan / jira-execute | §1 + §2 (페르소나) |
| harness-workflow gate 단계 (구 jira-test·jira-commit) / jira-complete / harness-gate | §1 + §4 (검증 명령) — 단 CLAUDE.md 커스텀 우선 |
| harness-plan / harness-review | §1 (fallback 스택 감지) — cwd 프로젝트 매칭이 먼저, 미매칭 시 §1 |

각 스킬은 본문에 다음 1줄만 둔다:

> 스택 감지 + <용도>: `~/.claude/skills/_stack-detection.md` §1(+§N) 참조.

스택 추가/페르소나 수정 시 **본 파일만** 고치면 모든 스킬에 일괄 반영된다 (과거엔 jira-start/create/plan/execute 4곳에 변형 복붙).

## 변경 이력

- **2026-06-09**: 신설. jira-start/create/plan/execute 에 4개 변형(비고/라벨/페르소나)으로 복붙돼 있던 스택 표를 단일 SSoT 로 추출. 감지 매핑(§1) 공통 + 용도 컬럼(§2~§4) 분리.
