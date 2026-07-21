# Spring Boot 테스트 패턴

## 명령어

| 카테고리 | Gradle | Maven |
|----------|--------|-------|
| Lint | Checkstyle/PMD (설정 시) | Checkstyle/PMD (설정 시) |
| Test | `./gradlew test` (Windows: `gradlew.bat test`) | `mvn test` |
| Build | `./gradlew build -x test` (Windows: `gradlew.bat build -x test`) | `mvn package -DskipTests` |

## 테스트 구조 확인

```
src/test/java/           # 단위/통합 테스트
src/test/resources/      # 테스트 설정 (application-test.yml 등)
```

## 주의사항

- H2 인메모리 DB를 사용하는 테스트 환경이면 MySQL 모드 설정 확인
- `@SpringBootTest` 통합 테스트는 컨텍스트 로딩 시간이 길 수 있음
- 테스트 프로파일(`application-test.yml`)이 있는지 확인
- Gradle wrapper(`gradlew` / `gradlew.bat`)가 있으면 시스템 Gradle 대신 사용
