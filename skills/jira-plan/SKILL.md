---
name: jira-plan
description: "jira-plan — Jira 이슈와 프로젝트 코드를 분석하여 스택 최고 개발자 페르소나로 개발 가이드 MD 파일(docs/<ISSUE-KEY>-dev-guide.md)을 생성합니다. 구현 계획이 필요할 때, '계획 세워줘', '개발 가이드 만들어줘', '플랜 짜줘', 'dev-guide 생성', '이슈 분석해줘', 'jira plan', '어떻게 구현할지 설계해줘' 등의 요청에 이 스킬을 사용하세요. harness-workflow 의 start·grill 단계 이후, /jira-execute 이전에 사용합니다 (구 /jira-start·/jira-clarify 는 2026-07-20 폐기)."
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

작업 디렉토리에서 프로젝트 스택을 자동 감지하고, 해당 스택의 **시니어 전문가 페르소나**를 즉시 활성화합니다. 감지 매핑 + 스택별 페르소나는 `~/.claude/skills/_stack-detection.md` §1 + §2 참조.

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

### 3·4 수행 모드 선택 — ultracode workflow vs 인라인

아래 **§3 코드 분석 + §4 dev-guide 생성** 은 두 모드 중 하나로 수행한다. 프로젝트·이슈 규모에 따라 자동 판단:

| 모드 | 진입 조건 | 방식 |
|------|----------|------|
| **(A) ultracode workflow** | Workflow 기능 사용 가능(`disableWorkflows`≠true, 지원 버전) **AND** 영향 범위가 넓음(키워드상 다수 모듈/파일·교차 도메인) | `Workflow` 툴로 *코드+위키+이슈+memory* multi-modal fan-out → structured map → dev-guide 초안 → 반박 검증 |
| **(B) 인라인** (기본·하위호환) | 위 조건 미충족 / 소규모 이슈 / workflow 비활성 | 메인 세션이 §3·§4 를 직접 수행 (아래 절차) |

> **트리거 워드 (2026-06 변경): `workflow` → `ultracode`.** 이 모드의 명칭이 "ultracode workflow" 다. **jira-plan 이 (A) 로 진입하는 것 자체가 `Workflow` 툴 opt-in 으로 인정**되므로(Workflow 툴 규칙 — "사용자가 invoke 한 skill/슬래시 커맨드의 지시가 Workflow 를 호출하라고 하면 그게 opt-in"), 사용자가 프롬프트에 `ultracode` 를 따로 타이핑하지 않아도 위 진입 조건만 충족하면 자동 트리거된다.
>
> **(B) 가 기본값**이다. Workflow 가 불확실하면 (B). (A) 는 "범위가 커서 컨텍스트 폭발이 우려될 때" 의 최적화이지 의무가 아니다.

#### (A) ultracode workflow 모드 — Understand / Design / Verify

> ⚠️ **범용 — 특정 프로젝트 경로를 하드코딩하지 말 것.** 아래 축은 *프로젝트에 실제 존재하는 소스만* 포함한다 (조건부). 산출물은 `docs/<KEY>-dev-guide.md.draft` 로 저장 → 메인 세션이 검토 후 확정 rename. 위키 쓰기(jira-ingest)·사용자 승인은 workflow 밖(§6 / 호출자).

**축 구성 (해당하는 것만)**:
- `code` — 스택 자동 감지된 소스 디렉토리(§1) 영향 파일·기존 패턴·충돌 지점 (항상)
- `wiki` — `docs/INDEX.md` cross-ref + ADR(예: `docs/08-decision-log.md`)의 "NEVER 재도입 금지" 류 제약 + 유사 dev-guide 선례 → **`docs/INDEX-SCHEMA.md` 존재 시에만**
- `issue` — §2 에서 수집한 Jira 본문/AC 를 프롬프트로 주입 (항상)
- `memory` — 프로젝트 memory 인덱스가 있으면 (`~/.claude/projects/<slug>/memory/MEMORY.md`) 관련 함정 수집 → **있을 때만**

**`Workflow` 툴에 전달할 스크립트 골격** (issueKey·축 목록·수집한 이슈 본문을 채워서 호출):

