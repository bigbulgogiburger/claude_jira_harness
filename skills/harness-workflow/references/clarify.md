# clarify — 요구 명확화 보조 자료 (구 /jira-clarify 폐기, grill 로 대체)

> 2026-07-20 명령 표면 축소: 실무에서 요구 명확화는 **grill 문답**(`grilling` 스킬, 한 번에 한 질문 — 운영 실측)이 완전히 대체했다.
> 이 문서는 grill 진입 **전** 컨텍스트 수집에 쓰던 유용한 패턴만 보존한다.

## 1. 딥 이슈 수집 (grill 전 사전 조사)

```
mcp__atlassian__getJiraIssue                     # 대상 이슈 (설명+댓글 전체 — 최신 댓글에 추가 요구 빈발)
mcp__atlassian__searchJiraIssuesUsingJql
  "issue in linkedIssues(<KEY>)"                 # 링크 이슈의 설명+댓글
  "parentEpic = <EPIC>"                          # 형제 이슈 맥락
  "project = <P> AND text ~ '<키워드>' AND created >= -30d"   # 최근 관련 버그
  "project = <P> AND status = Done AND text ~ '<키워드>' ORDER BY resolved DESC"  # 과거 유사 이슈 3~5개
```

## 2. 코드 심층 분석

- 호출 체인 추적: Entity → Repository → Service → Controller → DTO → QueryDSL Projection. **같은 값을 계산하는 모든 위치**를 찾는 것이 핵심.
- Cross-project 경계 감지: `@FeignClient`/`RestTemplate|WebClient` (Spring), `axios\.|fetch\(|/api/` (FE), `*_BASE_URL` env.
- wiki(INDEX.md) 운용 프로젝트는 착수 전 cross-ref 조회를 ALWAYS 룰로 두는 것을 권장.

## 3. grill 질문 원칙

- "뭘 해야 하나요?" ❌ → **"이렇게 이해했는데 맞나요?"** (가설 검증형). 코드에서 확인 가능한 건 질문하지 말고 직접 확인 후 결과만 공유.
- 카테고리: 가설 검증 / 의존성 그래프 공유 / 크로스 프로젝트 / 관련 이슈 통합 / 인수조건 제안.
- **한 번에 한 질문** (묶음 금지). 종료 신호("됐어", "넘어가자") 시 즉시 다음 단계.

## 4. 확정 결과 반영

- grill 확정 결정은 dev-guide(plan 단계 산출물)에 기록하는 것이 기본. Jira description 교체가 필요하면 `editJiraIssue` (리터럴 `\n` 금지 — 실제 개행 사용).
- 멀티 프로젝트 작업 판명 시 하위 이슈 생성은 `createJiraIssue`(Sub-task) + `createIssueLink`(blocks) — 생성 전 사용자 확인 필수.
