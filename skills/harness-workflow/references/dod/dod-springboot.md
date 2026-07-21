# Spring Boot DoD (Definition of Done) 체크리스트

## 필수 검증 항목

### 코드 품질
- [ ] 컴파일 오류 없음 (`gradlew build -x test` 또는 `mvn compile`)
- [ ] 테스트 통과 (`gradlew test` 또는 `mvn test`)
- [ ] `System.out.println`, `e.printStackTrace()` 등 디버그 출력 없음
- [ ] SLF4J Logger 사용 (디버그 출력 대신)
- [ ] 하드코딩된 시크릿 없음

### 아키텍처
- [ ] Controller → Service → Repository 계층 구조 준수
- [ ] DTO/Entity 분리 (Entity를 직접 응답으로 반환하지 않음)
- [ ] 트랜잭션 범위 적절 (`@Transactional` 위치)
- [ ] 예외 처리 적절 (글로벌 핸들러 또는 서비스 레벨)

### 보안
- [ ] SQL Injection 방지 (JPA/MyBatis 파라미터 바인딩)
- [ ] 인증/인가 확인 (필요 시)
- [ ] 입력 검증 (`@Valid`, `@Validated`)

### 설정
- [ ] 환경별 설정 분리 (`application-{profile}.yml`)
- [ ] 새 설정 항목은 `application.yml`에 추가
