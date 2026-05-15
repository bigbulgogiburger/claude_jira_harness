---
name: jira-plan
description: "jira-plan — Jira 이슈와 프로젝트 코드를 분석하여 스택 최고 개발자 페르소나로 개발 가이드 MD 파일(docs/<ISSUE-KEY>-dev-guide.md)을 생성합니다. 구현 계획이 필요할 때, '계획 세워줘', '개발 가이드 만들어줘', '플랜 짜줘', 'dev-guide 생성', '이슈 분석해줘', 'jira plan', '어떻게 구현할지 설계해줘' 등의 요청에 이 스킬을 사용하세요. /jira-start 및 /jira-clarify 이후, /jira-execute 이전에 사용합니다."
---

# jira-plan — Jira 이슈 분석 및 개발 가이드 MD 생성

Jira 이슈와 프로젝트 코드를 분석하여, 스택 최고 개발자 페르소나로 개발 가이드 MD 파일을 생성합니다.
지라에 댓글이나 설명을 작성할 때에는 한글로 작성합니다.

## Usage

```
/jira-plan <ISSUE-KEY>
```

- `ISSUE-KEY`: Jira 이슈 키 (예: PROJ-156, SCRUM-42)

## Procedure

### 1. 스택 감지 및 페르소나 활성화

작업 디렉토리에서 프로젝트 스택을 자동 감지하고, 해당 스택의 **시니어 전문가 페르소나**를 즉시 활성화합니다.

| 감지 파일 | 스택 | 페르소나 |
|-----------|------|----------|
| `build.gradle` / `pom.xml` | Spring Boot | **Spring Boot Master** — JPA/QueryDSL, CQRS, 트랜잭션 설계, 성능 최적화에 정통한 10년차 백엔드 아키텍트. Entity 설계 시 N+1을 먼저 고려하고, 서비스 분리는 항상 Read/Write로 시작함 |
| `pubspec.yaml` | Flutter/Dart | **Flutter Architect** — Riverpod/BLoC 상태관리, GoRouter, 플랫폼 채널, 위젯 성능 최적화에 정통한 시니어. Widget tree 최적화와 rebuild 최소화를 항상 우선시함 |
| `package.json` + Vue | Vue.js | **Vue.js Specialist** — Composition API, Pinia, Vite, SSR/SSG에 정통한 프론트엔드 시니어. 반응형 시스템 내부 동작을 이해하고, composable 설계를 선호함 |
| `package.json` + React | React | **React Expert** — Hooks, Server Components, Next.js, Zustand/Jotai에 정통한 프론트엔드 시니어. 렌더링 최적화와 데이터 페칭 패턴에 강함 |
| `package.json` + Angular | Angular | **Angular Master** — RxJS, Signal, NgModule/Standalone, Change Detection에 정통한 엔터프라이즈 프론트엔드 아키텍트 |
| `go.mod` | Go | **Go Expert** — goroutine 패턴, interface 설계, stdlib 활용, 에러 핸들링 철학에 정통한 시니어. 단순함과 명시성을 최우선으로 함 |
| `Cargo.toml` | Rust | **Rust Master** — ownership/lifetime, async runtime, trait 설계에 정통한 시스템 프로그래머. 안전성과 성능의 균형을 잡는 데 능함 |
| `pyproject.toml` / `requirements.txt` | Python | **Python Expert** — FastAPI/Django, type hints, async, 데이터 파이프라인에 정통한 시니어. Pythonic한 코드와 실용적 설계를 추구함 |

페르소나가 활성화되면, 이후 모든 분석과 가이드 작성에 해당 페르소나의 관점이 적용됩니다.

### 2. Jira 이슈 심층 분석

MCP Atlassian 도구로 이슈 정보를 수집합니다:

```
mcp__atlassian__getJiraIssue → 이슈 상세 (제목, 설명, 우선순위, 라벨)
mcp__atlassian__searchJiraIssuesUsingJql → 관련 이슈/서브태스크 조회
```

수집하는 정보:
- 이슈 설명, 인수조건(Acceptance Criteria)
- 댓글 (특히 최신 댓글에 추가 요구사항이 있는 경우)
- 서브태스크 또는 체크리스트
- 관련 이슈 (linked issues)
- 첨부파일 목록 (있으면)

### 3. 프로젝트 코드 분석

페르소나 관점에서 관련 코드를 분석합니다:

**3-1. CLAUDE.md 확인**
- 프로젝트 아키텍처, 도메인 모듈, 핵심 규칙 파악
- 참조 문서(`.claude/docs/reference/`)가 있으면 관련 문서 읽기

**3-2. 영향 범위 파악**
- 이슈 설명에서 키워드 추출 → 관련 파일 검색 (Grep/Glob)
- 수정 대상 Entity, DTO, Service, Controller, Repository 식별
- 연관된 테스트 파일 확인

