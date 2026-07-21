# 상시 블록 예시 — 프로젝트 NEVER 요약 (러너 step 세션 공통 주입)

> `phases/_always.md` 로 프로젝트 루트에 두면 harness-execute.py 가 모든 step 프롬프트 맨 앞에 주입한다.
> 목적: fresh 세션이 프로젝트의 **위반하기 쉬운 규칙만** 압축해 받는 것 (CLAUDE.md 전문 주입 금지 — 토큰 낭비).
> 아래는 형식 예시 — 프로젝트에 맞게 교체할 것.

## 불변식 (영구)

- 원격 push / merge 금지 — 러너 밖 인간 게이트.
- 컨트롤러 URL prefix 규약 (예: 프록시가 strip 하는 prefix 를 BE 에 중복 부착 금지).
- Write/Edit 전 Read 필수.

## 현행결정 (반전 = 신규 ADR + 오너 승인 필수)

- (예) 폐기된 엔티티/테이블 재도입 금지 — ADR-NNN.
- (예) NULL=전체 공통 시맨틱 축 — 조회는 `(id 일치 OR IS NULL)` 필수.

## 환경 함정

- (예) JAVA_HOME=<JDK 경로> 필수. gradle 데몬 ON (`--no-daemon` 금지 — Mockito 계열 깨짐).
- (예) dev 서버 가동 중 gradle test 금지 (클래스 삭제 레이스).
- (예) PowerShell 일괄치환 = 비ASCII 파손 — 텍스트 조작은 Node/Python(utf-8 명시).
- (예) DB 마이그레이션은 local 스키마만 — QA/prod 적용은 인간 수동 절차 (러너 FORBID).
