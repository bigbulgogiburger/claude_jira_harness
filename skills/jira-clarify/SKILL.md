---
name: jira-clarify
description: "jira-clarify — 대충 쓴 Jira 이슈를 구체화하고, 멀티 프로젝트 작업이면 하위 이슈를 자동 생성합니다. Jira 이슈 분석 시작 전, 요구사항이 불명확할 때, '이슈 정리해줘', '이슈 구체화', '요구사항 확인', 'AC 만들어줘', '하위 이슈 만들어줘', '서브태스크 생성', 'jira 정리' 등의 요청에 반드시 이 스킬을 사용하세요. /jira-start 이후, /jira-plan 이전에 사용합니다."
---

# jira-clarify — Jira 이슈 구체화 및 하위 이슈 생성

대충 쓰인 Jira 이슈를 분석하여 사용자와 Q&A를 진행하고, 이슈 설명을 보강한 뒤, 멀티 프로젝트 작업이면 하위 이슈를 자동 생성합니다.

지라에 댓글이나 설명을 작성할 때에는 한글로 작성합니다.

## Usage

```
/jira-clarify <ISSUE-KEY>
```

- `ISSUE-KEY`: Jira 이슈 키 (예: PROJ-156)

## 왜 이 단계가 필요한가

Jira 이슈는 현실적으로 "정산 분리 해주세요", "배송예정일 추가" 같은 한두 줄로 작성되는 경우가 많습니다. 이 상태에서 바로 plan을 세우면 잘못된 방향으로 개발하게 됩니다. 개발 전에 5분간 대화하는 것이 개발 후 2시간 삽질하는 것보다 훨씬 효율적입니다.

## Procedure

### 1. 딥 이슈 수집 (관련 이슈 크롤링)

단순히 해당 이슈만 보는 게 아니라, 주변 이슈까지 전부 긁어옵니다.

**1-1. 대상 이슈 조회**
```
mcp__atlassian__getJiraIssue → 이슈 상세 (제목, 설명, 댓글, 라벨, 컴포넌트)
```

**1-2. 관련 이슈 크롤링**

```
# 링크된 이슈 전부 조회
mcp__atlassian__getJiraIssueRemoteIssueLinks → 외부 링크
mcp__atlassian__searchJiraIssuesUsingJql
  → "issue in linkedIssues(<ISSUE-KEY>)" → 관련 이슈 댓글까지 조회

# 같은 Epic 하위 이슈
mcp__atlassian__searchJiraIssuesUsingJql
  → "parentEpic = <EPIC-KEY>" → 형제 이슈에서 맥락 수집

# 최근 관련 버그/요청
mcp__atlassian__searchJiraIssuesUsingJql
  → "project = <PROJECT> AND text ~ '<키워드>' AND created >= -30d"
```

수집 대상:
- 이슈 제목, 설명, 라벨, 컴포넌트
- **댓글 전체** — 최신 댓글에 추가 요구사항이 숨어있는 경우가 매우 많음
- 첨부파일 목록 (디자인 링크, 스크린샷 등)
- **링크된 이슈의 설명+댓글** — blocks, relates to 등
- 상위 Epic의 하위 이슈 목록 — 같은 기능의 다른 작업 맥락
- **최근 30일 내 같은 키워드의 버그/이슈** — 관련 버그 리포트 수집
- 기존 하위 이슈 (이미 있는지 확인)

수집한 정보에서 요구사항/제약사항/버그를 추출하여 정리합니다:

```
📡 이슈 수집 완료
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 대상: <ISSUE-KEY> — <제목>
📎 관련 이슈: <N>개 (링크 M개, Epic 형제 K개)
💬 댓글에서 발견한 추가 요구사항: <있음/없음>
🐛 관련 버그 리포트: <있으면 이슈 키 나열>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 2. 코드 심층 분석

#### 2-1. 스택 감지 및 CLAUDE.md 파악

작업 디렉토리에서 스택을 감지하고, CLAUDE.md에서 아키텍처/도메인/핵심 규칙을 파악합니다.

#### 2-2. 코드 의존성 그래프 추적

이슈 키워드로 관련 코드를 찾은 후, 단순 검색이 아닌 **호출 체인**을 추적합니다.

```
수정 대상 Entity/DTO 식별
  → 이 Entity를 사용하는 Repository 메서드 (Grep)
  → 이 Repository를 호출하는 Service 메서드 (Grep)
  → 이 Service를 호출하는 Controller (Grep)
  → 이 필드를 매핑하는 DTO (Grep)
  → 이 DTO를 사용하는 QueryDSL Projection (Grep)