**3-3. 의존성 분석**
- 수정 대상 코드의 호출 관계 (누가 호출하는지, 무엇을 호출하는지)
- DB 스키마 변경 필요 여부
- 외부 연동 (Feign, API) 영향 여부
- 기존 테스트 영향 여부

### 4. 개발 가이드 MD 파일 생성

`docs/` 디렉토리에 `<ISSUE-KEY>-dev-guide.md` 파일을 생성합니다.

#### MD 파일 템플릿

```markdown
# [<ISSUE-KEY>] <이슈 제목> — 개발 가이드

> 생성일: <날짜>
> 스택: <감지된 스택>
> 페르소나: <활성화된 페르소나명>

## 1. 요구사항 요약

### 비즈니스 목표
<이슈 설명에서 추출한 핵심 목표 2-3줄>

### 인수조건
- [ ] <AC1>
- [ ] <AC2>
- [ ] <AC3>

### 제약사항 / 주의사항
<기존 코드, 비즈니스 규칙, 성능 제약 등>

## 2. 영향 범위 분석

### 수정 대상 파일

| 파일 | 변경 유형 | 설명 |
|------|----------|------|
| `path/to/File.java` | 수정 | <변경 내용> |
| `path/to/NewFile.java` | 신규 | <생성 이유> |

### 연관 파일 (읽기 전용 — 수정하지 않지만 이해 필요)

| 파일 | 참조 이유 |
|------|----------|
| `path/to/Related.java` | <참조 이유> |

### DB 변경 (있는 경우)

```sql
-- DDL
ALTER TABLE ...
-- 마이그레이션
UPDATE ...
```

## 3. 구현 계획

### Phase 1: <단계명>
**목표**: <이 단계에서 달성할 것>

1. `path/to/File.java` — <구체적 변경 내용>
2. `path/to/File2.java` — <구체적 변경 내용>

**검증**: <이 단계 완료 확인 방법>

### Phase 2: <단계명>
...

### Phase N: 테스트
1. <테스트 대상과 방법>

## 4. 기술 상세

### 핵심 로직
<페르소나 관점에서 가장 중요한 기술적 판단 사항>

### 위험 요소
| 위험 | 영향도 | 대응 방안 |
|------|--------|----------|
| <위험1> | 높음/중간/낮음 | <대응> |

### 외부 연동 (있는 경우)
<Feign, API, 다른 팀 작업 필요사항>

## 5. 병렬 작업 가이드 (선택)

> 이 섹션은 독립적으로 진행 가능한 작업이 2개 이상일 때만 작성합니다.

### Agent Teams 구성 (권장)

| 역할 | 담당 범위 | subagent 타입 |
|------|----------|---------------|
| <역할1> | <파일/모듈> | <agent-type 또는 없음> |
| <역할2> | <파일/모듈> | <agent-type 또는 없음> |

### 작업 의존성

```
Phase 1 (독립)  →  Phase 2 (Phase 1 완료 후)
  ├─ Task A (teammate-1)
  └─ Task B (teammate-2)
```

### 파일 충돌 방지
<어떤 teammate가 어떤 파일을 소유하는지 명시>
```

#### 병렬 작업 가이드 작성 기준

다음 **모든** 조건을 충족할 때만 "5. 병렬 작업 가이드" 섹션을 작성합니다:

1. 독립적으로 작업 가능한 모듈/파일 그룹이 **2개 이상**
2. 각 그룹 간 **파일 충돌이 없음** (동일 파일을 수정하지 않음)
3. 병렬 작업으로 **실질적 시간 단축** 효과가 있음 (단순 파일 2-3개 수정은 순차가 나음)
4. Agent Teams 코디네이션 오버헤드 대비 **이점이 명확함**

충족하지 않으면 Phase를 순차적으로 설계하고, 섹션 자체를 생략합니다.

### 5. Jira 코멘트 및 결과 출력

#### Jira 코멘트
```
📋 개발 가이드 생성 완료

📝 파일: docs/<ISSUE-KEY>-dev-guide.md
🔧 스택: <감지된 스택>
📊 영향 범위: <수정 대상 파일 수>개 파일

주요 변경사항:
- <핵심 변경 1>
- <핵심 변경 2>

구현 단계: <Phase 수>단계
```

#### 터미널 출력
```
📋 개발 가이드 생성 완료
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 파일: docs/<ISSUE-KEY>-dev-guide.md
🔧 스택: <감지된 스택>
👤 페르소나: <페르소나명>

📊 분석 결과:
  수정 대상: <N>개 파일
  신규 생성: <M>개 파일
  DB 변경: <있음/없음>
  외부 연동: <있음/없음>

📐 구현 계획: <Phase 수>단계
  <각 Phase 한줄 요약>

병렬 작업: <가능/불필요>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

다음 단계: /jira-execute <ISSUE-KEY>
```

### 6. Wiki Ingest 자동 Chain (forecast 단계) — **MANDATORY**

