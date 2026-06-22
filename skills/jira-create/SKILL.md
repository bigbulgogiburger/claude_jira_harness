---
name: jira-create
description: "jira-create — 자연어 한 줄 또는 문서를 읽어 Jira 이슈를 생성합니다. 단일 이슈는 바로 등록하고, 문서 기반이면 에픽→이슈→하위이슈 계층으로 일괄 등록합니다. 'jira 이슈 만들어줘', '지라 이슈 등록해줘', '이슈 등록', '이슈 생성', '에픽 만들어줘', '스토리 추가', '백로그에 추가', '이 문서 보고 이슈 등록해줘', 'w1-w4.md 지라에 올려줘', '계획 문서를 지라로 옮겨줘', 'jira create', '/jira-create' 등의 요청에 반드시 이 스킬을 사용하세요. 워크플로우의 시작점으로, /jira-start 이전에 사용합니다."
---

# jira-create — Jira 이슈 등록

자연어 한 줄 혹은 문서(spec / 주차 계획 / RFC 등)를 받아 Jira 이슈로 만든다. 단일 이슈는 곧바로 등록하고, 문서 기반이면 에픽 → 이슈 → 하위이슈 계층으로 일괄 등록한다.

지라에 댓글이나 설명을 작성할 때에는 한글로 작성한다.

## Usage

```
# 단일 모드 (자연어)
/jira-create 대시보드에 KPI 위젯 추가하는 이슈 만들어줘
/jira-create [STD] 정산 화면 엑셀 다운로드 버그 등록

# 벌크 모드 (문서)
/jira-create docs/w1-w4.md 읽고 STD 프로젝트에 에픽→이슈→하위이슈로 등록
/jira-create plan.md 보고 이슈 만들어줘
```

옵션 인자:
- **prefix**: 대괄호(`[STD]`) 또는 명시적 단어("STD 프로젝트") 어느 쪽이든 인식. 미지정 시 후술 절차로 자동 감지.
- **mode 힌트**: "에픽", "하위이슈", "계층", "여러 이슈" 같은 단어가 있으면 벌크 모드로 가정.

## 모드 자동 판별

다음 중 하나라도 해당하면 **벌크 모드**, 그 외에는 **단일 모드**로 진행한다:

- 사용자 입력에 **파일 경로** 가 포함됨 (`*.md`, `*.txt`, `*.pdf`, `docs/...`)
- "에픽", "epic", "하위이슈", "subtask", "계층", "여러 이슈", "한 번에 등록" 같은 키워드
- 문서 안에 명백한 계층 구조(주차/Phase/모듈별 헤딩)가 있음

벌크 모드 절차는 `references/bulk-document-flow.md`를 따른다. 아래는 단일 모드 절차다.

## 단일 모드 절차

### 1. cloudId 확정

`mcp__atlassian__getAccessibleAtlassianResources` 로 cloudId를 확보한다. 사이트가 여러 개라면 가장 최근에 사용한 사이트(또는 사용자가 명시한 사이트)를 선택한다.

### 2. projectKey 확정 (prefix 감지)

다음 우선순위로 **첫 번째로 확정되는 값**을 사용한다:

1. **사용자 입력 명시** — `[STD]`, `STD 프로젝트`, `--prefix STD` 등
2. **현재 git 브랜치명** — `feature/SURINP-200-foo` → `SURINP`
3. **최근 브랜치 목록** — `git branch --all | grep -oE '[A-Z][A-Z0-9]+-[0-9]+' | sort -u | head` 결과의 다수 prefix
4. **최근 커밋 메시지** — `git log --oneline -50 | grep -oE '[A-Z][A-Z0-9]+-[0-9]+'`
5. **`mcp__atlassian__getVisibleJiraProjects`** — `action: "create"` 로 호출하여 사용 가능한 프로젝트 목록 조회. 1개뿐이면 그것 사용. 여러 개면 다음 6번으로.
6. **사용자에게 질문** — `AskUserQuestion`으로 후보 3-4개 제시. 절대 임의로 고르지 않는다.

> 한 번 확정되면 본 작업 동안에는 다시 묻지 않는다. 단, 사용자가 명시적으로 다른 프로젝트를 지목하면 즉시 교체한다.

### 3. 이슈 타입 메타데이터 조회

확정된 projectKey에 대해 `mcp__atlassian__getJiraProjectIssueTypesMetadata`를 호출하여 사용 가능한 issueTypeName 목록을 확인한다 (`Task`, `Story`, `Bug`, `Epic`, `Sub-task` 등). 프로젝트마다 다를 수 있으므로 **항상 메타에서 확인된 이름만 사용**한다.