```

**핵심: 같은 값을 계산하는 모든 위치를 찾는 것.**

예시 (실제 사례):
```
vendorCommissionTotal 계산 위치:
  1. OrderReport.updateFee()
  2. SettlementSnapshotService.createSettlementDetails()
  3. Settlement.recalculateFrom()
  4. SettlementQueryRepositoryImpl (list 집계)
  5. SettlementQueryRepositoryImpl (summary 집계)
→ 5곳 모두 동일한 공식이어야 함!
```

이 분석 결과를 Q&A에서 공유하여 사용자가 영향 범위를 정확히 파악할 수 있게 합니다.

#### 2-3. Feign/API 경계 자동 감지

코드에서 Feign Client 호출을 스캔하여, 이슈 작업이 외부 시스템에 걸치는지 자동으로 탐지합니다.

```bash
# Feign Client 인터페이스에서 관련 메서드 검색
Grep: "@FeignClient" → 클라이언트 목록
Grep: 이슈 키워드와 관련된 Feign 메서드
→ 해당 메서드를 호출하는 Service 추적
```

감지 결과 예시:
```
⚠️ 크로스 프로젝트 감지
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
이 기능은 다음 외부 호출을 포함합니다:

1. InternalCatalogClient.orderRegisterPost()
   order-service → catalog-service (POST /order-management/register/post)
   → 주문 완료등록 시 외부 판매자 요금 전달

2. InternalCatalogClient.getDeliveryPropose()
   order-service ← catalog-service (GET /internal/order-management/delivery-propose)
   → 배송예정 조회 시 응답 필드 추가 필요

→ catalog-service 수정이 필요합니다.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

#### 2-4. 과거 유사 이슈 참고

같은 프로젝트에서 비슷한 작업이 어떻게 진행됐는지 참고합니다.

```
mcp__atlassian__searchJiraIssuesUsingJql
  → "project = <PROJECT> AND status = Done AND text ~ '<핵심 키워드>' ORDER BY resolved DESC"
  → 최근 완료된 유사 이슈 3-5개 조회
```

유사 이슈에서 추출하는 정보:
- 작업 범위 (어떤 파일들을 수정했는지 — 커밋 메시지에서 유추)
- 하위 이슈 구성 (어떻게 분할했는지)
- 소요 시간 (있으면)
- 관련 댓글에서 발견된 패턴이나 주의사항

이를 Q&A에서 참고 정보로 공유:
```
📚 참고: 비슷한 작업 이력
- <DONE-KEY-1>: <제목> — 하위 이슈 3개로 분할, 2주 소요
- <DONE-KEY-2>: <제목> — order-service만 수정, 1주 소요
```

### 3. 스마트 Q&A 세션

수집한 정보와 코드 분석 결과를 기반으로, **구체적이고 맥락 있는 질문**을 합니다.

#### Q&A 원칙

좋은 Q&A는 "뭘 해야 하나요?"가 아니라 **"이렇게 이해했는데 맞나요?"** 형태입니다.

이슈와 코드를 이미 분석했기 때문에, 가설을 세우고 확인하는 방식으로 진행합니다. 사용자가 처음부터 설명할 필요가 없어야 합니다.

**나쁜 질문:**
- "이 이슈에서 뭘 해야 하나요?"
- "어떤 파일을 수정해야 하나요?"
- "프론트엔드 작업도 있나요?"

**좋은 질문:**
- "코드를 보니 `OrderReport`에 `vendorCommissionTotal` 필드가 있는데, 이번에 이 계산식이 `baseFee + handlingFee + commissionFee`로 바뀌어야 하는 게 맞나요?"
- "`InternalCatalogClient.getDeliveryPropose()`가 catalog-service을 호출하고 있어서, catalog-service에서도 `details`, `checks` 필드를 추가해야 합니다. 이것도 이 이슈 범위인가요, 아니면 별도 이슈로 따야 하나요?"
- "PROJ-157 댓글에 '수수료가 vendorCommissionTotal에 안 들어간다'는 버그가 있던데, 이번에 같이 수정하는 건가요?"

