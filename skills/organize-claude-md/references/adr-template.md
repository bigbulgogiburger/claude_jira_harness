# ADR (Architecture Decision Record) — CLAUDE.md 구조 결정 기록

> 참조 시점: CLAUDE.md / reference 구조에 **되돌리기 어려운** 결정을 내릴 때 (분할, 통합, 위치 이동, 정책 채택)
> 갱신 트리거: 새 구조 결정 시 ADR 추가, 기존 결정 번복 시 superseded 처리

## 왜 ADR 인가

CLAUDE.md 를 organize 한 결과물 (분할 구조, CHANGELOG 분리 임계점, monorepo 정책) 은 다음 invocation 때 "왜 이렇게 되어 있지?" 가 된다. 의도를 기록하지 않으면:

- 다음 organize 실행이 옛 구조로 되돌림 (예: CHANGELOG.md 를 다시 CLAUDE.md 에 흡수)
- Sub-project 가 추가됐을 때 root 정책 충돌 (`이 규칙은 왜 root 가 아니라 sub 에 있지?`)
- 다른 팀원이 영역 책임을 잘못 이해

ADR 은 이 의도를 **결정 시점에 한 번** 기록해서 미래의 모든 invocation 이 존중하게 한다.

## 언제 ADR 을 만드는가

다음 결정 중 하나라도 했으면 ADR 작성:

1. **CLAUDE.md 를 sub 별로 분할** ("왜 root + BE + FE 3개로 나눴는가")
2. **CHANGELOG.md 를 분리** ("왜 N 토큰 임계점에서 분리했는가")
3. **Reference 위치 패턴 채택** (A/B/C 중 어느 패턴 + 이유)
4. **Cross-cutting 문서 위치 결정** ("왜 root 단일 SSoT 가 아니라 양쪽 복사인가")
5. **Agents/hooks 통합 vs 분산 결정**
6. **Sub-project 추가/삭제**
7. **줄수 상한 예외 적용** ("왜 sub CLAUDE.md 가 150줄을 넘는가")

다음은 **ADR 불필요** — 코드만 보면 명백:
- 새 도메인 추가 (`domain-<name>.md` 신규)
- 키 추가/변경 (i18n, env)
- 단순 갱신 (Last Updated, 새 API 함수 행 추가)

## ADR 파일 위치

| 프로젝트 형태 | 위치 |
|-------------|------|
| 단일 프로젝트 | `docs/adr/` 또는 `.claude/adr/` |
| Monorepo | `<root>/docs/adr/` (cross-cutting 결정만, sub 전용 결정은 sub 안에 또는 root 에 prefix) |

Sub 전용 결정 (예: BE refs 의 testing.md 를 통합/분할) 도 root 에 두되 제목에 sub 명시:
```
ADR-005-BE-testing-md-split.md
ADR-006-FE-component-library-vs-design-tokens-split.md
```

## ADR 템플릿

```markdown
# ADR-<NNN>: <짧고 명확한 제목>

> Status: Accepted / Superseded by ADR-<MMM> / Deprecated
> Date: YYYY-MM-DD
> Scope: <영향 영역 — root | sub-<name> | cross-cutting>

## Context

<이 결정이 필요했던 문제. 발견한 시점의 상태. 측정 가능한 증거 (토큰 수, 줄 수, 발생 빈도 등).>

## Decision

<채택한 방안. 한 문장으로.>

## Alternatives Considered

- **대안 1**: <간단 설명> — 채택 안 한 이유
- **대안 2**: <간단 설명> — 채택 안 한 이유

## Consequences

**Positive:**
- <이점 1>
- <이점 2>

**Negative / Trade-offs:**
- <비용 1>
- <비용 2>

**Follow-up actions:**
- <후속 조치 — 코드 변경, 다른 ADR, sprint 작업 등>
```

## ADR 예시

### ADR-001: CLAUDE.md 를 root + BE + FE 3계층으로 분할

> Status: Accepted
> Date: 2026-05-11
> Scope: cross-cutting

**Context:** 단일 CLAUDE.md 가 1,200줄 도달. BE-only NEVER (Q-class 재생성) 와 FE-only NEVER (`<script setup>`) 가 한 파일에 공존하여 sub 단독 작업 시 노이즈. 매 세션 시작 시 양쪽 stack 의 규칙이 모두 컨텍스트에 로드됨.

**Decision:** Root (150줄, 시스템 전체) + `<be-dir>/CLAUDE.md` (120줄, BE stack) + `<fe-dir>/CLAUDE.md` (120줄, FE stack) 3계층.

**Alternatives Considered:**
- 단일 CLAUDE.md 유지 + sub 별 섹션 구분: 줄수만 늘고 lazy loading 안 됨
- Sub 만 두고 root 폐기: 풀스택 commit 정책 / 인프라 정보 둘 곳 없음

**Consequences:**
- Positive: sub 단독 작업 시 본인 stack 의 NEVER 만 로드 / 풀스택 작업 시 root 명시 로드로 cross-cutting 정책 즉시 적용
- Negative: 같은 규칙을 두 곳에 쓰면 drift — `cross-project.md` 가 sync 대책
- Follow-up: root CHANGELOG / sub CHANGELOG 분리 (ADR-002)

### ADR-002: Last Updated 비대화 임계점에서 CHANGELOG.md 분리

> Status: Accepted
> Date: 2026-05-11
> Scope: cross-cutting

**Context:** 단일 `Last Updated:` 라인에 closure 마다 "직전: ..." chain 으로 누적. 측정 결과 19회 closure 누적 시 ~28K 토큰 단일 라인. 컨텍스트 한계 압박.

**Decision:** `Last Updated:` 라인이 3,000 토큰 또는 5회 closure 누적 도달 시 `CHANGELOG.md` 분리. CLAUDE.md 의 Last Updated 는 직전 1~5건 한줄 요약 + CHANGELOG 링크만.

**Alternatives Considered:**
- 절대 안 줄임: 시간 지나면 무조건 한계 도달
- 매 closure 마다 분리: CHANGELOG 가 너무 잘게 — 한 번 분리한 후엔 누적 허용

**Consequences:**
- Positive: CLAUDE.md 항상 lean 유지 / 누적 history 는 CHANGELOG 에서 grep 가능
- Negative: 한 번 분리하는 작업 자체가 수동 (자동화 가능)
- Follow-up: organize-claude-md skill 이 임계점 도달 시 자동 제안

## NEVER 규칙

- **NEVER** ADR 의 status 를 임의로 Deprecated 처리 — 새 ADR (`Superseded by ADR-<N>`) 로 명시
- **NEVER** ADR 의 Date 를 사후 변경 — 결정 시점 보존이 ADR 의 본질
- **NEVER** Context 에 "느낌상" 적기 — 측정 가능한 증거 (수치, 발생 빈도) 명시
- **NEVER** ADR 을 reference 문서로 사용 — ADR 은 결정 기록, reference 는 사용 가이드