### 4. 스택 감지

감지 매핑 + 스택별 라벨 후보는 `~/.claude/skills/_stack-detection.md` §1 + §3 참조.

스택 감지는 라벨 자동 부여와 issueType 추정(예: 백엔드 프로젝트면 Story 대신 Task가 표준일 수 있음)에 사용한다.

### 5. 라이트 코드/문맥 분석

`/jira-clarify` 와 `/jira-plan` 이 이후 단계에서 깊이 파주므로 **여기서는 가볍게**만 본다. 목적은 "이 이슈가 말이 되는가, 어디쯤에 손이 갈 가능성이 있는가" 확인.

- `CLAUDE.md` 가 있으면 1회 읽어 도메인 용어 확인
- 사용자 입력의 명사구를 키워드로 `Grep` 1-2회 (예: "KPI 위젯" → `Kpi`, `kpi`, `dashboard`)
- 매치되는 파일이 있으면 1-2개만 짧게 확인하여 "관련 파일이 있다" 정도 파악
- 매치 없어도 진행 — 신규 기능일 수 있다

깊이 파지 않는다. 5분 이상 쓰지 않는다.

### 6. 이슈 타입 / 우선순위 / 라벨 결정

#### 이슈 타입

사용자 입력의 단어로 1차 추정 후 메타데이터에 존재하는 이름으로 매핑:

- "버그", "오류", "에러", "안 됨", "터짐" → **Bug** (없으면 Task)
- "에픽", "epic", "이니셔티브" → **Epic**
- "하위", "서브", "subtask" → **Sub-task** (parent 필요)
- "기능 추가", "구현", "만들어", "도입" → **Story** (없으면 Task)
- 그 외 / 모호 → **Task** (가장 중립적)

#### 우선순위

명시적 단어 없으면 설정하지 않는다 (프로젝트 기본값 사용). 명시되면 매핑:

- "긴급", "급함", "ASAP", "블로커" → `Highest` 또는 `High`
- "사소", "낮음", "나중에" → `Low`

#### 라벨 (kebab-case 권장)

자동 부여 후보 (해당하는 것만):
- 스택: `spring-boot` / `vue` / `react` / `flutter` / `python` / `go` / `rust`
- 영역: `backend` / `frontend` / `mobile` / `infra` / `docs`
- 종류: `feature` / `bug` / `tech-debt` / `refactor` / `docs` / `chore`
- 출처(벌크 모드): `from-doc-<basename>` (예: `from-doc-w1-w4`) — Jira 라벨은 영문/숫자/하이픈/언더스코어만 안전하므로 콜론 사용 금지

> 라벨은 case-sensitive다. **항상 소문자 + kebab-case**로 통일. `Spring-Boot`, `Spring_Boot`, `springBoot` 같이 변형하면 검색에서 분리된다.

자세한 라벨 컨벤션은 `references/jira-best-practices.md` 참고.

#### 날짜

- **Start date / Due date 는 기본적으로 설정하지 않는다.** 사용자가 명시적으로 일정을 언급한 경우에만 설정한다.
- 시스템 필드 `duedate` 만 백로그에 표시된다. 커스텀 시작일 필드는 프로젝트마다 키가 달라(`customfield_10015` 등) 충돌 위험이 있으니, 명시 요청 없이는 건드리지 않는다.

### 7. 드래프트 작성

`contentFormat: "markdown"` 으로 createJiraIssue를 호출한다 (ADF JSON 직접 작성보다 안전하고 가독성 좋음).

#### Summary 작성 규칙

- **동사로 시작하는 행동형**: "추가한다", "수정한다", "리팩터링한다" 보다는 명사구 + 명료한 행동 → "[Dashboard] KPI 위젯 추가"
- **컴포넌트 prefix 권장** (`[Dashboard]`, `[Settlement]`, `[API]`)
- **70자 이내**
- **버그면 증상 + 환경**: "[정산] 엑셀 다운로드 시 한글 파일명 깨짐"

#### Description 템플릿 (단일 이슈, 라이트 버전)

`/jira-clarify` 와 `/jira-plan` 이 이후에 디테일을 채울 것이므로 **여기서는 의도가 전달될 정도만** 작성한다. 과도한 추측은 피한다.

```markdown
## 배경
<왜 이 이슈가 필요한지 1-3줄. 사용자 입력에서 추출>

## 작업 범위
- <할 일 항목 1>
- <할 일 항목 2>
- <할 일 항목 3>

## 인수조건
- [ ] <검증 가능한 완료 기준 1>
- [ ] <검증 가능한 완료 기준 2>

## 참고
- 관련 파일: <라이트 분석에서 발견한 경로 0-3개>
- 관련 문서: <CLAUDE.md 섹션, RFC 등 있으면>
```