#### 질문 생성 프로세스

```
1. 이슈 설명에서 모호한 부분 식별
2. 코드 분석에서 발견한 기술적 판단점 정리
3. 관련 이슈/댓글에서 추가 요구사항 후보 정리
4. Feign 경계 분석에서 크로스 프로젝트 여부 확인
5. 과거 유사 이슈에서 범위 참고
→ 위 5가지를 종합하여 가설 기반 질문 3-5개 구성
```

#### 질문 카테고리

**A. 가설 검증** — "이렇게 이해했는데 맞나요?"
- 코드 분석 결과를 바탕으로 구체적 가설 제시
- "X Entity에 Y 필드를 추가하고, Z Service에서 계산하는 방식이 맞나요?"

**B. 의존성 그래프 공유** — "이만큼 영향받는데 전부 수정인가요?"
- 호출 체인 분석 결과를 보여주며 범위 확인
- "이 필드를 바꾸면 5곳에서 계산이 바뀌는데, 전부 수정 범위인가요?"

**C. 크로스 프로젝트 확인** — Feign 감지 결과 기반
- "이 API가 Feign으로 catalog-service을 호출하는데, 양쪽 다 수정이 필요합니다"
- "catalog-service 작업은 누가 하나요? 하위 이슈로 나눌까요?"

**D. 관련 이슈 통합** — 수집된 관련 이슈/버그 기반
- "PROJ-157에 관련 버그가 있는데, 이번에 같이 잡을까요?"
- "이 Epic의 다른 이슈에서 이미 X를 했는데, 여기서도 해야 하나요?"

**E. 인수조건 제안** — AC가 없을 때 가설로 제시
- "완료 기준을 이렇게 잡아도 될까요: 1) ... 2) ... 3) ..."

#### Q&A 진행 규칙

- **1라운드**: 분석 결과 요약 공유 + 가설 기반 질문 3-5개
- **2라운드 이후**: 사용자 답변에서 새 정보 반영 + 후속 질문 2-3개
- 사용자가 "됐어", "이 정도면 돼", "넘어가자" 등 종료 신호 → 즉시 다음 단계
- 3라운드 넘으면 "더 물어볼 게 있을까요?" 확인
- 코드에서 직접 확인할 수 있는 건 질문하지 않고 **직접 확인 후 결과만 공유**
- 사용자가 짧게 답하면 짧게, 상세하면 상세하게 — 응답 스타일 맞춤

### 4. 이슈 설명 보강

Q&A 결과를 반영하여 Jira 이슈를 업데이트합니다.

#### 4-1. 이슈 설명 덮어쓰기

`mcp__atlassian__editJiraIssue`의 `description` 필드로 설명을 **완전히 교체**합니다. 기존 설명은 버리고, Q&A에서 확정된 내용으로 새로 구성한 전체 텍스트를 `description`에 씁니다.

> **텍스트 포맷팅 주의**: Jira API에 보내는 텍스트에 리터럴 `\n` 문자열을 넣지 마라. 줄바꿈은 실제 개행문자를 사용하고, 목록은 `- ` 마크다운 문법을 사용한다.

작성 구조 (전체를 `description`에 덮어씀):

```
## 요구사항 (구체화됨)
<Q&A에서 확정된 요구사항>

## 인수조건 (Acceptance Criteria)
- [ ] AC1: <구체적 완료 기준>
- [ ] AC2: <구체적 완료 기준>
- [ ] AC3: <구체적 완료 기준>

## 영향 범위
- <프로젝트1>: <변경 내용 요약>
- <프로젝트2>: <변경 내용 요약>

## 의존성 그래프
<코드 분석에서 발견한 주요 호출 체인/계산 위치>

## 기술 메모
<Q&A에서 확인된 기술적 판단 사항>
<Feign 경계, 크로스 프로젝트 정보>
```

코멘트는 달지 않습니다. 구체화 내용은 설명에만 기록합니다.