> ⛔ **이 단계는 선택 사항 아님.** dev-guide 가 막 생성된 시점은 wiki INDEX 에 forecast entry 를 등록하는 **유일한 정상 시점**이다. `docs/INDEX-SCHEMA.md` 가 존재하는데 본 chain 을 누락하면 wiki 가 drift 한다 (orphan dev-guide, planned 누락 → 이후 closure 단계에서 row 가 갑자기 튀어나오는 비대칭).
>
> 본 절은 §1~§5 가 끝난 직후 **반드시** 실행한다. 사용자에게 "ingest 할까요?" 라고 물어보지 않는다 (조용한 누락 방지 — 명시적 `--no-ingest` 플래그만 인정).
>
> Karpathy LLM Wiki 패턴 적용 프로젝트는 `docs/INDEX-SCHEMA.md` 존재로 식별.

```
조건: docs/INDEX-SCHEMA.md 존재 AND 사용자가 --no-ingest 플래그 전달 안 함
호출: Skill('jira-ingest', '<KEY> forecast 모드로 ingest — dev-guide 가 방금 생성됨')
```

`--subtasks` 모드면 flag 자동 전파 (`_subtasks-convention.md` § 7 패턴):
```
Skill('jira-ingest', '<KEY> forecast --subtasks')
```

**자기 점검 (skill 종료 직전 last-mile check)**:
1. `docs/INDEX-SCHEMA.md` 존재? → 존재하면 본 §6 chain 호출 흔적이 conversation 에 있어야 함
2. 호출 흔적 없으면 → **지금 즉시 호출** + 사용자에게 "§6 chain 누락 감지 → 사후 호출함" 1줄 보고
3. 그래도 호출 못 한 사유 (skill 부재 등) 가 있으면 사용자에게 명시 경고

**조건 미충족 시 (wiki 미설정 프로젝트) 만 skip**:
- `docs/INDEX-SCHEMA.md` 부재 → "wiki 미설정 프로젝트 — ingest skip" 한 줄 로그만 출력
- jira-ingest 가 first-run onboarding 으로 진입하지 않도록 **jira-plan 안에서는 호출 자체를 skip** (사용자가 명시적으로 wiki 셋업 의도를 보일 때만 first-run flow 진입이 자연스러움)

**실패 격리**: ingest chain 실패해도 jira-plan 자체는 PASS — 위 §5 결과 출력은 이미 완료된 상태. 실패 시 경고만 출력하고 다음 단계 (/jira-execute) 안내 계속. 단 실패 자체는 **반드시 사용자에게 가시화** — 조용한 skip 금지.

### 7. 결과 출력 (Wiki ingest 후 보강)

§5 출력에 다음 라인 1개 추가 (ingest chain 이 호출된 경우만):

```
📚 Wiki ingest: forecast 등록 완료 (INDEX.md row added, LOG.md append)
```

ingest 가 skip 된 경우:
```
📚 Wiki ingest: skip (docs/INDEX-SCHEMA.md 부재 — wiki 미설정)
```

## Error Handling

- 이슈가 존재하지 않으면 오류 메시지 출력
- 스택을 감지할 수 없으면 사용자에게 스택 입력 요청
- CLAUDE.md가 없으면 경고 후 코드 분석만으로 진행
- 영향 범위가 너무 넓으면 (20개 파일 초과) 사용자에게 범위 축소 확인

## Notes

- 생성된 MD 파일은 `/jira-execute`에서 직접 소비하도록 설계됨
- CLAUDE.md에 프로젝트별 규칙이 있으면 가이드에 반영
- 페르소나는 "조언자"가 아닌 "실무자" — 추상적 조언이 아닌 **구체적인 파일 경로와 코드 변경** 제시
- 이미 `docs/<ISSUE-KEY>-dev-guide.md`가 존재하면 덮어쓸지 사용자에게 확인

## --subtasks Mode

사용자가 `/jira-plan <KEY> --subtasks` 로 호출하고 부모 이슈에 하위 작업이 있으면, 부모 dev-guide 처리 후 **추가로**:

1. 부모 dev-guide (`docs/<KEY>-dev-guide.md`) 에 § DAG / § Cross-cutting 결정 / § slice 진입점 표 포함
2. 각 하위 키마다 slice dev-guide 작성: `docs/<KEY>-<SUB-KEY>-dev-guide.md` (ADR-070 형식 — `### 0. Touched Files` 섹션 의무)
3. **각 하위 이슈에 짧은 댓글** 추가:
   ```
   📝 dev-guide 작성 완료: `docs/<KEY>-<SUB-KEY>-dev-guide.md`
   부모 통합 가이드: `docs/<KEY>-dev-guide.md`
   ```
4. 출력에 부모 + 하위별 dev-guide 경로 표 포함

자세한 정책: `~/.claude/skills/_subtasks-convention.md` § 3, § 5