이슈 타입별 변형은 `references/description-templates.md` 참고 (Bug 는 재현 절차/기대/실제, Epic 은 목표/성공 지표 등).

### 8. 사용자 확인 (필수)

이슈 생성은 외부에 공개되며 되돌리기 어려우므로 **반드시 드래프트를 보여주고 확인을 받는다**.

```
📋 이슈 드래프트
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏷️ 프로젝트: STD
📂 타입: Story
🎯 우선순위: (기본값)
🏷️ 라벨: vue, frontend, feature

📌 제목: [Dashboard] KPI 위젯 추가

📝 설명:
## 배경
대시보드에 핵심 지표를 한눈에 볼 수 있는 KPI 위젯이 없음.

## 작업 범위
- KPI 위젯 컴포넌트 신규 작성
- 대시보드 라우트에 위젯 배치
- 데이터 조회 API 연결

## 인수조건
- [ ] 대시보드 진입 시 KPI 위젯이 표시된다
- [ ] 데이터 로딩 / 에러 / 빈 상태가 모두 처리된다

## 참고
- 관련 파일: src/pages/Dashboard.vue
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

이대로 등록할까요? (수정사항이 있으면 알려주세요)
```

사용자가 수정 요청하면 반영 후 재확인. "그대로 해", "OK", "등록" 등의 승인 신호가 오면 다음 단계.

### 9. 이슈 등록

#### 필드 위치 — top-level vs `additional_fields`

`mcp__atlassian__createJiraIssue` 의 파라미터 배치를 혼동하지 않는다:

| 필드 | 위치 | 비고 |
|------|------|------|
| `cloudId`, `projectKey`, `issueTypeName`, `summary`, `description`, `contentFormat`, `parent`, `assignee_account_id`, `transition` | **top-level** | MCP 스키마의 직속 파라미터 |
| `labels`, `priority`, `duedate`, `customfield_*`, 그 외 모든 커스텀/시스템 필드 | **`additional_fields` 객체 내부** | 위 표에 없는 모든 것 |

> **`parent` 는 top-level**이다. Sub-task 의 부모 Story / Story 의 부모 Epic 모두 top-level `parent` 필드로 지정한다 (`additional_fields.parent` 가 아님).

#### 호출 예시

**일반 Story 등록:**
```
mcp__atlassian__createJiraIssue
  cloudId: <확정된 cloudId>
  projectKey: <확정된 prefix>
  issueTypeName: "Story"
  summary: <확정된 제목>
  description: <마크다운 본문>
  contentFormat: "markdown"
  additional_fields: {
    "labels": ["vue", "frontend", "feature"]
    // priority가 명시된 경우에만:
    // "priority": {"name": "High"}
  }
```

**기존 Epic 아래에 매다는 Story:**
```
mcp__atlassian__createJiraIssue
  cloudId: <확정된 cloudId>
  projectKey: "STD"
  issueTypeName: "Story"
  summary: "[Dashboard] KPI 위젯 추가"
  description: <마크다운 본문>
  contentFormat: "markdown"
  parent: "STD-300"          ← top-level
  additional_fields: {
    "labels": ["vue", "frontend", "feature"]
  }
```

**Sub-task 등록 (parent 는 부모 Story/Task):**
```
mcp__atlassian__createJiraIssue
  cloudId: <확정된 cloudId>
  projectKey: "STD"
  issueTypeName: "Sub-task"
  summary: "위젯 골격 + 스타일"
  description: <마크다운 본문>
  contentFormat: "markdown"
  parent: "STD-301"          ← top-level (부모 Story 키)
  additional_fields: {
    "labels": ["vue", "frontend"]
  }
```

> **company-managed(클래식) 프로젝트 예외**: 일부 클래식 프로젝트에서는 Epic↔Story 링크가 별도 커스텀 필드(흔히 `customfield_10014`, "Epic Link")로 동작할 수 있다. 그 경우 top-level `parent` 가 거부될 수 있으니, 실패 시 `getJiraIssueTypeMetaWithFields` 로 해당 issueType 의 필수 필드를 확인하고, `additional_fields: {"customfield_10014": "STD-300"}` 로 재시도. **메타가 알려준 필드만 사용** — 추측 금지.

> **마크다운 줄바꿈 주의**: description에 리터럴 `\n` 문자열을 넣지 말고 실제 개행문자를 사용한다. 목록은 `- ` 마크다운 문법.