```javascript
export const meta = {
  name: 'jira-plan-understand',
  description: 'jira-plan Understand/Design/Verify — multi-modal sweep → dev-guide 초안 → 제약·영향범위 반박 검증',
  phases: [{ title: 'Understand' }, { title: 'Design' }, { title: 'Verify', model: 'sonnet' }],
}
const issueKey = (typeof args === 'string' ? args : args?.issueKey)?.trim()
const FINDINGS = { type:'object', required:['axis','findings'], properties:{
  axis:{type:'string'}, findings:{type:'array', items:{type:'object', required:['kind','ref','note'],
  properties:{kind:{type:'string'},ref:{type:'string'},note:{type:'string'}}}} } }
const VERIFY = { type:'object', required:['dimension','verdict','issues'], properties:{
  dimension:{type:'string'}, verdict:{type:'string',enum:['PASS','REVISE']},
  issues:{type:'array', items:{type:'object', required:['severity','detail','evidence'],
  properties:{severity:{type:'string',enum:['blocker','advisory']},detail:{type:'string'},evidence:{type:'string'}}}} } }

phase('Understand')
// 축 구성: code 필수 / wiki·memory 조건부 / issue 본문 주입.
// 호출 전 메인 세션이 hasWiki(docs/INDEX-SCHEMA.md 존재), hasMemory(프로젝트 memory 존재),
// issueBody(§2 수집 Jira 본문·AC) 를 실제 값으로 치환해서 Workflow 의 script 로 전달.
const hasWiki = HAS_WIKI    // ← true/false 치환
const hasMemory = HAS_MEMORY  // ← true/false 치환
const issueBody = ISSUE_BODY  // ← §2 본문 문자열 치환
const AXES = [
  { axis:'code',  model:'sonnet', prompt:`${issueKey} 영향 파일·기존 패턴·충돌 지점을 스택 소스 디렉토리에서 READ ONLY 수집. kind=impacted-file|pattern, ref=파일경로:라인.` },
  ...(hasWiki ? [{ axis:'wiki', model:'sonnet', prompt:`${issueKey} 의 docs/INDEX.md cross-ref + ADR "NEVER 재도입 금지" 류 제약 + 유사 dev-guide 선례 수집(READ ONLY). kind=constraint|precedent, ref=ADR-NNN|STD-NNN|파일경로. 중복/모순 위험을 note 에.` }] : []),
  { axis:'issue', model:'haiku', prompt:`다음 이슈 요구사항·AC 를 정리: ${issueBody}. kind=requirement, ref=AC 번호 또는 ${issueKey}.` },
  ...(hasMemory ? [{ axis:'memory', model:'haiku', prompt:`${issueKey} 영역의 알려진 함정을 프로젝트 memory 인덱스에서 수집(READ ONLY). kind=trap, ref=memory slug.` }] : []),
]
const results = (await parallel(AXES.map(a => () =>
  agent(a.prompt, { label:`understand:${a.axis}`, phase:'Understand', schema:FINDINGS, agentType:'Explore', model:a.model })
    .then(r => r && ({ ...r, _axis:a.axis }))))).filter(Boolean)
// axis 는 agent 반환값(schema의 axis)을 신뢰하지 말고 AXES 가 부여한 값으로 고정 — agent 가 라벨을 임의 제목으로 채우는 문제 방지
const map = results.flatMap(r => (r.findings||[]).map(f => ({ ...f, axis:r._axis })))
const digest = map.map(f => `- [${f.axis}/${f.kind}] ${f.ref} — ${f.note}`).join('\n')

phase('Design')
// model 생략 = 세션 최상위 모델 상속(합성 품질 상한을 세션 모델로 제어). 워커(understand/verify)만 경량 티어로 고정.
const draftPath = `docs/${issueKey}-dev-guide.md.draft`
const draft = await agent(`너는 이 스택의 시니어다. 아래 map 근거로 ${issueKey} dev-guide 초안을 §4 템플릿 구조로 작성해 ${draftPath} 에 Write 하라. wiki constraint(ADR NEVER 룰)는 "준수"로 명시.\n## map\n${digest}`, { phase:'Design' })

phase('Verify')
const dims = [
  { d:'constraint-violation', p:`${draftPath} 가 ADR "NEVER 재도입 금지" 류 제약을 위반하는지 REFUTE. 위반=severity:blocker+evidence:ADR. 없으면 PASS.\n${map.filter(f=>f.kind==='constraint').map(f=>`- ${f.ref}: ${f.note}`).join('\n')||'(없음)'}` },
  { d:'scope-completeness', p:`${draftPath} 영향범위가 불완전한지 REFUTE. code sweep impacted-file 중 누락/연쇄영향. 누락=blocker+evidence:파일. 완전하면 PASS.\n${map.filter(f=>f.axis==='code').map(f=>`- ${f.ref}: ${f.note}`).join('\n')||'(없음)'}` },
]
const v = (await parallel(dims.map(x => () =>
  agent(x.p, { label:`verify:${x.d}`, phase:'Verify', schema:VERIFY, agentType:'Explore', model:'sonnet' })))).filter(Boolean)