### 5. 하위 이슈 생성 (멀티 프로젝트인 경우)

Q&A에서 여러 프로젝트/시스템에 걸친 작업으로 확인되면, 프로젝트별로 하위 이슈를 생성합니다.

#### 생성 기준

다음 중 하나라도 해당하면 하위 이슈를 생성합니다:
- 2개 이상의 프로젝트 수정 필요 (order-service + catalog-service, order-service + order-admin 등)
- Feign 경계 감지에서 양쪽 수정 필요로 확인
- 백엔드/프론트엔드 동시 작업 필요
- 다른 담당자에게 별도 작업 요청 필요

#### 생성 방법

`mcp__atlassian__createJiraIssue`로 하위 이슈를 생성합니다:

```json
{
  "projectKey": "<부모 이슈와 동일>",
  "issueType": "Sub-task",
  "parentKey": "<ISSUE-KEY>",
  "summary": "[<프로젝트명>] <작업 내용>",
  "description": "<해당 프로젝트에서 할 작업 상세>"
}
```

**하위 이슈 제목 패턴:**
- `[order-service] 정산 분리 — 외부 판매자 요금 필드 추가`
- `[catalog-service] 정산 분리 — 주문 완료등록 API 외부 판매자 요금 수신`
- `[order-admin] 정산 분리 — 외부 판매자 요금 컬럼 표시`

**하위 이슈 설명에 포함할 내용:**
- 해당 프로젝트에서의 구체적 작업 내용
- Feign 경계 분석에서 나온 API 경로 및 필드 정보
- 부모 이슈 참조
- 다른 하위 이슈와의 의존성 (있으면)
- 해당 프로젝트 관점의 인수조건

#### 이슈 링크 설정

하위 이슈 간 의존성이 있으면 `mcp__atlassian__createIssueLink`로 연결:
- order-service이 먼저 완료되어야 order-admin에서 API 호출 가능 → "blocks" 링크
- catalog-service이 Feign 수신 처리 완료해야 order-service에서 정상 동작 → "blocks" 링크

### 6. 결과 출력

```
📋 이슈 구체화 완료
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 이슈: <ISSUE-KEY> — <이슈 제목>

📡 수집 결과:
  관련 이슈: <N>개 크롤링
  관련 버그: <있으면 키 나열>
  과거 유사 이슈: <M>개 참고

🔍 코드 분석:
  영향 파일: <X>개
  호출 체인: <주요 의존성 요약>
  Feign 경계: <크로스 프로젝트 여부>

✅ 보강된 내용:
  인수조건: <N>개
  영향 범위: <프로젝트 목록>

📂 하위 이슈: (해당 시)
  <SUB-KEY-1>: [order-service] <작업 내용>
  <SUB-KEY-2>: [catalog-service] <작업 내용>
  <SUB-KEY-3>: [order-admin] <작업 내용>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

다음 단계: /jira-plan <ISSUE-KEY>
```

## Error Handling

- 이슈 미존재 → 오류 메시지
- 이슈가 이미 충분히 구체적 (AC 있고, 설명 상세) → "이슈가 이미 잘 정리되어 있어요. 바로 /jira-plan으로 넘어갈까요?" 확인
- 관련 이슈 크롤링에서 너무 많은 결과 (20개 초과) → 최근 10개만 사용, 나머지 스킵
- 하위 이슈 생성 실패 → 경고 후 수동 생성 안내
- MCP Atlassian 연결 실패 → 오프라인 모드로 Q&A만 진행, Jira 업데이트는 스킵

## Notes

- Q&A는 대화형이므로 사용자의 응답 스타일에 맞춤 (짧게 답하면 짧게, 상세하면 상세하게)
- 하위 이슈 생성 전에 반드시 사용자에게 확인 ("이렇게 하위 이슈를 만들까요?")
- 기존 이슈 설명은 버리고, Q&A로 확정된 내용으로 새로 구성한 텍스트로 description을 완전히 교체함 (append 금지, 코멘트 금지)
- `/jira-start`에서 이미 조회한 이슈 정보가 대화에 있으면 재조회하지 않고 활용
- 과거 유사 이슈 조회 시 해당 프로젝트의 JQL만 사용 (다른 프로젝트 혼입 방지)