### 10. 결과 출력

```
✅ 이슈 등록 완료
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔗 STD-247 — [Dashboard] KPI 위젯 추가
🏷️ 라벨: vue, frontend, feature
📂 타입: Story
🌐 https://<site>.atlassian.net/browse/STD-247
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

다음 단계: /jira-start STD-247
```

## 벌크 모드 (문서 → Epic → Issue → Subtask)

벌크 모드는 단계 수가 많고 트리 구성이 복잡하므로 별도 가이드로 분리했다.

**`references/bulk-document-flow.md` 를 읽고 그 절차를 따른다.**

핵심 원칙만 여기 요약:

1. **문서를 끝까지 읽는다** — 헤딩 구조와 주차/Phase/모듈 단위로 자연스러운 계층을 식별한다.
2. **기존 에픽을 먼저 검색한다** — `mcp__atlassian__searchJiraIssuesUsingJql` 로 `project = <KEY> AND issuetype = Epic AND text ~ "<핵심 키워드>"` 검색. 매치되면 신규 에픽을 만들지 않고 그 아래에 이슈를 매단다.
3. **트리 전체를 사용자에게 보여주고 일괄 승인** 받은 뒤에 등록을 시작한다 (개별 단계마다 묻지 않는다).
4. **등록 순서**: Epic → Story/Task → Sub-task. 각 단계의 키를 다음 단계의 `parent` 로 사용.
5. **설명은 적당히만 구체화** — `/jira-clarify`, `/jira-plan` 이 후속에서 채운다.

## Description 포맷 핵심 지침

(자세한 템플릿은 `references/description-templates.md`)

- **마크다운 사용**: `contentFormat: "markdown"`. ADF JSON 직접 작성 금지 (가독성/유지보수 손해).
- **체크박스 사용**: `- [ ]` 는 Jira 에디터에서 인터랙티브 체크박스로 렌더링되어 인수조건/DoD 추적에 유용.
- **헤딩 레벨**: H2(`##`)로 섹션, H3(`###`)로 하위 구분. H1은 제목과 중복되니 사용하지 않는다.
- **링크**: 마크다운 링크 `[텍스트](URL)` 그대로 동작. 이슈 키는 그냥 `STD-247` 로 적으면 자동 링크.
- **코드/명령**: 백틱 `` ` `` 또는 펜스 코드블록 ``` ``` ``` 사용.

## Error Handling

- **cloudId 못 찾음** → `mcp__atlassian__getAccessibleAtlassianResources` 결과를 보여주고 사용자에게 사이트 선택 요청
- **projectKey 모호 (감지 후보 여러 개)** → AskUserQuestion 으로 선택지 제시. 임의 선택 금지.
- **issueTypeName 메타에 없음** → 메타에서 받은 실제 이름 목록 보여주고 매핑 재시도. 흔한 변형: `Sub-task` vs `Subtask` vs `하위 작업`.
- **createJiraIssue 실패 (필수 필드 누락)** → `getJiraIssueTypeMetaWithFields` 로 해당 타입의 필수 필드 조회 후 사용자에게 보충 요청.
- **부모 에픽이 다른 프로젝트** → 같은 프로젝트로만 parent 가능. 사용자에게 알리고 확인.
- **벌크 모드 중간 실패** → 이미 만든 이슈 키 목록을 보여주고, 실패 지점부터 재개할지 / 롤백할지 사용자 결정.

## Notes

- **이슈 등록은 외부에 공개되고 되돌리기 어렵다.** 등록 직전 사용자 확인은 절대 생략하지 않는다.
- 벌크 모드에서 한 번 승인을 받았으면 매 이슈마다 다시 묻지 않는다 — 트리 전체를 한 번에 승인.
- 등록한 이슈에 대해 자동으로 `/jira-start`를 실행하지 않는다 — 다음 단계만 안내한다. 사용자가 여러 이슈를 만들고 그중 하나를 골라 시작하는 경우가 많다.
- 라벨은 케이스 통일이 중요하다. `Spring-Boot` 와 `spring-boot` 는 검색에서 분리된다. **항상 소문자 + kebab-case**.
- description은 라이트하게 — 후속 `/jira-clarify`, `/jira-plan` 이 채울 여지를 남긴다. 처음부터 5페이지짜리 설계 문서 만들지 않는다.
- 한국어 사용자가 영어 키워드("dashboard", "auth")로 입력해도 그대로 살린다. 강제로 한글로 번역하지 않는다 (코드/디렉토리명과 매칭이 깨짐).