const blockers = v.flatMap(r => (r.issues||[]).filter(i => i.severity==='blocker').map(i => ({ dimension:r.dimension, ...i })))
return { issueKey, draftPath, findings: map.length, verdict: blockers.length ? 'REVISE' : 'PASS', blockers, designSummary: draft }
```

**호출**: 위 스크립트의 `HAS_WIKI`/`HAS_MEMORY` 를 `true`/`false` 로, `ISSUE_BODY` 를 §2 수집 본문(백틱/줄바꿈 escape)으로 치환한 뒤 `Workflow({ script: <치환본>, args: "<ISSUE-KEY>" })` 로 실행. workflow 는 백그라운드 실행이며 완료 시 결과(JSON) 가 돌아온다.

**모드 (A) 후처리**:
1. workflow 결과의 `verdict` 확인 — `REVISE` 면 `blockers` 를 사용자에게 보고하고 보강(재실행 또는 수동 수정) 후 진행
2. `PASS` 면 `docs/<KEY>-dev-guide.md.draft` 를 검토 → 문제 없으면 `docs/<KEY>-dev-guide.md` 로 확정(rename/저장)
3. 이후 **§5·§6·§7 은 모드와 무관하게 동일하게 수행** (Jira 코멘트, wiki ingest forecast, 결과 출력)

**모델 티어링** (performance.md 정합 — fan-out 워커는 경량 티어로 고정, 합성만 세션 최상위 모델 상속):

| 단계 | agent | 작업 성격 | model |
|------|-------|----------|-------|
| Understand | `code` · `wiki` | 소스 영향·cascade 분석 / ADR "NEVER" 제약 탐지 (false-negative = blocker 누락) | `sonnet` |
| Understand | `issue` · `memory` | 주입된 이슈 본문 요약 / memory 인덱스 함정 retrieval (저난도) | `haiku` |
| Design | (합성) | dev-guide 초안 작성 — 시니어 페르소나, 추론 부담 최상 | **상속** (`model` 생략 → 세션 모델) |
| Verify | constraint · scope | 반박(REFUTE) 검증 — 통과 오판이 곧 누락 blocker | `sonnet` |

- **Design 만 `model` 미지정** → 세션 최상위(현재 Opus / Sonnet 세션이면 Sonnet)를 상속. 사용자가 세션 모델로 "합성 품질 상한"을 제어하고, 워커는 명시 티어로 고정해 Opus 토큰 낭비를 막는다. (워크플로 `agent()` 기본값이 메인 루프 모델 상속이라, 과거 전 에이전트가 Opus로 뜬 건 세션이 Opus였기 때문.)
- `agentType:'Explore'` 와 조합 시 `model` 이 Explore 정의의 frontmatter 모델보다 **우선**하므로 티어링이 확실히 적용된다.
- 더 보수적: `code`/`wiki`·verify 를 `haiku` 로 내림(비용↓, ADR 제약 누락 위험↑). 더 공격적: verify 를 상속(세션 Opus)으로 올림(반박 강도↑).

조정 가능(PoC 기본은 보수적): verifier 차원당 1명 → 신뢰도 필요 시 차원당 N=3 다수결, `code` 축 → BE/FE 2-reader 분할.

---

#### (B) 인라인 모드 — 프로젝트 코드 분석

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

### Workflow 레인 구성 (2026-07-20 — 구 "Agent Teams 구성" supersede, Agent Teams 신규 사용 금지)

> ⚠️ **이 표를 작성하면 jira-execute § 4A(dynamic Workflow 병렬 모드)가 진입** — 각 행이 Workflow `agent()` 레인 1개가 된다. **모든 레인에 model 을 명시**(BE 복잡 도메인=opus / FE·기계적=sonnet — 미지정=메인 모델 상속 함정) + 웨이브 시작 시 모델 스모크 프로브. 공통 계약(DTO/interface/migration)은 Phase 0 scaffold 로 메인이 선행. 레인 간 합의가 필요 없는 disjoint fan-out 이 아니면 § 5 섹션 자체를 작성하지 말고 Phase 를 순차 설계하세요. 상세: `harness-workflow/references/parallel-modes.md`.

| 레인 | 담당 범위 (touched files) | model | subagent 타입 |
|------|--------------------------|-------|---------------|
| <레인1> | <파일/모듈> | opus/sonnet | <agent-type 또는 없음> |
| <레인2> | <파일/모듈> | opus/sonnet | <agent-type 또는 없음> |

### 작업 의존성

```
Phase 0 scaffold (메인 직접)  →  Phase 1 (레인 병렬)  →  Phase 2 (Phase 1 완료 후)
  ├─ Task A (레인-1)
  └─ Task B (레인-2)
```

### 파일 충돌 방지
<어떤 레인이 어떤 파일을 소유하는지 명시 — 겹치면 같은 레인으로 클러스터링 또는 worktree 격리>
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

> ⚠️ **2026-07-20 표면 폐지 (ADR-106)**: `--subtasks` 플래그 표면은 폐기 — 이 섹션은 하위이슈 **미러 규칙**(전이 동기화·짧은 댓글)으로만 유효하며, harness-workflow 가 플래그 없이 수행한다 (`_subtasks-convention.md` §7). slice 병렬 실행 단위는 Workflow 레인 (`harness-workflow/references/parallel-modes.md`).

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
